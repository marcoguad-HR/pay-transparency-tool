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

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.web.api import chat, upload, health

# =============================================================================
# CONFIGURAZIONE APP
# =============================================================================

app = FastAPI(
    title="Pay Transparency Tool",
    description="EU Directive 2023/970 compliance tool — RAG + Pay Gap Analysis",
    version="0.1.0",
)

# --- Percorsi ---
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# --- Templates Jinja2 ---
# Crea la directory templates se non esiste (graceful per Task 2)
TEMPLATES_DIR.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

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
