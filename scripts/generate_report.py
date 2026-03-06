#!/usr/bin/env python3
"""
Generate Report — Script CLI per la reportistica del Pay Transparency Tool.

Legge il database SQLite di analytics e stampa (o salva) un report
formattato con metriche di utilizzo, qualita' delle risposte, provenienza
geografica, trend giornalieri ed errori.

Uso:
    python scripts/generate_report.py                     # ultimi 30 giorni, a terminale
    python scripts/generate_report.py --days 7            # ultimi 7 giorni
    python scripts/generate_report.py --output report.txt # salva su file
    make report          # alias
    make report-weekly   # alias --days 7
    make report-save     # salva con data nel nome
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Permette di eseguire lo script dalla root del progetto
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.utils.analytics import AnalyticsLogger  # noqa: E402


# =============================================================================
# COSTANTI DI FORMATTAZIONE
# =============================================================================

_DAY_NAMES_IT = {
    "Monday": "Lun",
    "Tuesday": "Mar",
    "Wednesday": "Mer",
    "Thursday": "Gio",
    "Friday": "Ven",
    "Saturday": "Sab",
    "Sunday": "Dom",
}


# =============================================================================
# GENERAZIONE REPORT
# =============================================================================

def generate_report(days: int = 30, db_path: str = "./data/analytics.db") -> str:
    """
    Genera il report come stringa di testo.

    Args:
        days: periodo di analisi in giorni
        db_path: percorso del database SQLite

    Returns:
        Il report formattato come stringa multi-linea
    """
    db = AnalyticsLogger(db_path=db_path)
    data = db.get_summary(days=days)

    if "error" in data:
        return f"[ERRORE] Impossibile leggere il database: {data['error']}\n"

    if data["total_queries"] == 0:
        since_dt = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            f"Nessuna query registrata negli ultimi {days} giorni "
            f"(dal {since_dt.strftime('%d/%m/%Y')}).\n"
            "Assicurati che il server sia in esecuzione e che siano state "
            "effettuate alcune richieste.\n"
        )

    lines = []

    # --- Header ---
    now = datetime.now(timezone.utc)
    since_dt = now - timedelta(days=days)
    lines += [
        "=" * 60,
        "   PAY TRANSPARENCY TOOL — REPORT UTILIZZO",
        "=" * 60,
        f"Periodo: {since_dt.strftime('%d/%m/%Y')} — {now.strftime('%d/%m/%Y')} ({days} giorni)",
        f"Generato il: {now.strftime('%d/%m/%Y %H:%M')} UTC",
        "",
    ]

    # --- Metriche generali ---
    lines += [
        "📊 METRICHE GENERALI",
        "-" * 40,
        f"  Totale domande ricevute:  {data['total_queries']}",
        f"  Media domande/giorno:     {data['avg_queries_per_day']}",
    ]
    if data["avg_response_time_ms"] is not None:
        lines.append(f"  Tempo medio di risposta:  {int(data['avg_response_time_ms'])} ms")
    else:
        lines.append("  Tempo medio di risposta:  N/D")
    lines.append("")

    # --- Qualita' risposte ---
    lines += [
        "🎯 QUALITÀ RISPOSTE",
        "-" * 40,
    ]
    if data["avg_confidence"] is not None:
        lines.append(f"  Confidence score medio:   {data['avg_confidence']:.2f} / 1.00")
    else:
        lines.append("  Confidence score medio:   N/D")

    unanswered = data["unanswered_count"]
    unanswered_pct = data["unanswered_pct"]
    lines.append(f"  Domande senza risposta:   {unanswered} ({unanswered_pct}%)")

    if data["unanswered_top10"]:
        lines.append("\n  Top 10 domande senza risposta:")
        for i, item in enumerate(data["unanswered_top10"], 1):
            query = item["query"]
            if len(query) > 70:
                query = query[:67] + "..."
            conf = item["confidence"]
            conf_str = f"{conf:.2f}" if conf is not None else "N/D"
            lines.append(f"   {i:2d}. \"{query}\" (confidence: {conf_str})")
    lines.append("")

    # --- Provenienza ---
    lines += [
        "🌍 PROVENIENZA",
        "-" * 40,
    ]
    breakdown = data["country_breakdown"]
    total = data["total_queries"]
    if breakdown:
        it_count = breakdown.get("IT", 0)
        local_count = breakdown.get("local", 0)
        unknown_count = breakdown.get("unknown", 0)
        other_count = total - it_count - local_count - unknown_count

        if it_count:
            lines.append(f"  Italia:   {it_count} ({_pct(it_count, total)}%)")
        if local_count:
            lines.append(f"  Locale:   {local_count} ({_pct(local_count, total)}%)")
        if unknown_count:
            lines.append(f"  Sconos.:  {unknown_count} ({_pct(unknown_count, total)}%)")
        if other_count > 0:
            lines.append(f"  Altro:    {other_count} ({_pct(other_count, total)}%)")

        # Elenco paesi esclusi IT/local/unknown
        foreign = {
            k: v for k, v in sorted(breakdown.items(), key=lambda x: -x[1])
            if k not in ("IT", "local", "unknown")
        }
        if foreign:
            lines.append("\n  Paesi esteri:")
            for country, count in foreign.items():
                lines.append(f"    {country}: {count} ({_pct(count, total)}%)")
    else:
        lines.append("  Nessun dato disponibile.")
    lines.append("")

    # --- Utilizzo tool ---
    lines += [
        "🔧 UTILIZZO TOOL",
        "-" * 40,
    ]
    tool_bd = data["tool_breakdown"]
    if tool_bd:
        tool_labels = {
            "rag":             "Solo RAG (normativa)",
            "agent":           "Agent (ibrido)",
            "analyze_pay_gap": "Analisi dati",
            "unknown":         "Sconosciuto",
        }
        for tool_key, label in tool_labels.items():
            count = tool_bd.get(tool_key, 0)
            if count:
                lines.append(f"  {label:<25} {count} ({_pct(count, total)}%)")
        # Tool non previsti
        for tool_key, count in tool_bd.items():
            if tool_key not in tool_labels:
                lines.append(f"  {tool_key:<25} {count} ({_pct(count, total)}%)")
    else:
        lines.append("  Nessun dato disponibile.")
    lines.append("")

    # --- Trend 7 giorni ---
    lines += [
        "📈 TREND (ultimi 7 giorni)",
        "-" * 40,
    ]
    trend = data["daily_trend"]
    if trend:
        max_count = max(trend.values()) if trend else 1
        for day_str, count in sorted(trend.items()):
            try:
                day_dt = datetime.strptime(day_str, "%Y-%m-%d")
                day_label = _DAY_NAMES_IT.get(day_dt.strftime("%A"), day_str)
                date_label = day_dt.strftime("%d/%m")
            except ValueError:
                day_label = day_str
                date_label = ""
            bar = "█" * max(1, int(count / max_count * 20))
            lines.append(f"  {day_label} {date_label}: {bar} {count}")
    else:
        lines.append("  Nessun dato disponibile.")
    lines.append("")

    # --- Errori ---
    lines += [
        "⚠️  ERRORI",
        "-" * 40,
        f"  Totale errori: {data['error_count']}",
    ]
    if data["top_errors"]:
        lines.append("\n  Errori più frequenti:")
        for err in data["top_errors"]:
            err_short = err if len(err) <= 80 else err[:77] + "..."
            lines.append(f"    - {err_short}")
    lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)


# =============================================================================
# HELPER
# =============================================================================

def _pct(value: int, total: int) -> str:
    """Calcola percentuale arrotondata a 1 decimale."""
    if total == 0:
        return "0.0"
    return f"{value / total * 100:.1f}"


# =============================================================================
# ENTRY POINT
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera report di utilizzo del Pay Transparency Tool.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        metavar="N",
        help="Periodo di analisi in giorni (default: 30)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="FILE",
        help="File di output (default: stampa a terminale)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="./data/analytics.db",
        metavar="PATH",
        help="Percorso del database SQLite (default: ./data/analytics.db)",
    )
    args = parser.parse_args()

    report = generate_report(days=args.days, db_path=args.db)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"Report salvato in: {output_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
