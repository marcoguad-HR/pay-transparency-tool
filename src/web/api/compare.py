"""
Compare API — Endpoint POST /api/compare per il confronto pari valore.
"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
import time
from src.analysis.equal_value_calculator import EqualValueCalculator, RoleScores
from src.utils.logger import get_logger
from src.utils.analytics import get_analytics

router = APIRouter()
logger = get_logger("web.api.compare")


@router.get("/api/compare/form", response_class=HTMLResponse)
async def compare_form(request: Request):
    """Restituisce il form vuoto (usato dal bottone 'Nuovo confronto')."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "partials/equal_value_form.html",
        {"request": request},
    )


@router.post("/api/compare", response_class=HTMLResponse)
async def compare(
    request: Request,
    role_a_name: str = Form(...),
    role_b_name: str = Form(...),
    # 16 fattori per ruolo A
    role_a_S1: int = Form(...), role_a_S2: int = Form(...),
    role_a_S3: int = Form(...), role_a_S4: int = Form(...),
    role_a_E1: int = Form(...), role_a_E2: int = Form(...),
    role_a_E3: int = Form(...), role_a_E4: int = Form(...),
    role_a_R1: int = Form(...), role_a_R2: int = Form(...),
    role_a_R3: int = Form(...), role_a_R4: int = Form(...),
    role_a_W1: int = Form(...), role_a_W2: int = Form(...),
    role_a_W3: int = Form(...), role_a_W4: int = Form(...),
    # 16 fattori per ruolo B
    role_b_S1: int = Form(...), role_b_S2: int = Form(...),
    role_b_S3: int = Form(...), role_b_S4: int = Form(...),
    role_b_E1: int = Form(...), role_b_E2: int = Form(...),
    role_b_E3: int = Form(...), role_b_E4: int = Form(...),
    role_b_R1: int = Form(...), role_b_R2: int = Form(...),
    role_b_R3: int = Form(...), role_b_R4: int = Form(...),
    role_b_W1: int = Form(...), role_b_W2: int = Form(...),
    role_b_W3: int = Form(...), role_b_W4: int = Form(...),
):
    """Confronta 2 ruoli e restituisce il risultato come HTML partial."""
    start_time = time.monotonic()
    templates = request.app.state.templates

    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    try:
        role_a = RoleScores(
            name=role_a_name,
            S1=role_a_S1, S2=role_a_S2, S3=role_a_S3, S4=role_a_S4,
            E1=role_a_E1, E2=role_a_E2, E3=role_a_E3, E4=role_a_E4,
            R1=role_a_R1, R2=role_a_R2, R3=role_a_R3, R4=role_a_R4,
            W1=role_a_W1, W2=role_a_W2, W3=role_a_W3, W4=role_a_W4,
        )
        role_b = RoleScores(
            name=role_b_name,
            S1=role_b_S1, S2=role_b_S2, S3=role_b_S3, S4=role_b_S4,
            E1=role_b_E1, E2=role_b_E2, E3=role_b_E3, E4=role_b_E4,
            R1=role_b_R1, R2=role_b_R2, R3=role_b_R3, R4=role_b_R4,
            W1=role_b_W1, W2=role_b_W2, W3=role_b_W3, W4=role_b_W4,
        )

        calculator = EqualValueCalculator()
        result = calculator.compare(role_a, role_b)

        response_html = templates.TemplateResponse(
            "partials/equal_value_result.html",
            {"request": request, "result": result},
        ).body.decode()

        # Analytics — log confronto riuscito
        get_analytics().log_query(
            query_text=f"Confronto pari valore: {role_a_name} vs {role_b_name}",
            response_text=f"Verdetto: {result.verdict_label} (diff: {result.difference_pct:.1f}%)",
            response_time_ms=int((time.monotonic() - start_time) * 1000),
            ip_address=client_ip,
            user_agent=user_agent,
            tool_used="equal_value",
        )

        return HTMLResponse(content=response_html)

    except ValueError as e:
        logger.warning(f"Validazione fallita: {e}")
        error_html = templates.TemplateResponse(
            "partials/chat_error.html",
            {"request": request, "error": str(e), "timestamp": ""},
        ).body.decode()
        get_analytics().log_query(
            query_text=f"Confronto pari valore: {role_a_name} vs {role_b_name}",
            response_time_ms=int((time.monotonic() - start_time) * 1000),
            ip_address=client_ip,
            user_agent=user_agent,
            tool_used="equal_value",
            error=f"validation: {e}",
        )
        return HTMLResponse(content=error_html, status_code=200)

    except Exception as e:
        logger.error(f"Errore nel confronto: {type(e).__name__}: {e}")
        error_html = templates.TemplateResponse(
            "partials/chat_error.html",
            {"request": request, "error": "Errore nel calcolo del confronto. Riprova.", "timestamp": ""},
        ).body.decode()
        get_analytics().log_query(
            query_text="Confronto pari valore: errore",
            response_time_ms=int((time.monotonic() - start_time) * 1000),
            ip_address=client_ip,
            user_agent=user_agent,
            tool_used="equal_value",
            error=f"{type(e).__name__}: {str(e)[:200]}",
        )
        return HTMLResponse(content=error_html, status_code=200)
