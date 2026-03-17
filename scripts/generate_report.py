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

def generate_linkedin_snippet(days: int = 30, db_path: str = "./data/analytics.db") -> str:
    """
    Genera un testo pronto per un post LinkedIn con i KPI principali.

    Args:
        days: periodo di analisi in giorni
        db_path: percorso del database SQLite

    Returns:
        Testo formattato per LinkedIn (copy-paste ready)
    """
    db = AnalyticsLogger(db_path=db_path)
    data = db.get_summary(days=days)

    if "error" in data or data["total_queries"] == 0:
        return "Nessun dato disponibile per generare il post LinkedIn.\n"

    total = data["total_queries"]
    countries = data["country_breakdown"]
    tool_bd = data["tool_breakdown"]
    unanswered_pct = data["unanswered_pct"]

    # Calcola utenti unici (distinct IP) — query diretta
    import sqlite3
    conn = sqlite3.connect(db_path)
    since = data["since"]
    unique_ips = conn.execute(
        "SELECT COUNT(DISTINCT ip_address) FROM query_logs WHERE timestamp >= ?",
        (since,),
    ).fetchone()[0]
    conn.close()

    # Paesi (esclusi local e unknown)
    real_countries = {k: v for k, v in countries.items() if k not in ("local", "unknown", None)}
    n_countries = len(real_countries)
    country_list = ", ".join(
        f"{k} ({v})" for k, v in sorted(real_countries.items(), key=lambda x: -x[1])[:5]
    )

    # Tool usage
    rag_count = tool_bd.get("rag", 0) + tool_bd.get("cache", 0)
    agent_count = tool_bd.get("agent", 0) + tool_bd.get("analyze_pay_gap", 0)

    # Top domande (non unanswered — le piu' frequenti in generale)
    conn = sqlite3.connect(db_path)
    top_queries = conn.execute(
        """
        SELECT query_text, COUNT(*) as cnt
        FROM query_logs
        WHERE timestamp >= ? AND tool_used NOT IN ('blocked', 'backfill')
        GROUP BY query_text
        ORDER BY cnt DESC
        LIMIT 5
        """,
        (since,),
    ).fetchall()
    conn.close()

    lines = [
        "=" * 50,
        "  POST LINKEDIN — KPI Pay Transparency Tool",
        "=" * 50,
        "",
        "--- DATI GREZZI (scegli cosa includere nel post) ---",
        "",
        f"Periodo: ultimi {days} giorni",
        f"Domande ricevute: {total}",
        f"Utenti unici (IP distinti): {unique_ips}",
        f"Paesi: {n_countries} ({country_list})" if n_countries else "Paesi: dati non disponibili",
        f"Domande sulla normativa (RAG): {rag_count} ({_pct(rag_count, total)}%)",
        f"Domande su analisi dati: {agent_count} ({_pct(agent_count, total)}%)",
        f"Tasso di risposte efficaci: {100 - unanswered_pct:.1f}%",
    ]

    if data["avg_response_time_ms"] is not None:
        lines.append(f"Tempo medio di risposta: {int(data['avg_response_time_ms'])} ms")

    if top_queries:
        lines += ["", "Top 5 domande piu' frequenti:"]
        for i, (q, c) in enumerate(top_queries, 1):
            q_short = q[:60] + "..." if len(q) > 60 else q
            lines.append(f"  {i}. \"{q_short}\" ({c}x)")

    lines += [
        "",
        "--- BOZZA POST (da personalizzare) ---",
        "",
        f"Nelle prime {days // 7} settimane dal lancio, il Pay Transparency Tool ha ricevuto "
        f"{total} domande da {unique_ips} professionisti HR"
        + (f" provenienti da {n_countries} paesi." if n_countries > 1 else "."),
        "",
        "Le domande piu' frequenti riguardano:"
        if top_queries else "",
    ]

    if top_queries:
        # Raggruppa in temi
        lines.append("- Obblighi di reporting e scadenze")
        lines.append("- Calcolo e interpretazione del gender pay gap")
        lines.append("- Sanzioni e compliance")
        lines.append("(personalizza in base ai dati reali)")

    lines += [
        "",
        f"Il {100 - unanswered_pct:.0f}% delle domande ha ricevuto una risposta precisa, "
        "citando articoli specifici della Direttiva EU 2023/970.",
        "",
        "Il tool e' completamente gratuito e open source.",
        "",
        "=" * 50,
    ]

    return "\n".join(lines)


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
    parser.add_argument(
        "--linkedin",
        action="store_true",
        help="Genera snippet KPI per post LinkedIn invece del report completo",
    )
    args = parser.parse_args()

    if args.linkedin:
        report = generate_linkedin_snippet(days=args.days, db_path=args.db)
    else:
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
