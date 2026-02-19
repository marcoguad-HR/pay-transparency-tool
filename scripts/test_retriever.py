"""
Script di test per il Retriever (Fase 1.2).

Cosa fa:
1. Crea un DirectiveRetriever
2. Fa 3 domande diverse sulla Direttiva EU
3. Mostra i risultati trovati per ciascuna

PREREQUISITO: devi aver già eseguito test_ingestion.py almeno una volta
(altrimenti il vector database è vuoto e non trova nulla).

Esegui con:
    cd ~/Desktop/pay-transparency-tool
    source .venv/bin/activate
    python scripts/test_retriever.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.retriever import DirectiveRetriever
from src.utils.logger import get_logger

logger = get_logger("test_retriever")


def main():
    logger.info("=== TEST RETRIEVER ===\n")

    retriever = DirectiveRetriever()

    # 3 domande di prova che coprono diversi aspetti della Direttiva
    queries = [
        "What is the transposition deadline for the directive?",
        "What does Article 7 say about pay transparency?",
        "What is the gender pay gap reporting obligation?",
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"DOMANDA: {query}")
        print(f"{'='*60}")

        # Cerca i top-3 chunk più rilevanti
        results = retriever.retrieve(query, top_k=3)

        for i, result in enumerate(results):
            print(f"\n--- Risultato {i+1} ---")
            print(f"Fonte: {result.source}")
            # Mostra i primi 300 caratteri per dare un'idea del contenuto
            print(f"Testo: {result.text[:300]}...")

    logger.info("\n=== TEST RETRIEVER COMPLETATO ===")


if __name__ == "__main__":
    main()
