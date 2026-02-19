"""
Logger centralizzato con output formattato.

Perché usare logging invece di print()?
- print() va bene per debug veloce, ma in un progetto serio serve di più:
  - Livelli: puoi distinguere tra INFO, WARNING, ERROR
  - Formattazione: timestamp, nome del modulo, colori
  - Controllo: puoi disattivare i log di debug in produzione

Usiamo 'rich' per avere output colorato e leggibile nel terminale.
"""

import logging
from rich.logging import RichHandler  # Handler che formatta i log con colori


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Crea un logger con output formattato tramite rich.

    Args:
        name: nome del logger (di solito il nome del modulo, es. "rag.ingestion")
        level: livello minimo di log da mostrare.
               DEBUG < INFO < WARNING < ERROR < CRITICAL
               Se level="INFO", i messaggi DEBUG vengono ignorati.

    Returns:
        Un oggetto Logger pronto all'uso.

    Uso:
        logger = get_logger("mio_modulo")
        logger.info("Tutto ok")           # Messaggio informativo
        logger.warning("Attenzione!")      # Qualcosa di strano
        logger.error("Qualcosa è rotto")   # Errore
    """
    logger = logging.getLogger(name)

    # Evita di aggiungere handler duplicati se il logger è già configurato
    if not logger.handlers:
        handler = RichHandler(
            rich_tracebacks=True,   # Mostra gli errori in modo leggibile
            markup=True,            # Permette formattazione rich nei messaggi
        )
        handler.setLevel(getattr(logging, level.upper()))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level.upper()))

    return logger
