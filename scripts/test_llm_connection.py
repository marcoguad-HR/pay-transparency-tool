"""
Script di test per verificare la connessione al LLM (Groq + Llama 3.3).

Cosa fa:
1. Carica la configurazione (API key + modello)
2. Crea un client Datapizza AI per Groq (API compatibile con OpenAI)
3. Invia una domanda semplice
4. Stampa la risposta

Se funziona, significa che tutto il setup è corretto!
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datapizza.clients.openai import OpenAIClient
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger("test_llm")


def main():
    config = Config.get_instance()

    if not config.api_key:
        logger.error("API key non trovata! Controlla il file .env")
        return

    logger.info(f"Modello: {config.llm_config.get('model')}")

    # Groq usa un'API compatibile con OpenAI, quindi usiamo OpenAIClient
    # con base_url che punta a Groq invece che a OpenAI
    client = OpenAIClient(
        api_key=config.api_key,
        model=config.llm_config.get("model", "llama-3.3-70b-versatile"),
        base_url=config.llm_config.get("base_url", "https://api.groq.com/openai/v1"),
        temperature=config.llm_config.get("temperature", 0.1),
    )

    logger.info("Invio domanda a Groq (Llama 3.3)...")
    response = client.invoke(
        "Rispondi in italiano in massimo 2 frasi: cos'è il gender pay gap?"
    )

    print("\n" + "=" * 50)
    print("RISPOSTA DA LLAMA 3.3 (via Groq):")
    print("=" * 50)
    print(response.text)
    print("=" * 50)

    logger.info("Connessione verificata con successo!")


if __name__ == "__main__":
    main()
