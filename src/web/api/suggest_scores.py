"""
Suggest Scores API — POST /api/suggest-scores
Analizza una Job Description con LLM e suggerisce i 16 punteggi SERW.
"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse
import json
import re
from src.utils.config import Config
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger("web.api.suggest_scores")

SUGGEST_SYSTEM_PROMPT = """Sei un esperto di job evaluation secondo i criteri SERW della Direttiva EU 2023/970.

Data la descrizione di un ruolo, assegna un punteggio da 1 a 5 per ciascuno dei 16 sotto-fattori:

SKILLS (Competenze):
- S1: Istruzione/qualifiche (1=nessun titolo, 5=post-laurea/certificazioni rare)
- S2: Esperienza (1=nessuna, 5=10+ anni in ruoli complessi)
- S3: Conoscenze tecniche (1=base, 5=expertise rara)
- S4: Capacità interpersonali (1=minime, 5=negoziazione avanzata/leadership)

EFFORT (Impegno):
- E1: Impegno fisico (1=sedentario, 5=lavoro fisico intenso)
- E2: Concentrazione mentale (1=routine, 5=problem-solving complesso costante)
- E3: Impegno emotivo (1=minimo contatto, 5=gestione crisi/traumi)
- E4: Multi-tasking/pressione tempi (1=ritmo calmo, 5=deadline costanti multiple)

RESPONSIBILITY (Responsabilità):
- R1: Supervisione persone (1=nessuna, 5=grandi team/struttura complessa)
- R2: Impatto finanziario (1=nessuno, 5=decisioni milionarie)
- R3: Benessere altrui (1=nessuno, 5=vita/salute persone)
- R4: Dati sensibili (1=nessuno, 5=dati strategici/personali critici)

WORKING CONDITIONS (Condizioni):
- W1: Ambiente fisico/rischi (1=ufficio, 5=ambiente pericoloso)
- W2: Stress psicologico (1=basso, 5=costante alto stress)
- W3: Orari disagiati (1=standard, 5=turni/notti/reperibilità)
- W4: Trasferte (1=nessuna, 5=trasferte frequenti/lunghe)

Rispondi SOLO con un JSON valido in questo formato esatto:
{"S1":3,"S2":2,"S3":4,"S4":3,"E1":1,"E2":4,"E3":3,"E4":3,"R1":2,"R2":3,"R3":1,"R4":2,"W1":1,"W2":3,"W3":1,"W4":2}"""

_EXPECTED_KEYS = {"S1", "S2", "S3", "S4", "E1", "E2", "E3", "E4",
                  "R1", "R2", "R3", "R4", "W1", "W2", "W3", "W4"}


@router.post("/api/suggest-scores")
async def suggest_scores(request: Request, description: str = Form(..., min_length=10)):
    """Analizza JD e suggerisce punteggi SERW via LLM."""
    import asyncio
    logger.info(f"Suggest scores request: '{description[:80]}...'")

    try:
        config = Config.get_instance()
        llm_config = config.llm_config

        from groq import Groq
        client = Groq(api_key=config.api_key)

        def _call_llm():
            response = client.chat.completions.create(
                model=llm_config.get("model", "llama-3.3-70b-versatile"),
                messages=[
                    {"role": "system", "content": SUGGEST_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Ruolo da valutare:\n{description}"},
                ],
                temperature=0.1,
                max_tokens=200,
            )
            return response.choices[0].message.content

        raw = await asyncio.wait_for(asyncio.to_thread(_call_llm), timeout=30.0)
        scores = parse_llm_scores(raw)

        return JSONResponse(content={"scores": scores})

    except ValueError as e:
        logger.warning(f"Parsing LLM fallito: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=422)
    except Exception as e:
        logger.error(f"Errore suggest_scores: {type(e).__name__}: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


def parse_llm_scores(raw: str) -> dict[str, int]:
    """Parsa l'output LLM e restituisce i 16 punteggi validati.

    Accetta JSON pulito o JSON embedded in testo/markdown.
    Raise ValueError se il parsing fallisce o i punteggi non sono validi.
    """
    # Cerca JSON nel testo (il LLM potrebbe aggiungere testo attorno)
    match = re.search(r'\{[^}]+\}', raw)
    if not match:
        raise ValueError(f"Nessun JSON trovato nell'output LLM: {raw[:200]}")

    try:
        data = json.loads(match.group())
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON non valido: {e}")

    missing = _EXPECTED_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Fattori mancanti: {missing}")

    scores = {}
    for key in _EXPECTED_KEYS:
        val = int(data[key])
        if not 1 <= val <= 5:
            raise ValueError(f"Punteggio {key}={val} fuori range 1-5")
        scores[key] = val

    return scores
