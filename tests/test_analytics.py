"""
Test per src/utils/analytics.py — AnalyticsLogger e generate_report.py.

Copre:
- Creazione database e tabella
- Inserimento log (sincrono per testabilità)
- get_summary con dati di esempio
- Fallback silenzioso se il DB è inaccessibile
- Rilevamento "query senza risposta"
- Generazione report testuale
"""

import sqlite3
import threading
import time
from pathlib import Path

import pytest

from src.utils.analytics import AnalyticsLogger, _detect_unanswered, get_analytics


# =============================================================================
# FIXTURE
# =============================================================================

@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Restituisce un percorso temporaneo per il database di test."""
    return str(tmp_path / "test_analytics.db")


@pytest.fixture
def logger(db_path: str) -> AnalyticsLogger:
    """Crea un AnalyticsLogger su un DB temporaneo."""
    return AnalyticsLogger(db_path=db_path)


# =============================================================================
# TEST: CREAZIONE DATABASE E TABELLA
# =============================================================================

class TestDatabaseInit:
    """Verifica che il DB e la tabella vengano creati correttamente."""

    def test_db_file_created(self, db_path: str) -> None:
        """Il file SQLite viene creato all'init."""
        AnalyticsLogger(db_path=db_path)
        assert Path(db_path).exists()

    def test_table_exists(self, db_path: str) -> None:
        """La tabella query_logs esiste dopo l'init."""
        AnalyticsLogger(db_path=db_path)
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='query_logs'"
            ).fetchall()
        assert len(rows) == 1

    def test_table_has_correct_columns(self, db_path: str) -> None:
        """La tabella ha tutte le colonne attese."""
        expected = {
            "id", "timestamp", "query_text", "response_text",
            "confidence_score", "is_unanswered", "response_time_ms",
            "ip_address", "country_code", "user_agent", "tool_used", "error",
        }
        AnalyticsLogger(db_path=db_path)
        with sqlite3.connect(db_path) as conn:
            info = conn.execute("PRAGMA table_info(query_logs)").fetchall()
        columns = {row[1] for row in info}
        assert expected.issubset(columns)

    def test_directory_created_if_missing(self, tmp_path: Path) -> None:
        """Crea la directory del DB se non esiste."""
        nested_path = str(tmp_path / "nested" / "dir" / "analytics.db")
        AnalyticsLogger(db_path=nested_path)
        assert Path(nested_path).exists()

    def test_init_idempotent(self, db_path: str) -> None:
        """Creare due istanze sullo stesso DB non causa errori."""
        AnalyticsLogger(db_path=db_path)
        AnalyticsLogger(db_path=db_path)  # non deve sollevare
        assert Path(db_path).exists()


# =============================================================================
# TEST: INSERIMENTO LOG
# =============================================================================

