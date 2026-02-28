"""
Query Transformer — Step-back prompting per migliorare il retrieval RAG.

Cos'e' lo step-back prompting?
Data una domanda specifica, genera una versione piu' ampia ("step-back")
che recupera contesto complementare dalla Direttiva.

Esempio:
    Originale:  "Cosa succede se il gap supera il 5%?"
    Step-back:  "Quali sono i requisiti di reporting e valutazione del
                 pay gap nella Direttiva EU 2023/970?"

La query step-back cattura contesto regolatorio piu' ampio che la
domanda specifica potrebbe non matchare.

ATTENZIONE rate limit: ogni trasformazione costa 1 chiamata LLM a Groq.
Per questo e' disabilitato di default (rag.query_transform_enabled: false).
Abilitare solo quando si vuole massima qualita' di retrieval.
"""

from dataclasses import dataclass

from datapizza.clients.openai import OpenAIClient

from src.utils.config import Config
from src.utils.logger import get_logger
from src.utils.rate_limiter import invoke_with_retry

logger = get_logger("rag.query_transformer")

# Prompt per generare la query step-back
STEP_BACK_PROMPT = """Data una domanda specifica sulla Direttiva EU 2023/970 (Pay Transparency Directive), genera una versione PIU' AMPIA e GENERALE della domanda che aiuti a recuperare contesto regolatorio di sfondo.

REGOLE:
- Rispondi con UNA SOLA domanda, piu' ampia dell'originale
- Mantienila rilevante all'argomento originale
- Non aggiungere informazioni non implicite nella domanda originale
- Rispondi SOLO con la domanda piu' ampia, nient'altro

Domanda originale: {query}

Domanda piu' ampia:"""


@dataclass
class TransformedQuery:
    """Risultato della trasformazione della query."""
    original: str
    step_back: str | None = None  # None se la trasformazione e' disabilitata


class QueryTransformer:
    """
    Trasforma le query per migliorare il retrieval.

    Se abilitato, genera una query step-back usando il LLM.
    Se disabilitato, restituisce la query originale senza modifiche
    (zero overhead, zero chiamate API).

    Uso:
        transformer = QueryTransformer()
        result = transformer.transform("Cosa dice l'Art. 10?")
        print(result.original)    # "Cosa dice l'Art. 10?"
        print(result.step_back)   # "Quali sono i requisiti di valutazione..."
    """

    def __init__(self):
        config = Config.get_instance()
        llm_config = config.llm_config
        rag_config = config.rag_config

        self.enabled = rag_config.get("query_transform_enabled", False)

        if self.enabled:
            self.client = OpenAIClient(
                api_key=config.api_key,
                model=llm_config.get("model", "llama-3.3-70b-versatile"),
                base_url=llm_config.get("base_url", "https://api.groq.com/openai/v1"),
                temperature=0.3,  # Un po' di creativita' per riformulare
                system_prompt="Sei un assistente che riformula domande per migliorare la ricerca.",
            )
            logger.info("QueryTransformer abilitato (step-back prompting)")
        else:
            self.client = None
            logger.info("QueryTransformer disabilitato (rag.query_transform_enabled: false)")

    def transform(self, query: str) -> TransformedQuery:
        """
        Genera una query step-back per la domanda data.

        Se disabilitato o in caso di errore, restituisce solo l'originale
        senza impatto sul funzionamento del sistema.
        """
        if not self.enabled or self.client is None:
            return TransformedQuery(original=query)

        try:
            prompt = STEP_BACK_PROMPT.format(query=query)
            response = invoke_with_retry(self.client, prompt)
            step_back = response.text.strip().strip('"')

            logger.info(f"Step-back query: '{step_back}'")
            return TransformedQuery(original=query, step_back=step_back)
        except Exception as e:
            logger.warning(f"Trasformazione query fallita: {e}. Uso query originale.")
            return TransformedQuery(original=query)
