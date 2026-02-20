"""
Pydantic Schemas — Modelli di validazione per le API web.

Definisce i modelli di request/response usati dagli endpoint FastAPI.
Pydantic valida automaticamente i dati in ingresso e serializza quelli in uscita.

Nota: gli endpoint HTMX restituiscono HTML (non JSON), quindi questi schema
servono principalmente per validazione interna e documentazione OpenAPI.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request per l'endpoint POST /api/chat."""
    text: str = Field(..., min_length=1, description="Domanda dell'utente")


class ChatResponse(BaseModel):
    """Response dall'endpoint POST /api/chat (usato per documentazione OpenAPI)."""
    role: str = Field(..., description="Ruolo del messaggio: 'user' o 'assistant'")
    text: str = Field(..., description="Contenuto del messaggio")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%H:%M"),
        description="Timestamp del messaggio (HH:MM)",
    )
