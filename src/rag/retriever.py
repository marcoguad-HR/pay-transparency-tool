"""
Retriever — Fase 1.2 del progetto Pay Transparency Tool.

Cos'è il Retriever?
È il componente che, data una domanda dell'utente, cerca nel vector database
i pezzi di testo (chunk) più rilevanti per rispondere.

Come funziona:
1. L'utente fa una domanda: "Qual è la deadline di trasposizione?"
2. Il retriever trasforma la domanda in un vettore (embedding)
3. Cerca in Qdrant i chunk con vettori più "vicini" a quello della domanda
4. Restituisce i top-k chunk più rilevanti, formattati e pronti per il LLM

Analogia: è come un bibliotecario che, data una domanda,
va a cercare le pagine giuste in un libro enorme.

La "vicinanza" tra vettori si misura con la cosine similarity:
- 1.0 = significato identico
- 0.5 = vagamente correlato
- 0.0 = nessuna relazione
"""

from dataclasses import dataclass, field

# FastEmbed — per creare l'embedding della domanda dell'utente
from fastembed import TextEmbedding

# Datapizza AI — vector store e tipi
from datapizza.vectorstores.qdrant import QdrantVectorstore
from datapizza.type import Chunk

# Moduli interni
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger("rag.retriever")


@dataclass
class RetrievalResult:
    """
    Risultato di una ricerca nel vector database.

    Perché una dataclass?
    È un modo compatto di creare una classe che contiene solo dati.
    Invece di scrivere __init__, __repr__, ecc., Python li genera da solo.

    Esempio:
        result = RetrievalResult(text="...", source="directive_EN.pdf", score=0.85)
        print(result.text)    # il contenuto del chunk
        print(result.source)  # da quale documento viene
        print(result.score)   # quanto è rilevante (0.0 - 1.0)
    """
    text: str                          # Contenuto del chunk trovato
    source: str = ""                   # File di provenienza
    chunk_id: str = ""                 # ID univoco del chunk in Qdrant
    score: float = 0.0                 # Rilevanza (cosine similarity)
    metadata: dict = field(default_factory=dict)  # Metadati aggiuntivi


class DirectiveRetriever:
    """
    Cerca i chunk più rilevanti nel vector database per una data domanda.

    Uso:
        retriever = DirectiveRetriever()
        results = retriever.retrieve("What is the transposition deadline?")
        for r in results:
            print(f"[{r.score:.2f}] {r.text[:100]}...")
    """

    def __init__(self):
        """
        Inizializza il retriever leggendo la configurazione.

        Componenti:
        - embedder: stesso modello usato nell'ingestion (DEVE essere lo stesso!)
        - vectorstore: connessione a Qdrant per cercare i vettori
        - top_k: quanti risultati restituire (default: 5)
        """
        config = Config.get_instance()

        emb_config = config.embeddings_config
        vs_config = config.vectorstore_config
        rag_config = config.rag_config

        self.collection_name = vs_config.get("collection_name", "eu_directive_2023_970")
        self.top_k = rag_config.get("top_k", 5)

        # IMPORTANTE: il modello di embedding deve essere lo STESSO usato
        # durante l'ingestion! Se usi un modello diverso, i vettori non
        # saranno confrontabili e i risultati saranno spazzatura.
        model_name = emb_config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
        self.embedder = TextEmbedding(model_name=model_name)

        # Connessione allo stesso Qdrant dove abbiamo salvato i chunk
        vs_path = vs_config.get("location", "./data/vectordb")
        self.vectorstore = QdrantVectorstore(location=None, path=vs_path)

        logger.info(f"Retriever inizializzato: collection={self.collection_name}, top_k={self.top_k}")

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievalResult]:
        """
        Cerca i chunk più rilevanti per la domanda data.

        Args:
            query: la domanda dell'utente (es. "What is Article 7 about?")
            top_k: quanti risultati restituire (se None, usa il default da config)

        Returns:
            Lista di RetrievalResult ordinati per rilevanza (il più rilevante prima).

        Come funziona internamente:
        1. Trasforma la query in un vettore a 384 dimensioni
        2. Chiede a Qdrant: "dammi i top_k vettori più vicini a questo"
        3. Qdrant restituisce i chunk con il loro testo e metadata
        4. Convertiamo tutto in RetrievalResult per uso più comodo
        """
        k = top_k or self.top_k

        logger.info(f"Ricerca per: '{query}' (top_k={k})")

        # Step 1: Crea l'embedding della domanda
        # embed() è un generatore, quindi:
        # - list() lo converte in lista
        # - [0] prende il primo (e unico) risultato
        # - .tolist() converte da numpy array a lista Python
        query_vector = list(self.embedder.embed([query]))[0].tolist()

        # Step 2: Cerca in Qdrant i chunk più simili
        # vector_name="dense" deve corrispondere al nome usato nell'ingestion
        chunks = self.vectorstore.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            k=k,
            vector_name="dense",
        )

        # Step 3: Converti i Chunk di Datapizza in RetrievalResult
        results = self._format_results(chunks)

        logger.info(f"  Trovati {len(results)} risultati")
        return results

    def _format_results(self, chunks: list[Chunk]) -> list[RetrievalResult]:
        """
        Converte i chunk grezzi di Qdrant in RetrievalResult più comodi.

        Perché questa conversione?
        I Chunk di Datapizza hanno una struttura generica. RetrievalResult
        è specifico per il nostro progetto: ha campi chiari (source, score)
        e metodi utili che potremmo aggiungere in futuro.

        Nota: Qdrant non restituisce uno "score" nei chunk di Datapizza AI
        (la libreria non lo mappa). Per ora mettiamo 0.0.
        In futuro potremmo accedere direttamente al client Qdrant per avere
        lo score, ma per il nostro uso non è critico: l'ordine è comunque
        dal più rilevante al meno rilevante.
        """
        results = []

        for chunk in chunks:
            # chunk.metadata contiene il payload salvato durante l'ingestion:
            # {"text": "...", "source": "data/documents/...", "boundingRegions": [...]}
            metadata = chunk.metadata or {}

            results.append(RetrievalResult(
                text=chunk.text,
                source=metadata.get("source", "sconosciuto"),
                chunk_id=str(chunk.id),
                score=0.0,  # Qdrant ordina per rilevanza, ma lo score non è mappato
                metadata=metadata,
            ))

        return results
