"""
Upload API — Endpoint POST /api/upload per caricamento file CSV/Excel.

Riceve un file dal form HTMX, lo salva temporaneamente in /tmp,
esegue il caricamento dati + analisi pay gap, e restituisce un
frammento HTML con i risultati della compliance.

Solo file CSV e Excel (.csv, .xlsx, .xls) sono accettati.
"""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse

from src.utils.logger import get_logger

logger = get_logger("web.api.upload")

router = APIRouter()

# Estensioni file accettate
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# Limite dimensione file: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/api/upload", response_class=HTMLResponse)
def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Endpoint upload per HTMX.

    Riceve un file CSV/Excel, esegue l'analisi gender pay gap completa,
    e restituisce un frammento HTML con i risultati.

    Validazioni:
    - Il file deve avere estensione .csv, .xlsx o .xls
    - Il file deve essere leggibile da PayDataLoader (colonne obbligatorie, ecc.)
    """
    templates = request.app.state.templates

    # --- Validazione estensione ---
    filename = file.filename or "unknown"
    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        logger.warning(f"Upload rifiutato: estensione '{suffix}' non supportata ({filename})")
        error_html = templates.TemplateResponse(
            "partials/upload_error.html",
            {
                "request": request,
                "error": (
                    f"Formato file non supportato: '{suffix}'. "
                    f"Carica un file .csv, .xlsx o .xls."
                ),
            },
        ).body.decode()
        return HTMLResponse(content=error_html, status_code=422)

    # --- Salva il file in /tmp ---
    tmp_path = None
    try:
        # Leggi il contenuto e verifica la dimensione
        content = file.file.read()

        if len(content) > MAX_FILE_SIZE:
            logger.warning(
                f"Upload rifiutato: file '{filename}' troppo grande "
                f"({len(content)} bytes, limite {MAX_FILE_SIZE} bytes)"
            )
            error_html = templates.TemplateResponse(
                "partials/upload_error.html",
                {
                    "request": request,
                    "error": (
                        f"File troppo grande ({len(content) // (1024 * 1024)} MB). "
                        f"Il limite massimo e' {MAX_FILE_SIZE // (1024 * 1024)} MB."
                    ),
                },
            ).body.decode()
            return HTMLResponse(content=error_html, status_code=422)

        # Crea un file temporaneo con la stessa estensione
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, prefix="paytool_"
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        logger.info(f"File salvato in {tmp_path} ({len(content)} bytes)")

        # --- Carica e analizza ---
        from src.analysis.data_loader import PayDataLoader, DataLoadError, DataValidationError
        from src.analysis.gap_calculator import GapCalculator

        loader = PayDataLoader()
        load_result = loader.load(tmp_path)

        calculator = GapCalculator(load_result.df)
        compliance_result = calculator.full_analysis()

        logger.info(
            f"Analisi completata per '{filename}': "
            f"{load_result.n_employees} dipendenti, "
            f"compliant={compliance_result.is_compliant}"
        )

        # --- Renderizza il risultato HTML ---
        result_html = templates.TemplateResponse(
            "partials/upload_result.html",
            {
                "request": request,
                "filename": filename,
                "load_result": load_result,
                "result": compliance_result,
                "warnings": load_result.warnings,
            },
        ).body.decode()
        return HTMLResponse(content=result_html)

    except (DataLoadError, DataValidationError) as e:
        logger.warning(f"Errore dati nel file '{filename}': {e}")
        error_html = templates.TemplateResponse(
            "partials/upload_error.html",
            {"request": request, "error": str(e)},
        ).body.decode()
        return HTMLResponse(content=error_html, status_code=422)

    except Exception as e:
        logger.error(f"Errore durante upload/analisi di '{filename}': {e}", exc_info=True)
        error_html = templates.TemplateResponse(
            "partials/upload_error.html",
            {
                "request": request,
                "error": "Si e' verificato un errore durante l'analisi. Verifica il formato del file.",
            },
        ).body.decode()
        return HTMLResponse(content=error_html, status_code=500)

    finally:
        # Pulizia file temporaneo
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
            logger.info(f"File temporaneo rimosso: {tmp_path}")
