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
"""

import asyncio
import threading
from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

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


@router.post("/api/chat", response_class=HTMLResponse)
async def chat(request: Request, text: str = Form(..., min_length=1)):
    """
    Endpoint chat per HTMX.

    Riceve la domanda come form data, chiama l'agent, e restituisce
    un frammento HTML con la bolla utente + la bolla risposta.

    In caso di errore (rate limit, eccezione generica), restituisce
    un frammento HTML con il messaggio di errore stilizzato.

    L'endpoint e' async: la chiamata all'agent (sincrona e pesante)
    gira in un thread separato via asyncio.to_thread, cosi' uvicorn
    non blocca l'event loop e puo' gestire altre richieste.
    """
    timestamp = datetime.now().strftime("%H:%M")
    templates = request.app.state.templates

    logger.info(f"Chat request: '{text[:80]}...' " if len(text) > 80 else f"Chat request: '{text}'")

    # Bolla utente — la mostriamo sempre, anche se poi l'agent fallisce
    user_bubble_html = templates.TemplateResponse(
        "partials/chat_message.html",
        {"request": request, "role": "user", "text": text, "timestamp": timestamp},
    ).body.decode()

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

        assistant_html = templates.TemplateResponse(
            "partials/chat_message.html",
            {"request": request, "role": "assistant", "text": answer, "timestamp": timestamp},
        ).body.decode()

        logger.info("Chat response generata con successo")
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
        logger.error(f"Errore durante chat: {e}", exc_info=True)
        error_html = templates.TemplateResponse(
            "partials/chat_error.html",
            {
                "request": request,
                "error": "Si e' verificato un errore interno. Riprova tra qualche istante.",
                "timestamp": timestamp,
            },
        ).body.decode()
        return HTMLResponse(content=user_bubble_html + error_html, status_code=200)
