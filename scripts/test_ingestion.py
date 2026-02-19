"""
Script di test per la pipeline di ingestion (Fase 1.1).

Cosa fa:
1. Crea un'istanza di DirectiveIngestion
2. Esegue l'ingestion del PDF della Direttiva EU (versione inglese)
3. Mostra il numero di chunk creati
4. Fa una ricerca di prova per verificare che i vettori funzionino

Esegui con:
    cd ~/Desktop/pay-transparency-tool
    source .venv/bin/activate
    python scripts/test_ingestion.py
"""

import sys
from pathlib import Path

# Aggiungi la root del progetto al path di Python
# così possiamo importare i moduli da src/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.ingestion import DirectiveIngestion
from src.utils.logger import get_logger

logger = get_logger("test_ingestion")


def main():
    # Percorso del PDF della Direttiva EU
    pdf_path = "data/documents/CELEX_32023L0970_EN_TXT.pdf"

    if not Path(pdf_path).exists():
        logger.error(f"File non trovato: {pdf_path}")
        logger.error("Assicurati di essere nella directory del progetto!")
        return

    # --- Fase 1: Ingestion ---
    logger.info("=== TEST INGESTION ===")

    ingestion = DirectiveIngestion()

    # Reset per ricominciare da zero (utile in fase di sviluppo)
    ingestion.reset()

    # Esegui l'ingestion
    n_chunks = ingestion.ingest(pdf_path)
    logger.info(f"Risultato: {n_chunks} chunk creati e salvati")

    # --- Fase 2: Verifica con una ricerca di prova ---
    logger.info("\n=== TEST RICERCA DI PROVA ===")

    # Importa FastEmbed per creare l'embedding della query
    from fastembed import TextEmbedding
    from src.utils.config import Config

    config = Config.get_instance()
    emb_config = config.embeddings_config
    model_name = emb_config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")

    embedder = TextEmbedding(model_name=model_name)

    # Domanda di prova
    query = "What is the transposition deadline for the directive?"
    logger.info(f"Query di prova: '{query}'")

    # Crea l'embedding della query
    query_vector = list(embedder.embed([query]))[0].tolist()

    # Cerca i 3 chunk più rilevanti
    results = ingestion.vectorstore.search(
        collection_name=ingestion.collection_name,
        query_vector=query_vector,
        k=3,
        vector_name="dense",
    )

    logger.info(f"Trovati {len(results)} risultati:")
    for i, chunk in enumerate(results):
        print(f"\n--- Risultato {i+1} ---")
        print(f"ID: {chunk.id}")
        # Mostra i primi 200 caratteri del chunk
        print(f"Testo: {chunk.text[:200]}...")
        print(f"Metadata: {chunk.metadata}")

    logger.info("\n=== TEST COMPLETATO CON SUCCESSO ===")


if __name__ == "__main__":
    main()
