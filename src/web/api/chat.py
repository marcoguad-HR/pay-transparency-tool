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
from src.utils.analytics import get_analytics
from src.utils.rate_limiter import RateLimitError

logger = get_logger("web.api.chat")

router = APIRouter()

# Lock per inizializzazione thread-safe del PayTransparencyRouter
_router_lock = threading.Lock()

# Keyword che indicano una richiesta di aiuto sull'uso del tool (onboarding).
# Queste query ricevono una risposta fissa (0 LLM calls) con istruzioni pratiche.
_HELP_KEYWORDS = {
    "come caricare", "come carico", "dove carico", "come si carica",
    "come si usa", "come funziona", "come uso", "come utilizzo",
    "caricare i dati", "caricare il file", "caricare un file",
    "caricare il csv", "caricare un csv",
    "in questo tool", "in questo sito", "su questo sito",
    "tool locale", "tool offline", "analisi locale",
    "dove trovo", "dove posso", "come faccio",
    "istruzioni", "guida", "tutorial", "aiuto",
    "upload", "caricamento",
}

_HELP_RESPONSE = """## Come usare il tool di analisi retributiva

Hai **due opzioni** per analizzare il gender pay gap della tua azienda:

### Opzione 1 — Analisi online (su questo sito)
1. Clicca sulla tab **"Analisi Dati"** in alto
2. Prepara un file CSV o Excel con almeno le colonne **gender** (M/F) e **base_salary** (lordo annuo)
3. Trascina il file nell'area di upload o clicca per selezionarlo
4. Il report appare in pochi secondi

### Opzione 2 — Analisi offline (nel tuo computer)
1. Clicca su **"Analisi nel tuo computer"** nella tab Analisi Dati per scaricare il tool locale
2. Apri il file HTML scaricato nel tuo browser
3. Carica il CSV — **nessun dato lascia il tuo computer**

### Come preparare il file
- **Colonne obbligatorie**: `gender` (M/F) e `base_salary` (numero, es. 45000)
- **Colonne consigliate**: `department` e `level` per l'analisi per categoria
- **Colonna opzionale**: `bonus` per il gap sulla retribuzione variabile
- Puoi scaricare un **template Excel** precompilato dalla tab Analisi Dati

### Formati supportati
- CSV (separatore virgola o punto e virgola)
- Excel (.xlsx, .xls)
- I dati individuali **non vengono mai inviati a servizi esterni**: l'analisi sul sito calcola solo aggregati, il tool locale funziona interamente nel browser.

📌 Hai domande sulla **Direttiva EU 2023/970**? Chiedimele qui — sono il chatbot normativo!"""


# Keyword che indicano una query sui dati retributivi (richiede l'agent completo).
# Se nessuna keyword matcha, la query viene gestita dal RAG diretto (1 LLM call).
_DATA_KEYWORDS = {
    "gap", "analisi dati", "retribuzion", "stipend", "salari",
    "bonus", "quartil", "csv", "excel", "dataset", "calcola",
    "dati retributiv", "pay gap", "gender gap",
}

# Keyword che indicano una query sulla normativa EU (direttiva, articoli, compliance).
# Se presenti insieme a _DATA_KEYWORDS, la query e' "ibrida" e richiede l'agent.
_NORMATIVE_KEYWORDS = {
    "direttiva", "articolo", "art.", "normativa",
    "obbligh", "scadenz", "trasposizione", "sanzioni",
    "conforme", "compliance", "legge", "decreto",
}

# Keyword che indicano una query sul pari valore / confronto ruoli.
# L'utente viene indirizzato al Comparatore con una risposta fissa (0 LLM calls).
_EQUAL_VALUE_KEYWORDS = {
    "pari valore", "equal value", "confronta ruoli", "confrontare ruoli",
    "confronto ruoli", "confronto tra ruoli", "stessa mansione",
    "lavoro di pari valore", "job evaluation", "valutazione ruoli",
    "comparare ruoli", "comparazione ruoli", "comparatore",
    "serw", "skills effort responsibility working",
}

_EQUAL_VALUE_RESPONSE = """## Confronto di pari valore tra ruoli

Per determinare se due ruoli sono di **"lavoro di pari valore"** ai sensi dell'**Art. 4(4)** della Direttiva EU 2023/970, puoi usare il nostro **Comparatore Pari Valore**.

Il Comparatore valuta i ruoli su **16 criteri oggettivi** raggruppati in 4 categorie (modello SERW):
- **Competenze** — istruzione, esperienza, conoscenze tecniche, capacita' interpersonali
- **Impegno** — fisico, mentale, emotivo, multi-tasking
- **Responsabilita'** — supervisione, impatto finanziario, benessere altrui, dati sensibili
- **Condizioni di lavoro** — ambiente fisico, stress, orari, trasferte

Puoi descrivere i ruoli a parole e l'AI suggerira' i punteggi, oppure compilarli manualmente.

**Clicca sulla tab "Comparatore" in alto per iniziare.**"""


def _is_equal_value_query(text: str) -> bool:
    """True se la query riguarda il pari valore / confronto ruoli."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in _EQUAL_VALUE_KEYWORDS)


def _needs_agent(text: str) -> bool:
    """True se la query richiede analisi dati (agent), False per normativa (RAG diretto)."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in _DATA_KEYWORDS)


def _is_help_query(text: str) -> bool:
    """True se la query chiede come usare il tool (onboarding/help).

    Queste query ricevono una risposta fissa con istruzioni pratiche (0 LLM calls).
    Ha priorità su tutti gli altri path di routing.
    """
    text_lower = text.lower()
    return any(kw in text_lower for kw in _HELP_KEYWORDS)


def _is_pure_data_query(text: str) -> bool:
    """True se la query e' pura analisi dati senza componente normativa.

    Queste query vengono gestite con un report template-based (zero LLM calls).
    Query ibride (dati + normativa) passano dall'agent.
    """
    text_lower = text.lower()
    has_data = any(kw in text_lower for kw in _DATA_KEYWORDS)
    has_normative = any(kw in text_lower for kw in _NORMATIVE_KEYWORDS)
    return has_data and not has_normative


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

    start_time = time.monotonic()
    user_agent = request.headers.get("user-agent", "")

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
        get_analytics().log_query(
            query_text=text,
            response_time_ms=0,
            ip_address=client_ip,
            user_agent=user_agent,
            tool_used="blocked",
            error="ip_rate_limit",
        )
        return HTMLResponse(content=user_bubble_html + error_html, status_code=200)

    # Bolla utente — la mostriamo sempre, anche se poi l'agent fallisce
    user_bubble_html = templates.TemplateResponse(
        "partials/chat_message.html",
        {"request": request, "role": "user", "text": text, "timestamp": timestamp},
    ).body.decode()

    # --- Help/onboarding path (zero LLM, risposta fissa) ---
    if _is_help_query(text):
        answer = _HELP_RESPONSE
        assistant_html = templates.TemplateResponse(
            "partials/chat_message.html",
            {"request": request, "role": "assistant", "text": answer, "timestamp": timestamp},
        ).body.decode()
        logger.info("Chat response: help/onboarding (0 LLM calls)")
        get_analytics().log_query(
            query_text=text,
            response_text=answer,
            response_time_ms=int((time.monotonic() - start_time) * 1000),
            ip_address=client_ip,
            user_agent=user_agent,
            tool_used="help",
        )
        return HTMLResponse(content=user_bubble_html + assistant_html)

    # --- Equal value path (zero LLM, risposta fissa con redirect al Comparatore) ---
    if _is_equal_value_query(text):
        answer = _EQUAL_VALUE_RESPONSE
        assistant_html = templates.TemplateResponse(
            "partials/chat_message.html",
            {"request": request, "role": "assistant", "text": answer, "timestamp": timestamp},
        ).body.decode()
        logger.info("Chat response: equal_value routing (0 LLM calls)")
        get_analytics().log_query(
            query_text=text,
            response_text=answer,
            response_time_ms=int((time.monotonic() - start_time) * 1000),
            ip_address=client_ip,
            user_agent=user_agent,
            tool_used="equal_value_routing",
        )
        return HTMLResponse(content=user_bubble_html + assistant_html)

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
        get_analytics().log_query(
            query_text=text,
            response_text=cached_answer,
            response_time_ms=int((time.monotonic() - start_time) * 1000),
            ip_address=client_ip,
            user_agent=user_agent,
            tool_used="cache",
        )
        return HTMLResponse(content=user_bubble_html + assistant_html)

    # Routing a 3 vie:
    # 1. Template path: query pure sui dati → report markdown (0 LLM calls, ~50ms)
    # 2. Agent path: query ibride (dati + normativa) → agent completo (3 LLM calls)
    # 3. RAG fast-path: query sulla normativa → RAG diretto (1 LLM call)
    # Timeout server 90s < timeout client HTMX 120s.
    is_pure_data = _is_pure_data_query(text)
    use_agent = _needs_agent(text) and not is_pure_data

    if is_pure_data:
        route_label = "Template path (zero LLM)"
    elif use_agent:
        route_label = "Agent path"
    else:
        route_label = "Fast-path RAG"
    logger.info(f"Routing: {route_label}")

    try:
        if is_pure_data:
            from src.analysis.data_loader import PayDataLoader
            from src.analysis.gap_calculator import GapCalculator
            from src.analysis.template_report import generate_markdown_report

            loader = PayDataLoader()
            load_result = loader.load("data/demo/demo_employees.csv")
            calculator = GapCalculator(load_result.df)
            compliance_result = calculator.full_analysis()
            answer = generate_markdown_report(compliance_result, load_result)

        elif use_agent:
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
        get_analytics().log_query(
            query_text=text,
            response_text=answer,
            response_time_ms=int((time.monotonic() - start_time) * 1000),
            ip_address=client_ip,
            user_agent=user_agent,
            tool_used="template" if is_pure_data else ("agent" if use_agent else "rag"),
        )
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
        get_analytics().log_query(
            query_text=text,
            response_time_ms=int((time.monotonic() - start_time) * 1000),
            ip_address=client_ip,
            user_agent=user_agent,
            tool_used="template" if is_pure_data else ("agent" if use_agent else "rag"),
            error="timeout_90s",
        )
        return HTMLResponse(content=user_bubble_html + error_html, status_code=200)

    except RateLimitError as e:
        logger.warning(f"Rate limit durante chat: {e}")
        error_html = templates.TemplateResponse(
            "partials/chat_error.html",
            {"request": request, "error": str(e), "timestamp": timestamp},
        ).body.decode()
        get_analytics().log_query(
            query_text=text,
            response_time_ms=int((time.monotonic() - start_time) * 1000),
            ip_address=client_ip,
            user_agent=user_agent,
            tool_used="template" if is_pure_data else ("agent" if use_agent else "rag"),
            error=f"groq_rate_limit: {e}",
        )
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
        get_analytics().log_query(
            query_text=text,
            response_time_ms=int((time.monotonic() - start_time) * 1000),
            ip_address=client_ip,
            user_agent=user_agent,
            tool_used="template" if is_pure_data else ("agent" if use_agent else "rag"),
            error=f"{type(e).__name__}: {str(e)[:200]}",
        )
        return HTMLResponse(content=user_bubble_html + error_html, status_code=200)
