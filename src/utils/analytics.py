"""
Analytics Logger — Sistema di logging e reportistica per Pay Transparency Tool.

Registra ogni query ricevuta in un database SQLite locale, inclusi:
- Testo della domanda e della risposta
- Confidence score e flag "senza risposta"
- Tempo di risposta, IP, paese, user agent
- Tool usato (rag / agent / analyze_pay_gap)

Design:
- Fire-and-forget: il logging avviene in un thread daemon separato,
  così non blocca mai la risposta HTTP all'utente.
- Geo-IP cache: i risultati di ip-api.com vengono cachati in memoria
  per evitare chiamate ripetute per lo stesso IP.
- Zero dipendenze aggiuntive: usa solo sqlite3 e urllib (built-in).
"""

import sqlite3
import threading
import urllib.request
import urllib.error
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("utils.analytics")

# Schema della tabella di log
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS query_logs (
    id                INTEGER  PRIMARY KEY AUTOINCREMENT,
    timestamp         TEXT     NOT NULL,
    query_text        TEXT     NOT NULL,
    response_text     TEXT,
    confidence_score  REAL,
    is_unanswered     BOOLEAN  DEFAULT 0,
    response_time_ms  INTEGER,
    ip_address        TEXT,
    country_code      TEXT,
    user_agent        TEXT,
    tool_used         TEXT,
    error             TEXT
);
"""

# Frasi che indicano che il RAG non ha trovato informazioni
_NO_ANSWER_PHRASES = [
    "non ho trovato informazioni",
    "informazioni sufficienti",
    "non sono in grado",
    "non ho trovato",
    "not found",
    "insufficient information",
    "non posso rispondere",
    "dati non disponibili",
]

# IP privati e localhost — non geolocalizzabili
_PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "::1", "localhost")


class AnalyticsLogger:
    """
    Logger anonimo per le query ricevute dal tool.

    Ogni query viene salvata in SQLite in modo asincrono (fire-and-forget).
    Se il DB è inaccessibile, il fallimento viene loggato ma non rilancia
    eccezioni: il comportamento del sistema non deve cambiare.

    Uso:
        logger = AnalyticsLogger()
        logger.log_query(
            query_text="Qual è la deadline?",
            response_text="La deadline è...",
            confidence_score=0.85,
            response_time_ms=1200,
            ip_address="1.2.3.4",
            tool_used="rag",
        )
        summary = logger.get_summary(days=7)
    """

    def __init__(self, db_path: str = "./data/analytics.db") -> None:
        """
        Inizializza il logger e crea il database/tabella se non esistono.

        Args:
            db_path: percorso del file SQLite (verrà creata la directory se mancante)
        """
        self.db_path = Path(db_path)
        # Cache {ip: country_code} — rimane in memoria per tutta la vita del processo
        self._geo_cache: dict[str, str] = {}
        self._geo_lock = threading.Lock()
        self._init_db()

    # -------------------------------------------------------------------------
    # SETUP
    # -------------------------------------------------------------------------

    def _init_db(self) -> None:
        """Crea directory, database e tabella se non esistono."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.execute(_CREATE_TABLE_SQL)
                conn.commit()
            logger.info(f"Analytics DB pronto: {self.db_path}")
        except Exception as e:
            logger.warning(f"Analytics DB init fallita (il logging sarà disabilitato): {e}")

    def _connect(self) -> sqlite3.Connection:
        """
        Apre una nuova connessione SQLite.

        Ogni thread deve usare la propria connessione per evitare
        problemi di thread-safety con SQLite.
        """
        return sqlite3.connect(str(self.db_path), timeout=5.0)

    # -------------------------------------------------------------------------
    # GEOLOCALIZZAZIONE IP
    # -------------------------------------------------------------------------

    def _get_country(self, ip: str | None) -> str:
        """
        Restituisce il codice paese a 2 lettere per un IP (es. "IT", "DE").

        - IP locali/privati → "local"
        - Cache hit → risposta immediata
        - ip-api.com → query HTTP con timeout 3s
        - Fallback → "unknown"

        Args:
            ip: indirizzo IP dell'utente (può essere None)

        Returns:
            Codice paese ISO 3166-1 alpha-2 o "local" / "unknown"
        """
        if not ip:
            return "unknown"

        # IP privati e localhost
        if any(ip.startswith(prefix) for prefix in _PRIVATE_PREFIXES):
            return "local"

        # Cache hit (thread-safe)
        with self._geo_lock:
            if ip in self._geo_cache:
                return self._geo_cache[ip]

        # Chiamata al servizio gratuito ip-api.com (no API key, max 1000 req/min)
        country = "unknown"
        try:
            url = f"http://ip-api.com/json/{ip}?fields=countryCode,status"
            req = urllib.request.Request(url, headers={"User-Agent": "pay-transparency-tool/0.1"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                if data.get("status") == "success":
                    country = data.get("countryCode", "unknown")
        except Exception:
            # Fallback silenzioso: timeout, rete assente, ecc.
            pass

        with self._geo_lock:
            self._geo_cache[ip] = country

        return country

    # -------------------------------------------------------------------------
    # LOGGING (fire-and-forget)
    # -------------------------------------------------------------------------

    def log_query(
        self,
        query_text: str,
        response_text: str | None = None,
        confidence_score: float | None = None,
        is_unanswered: bool | None = None,
        response_time_ms: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        tool_used: str | None = None,
        error: str | None = None,
    ) -> None:
        """
        Salva un record di query nel database in modo asincrono (fire-and-forget).

        Il metodo ritorna immediatamente: l'insert avviene in un thread daemon
        separato. Se il thread fallisce, l'errore viene loggato ma non propagato.

        Args:
            query_text: testo della domanda dell'utente
            response_text: risposta del tool (verrà troncata a 500 char)
            confidence_score: score 0.0-1.0 (None se non disponibile)
            is_unanswered: override manuale; se None viene calcolato automaticamente
            response_time_ms: tempo di risposta in millisecondi
            ip_address: IP dell'utente (verrà geolocalizzato)
            user_agent: header User-Agent
            tool_used: "rag", "agent" o "analyze_pay_gap"
            error: messaggio di errore se la richiesta è fallita
        """
        # Determina is_unanswered se non fornito esplicitamente
        if is_unanswered is None:
            is_unanswered = _detect_unanswered(confidence_score, response_text)

        # Tronca la risposta per non gonfiare il DB
        if response_text and len(response_text) > 500:
            response_text = response_text[:497] + "..."

        timestamp = datetime.now(timezone.utc).isoformat()

        def _insert() -> None:
            """Eseguito in thread daemon separato."""
            try:
                # Geolocalizzazione (con timeout 3s built-in)
                country_code = self._get_country(ip_address)

                with self._connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO query_logs (
                            timestamp, query_text, response_text,
                            confidence_score, is_unanswered, response_time_ms,
                            ip_address, country_code, user_agent, tool_used, error
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            timestamp,
                            query_text,
                            response_text,
                            confidence_score,
                            int(is_unanswered),
                            response_time_ms,
                            ip_address,
                            country_code,
                            user_agent,
                            tool_used,
                            error,
                        ),
                    )
                    conn.commit()
            except Exception as exc:
                logger.warning(f"Analytics insert fallita: {exc}")

        thread = threading.Thread(target=_insert, daemon=True, name="analytics-insert")
        thread.start()

    # -------------------------------------------------------------------------
    # REPORTISTICA
    # -------------------------------------------------------------------------

    def get_summary(self, days: int = 30) -> dict[str, Any]:
        """
        Restituisce metriche aggregate degli ultimi N giorni.

        Args:
            days: periodo di analisi in giorni (default: 30)

        Returns:
            dict con le seguenti chiavi:
            - period_days: int
            - since: str (ISO 8601)
            - total_queries: int
            - avg_queries_per_day: float
            - avg_response_time_ms: float | None
            - avg_confidence: float | None
            - unanswered_count: int
            - unanswered_pct: float
            - unanswered_top10: list[dict] — top 10 query senza risposta
            - country_breakdown: dict[str, int]
            - tool_breakdown: dict[str, int]
            - daily_trend: dict[str, int] — ultimi 7 giorni
            - error_count: int
            - top_errors: list[str]
        """
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                return _build_summary(conn, since, days)
        except Exception as e:
            logger.warning(f"get_summary fallita: {e}")
            return {"error": str(e)}


# =============================================================================
# FUNZIONI HELPER (private al modulo)
# =============================================================================

def _detect_unanswered(confidence: float | None, response: str | None) -> bool:
    """
    Determina se una risposta è da considerarsi "senza risposta".

    Una query è senza risposta se:
    - confidence_score < 0.4, OPPURE
    - la risposta contiene frasi tipiche di "non so"
    """
    if confidence is not None and confidence < 0.4:
        return True

    if response:
        response_lower = response.lower()
        if any(phrase in response_lower for phrase in _NO_ANSWER_PHRASES):
            return True

    return False


def _build_summary(conn: sqlite3.Connection, since: str, days: int) -> dict[str, Any]:
    """Costruisce il dizionario di riepilogo leggendo dal DB."""

    # --- Metriche generali ---
    row = conn.execute(
        """
        SELECT
            COUNT(*)                        AS total,
            AVG(response_time_ms)           AS avg_ms,
            AVG(confidence_score)           AS avg_conf,
            SUM(is_unanswered)              AS unanswered,
            SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) AS errors
        FROM query_logs
        WHERE timestamp >= ?
        """,
        (since,),
    ).fetchone()

    total = row["total"] or 0
    unanswered = int(row["unanswered"] or 0)
    unanswered_pct = round(unanswered / total * 100, 1) if total > 0 else 0.0

    # --- Top 10 query senza risposta ---
    unanswered_rows = conn.execute(
        """
        SELECT query_text, confidence_score
        FROM query_logs
        WHERE timestamp >= ? AND is_unanswered = 1
        ORDER BY timestamp DESC
        LIMIT 10
        """,
        (since,),
    ).fetchall()

    # --- Breakdown per paese ---
    country_rows = conn.execute(
        """
        SELECT country_code, COUNT(*) AS cnt
        FROM query_logs
        WHERE timestamp >= ?
        GROUP BY country_code
        ORDER BY cnt DESC
        """,
        (since,),
    ).fetchall()

    # --- Breakdown per tool ---
    tool_rows = conn.execute(
        """
        SELECT COALESCE(tool_used, 'unknown') AS tool, COUNT(*) AS cnt
        FROM query_logs
        WHERE timestamp >= ?
        GROUP BY tool_used
        ORDER BY cnt DESC
        """,
        (since,),
    ).fetchall()

    # --- Trend ultimi 7 giorni ---
    seven_days_ago = (
        datetime.now(timezone.utc) - timedelta(days=7)
    ).isoformat()
    trend_rows = conn.execute(
        """
        SELECT SUBSTR(timestamp, 1, 10) AS day, COUNT(*) AS cnt
        FROM query_logs
        WHERE timestamp >= ?
        GROUP BY day
        ORDER BY day
        """,
        (seven_days_ago,),
    ).fetchall()

    # --- Top errori ---
    error_rows = conn.execute(
        """
        SELECT error, COUNT(*) AS cnt
        FROM query_logs
        WHERE timestamp >= ? AND error IS NOT NULL
        GROUP BY error
        ORDER BY cnt DESC
        LIMIT 5
        """,
        (since,),
    ).fetchall()

    return {
        "period_days": days,
        "since": since,
        "total_queries": total,
        "avg_queries_per_day": round(total / days, 1) if days > 0 else 0.0,
        "avg_response_time_ms": round(row["avg_ms"], 0) if row["avg_ms"] else None,
        "avg_confidence": round(row["avg_conf"], 3) if row["avg_conf"] else None,
        "unanswered_count": unanswered,
        "unanswered_pct": unanswered_pct,
        "unanswered_top10": [
            {"query": r["query_text"], "confidence": r["confidence_score"]}
            for r in unanswered_rows
        ],
        "country_breakdown": {r["country_code"]: r["cnt"] for r in country_rows},
        "tool_breakdown": {r["tool"]: r["cnt"] for r in tool_rows},
        "daily_trend": {r["day"]: r["cnt"] for r in trend_rows},
        "error_count": int(row["errors"] or 0),
        "top_errors": [r["error"] for r in error_rows],
    }


# =============================================================================
# SINGLETON — un'unica istanza condivisa da tutti gli endpoint
# =============================================================================

_analytics_instance: AnalyticsLogger | None = None
_analytics_lock = threading.Lock()


def get_analytics() -> AnalyticsLogger:
    """
    Restituisce l'istanza singleton di AnalyticsLogger (thread-safe).

    Lazy-init: viene creato al primo accesso.
    """
    global _analytics_instance
    if _analytics_instance is None:
        with _analytics_lock:
            if _analytics_instance is None:
                _analytics_instance = AnalyticsLogger()
    return _analytics_instance
