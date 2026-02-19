"""
Modulo di configurazione centralizzata.

Questo file ha un solo scopo: caricare le impostazioni del progetto
(API key, parametri del modello AI, ecc.) e renderle disponibili
a tutti gli altri moduli del progetto.

Concetti Python usati qui:
- Classe: un "modello" che raggruppa dati e funzioni correlate
- @property: trasforma un metodo in un attributo (si legge senza parentesi)
- @classmethod: metodo che appartiene alla classe, non all'istanza
- Singleton: pattern che garantisce una sola istanza della classe
"""

import os                          # Per leggere le variabili d'ambiente (es. API key)
from pathlib import Path           # Per gestire percorsi di file in modo sicuro
import yaml                        # Per leggere file .yaml (libreria PyYAML)
from dotenv import load_dotenv     # Per caricare le variabili dal file .env


class Config:
    """Gestisce tutta la configurazione del progetto."""

    # Variabile di classe condivisa tra tutte le istanze.
    # Serve per il pattern Singleton: ne esiste una sola copia.
    _instance = None

    def __init__(self, config_path: str = "config.yaml"):
        """
        Inizializza la configurazione.

        Args:
            config_path: percorso del file YAML di configurazione.
                         Se non esiste, usa config.yaml.example come fallback.
        """
        # Carica le variabili dal file .env nel sistema operativo.
        # Dopo questa riga, os.getenv("GOOGLE_API_KEY") restituisce la tua key.
        load_dotenv()

        # Converte la stringa del percorso in un oggetto Path,
        # che è più comodo per controllare se il file esiste, ecc.
        self.config_path = Path(config_path)

        # Carica il file YAML e salva il contenuto come dizionario Python.
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """
        Carica il file YAML di configurazione.

        Logica:
        1. Se esiste config.yaml → usa quello
        2. Altrimenti se esiste config.yaml.example → usa quello
        3. Altrimenti → ritorna un dizionario vuoto

        Returns:
            dict: il contenuto del file YAML come dizionario Python.
        """
        # Caso 1: il file config.yaml esiste
        if self.config_path.exists():
            # 'open' apre il file, 'with' lo chiude automaticamente quando finisce
            with open(self.config_path, "r") as f:
                # yaml.safe_load converte il YAML in un dizionario Python
                # Esempio: "llm:\n  model: gemini" diventa {"llm": {"model": "gemini"}}
                return yaml.safe_load(f) or {}

        # Caso 2: il file .example esiste (fallback)
        example_path = Path(str(self.config_path) + ".example")
        if example_path.exists():
            with open(example_path, "r") as f:
                return yaml.safe_load(f) or {}

        # Caso 3: nessun file trovato
        return {}

    # --- Proprietà: si leggono come attributi, senza parentesi ---
    # Esempio: config.api_key  (NON config.api_key())

    @property
    def api_key(self) -> str:
        """Legge la API key del provider LLM dalla variabile d'ambiente."""
        return os.getenv("GROQ_API_KEY", "")

    @property
    def llm_config(self) -> dict:
        """Configurazione del modello di linguaggio (Gemini)."""
        return self._config.get("llm", {})

    @property
    def embeddings_config(self) -> dict:
        """Configurazione del modello di embedding."""
        return self._config.get("embeddings", {})

    @property
    def vectorstore_config(self) -> dict:
        """Configurazione del vector database (Qdrant)."""
        return self._config.get("vectorstore", {})

    @property
    def rag_config(self) -> dict:
        """Configurazione del sistema RAG."""
        return self._config.get("rag", {})

    # --- Singleton: garantisce una sola istanza ---

    @classmethod
    def get_instance(cls, config_path: str = "config.yaml") -> "Config":
        """
        Ritorna l'unica istanza di Config (pattern Singleton).

        La prima volta crea l'istanza. Le volte successive ritorna
        la stessa, senza ricaricare il file.

        Perché? Così tutti i moduli del progetto condividono la stessa
        configurazione, senza ricaricare il file YAML ogni volta.
        """
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance
