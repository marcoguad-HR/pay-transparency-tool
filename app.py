"""
Pay Transparency Tool — FastAPI Entry Point.

Punto di ingresso per il frontend web. Configura:
- Jinja2 templates (per HTML partials HTMX)
- Static files (CSS, JS)
- Router per gli endpoint API (/api/chat, /api/upload, /api/health)

Avvio:
    uvicorn app:app --reload

Il server gira sulla root del progetto, quindi tutti gli import
come `from src.agent.router import ...` funzionano correttamente.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from src.web.api import chat, upload, health, cache_admin, downloads, compare, suggest_scores

# =============================================================================
# CONFIGURAZIONE APP
# =============================================================================

# --- Percorsi ---
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle. Crea directory e valida configurazione."""
    import logging
    import os

    TEMPLATES_DIR.mkdir(exist_ok=True)

    startup_logger = logging.getLogger("pay_transparency.startup")

    # --- Validazione GROQ_API_KEY ---
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        startup_logger.info("GROQ_API_KEY: configurata ✓")
    else:
        startup_logger.error(
            "GROQ_API_KEY: MANCANTE ✗ — le query AI falliranno. "
            "Imposta la variabile d'ambiente: export GROQ_API_KEY=<la_tua_chiave>"
        )

    # --- Validazione config.yaml ---
    config_path = BASE_DIR / "config.yaml"
    config_example = BASE_DIR / "config.yaml.example"
    if config_path.exists():
        startup_logger.info("config.yaml: trovato ✓")
    elif config_example.exists():
        startup_logger.warning(
            "config.yaml: non trovato, uso fallback config.yaml.example. "
            "Copia il file: cp config.yaml.example config.yaml"
        )
    else:
        startup_logger.error("config.yaml: non trovato e nessun fallback disponibile ✗")

    # --- Validazione vectordb ---
    vectordb_path = BASE_DIR / "data" / "vectordb"
    if vectordb_path.exists() and any(vectordb_path.iterdir()):
        startup_logger.info("vectordb: presente ✓")
    else:
        startup_logger.warning(
            "vectordb: non trovato o vuoto — il RAG non funzionerà. "
            "Esegui lo script di ingestion per costruire il database vettoriale."
        )

    yield


# CORS non e' configurato intenzionalmente: il frontend e' servito dalla
# stessa origine (Jinja2 templates), quindi non servono header CORS.
app = FastAPI(
    title="Pay Transparency Tool",
    description="EU Directive 2023/970 compliance tool — RAG + Pay Gap Analysis",
    version="0.1.0",
    lifespan=lifespan,
)


# --- Cache-control middleware ---
# Previene template stantii nel browser dopo deploy di fix frontend.
class NoCacheHTMLMiddleware(BaseHTTPMiddleware):
    """Set Cache-Control: no-cache on HTML responses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if "text/html" in response.headers.get("content-type", ""):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


app.add_middleware(NoCacheHTMLMiddleware)

# --- Templates Jinja2 ---
# Nota: la directory viene creata nel lifespan event, ma Jinja2Templates
# non richiede che esista al momento della creazione dell'oggetto —
# verifica l'esistenza solo al primo render.
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Aggiungi zip() ai globals Jinja2 (usato in equal_value_result.html)
templates.env.globals["zip"] = zip

# Salva templates in app.state cosi' tutti gli endpoint possono accedervi
app.state.templates = templates

# --- Static files ---
# Monta solo se la directory esiste (graceful per Task 2)
if STATIC_DIR.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# =============================================================================
# ROUTER
# =============================================================================

app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(health.router)
app.include_router(cache_admin.router)
app.include_router(downloads.router)
app.include_router(compare.router)
app.include_router(suggest_scores.router)


# =============================================================================
# ROOT — Pagina principale (placeholder fino a Task 2)
# =============================================================================

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """
    Pagina principale. Renderizza il template index.html se esiste,
    altrimenti restituisce un placeholder HTML minimale.
    """
    index_template = TEMPLATES_DIR / "index.html"
    if index_template.exists():
        return templates.TemplateResponse("index.html", {"request": request})

    # Placeholder fino a quando i template non vengono creati (Task 2)
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head><title>Pay Transparency Tool</title></head>
    <body>
        <h1>Pay Transparency Tool</h1>
        <p>Frontend in costruzione. API disponibili:</p>
        <ul>
            <li>POST /api/chat — Chat con l'agent (form data)</li>
            <li>POST /api/upload — Upload file CSV/Excel</li>
            <li>GET /api/health — Health check (JSON)</li>
            <li>GET /docs — Documentazione OpenAPI interattiva</li>
        </ul>
    </body>
    </html>
    """)
