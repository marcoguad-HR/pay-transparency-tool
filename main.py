"""
Pay Transparency Tool — Entry Point.

Punto di ingresso dell'applicazione. Usa argparse per il routing dei comandi:
- ingest:   Ingestione PDF direttiva nel vector DB
- query:    Domanda RAG sulla direttiva
- analyze:  Analisi gender pay gap da file CSV/Excel
- agent:    Agent interattivo (RAG + analisi dati)
"""

import argparse
import sys

from src.cli.interface import CLI


def main():
    parser = argparse.ArgumentParser(
        description="Pay Transparency Tool — Compliance EU Directive 2023/970",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Esempi:
  python main.py ingest data/documents/CELEX_32023L0970_EN_TXT.pdf
  python main.py query "Qual è la deadline di trasposizione?"
  python main.py analyze data/demo/demo_employees.csv --type compliance
  python main.py agent "Qual è il gap nel Finance?"
  python main.py agent                                  # modalità interattiva
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Comandi disponibili")

    # --- ingest ---
    ingest_parser = subparsers.add_parser(
        "ingest", help="Ingestione PDF direttiva nel vector database"
    )
    ingest_parser.add_argument("pdf_path", help="Percorso del file PDF")
    ingest_parser.add_argument(
        "--reset", action="store_true", help="Resetta il vector DB prima dell'ingestion"
    )

    # --- query ---
    query_parser = subparsers.add_parser(
        "query", help="Domanda sulla Direttiva EU (via RAG)"
    )
    query_parser.add_argument("question", help="La domanda da porre")
    query_parser.add_argument(
        "--verify", action="store_true", help="Abilita verifica anti-allucinazione"
    )

    # --- analyze ---
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analisi gender pay gap da file dati"
    )
    analyze_parser.add_argument(
        "file_path",
        nargs="?",
        default="data/demo/demo_employees.csv",
        help="Percorso del file CSV/Excel (default: demo dataset)",
    )
    analyze_parser.add_argument(
        "--type",
        choices=["full", "overall", "category", "quartiles", "bonus", "compliance"],
        default="full",
        dest="analysis_type",
        help="Tipo di analisi (default: full)",
    )

    # --- agent ---
    agent_parser = subparsers.add_parser(
        "agent", help="Agent interattivo (routing automatico RAG + dati)"
    )
    agent_parser.add_argument(
        "question", nargs="?", help="Domanda singola (ometti per modalità interattiva)"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    cli = CLI()
    cli.dispatch(args)


if __name__ == "__main__":
    main()