class TestLogQuery:
    """Verifica l'inserimento dei record nel database."""

    def _flush(self, delay: float = 0.2) -> None:
        """Attende che i thread daemon completino l'insert."""
        time.sleep(delay)

    def test_basic_insert(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Un record viene inserito nel DB."""
        logger.log_query(query_text="Test query")
        self._flush()

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute("SELECT query_text FROM query_logs").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "Test query"

    def test_all_fields_stored(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Tutti i campi vengono salvati correttamente."""
        logger.log_query(
            query_text="Qual è la deadline?",
            response_text="La deadline è il 7 giugno 2026.",
            confidence_score=0.85,
            is_unanswered=False,
            response_time_ms=1200,
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
            tool_used="rag",
        )
        self._flush()

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM query_logs LIMIT 1").fetchone()

        assert row["query_text"] == "Qual è la deadline?"
        assert "La deadline" in row["response_text"]
        assert abs(row["confidence_score"] - 0.85) < 0.001
        assert row["is_unanswered"] == 0
        assert row["response_time_ms"] == 1200
        assert row["tool_used"] == "rag"

    def test_response_truncated_at_500(self, logger: AnalyticsLogger, db_path: str) -> None:
        """La risposta viene troncata a 500 caratteri."""
        long_response = "x" * 600
        logger.log_query(query_text="q", response_text=long_response)
        self._flush()

        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT response_text FROM query_logs").fetchone()
        assert len(row[0]) == 500
        assert row[0].endswith("...")

    def test_multiple_inserts(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Più query vengono inserite correttamente."""
        for i in range(5):
            logger.log_query(query_text=f"query {i}", tool_used="rag")
        self._flush(0.4)

        with sqlite3.connect(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM query_logs").fetchone()[0]
        assert count == 5

    def test_is_unanswered_auto_detected_low_confidence(
        self, logger: AnalyticsLogger, db_path: str
    ) -> None:
        """is_unanswered = 1 se confidence < 0.4 e non è fornito esplicitamente."""
        logger.log_query(query_text="domanda oscura", confidence_score=0.2)
        self._flush()

        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT is_unanswered FROM query_logs").fetchone()
        assert row[0] == 1

    def test_is_unanswered_auto_detected_by_phrase(
        self, logger: AnalyticsLogger, db_path: str
    ) -> None:
        """is_unanswered = 1 se la risposta contiene 'non ho trovato'."""
        logger.log_query(
            query_text="domanda",
            response_text="Non ho trovato informazioni sufficienti nel contesto.",
            confidence_score=0.9,
        )
        self._flush()

        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT is_unanswered FROM query_logs").fetchone()
        assert row[0] == 1

    def test_error_field_saved(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Il campo error viene salvato correttamente."""
        logger.log_query(query_text="q", error="TimeoutError: 90s")
        self._flush()

        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT error FROM query_logs").fetchone()
        assert row[0] == "TimeoutError: 90s"


# =============================================================================
# TEST: GET_SUMMARY
# =============================================================================

class TestGetSummary:
    """Verifica il calcolo delle metriche aggregate."""

    def _insert_direct(self, db_path: str, records: list[dict]) -> None:
        """Inserisce record direttamente nel DB (sincrono, per i test)."""
        with sqlite3.connect(db_path) as conn:
            for r in records:
                conn.execute(
                    """
                    INSERT INTO query_logs (
                        timestamp, query_text, response_text,
                        confidence_score, is_unanswered, response_time_ms,
                        ip_address, country_code, user_agent, tool_used, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r.get("timestamp", "2026-03-01T10:00:00+00:00"),
                        r.get("query_text", "test"),
                        r.get("response_text"),
                        r.get("confidence_score"),
                        r.get("is_unanswered", 0),
                        r.get("response_time_ms"),
                        r.get("ip_address"),
                        r.get("country_code", "IT"),
                        r.get("user_agent"),
                        r.get("tool_used", "rag"),
                        r.get("error"),
                    ),
                )
            conn.commit()

    def test_empty_db_returns_zero_total(self, logger: AnalyticsLogger) -> None:
        """Con DB vuoto, total_queries è 0."""
        summary = logger.get_summary(days=30)
        assert summary["total_queries"] == 0

    def test_total_queries(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Conta correttamente il totale delle query."""
        self._insert_direct(db_path, [
            {"query_text": "q1"},
            {"query_text": "q2"},
            {"query_text": "q3"},
        ])
        summary = logger.get_summary(days=30)
        assert summary["total_queries"] == 3

    def test_avg_response_time(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Calcola correttamente la media dei tempi di risposta."""
        self._insert_direct(db_path, [
            {"query_text": "q", "response_time_ms": 1000},
            {"query_text": "q", "response_time_ms": 2000},
        ])
        summary = logger.get_summary(days=30)
        assert summary["avg_response_time_ms"] == 1500.0

    def test_avg_confidence(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Calcola correttamente il confidence score medio."""
        self._insert_direct(db_path, [
            {"query_text": "q", "confidence_score": 0.8},
            {"query_text": "q", "confidence_score": 0.6},
        ])
        summary = logger.get_summary(days=30)
        assert abs(summary["avg_confidence"] - 0.7) < 0.01

    def test_unanswered_count(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Conta correttamente le query senza risposta."""
        self._insert_direct(db_path, [
            {"query_text": "q1", "is_unanswered": 0},
            {"query_text": "q2", "is_unanswered": 1},
            {"query_text": "q3", "is_unanswered": 1},
        ])
        summary = logger.get_summary(days=30)
        assert summary["unanswered_count"] == 2
        assert summary["unanswered_pct"] == pytest.approx(66.7, abs=0.1)

    def test_country_breakdown(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Raggruppa correttamente per paese."""
        self._insert_direct(db_path, [
            {"query_text": "q", "country_code": "IT"},
            {"query_text": "q", "country_code": "IT"},
            {"query_text": "q", "country_code": "DE"},
        ])
        summary = logger.get_summary(days=30)
        assert summary["country_breakdown"]["IT"] == 2
        assert summary["country_breakdown"]["DE"] == 1

    def test_tool_breakdown(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Raggruppa correttamente per tool."""
        self._insert_direct(db_path, [
            {"query_text": "q", "tool_used": "rag"},
            {"query_text": "q", "tool_used": "rag"},
            {"query_text": "q", "tool_used": "agent"},
        ])
        summary = logger.get_summary(days=30)
        assert summary["tool_breakdown"]["rag"] == 2
        assert summary["tool_breakdown"]["agent"] == 1

    def test_unanswered_top10(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Restituisce le top query senza risposta."""
        self._insert_direct(db_path, [
            {"query_text": "domanda senza risposta", "is_unanswered": 1},
            {"query_text": "altra domanda", "is_unanswered": 0},
        ])
        summary = logger.get_summary(days=30)
        assert len(summary["unanswered_top10"]) == 1
        assert summary["unanswered_top10"][0]["query"] == "domanda senza risposta"

    def test_period_filter(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Le query vecchie vengono escluse dal periodo."""
        self._insert_direct(db_path, [
            # Query di 100 giorni fa — deve essere esclusa
            {"query_text": "vecchia", "timestamp": "2025-11-01T10:00:00+00:00"},
            # Query recente — deve essere inclusa
            {"query_text": "recente", "timestamp": "2026-03-01T10:00:00+00:00"},
        ])
        summary = logger.get_summary(days=30)
        assert summary["total_queries"] == 1

    def test_error_count(self, logger: AnalyticsLogger, db_path: str) -> None:
        """Conta correttamente gli errori."""
        self._insert_direct(db_path, [
            {"query_text": "q", "error": "TimeoutError"},
            {"query_text": "q", "error": "TimeoutError"},
            {"query_text": "q", "error": None},
        ])
        summary = logger.get_summary(days=30)
        assert summary["error_count"] == 2


# =============================================================================
# TEST: FALLBACK SE DB INACCESSIBILE
# =============================================================================

class TestFallback:
    """Verifica che il logging non blocchi se il DB è inaccessibile."""

    def test_log_query_silently_fails_on_bad_path(self) -> None:
        """log_query non solleva eccezioni se il DB path non è valido."""
        # Usa un path impossibile (file come directory)
        bad_logger = AnalyticsLogger.__new__(AnalyticsLogger)
        bad_logger.db_path = Path("/dev/null/impossible.db")
        bad_logger._geo_cache = {}
        bad_logger._geo_lock = threading.Lock()

        # Non deve sollevare
        bad_logger.log_query(query_text="test")
        time.sleep(0.2)  # attendi thread

    def test_get_summary_returns_error_key_on_bad_db(self, tmp_path: Path) -> None:
        """get_summary restituisce {'error': ...} se il DB è inaccessibile."""
        bad_logger = AnalyticsLogger.__new__(AnalyticsLogger)
        bad_logger.db_path = Path("/dev/null/impossible.db")
        bad_logger._geo_cache = {}
        bad_logger._geo_lock = threading.Lock()

        result = bad_logger.get_summary(days=30)
        assert "error" in result


# =============================================================================
# TEST: _detect_unanswered
# =============================================================================

class TestDetectUnanswered:
    """Verifica la logica di rilevamento "senza risposta"."""

    def test_low_confidence_is_unanswered(self) -> None:
        assert _detect_unanswered(0.2, "qualunque risposta") is True

    def test_high_confidence_is_answered(self) -> None:
        assert _detect_unanswered(0.8, "risposta valida") is False

    def test_no_info_phrase_detected(self) -> None:
        assert _detect_unanswered(0.9, "Non ho trovato informazioni sufficienti") is True

    def test_phrase_case_insensitive(self) -> None:
        assert _detect_unanswered(0.9, "NON HO TROVATO INFORMAZIONI") is True

    def test_none_confidence_with_clean_answer(self) -> None:
        assert _detect_unanswered(None, "risposta normale") is False

    def test_none_confidence_with_no_info_phrase(self) -> None:
        assert _detect_unanswered(None, "non ho trovato dati") is True

    def test_boundary_confidence_040(self) -> None:
        """0.4 non è sotto soglia (< 0.4)."""
        assert _detect_unanswered(0.4, "risposta valida") is False

    def test_boundary_confidence_039(self) -> None:
        """0.39 è sotto soglia."""
        assert _detect_unanswered(0.39, "risposta valida") is True


# =============================================================================
# TEST: GENERATE REPORT
# =============================================================================

class TestGenerateReport:
    """Verifica la generazione del report testuale."""

    def _seed_db(self, db_path: str) -> None:
        """Popola il DB con dati fittizi per i test del report."""
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS query_logs ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "timestamp TEXT NOT NULL,"
                "query_text TEXT NOT NULL,"
                "response_text TEXT,"
                "confidence_score REAL,"
                "is_unanswered BOOLEAN DEFAULT 0,"
                "response_time_ms INTEGER,"
                "ip_address TEXT,"
                "country_code TEXT,"
                "user_agent TEXT,"
                "tool_used TEXT,"
                "error TEXT"
                ")"
            )
            records = [
                ("2026-03-01T10:00:00+00:00", "Qual è la deadline?", "La deadline è...", 0.85, 0, 900, "1.2.3.4", "IT", "Chrome", "rag", None),
                ("2026-03-01T11:00:00+00:00", "Cosa dice l'art. 7?", "L'art. 7 dice...", 0.75, 0, 1100, "1.2.3.5", "IT", "Firefox", "rag", None),
                ("2026-03-01T12:00:00+00:00", "Calcola il pay gap", "Gap: 7%", None, 0, 2500, "5.6.7.8", "DE", "Chrome", "agent", None),
                ("2026-03-01T13:00:00+00:00", "Domanda oscura", "Non ho trovato informazioni", 0.15, 1, 800, "9.10.11.12", "unknown", "Safari", "rag", None),
                ("2026-03-01T14:00:00+00:00", "Altra domanda", None, None, 0, None, None, None, None, "rag", "TimeoutError"),
            ]
            conn.executemany(
                "INSERT INTO query_logs (timestamp, query_text, response_text, confidence_score, is_unanswered, response_time_ms, ip_address, country_code, user_agent, tool_used, error) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                records,
            )
            conn.commit()

    def test_report_contains_header(self, tmp_path: Path) -> None:
        """Il report contiene l'intestazione."""
        from scripts.generate_report import generate_report
        db_path = str(tmp_path / "test.db")
        self._seed_db(db_path)
        report = generate_report(days=30, db_path=db_path)
        assert "PAY TRANSPARENCY TOOL" in report
        assert "REPORT UTILIZZO" in report

    def test_report_contains_total_queries(self, tmp_path: Path) -> None:
        """Il report mostra il numero totale di query."""
        from scripts.generate_report import generate_report
        db_path = str(tmp_path / "test.db")
        self._seed_db(db_path)
        report = generate_report(days=30, db_path=db_path)
        assert "5" in report  # 5 records inseriti

    def test_report_contains_tool_section(self, tmp_path: Path) -> None:
        """Il report contiene la sezione UTILIZZO TOOL."""
        from scripts.generate_report import generate_report
        db_path = str(tmp_path / "test.db")
        self._seed_db(db_path)
        report = generate_report(days=30, db_path=db_path)
        assert "UTILIZZO TOOL" in report
        assert "RAG" in report.upper() or "rag" in report.lower()

    def test_report_empty_db(self, tmp_path: Path) -> None:
        """Con DB vuoto, il report mostra un messaggio appropriato."""
        from scripts.generate_report import generate_report
        db_path = str(tmp_path / "empty.db")
        # Crea DB vuoto
        AnalyticsLogger(db_path=db_path)
        report = generate_report(days=30, db_path=db_path)
        assert "Nessuna query" in report

    def test_report_output_to_file(self, tmp_path: Path) -> None:
        """Il report viene salvato su file con --output."""
        import subprocess
        import sys
        db_path = str(tmp_path / "test.db")
        output_file = str(tmp_path / "report.txt")
        self._seed_db(db_path)
        result = subprocess.run(
            [sys.executable, "scripts/generate_report.py",
             "--days", "30", "--db", db_path, "--output", output_file],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert Path(output_file).exists()
        content = Path(output_file).read_text(encoding="utf-8")
        assert "PAY TRANSPARENCY TOOL" in content


# =============================================================================
# TEST: SINGLETON
# =============================================================================

class TestSingleton:
    """Verifica che get_analytics() restituisca sempre la stessa istanza."""

    def test_singleton_returns_same_instance(self) -> None:
        """Due chiamate a get_analytics() restituiscono lo stesso oggetto."""
        a = get_analytics()
        b = get_analytics()
        assert a is b

    def test_singleton_is_analytics_logger(self) -> None:
        """Il singleton è un'istanza di AnalyticsLogger."""
        assert isinstance(get_analytics(), AnalyticsLogger)
