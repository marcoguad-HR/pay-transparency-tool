"""
Test per analytics degli upload CSV e download del tool locale.

Copre:
- Upload CSV: log analytics su successo, errore dati, estensione non supportata
- Download tool locale: log analytics, risposta corretta con/senza file
"""

import io
import sqlite3
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.utils.analytics import AnalyticsLogger


# =============================================================================
# FIXTURE
# =============================================================================

@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Percorso temporaneo per il database analytics di test."""
    return str(tmp_path / "test_analytics.db")


@pytest.fixture
def analytics(db_path: str) -> AnalyticsLogger:
    """AnalyticsLogger su DB temporaneo."""
    return AnalyticsLogger(db_path=db_path)


@pytest.fixture
def app_client(analytics):
    """TestClient FastAPI con analytics mockato."""
    from fastapi.testclient import TestClient
    from app import app

    # Patch get_analytics per usare il nostro DB di test
    with patch("src.web.api.upload.get_analytics", return_value=analytics), \
         patch("src.web.api.downloads.get_analytics", return_value=analytics):
        yield TestClient(app), analytics


def _wait_for_analytics(analytics: AnalyticsLogger, expected_count: int, timeout: float = 2.0):
    """Attende che il thread fire-and-forget di analytics completi l'insert."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with analytics._connect() as conn:
                count = conn.execute("SELECT COUNT(*) FROM query_logs").fetchone()[0]
                if count >= expected_count:
                    return count
        except Exception:
            pass
        time.sleep(0.05)
    return 0


# =============================================================================
# TEST: UPLOAD ANALYTICS
# =============================================================================

class TestUploadAnalytics:
    """Verifica che gli upload vengano tracciati in analytics."""

    def test_upload_estensione_non_supportata_logga_errore(self, app_client):
        """Upload con estensione .txt deve loggare errore in analytics."""
        client, analytics = app_client

        fake_file = io.BytesIO(b"test content")
        response = client.post(
            "/api/upload",
            files={"file": ("test.txt", fake_file, "text/plain")},
        )

        assert response.status_code == 422
        count = _wait_for_analytics(analytics, 1)
        assert count == 1

        with analytics._connect() as conn:
            row = conn.execute(
                "SELECT query_text, tool_used, error FROM query_logs"
            ).fetchone()
            assert row[0] == "[UPLOAD] test.txt"
            assert row[1] == "upload"
            assert "estensione_non_supportata" in row[2]

    def test_upload_csv_valido_logga_successo(self, app_client):
        """Upload CSV valido deve loggare successo con dati di compliance."""
        client, analytics = app_client

        csv_content = "gender,base_salary\nM,50000\nF,45000\nM,55000\nF,48000\n"
        fake_file = io.BytesIO(csv_content.encode("utf-8"))
        response = client.post(
            "/api/upload",
            files={"file": ("dati.csv", fake_file, "text/csv")},
        )

        assert response.status_code == 200
        count = _wait_for_analytics(analytics, 1)
        assert count == 1

        with analytics._connect() as conn:
            row = conn.execute(
                "SELECT query_text, tool_used, response_text, error FROM query_logs"
            ).fetchone()
            assert row[0] == "[UPLOAD] dati.csv"
            assert row[1] == "upload"
            assert "dipendenti=" in row[2]
            assert "compliant=" in row[2]
            assert "gap_medio=" in row[2]
            assert row[3] is None  # nessun errore

    def test_upload_csv_non_valido_logga_errore_dati(self, app_client):
        """Upload CSV con colonne mancanti deve loggare errore dati."""
        client, analytics = app_client

        csv_content = "nome,cognome\nMario,Rossi\n"
        fake_file = io.BytesIO(csv_content.encode("utf-8"))
        response = client.post(
            "/api/upload",
            files={"file": ("bad.csv", fake_file, "text/csv")},
        )

        assert response.status_code == 422
        count = _wait_for_analytics(analytics, 1)
        assert count == 1

        with analytics._connect() as conn:
            row = conn.execute(
                "SELECT query_text, tool_used, error FROM query_logs"
            ).fetchone()
            assert row[0] == "[UPLOAD] bad.csv"
            assert row[1] == "upload"
            assert "dati_non_validi" in row[2]


# =============================================================================
# TEST: DOWNLOAD TOOL LOCALE
# =============================================================================

class TestDownloadLocalToolAnalytics:
    """Verifica che i download del tool locale vengano tracciati."""

    def test_download_logga_in_analytics(self, app_client):
        """Il download del tool locale deve creare un record analytics."""
        client, analytics = app_client

        response = client.get("/api/download-local-tool")

        # Il file non esiste ancora, ma il log deve comunque avvenire
        assert response.status_code == 200
        count = _wait_for_analytics(analytics, 1)
        assert count == 1

        with analytics._connect() as conn:
            row = conn.execute(
                "SELECT query_text, tool_used, error FROM query_logs"
            ).fetchone()
            assert row[0] == "[DOWNLOAD] local-tool.html"
            assert row[1] == "download_local_tool"
            assert row[2] is None  # nessun errore

    def test_download_senza_file_mostra_coming_soon(self, app_client, tmp_path):
        """Se il file HTML non esiste, mostra pagina informativa."""
        client, analytics = app_client

        # Punta STATIC_DIR a una directory vuota cosi' il file non viene trovato
        with patch("src.web.api.downloads.STATIC_DIR", tmp_path):
            response = client.get("/api/download-local-tool")

        assert response.status_code == 200
        assert "in fase di sviluppo" in response.text

    def test_download_con_file_serve_il_file(self, app_client, tmp_path):
        """Se il file HTML esiste, lo serve come download."""
        client, analytics = app_client

        # Crea un file finto nella directory static
        with patch("src.web.api.downloads.STATIC_DIR", tmp_path):
            tool_file = tmp_path / "local-tool.html"
            tool_file.write_text("<html><body>Tool locale</body></html>")

            response = client.get("/api/download-local-tool")

        assert response.status_code == 200
        assert "Tool locale" in response.text
