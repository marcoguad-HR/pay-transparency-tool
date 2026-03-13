"""
Chat API — Endpoint POST /api/chat per il frontend HTMX.

Riceve la domanda dell'utente come form data (non JSON, perche' HTMX
invia form-encoded), la passa al PayTransparencyRouter, e restituisce
un frammento HTML con le bolle messaggio (user + assistant).

L'HTML parziale viene inserito nella pagina dal frontend tramite hx-swap.

Concetti usati:
- Form(...)  : parsing di dati form-encoded (application/x-www-form-urlencoded)
- HTMLResponse: risposta con Content-Type text/html
- Jinja2Templates: rendering di template HTML con variabili

Ottimizzazioni attive:
- ResponseCache: risposta in-memoria (exact + similarity), TTL 24h, LRU 500
- IP Rate Limiter: 15 req/min per IP con burst 5 (sliding window)
"""

import asyncio
import collections
import threading
import time
from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from src.utils.cache import get_cache
from src.utils.logger import get_logger
from src.utils.rate_limiter import RateLimitError

logger = get_logger("web.api.chat")

router = APIRouter()

# Lock per inizializzazione thread-safe del PayTransparencyRouter
_router_lock = threading.Lock()

# Keyword che indicano una query sui dati retributivi (richiede l'agent completo).
# Se nessuna keyword matcha, la query viene gestita dal RAG diretto (1 LLM call).
_DATA_KEYWORDS = {
    "gap", "analisi dati", "retribuzion", "stipend", "salari",
    "bonus", "quartil", "csv", "excel", "dataset", "calcola",
    "dati retributiv", "pay gap", "gender gap",
}


