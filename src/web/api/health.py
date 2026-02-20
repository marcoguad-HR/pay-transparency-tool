"""
Health API — Endpoint GET /api/health per monitoring.

Restituisce JSON (non HTML) con lo stato dei componenti del sistema:
- api: sempre "ok" se l'endpoint risponde
- vectordb: verifica che la collection Qdrant esista
- llm_configured: verifica che la GROQ_API_KEY sia impostata

Utile per health check automatici, load balancer, o debug.
"""

import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.utils.logger import get_logger

logger = get_logger("web.api.health")

router = APIRouter()


@router.get("/api/health")
def health_check():
    """
    Health check del sistema.

    Restituisce JSON con lo stato di ogni componente.
    HTTP 200 se il sistema e' funzionante, 503 se qualcosa non va.
    """
    status = {
        "status": "ok",
        "components": {
            "api": "ok",
            "vectordb": _check_vectordb(),
            "llm_configured": _check_llm_key(),
        },
    }

    # Se qualche componente non e' "ok", lo stato generale diventa "degraded"
    component_values = list(status["components"].values())
    if any(v != "ok" for v in component_values):
        status["status"] = "degraded"

    http_status = 200 if status["status"] == "ok" else 503
    return JSONResponse(content=status, status_code=http_status)


def _check_vectordb() -> str:
    """
    Verifica che il vector database directory esista e contenga file.

    Usa un semplice controllo del filesystem anziche' creare un QdrantClient,
    che aprirebbe file lock esclusivi e causerebbe conflitti con il client
    gia' in uso dal retriever.
    """
    try:
        from pathlib import Path

        from src.utils.config import Config

        config = Config.get_instance()
        vs_config = config.vectorstore_config
        location = Path(vs_config.get("location", "./data/vectordb"))

        if location.exists() and any(location.iterdir()):
            return "ok"
        return "empty"

    except Exception as e:
        logger.warning(f"Health check vectordb fallito: {e}")
        return f"error: {e}"


def _check_llm_key() -> str:
    """Verifica che la chiave API Groq sia configurata."""
    key = os.getenv("GROQ_API_KEY", "")
    if key:
        return "ok"
    return "missing GROQ_API_KEY"
