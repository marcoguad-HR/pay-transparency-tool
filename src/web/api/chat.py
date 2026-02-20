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


def _get_router(app_state):
    """Lazy init thread-safe del PayTransparencyRouter (double-checked locking)."""
    if not hasattr(app_state, "agent_router"):
        with _router_lock:
            if not hasattr(app_state, "agent_router"):
                from src.agent.router import PayTransparencyRouter
                app_state.agent_router = PayTransparencyRouter()
    return app_state.agent_router


@router.post("/api/chat", response_class=HTMLResponse)
def chat(request: Request, text: str = Form(..., min_length=1)):
    """
    Endpoint chat per HTMX.

    Riceve la domanda come form data, chiama l'agent, e restituisce
    un frammento HTML con la bolla utente + la bolla risposta.

    In caso di errore (rate limit, eccezione generica), restituisce
    un frammento HTML con il messaggio di errore stilizzato.
    """
    timestamp = datetime.now().strftime("%H:%M")
    templates = request.app.state.templates

    logger.info(f"Chat request: '{text[:80]}...' " if len(text) > 80 else f"Chat request: '{text}'")

    # Bolla utente — la mostriamo sempre, anche se poi l'agent fallisce
    user_bubble_html = templates.TemplateResponse(
        "partials/chat_message.html",
        {"request": request, "role": "user", "text": text, "timestamp": timestamp},
    ).body.decode()

    # Chiama l'agent (lazy init thread-safe via _get_router)
    try:
        agent_router = _get_router(request.app.state)
        answer = agent_router.ask(text)

        assistant_html = templates.TemplateResponse(
            "partials/chat_message.html",
            {"request": request, "role": "assistant", "text": answer, "timestamp": timestamp},
        ).body.decode()

        logger.info("Chat response generata con successo")
        return HTMLResponse(content=user_bubble_html + assistant_html)

    except RateLimitError as e:
        logger.warning(f"Rate limit durante chat: {e}")
        error_html = templates.TemplateResponse(
            "partials/chat_error.html",
            {"request": request, "error": str(e), "timestamp": timestamp},
        ).body.decode()
        return HTMLResponse(content=user_bubble_html + error_html, status_code=429)

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
        return HTMLResponse(content=user_bubble_html + error_html, status_code=500)