def _needs_agent(text: str) -> bool:
    """True se la query richiede analisi dati (agent), False per normativa (RAG diretto)."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in _DATA_KEYWORDS)


# ===========================================================================
# Rate Limiter per IP — sliding window 15 req/min, burst 5
# ===========================================================================

_IP_RATE_LIMIT = 15          # max richieste per minuto per IP
_IP_BURST_SIZE = 5           # max richieste in raffica (<1s)
_IP_WINDOW_SECONDS = 60      # finestra sliding window

# dict IP → deque di timestamp delle ultime richieste
_ip_timestamps: dict[str, collections.deque] = {}
_ip_lock = threading.Lock()


def _check_ip_rate_limit(ip: str) -> bool:
    """
    Controlla se l'IP ha superato il rate limit (sliding window).

    Returns:
        True se la richiesta è permessa, False se va bloccata con 429.
    """
    now = time.time()
    with _ip_lock:
        if ip not in _ip_timestamps:
            _ip_timestamps[ip] = collections.deque()

        dq = _ip_timestamps[ip]

        # Rimuovi i timestamp fuori dalla finestra
        while dq and now - dq[0] > _IP_WINDOW_SECONDS:
            dq.popleft()

        # Burst check: max _IP_BURST_SIZE richieste nell'ultimo secondo
        burst_count = sum(1 for ts in dq if now - ts < 1.0)
        if burst_count >= _IP_BURST_SIZE:
            logger.warning(f"IP rate limit BURST: {ip} ({burst_count} req nell'ultimo secondo)")
            return False

        # Window check: max _IP_RATE_LIMIT richieste nell'ultimo minuto
        if len(dq) >= _IP_RATE_LIMIT:
            logger.warning(f"IP rate limit WINDOW: {ip} ({len(dq)} req nell'ultimo minuto)")
            return False

        dq.append(now)
        return True


# ===========================================================================
# Endpoint /api/chat
# ===========================================================================

@router.post("/api/chat", response_class=HTMLResponse)
async def chat(request: Request, text: str = Form(..., min_length=1)):
    """
    Endpoint chat per HTMX.

    Flusso:
    1. Check rate limit per IP → errore se superato
    2. Check cache (exact + similarity) → risposta istantanea se HIT
    3. RAG / Agent (solo su MISS) → salva in cache
    4. Risposta HTML con bolla utente + bolla assistant

    In caso di errore (rate limit, eccezione generica), restituisce
    un frammento HTML con il messaggio di errore stilizzato.

    L'endpoint e' async: la chiamata all'agent (sincrona e pesante)
    gira in un thread separato via asyncio.to_thread, cosi' uvicorn
    non blocca l'event loop e puo' gestire altre richieste.
    """
    timestamp = datetime.now().strftime("%H:%M")
    templates = request.app.state.templates

    # Estrai IP (considera X-Forwarded-For per proxy/Caddy)
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown"

    logger.info(f"Chat request [{client_ip}]: '{text[:80]}'" if len(text) > 80 else f"Chat request [{client_ip}]: '{text}'")

    # --- Rate limit per IP ---
    if not _check_ip_rate_limit(client_ip):
        user_bubble_html = templates.TemplateResponse(
            "partials/chat_message.html",
            {"request": request, "role": "user", "text": text, "timestamp": timestamp},
        ).body.decode()
        error_html = templates.TemplateResponse(
            "partials/chat_error.html",
            {
                "request": request,
                "error": "Troppe richieste. Attendi qualche secondo prima di inviare un altro messaggio.",
                "timestamp": timestamp,
            },
        ).body.decode()
        return HTMLResponse(content=user_bubble_html + error_html, status_code=200)

    # Bolla utente — la mostriamo sempre, anche se poi l'agent fallisce
    user_bubble_html = templates.TemplateResponse(
        "partials/chat_message.html",
        {"request": request, "role": "user", "text": text, "timestamp": timestamp},
    ).body.decode()

    # --- Check cache ---
    cache = get_cache()
    cached_answer = cache.get(text)
    if cached_answer is not None:
        assistant_html = templates.TemplateResponse(
            "partials/chat_message.html",
            {
                "request": request,
                "role": "assistant",
                "text": cached_answer,
                "timestamp": timestamp,
            },
        ).body.decode()
        logger.info("Chat response servita da cache (0 Groq calls)")
        return HTMLResponse(content=user_bubble_html + assistant_html)

    # Fast-path: query sulla normativa → RAG diretto (1 LLM call).
    # Agent path: query sui dati retributivi → agent completo (3 LLM calls).
    # Timeout server 90s < timeout client HTMX 120s.
    use_agent = _needs_agent(text)
    logger.info(f"Routing: {'Agent path' if use_agent else 'Fast-path RAG'}")

    try:
        if use_agent:
            from src.agent.router import PayTransparencyRouter
            agent_router = PayTransparencyRouter()
            answer = await asyncio.wait_for(
                asyncio.to_thread(agent_router.ask, text),
                timeout=90.0,
            )
        else:
            from src.agent.router import _get_generator
            gen = _get_generator()
            answer = await asyncio.wait_for(
                asyncio.to_thread(lambda: gen.generate(text, verify=False).answer),
                timeout=90.0,
            )

        # --- Salva in cache (solo risposte valide, non errori) ---
        cache.set(text, answer)

        assistant_html = templates.TemplateResponse(
            "partials/chat_message.html",
            {"request": request, "role": "assistant", "text": answer, "timestamp": timestamp},
        ).body.decode()

        logger.info("Chat response generata con successo (salvata in cache)")
        return HTMLResponse(content=user_bubble_html + assistant_html)

    except asyncio.TimeoutError:
        logger.warning(f"Chat request timed out after 90s: '{text[:80]}'")
        error_html = templates.TemplateResponse(
            "partials/chat_error.html",
            {
                "request": request,
                "error": "La richiesta ha impiegato troppo tempo. Il servizio potrebbe essere sovraccarico. Riprova tra qualche istante.",
                "timestamp": timestamp,
            },
        ).body.decode()
        # HTMX ignora 5xx by default. Usiamo 200 per renderizzare l'errore nella chat.
        return HTMLResponse(content=user_bubble_html + error_html, status_code=200)

    except RateLimitError as e:
        logger.warning(f"Rate limit durante chat: {e}")
        error_html = templates.TemplateResponse(
            "partials/chat_error.html",
            {"request": request, "error": str(e), "timestamp": timestamp},
        ).body.decode()
        return HTMLResponse(content=user_bubble_html + error_html, status_code=200)

    except Exception as e:
        logger.error(f"Errore durante chat: {type(e).__name__}: {e}", exc_info=True)

        error_str = str(e).lower()
        error_type = type(e).__name__.lower()

        if "auth" in error_type or "auth" in error_str or "api key" in error_str or "invalid_api_key" in error_str:
            user_msg = "Il servizio AI non è configurato correttamente (chiave API mancante o non valida). Contatta l'amministratore del sistema."
        elif "connection" in error_type or "connect" in error_str or "network" in error_str or "unreachable" in error_str:
            user_msg = "Impossibile raggiungere il servizio AI. Verifica la connessione di rete e riprova."
        elif "quota" in error_str or "rate" in error_str or "limit" in error_str:
            user_msg = "Limite di richieste raggiunto. Attendi qualche minuto e riprova."
        else:
            user_msg = "Si è verificato un errore interno. Riprova tra qualche istante."

        error_html = templates.TemplateResponse(
            "partials/chat_error.html",
            {
                "request": request,
                "error": user_msg,
                "timestamp": timestamp,
            },
        ).body.decode()
        return HTMLResponse(content=user_bubble_html + error_html, status_code=200)
