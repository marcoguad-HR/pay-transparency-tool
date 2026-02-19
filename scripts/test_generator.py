"""
Script di test per il Generator RAG (Fase 1.3).

Cosa fa:
1. Crea un RAGGenerator (che al suo interno crea anche il Retriever)
2. Fa 3 domande sulla Direttiva EU
3. Per ogni domanda mostra: risposta, confidenza, fonti usate

PREREQUISITO: devi aver già eseguito test_ingestion.py
(il vector database deve contenere i chunk della Direttiva).

Esegui con:
    cd ~/Desktop/pay-transparency-tool
    source .venv/bin/activate
    python scripts/test_generator.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.generator import RAGGenerator
from src.utils.logger import get_logger

logger = get_logger("test_generator")


def main():
    logger.info("=== TEST GENERATOR RAG ===\n")

    generator = RAGGenerator()

    queries = [
        "What is the transposition deadline for member states?",
        "What are the pay reporting obligations under Article 9?",
        "Qual è la soglia di dipendenti per l'obbligo di reporting?",
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"DOMANDA: {query}")
        print(f"{'='*60}")

        response = generator.generate(query, top_k=5)

        print(f"\nRISPOSTA:")
        print(response.answer)

        print(f"\nCONFIDENZA: {response.confidence:.0%}")

        print(f"\nFONTI USATE ({len(response.sources)}):")
        for i, src in enumerate(response.sources, 1):
            source_name = src.source.split("/")[-1] if src.source else "?"
            print(f"  {i}. {source_name} — '{src.text[:80]}...'")

    logger.info("\n=== TEST GENERATOR COMPLETATO ===")


if __name__ == "__main__":
    main()
