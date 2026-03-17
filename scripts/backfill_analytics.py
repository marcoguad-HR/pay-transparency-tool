#!/usr/bin/env python3
"""
Backfill Analytics — Recupera query storiche dai log di sistema e le inserisce
nel database analytics.

Legge righe di log nel formato:
    <timestamp> ... Chat request [<ip>]: '<query_text>'

e le inserisce in data/analytics.db con tool_used='backfill'.

Uso:
    # Da file di log esportato:
    python scripts/backfill_analytics.py --file /tmp/paytool_logs.txt

    # Da stdin (pipe da journalctl):
    journalctl -u paytool --since "2026-03-12" --until "2026-03-18" --no-pager | \
        python scripts/backfill_analytics.py --stdin

    # Dry run (mostra cosa verrebbe inserito, senza toccare il DB):
    python scripts/backfill_analytics.py --file logs.txt --dry-run

    # Con geolocalizzazione IP (piu' lento, chiama ip-api.com):
    python scripts/backfill_analytics.py --file logs.txt --geolocate
"""

import argparse
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import json
from datetime import datetime, timezone
from pathlib import Path

# Permette di eseguire lo script dalla root del progetto
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

DB_PATH = project_root / "data" / "analytics.db"

# Regex per estrarre i campi dal log.
# Formato journald: "Mar 12 14:23:45 hostname python[1234]: Chat request [1.2.3.4]: 'query text'"
# Formato logger:   "2026-03-12 14:23:45 ... Chat request [1.2.3.4]: 'query text'"
_LOG_PATTERN = re.compile(
    r"Chat request \[(?P<ip>[^\]]+)\]: '(?P<query>.+?)(?:')?$"
)

# Pattern per timestamp journald: "Mar 12 14:23:45"
_JOURNALD_TS = re.compile(
    r"^(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})"
)

# Pattern per timestamp ISO-like: "2026-03-12 14:23:45" o "2026-03-12T14:23:45"
_ISO_TS = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})[T ](?P<time>\d{2}:\d{2}:\d{2})"
)

_MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _parse_timestamp(line: str, year: int = 2026) -> str | None:
    """Estrae un timestamp ISO 8601 dalla riga di log."""
    # Prova formato ISO
    m = _ISO_TS.search(line)
    if m:
        return f"{m.group('date')}T{m.group('time')}+00:00"

    # Prova formato journald (senza anno)
    m = _JOURNALD_TS.match(line)
    if m:
        month = _MONTH_MAP.get(m.group("month"))
        if month:
            day = int(m.group("day"))
            return f"{year}-{month:02d}-{day:02d}T{m.group('time')}+00:00"

    return None


def _geolocate_ip(ip: str, cache: dict) -> str:
    """Geolocalizza un IP usando ip-api.com (con cache in memoria)."""
    if ip in cache:
        return cache[ip]

    if ip in ("unknown", "127.0.0.1", "::1", "localhost") or ip.startswith("192.168.") or ip.startswith("10."):
        cache[ip] = "local"
        return "local"

    try:
        url = f"http://ip-api.com/json/{ip}?fields=countryCode"
        req = urllib.request.Request(url, headers={"User-Agent": "backfill-script/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            country = data.get("countryCode", "unknown")
    except Exception:
        country = "unknown"

    cache[ip] = country
    # Rate limit ip-api.com: max 45 req/min free tier
    time.sleep(1.5)
    return country


def parse_logs(lines: list[str], year: int = 2026) -> list[dict]:
    """Parsa le righe di log e restituisce una lista di record."""
    records = []
    for line in lines:
        m = _LOG_PATTERN.search(line)
        if not m:
            continue

        ts = _parse_timestamp(line, year=year)
        if not ts:
            ts = datetime.now(timezone.utc).isoformat()

        query = m.group("query")
        ip = m.group("ip")

        # Salta query di test
        if query.lower().strip() in ("test", "test analytics", "ping"):
            continue

        records.append({
            "timestamp": ts,
            "query_text": query,
            "ip_address": ip,
            "tool_used": "backfill",
        })

    return records


def insert_records(
    records: list[dict],
    db_path: Path = DB_PATH,
    geolocate: bool = False,
    dry_run: bool = False,
) -> int:
    """Inserisce i record nel database analytics."""
    if dry_run:
        for r in records:
            print(f"  [{r['timestamp'][:19]}] [{r['ip_address']}] {r['query_text'][:70]}")
        return len(records)

    geo_cache: dict = {}
    conn = sqlite3.connect(str(db_path))

    # Recupera query gia' presenti per evitare duplicati
    existing = set()
    try:
        rows = conn.execute("SELECT timestamp, query_text FROM query_logs").fetchall()
        for ts, qt in rows:
            existing.add((ts, qt))
    except sqlite3.OperationalError:
        pass  # Tabella non esiste ancora

    inserted = 0
    skipped = 0
    for r in records:
        key = (r["timestamp"], r["query_text"])
        if key in existing:
            skipped += 1
            continue

        country = _geolocate_ip(r["ip_address"], geo_cache) if geolocate else None

        conn.execute(
            """
            INSERT INTO query_logs (
                timestamp, query_text, response_text,
                confidence_score, is_unanswered, response_time_ms,
                ip_address, country_code, user_agent, tool_used, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r["timestamp"],
                r["query_text"],
                None,  # response_text non recuperabile dai log
                None,  # confidence_score
                None,  # is_unanswered
                None,  # response_time_ms
                r["ip_address"],
                country,
                None,  # user_agent
                r["tool_used"],
                None,  # error
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()

    if skipped:
        print(f"  Skippate {skipped} righe gia' presenti nel DB")

    return inserted


def main():
    parser = argparse.ArgumentParser(
        description="Backfill analytics DB dai log di sistema",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=str, help="File di log da parsare")
    source.add_argument("--stdin", action="store_true", help="Leggi da stdin (pipe da journalctl)")

    parser.add_argument("--dry-run", action="store_true", help="Mostra cosa verrebbe inserito senza toccare il DB")
    parser.add_argument("--geolocate", action="store_true", help="Geolocalizza gli IP (lento, chiama ip-api.com)")
    parser.add_argument("--year", type=int, default=2026, help="Anno per timestamp journald senza anno (default: 2026)")
    parser.add_argument("--db", type=str, default=str(DB_PATH), help=f"Path del DB analytics (default: {DB_PATH})")

    args = parser.parse_args()

    # Leggi le righe
    if args.stdin:
        lines = sys.stdin.readlines()
        print(f"Lette {len(lines)} righe da stdin")
    else:
        path = Path(args.file)
        if not path.exists():
            print(f"Errore: file '{args.file}' non trovato")
            sys.exit(1)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        print(f"Lette {len(lines)} righe da {args.file}")

    # Parsa
    records = parse_logs(lines, year=args.year)
    print(f"Trovate {len(records)} query nel log")

    if not records:
        print("Nessuna query da inserire.")
        return

    # Inserisci
    if args.dry_run:
        print("\n--- DRY RUN (nessuna modifica al DB) ---")

    n = insert_records(
        records,
        db_path=Path(args.db),
        geolocate=args.geolocate,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"\n{n} record verrebbero inseriti")
    else:
        print(f"\n{n} record inseriti in {args.db}")
        print(f"Verifica: sqlite3 {args.db} \"SELECT COUNT(*) FROM query_logs;\"")


if __name__ == "__main__":
    main()
