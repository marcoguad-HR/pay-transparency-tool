"""
Test completo del pipeline RAG con verifica anti-allucinazione (Fase 1).

Cosa fa:
1. Fa 3 domande sulla Direttiva EU con verify=True
2. Per ogni domanda mostra: risposta, confidenza, esito verifica
3. Fa una domanda "trabocchetto" per testare se il sistema resiste

PREREQUISITO: test_ingestion.py deve essere stato eseguito.

Esegui con:
    cd ~/Desktop/pay-transparency-tool
    source .venv/bin/activate
    python scripts/test_rag_pipeline.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.generator import RAGGenerator
from src.utils.logger import get_logger

logger = get_logger("test_rag_pipeline")


def main():
    logger.info("=== TEST PIPELINE RAG COMPLETO (con verifica) ===\n")

    generator = RAGGenerator()

    queries = [
        # Domanda con risposta chiara nel contesto
        "What is the transposition deadline for member states?",
        # Domanda in italiano
        "Quali informazioni deve fornire il datore di lavoro secondo l'Articolo 9?",
        # Domanda "trabocchetto" — la risposta NON è nel contesto
        "What are the specific fines for non-compliance in Germany?",
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"DOMANDA: {query}")
        print(f"{'='*60}")

        # verify=True attiva l'anti-allucinazione
        response = generator.generate(query, top_k=5, verify=True)

        print(f"\nRISPOSTA:")
        print(response.answer)

        print(f"\nCONFIDENZA: {response.confidence:.0%}")

        # Mostra l'esito della verifica
        if response.verified is not None:
            status = "VERIFICATA" if response.verified else "NON VERIFICATA"
            print(f"VERIFICA: {status}")
            if response.verification_reasoning:
                print(f"MOTIVAZIONE: {response.verification_reasoning}")

        print(f"FONTI: {len(response.sources)} chunk usati")

    logger.info("\n=== TEST PIPELINE COMPLETATO ===")


if __name__ == "__main__":
    main()
