"""
Scarica il PDF della Direttiva EU 2023/970 da EUR-Lex.

La direttiva è il documento normativo su cui si basa tutto il modulo RAG.
Viene salvata in data/documents/ per poi essere indicizzata dal vector DB.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import urllib.request
from src.utils.logger import get_logger

logger = get_logger("download")

# URL ufficiale dal sito EUR-Lex (il portale delle leggi EU)
DIRECTIVE_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32023L0970"
OUTPUT_PATH = Path("data/documents/directive_eu_2023_970_EN.pdf")


def download_directive():
    """Scarica il PDF della direttiva se non è già presente."""
    # Crea la cartella se non esiste
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Se il file esiste già, non lo riscarichiamo
    if OUTPUT_PATH.exists():
        logger.info(f"Direttiva già presente: {OUTPUT_PATH}")
        return

    logger.info("Scaricamento Direttiva EU 2023/970 in corso...")
    urllib.request.urlretrieve(DIRECTIVE_URL, OUTPUT_PATH)

    # Mostra la dimensione del file scaricato
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    logger.info(f"Salvata in {OUTPUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    download_directive()
