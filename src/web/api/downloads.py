"""
Downloads API — Endpoint per il download di risorse con tracking analytics.

Traccia i download del tool locale HTML e del template Excel,
registrando l'evento nel database analytics prima di servire il file.
"""

import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse

from src.utils.analytics import get_analytics
from src.utils.logger import get_logger

logger = get_logger("web.api.downloads")

router = APIRouter()

# Percorso base del progetto (2 livelli sopra src/web/api/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
STATIC_DIR = BASE_DIR / "static"


@router.get("/api/download-local-tool")
def download_local_tool(request: Request):
    """
    Serve il tool locale HTML con tracking del download.

    Logga il download in analytics con tool_used="download_local_tool",
    poi restituisce il file. Se il file non esiste ancora, restituisce
    una pagina informativa.
    """
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    # Log analytics (fire-and-forget)
    get_analytics().log_query(
        query_text="[DOWNLOAD] local-tool.html",
        response_time_ms=0,
        ip_address=client_ip,
        user_agent=user_agent,
        tool_used="download_local_tool",
    )

    logger.info(f"Download tool locale richiesto [{client_ip}]")

    file_path = STATIC_DIR / "local-tool.html"

    if file_path.exists():
        return FileResponse(
            path=str(file_path),
            filename="pay-transparency-locale.html",
            media_type="text/html",
        )

    # Il file non esiste ancora — pagina informativa
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html lang="it">
        <head>
            <meta charset="UTF-8">
            <title>Tool Locale — In arrivo</title>
            <style>
                body { font-family: system-ui, sans-serif; max-width: 600px;
                       margin: 80px auto; padding: 0 20px; color: #374151; }
                h1 { color: #111827; }
                a { color: #2563EB; }
                .box { background: #F0FDF4; border: 1px solid #BBF7D0;
                       border-radius: 12px; padding: 24px; margin-top: 24px; }
            </style>
        </head>
        <body>
            <h1>Tool Locale di Analisi Pay Gap</h1>
            <div class="box">
                <p><strong>Questa funzionalita' e' in fase di sviluppo.</strong></p>
                <p>Presto potrai scaricare un file HTML che analizza il gender pay gap
                   direttamente nel tuo browser, senza inviare dati a nessun server.</p>
                <p>Nel frattempo puoi usare la
                   <a href="/">sezione Analisi Dati</a> del portale.</p>
            </div>
        </body>
        </html>
        """,
        status_code=200,
    )
