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

import pickle
from dataclasses import dataclass, field
from pathlib import Path

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
    article_header: str = ""           # Es. "Article 10 - Joint pay assessments"


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

        # Carica indice BM25 se disponibile (per fusion retrieval)
        self.bm25_data = self._load_bm25_index(vs_path)

        logger.info(f"Retriever inizializzato: collection={self.collection_name}, "
                    f"top_k={self.top_k}, fusion={'ON' if self.bm25_data else 'OFF'}")

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievalResult]:
        """
        Cerca i chunk più rilevanti per la domanda data.

        Se l'indice BM25 è disponibile, usa la Fusion Retrieval:
        combina ricerca vettoriale (semantica) e BM25 (keyword) con
        Reciprocal Rank Fusion (RRF) per risultati migliori.

        Se l'indice BM25 non è disponibile, fallback a ricerca solo vettoriale
        (backward compatible con il comportamento originale).

        Args:
            query: la domanda dell'utente (es. "What is Article 7 about?")
            top_k: quanti risultati restituire (se None, usa il default da config)

        Returns:
            Lista di RetrievalResult ordinati per rilevanza (il più rilevante prima).
        """
        k = top_k or self.top_k

        logger.info(f"Ricerca per: '{query}' (top_k={k})")

        # Step 1: Crea l'embedding della domanda
        query_vector = list(self.embedder.embed([query]))[0].tolist()

        # Step 2: Ricerca vettoriale in Qdrant (recupera il doppio per la fusion)
        fetch_k = k * 2 if self.bm25_data else k
        chunks = self.vectorstore.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            k=fetch_k,
            vector_name="dense",
        )
        vector_results = self._format_results(chunks)

        # Step 3: Se BM25 disponibile, fusion; altrimenti solo vettoriale
        if self.bm25_data:
            bm25_results = self._bm25_search(query, k=fetch_k)
            results = self._reciprocal_rank_fusion(vector_results, bm25_results, k=k)
            logger.info(f"  Fusion retrieval: {len(results)} risultati (vector+BM25)")
        else:
            results = vector_results[:k]
            logger.info(f"  Trovati {len(results)} risultati (solo vettoriale)")

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
                article_header=metadata.get("article_header", ""),
            ))

        return results

    def _load_bm25_index(self, vs_path: str) -> dict | None:
        """
        Carica l'indice BM25 da disco, se disponibile.

        L'indice viene creato durante l'ingestion (Step 6 in ingestion.py).
        Se il file non esiste (es. prima ingestion o vectordb cancellato),
        il retriever funziona comunque in modalita' solo vettoriale.
        """
        bm25_path = Path(f"{vs_path}/bm25_index.pkl")

        if bm25_path.exists():
            with open(bm25_path, "rb") as f:
                data = pickle.load(f)
            logger.info("Indice BM25 caricato per fusion retrieval")
            return data

        logger.info("Indice BM25 non trovato, retrieval solo vettoriale")
        return None

    def _bm25_search(self, query: str, k: int) -> list[RetrievalResult]:
        """
        Cerca usando l'indice BM25 (keyword matching).

        BM25 eccelle quando la query contiene termini specifici
        presenti letteralmente nei documenti (es. "Article 10",
        "transposition deadline", "joint pay assessment").
        """
        tokenized_query = query.lower().split()
        scores = self.bm25_data["bm25"].get_scores(tokenized_query)

        # Ordina per score decrescente, prendi i top-k
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Solo risultati con score BM25 positivo
                metadata = self.bm25_data["chunk_metadata"][idx]
                results.append(RetrievalResult(
                    text=self.bm25_data["chunk_texts"][idx],
                    source=metadata.get("source", ""),
                    chunk_id=self.bm25_data["chunk_ids"][idx],
                    score=float(scores[idx]),
                    metadata=metadata,
                    article_header=metadata.get("article_header", ""),
                ))
        return results

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[RetrievalResult],
        bm25_results: list[RetrievalResult],
        k: int,
        rrf_k: int = 60,
    ) -> list[RetrievalResult]:
        """
        Combina due liste di risultati con Reciprocal Rank Fusion (RRF).

        RRF e' un metodo robusto per fondere ranking eterogenei senza
        bisogno di normalizzare gli score (che hanno scale diverse tra
        cosine similarity e BM25).

        Formula: RRF_score(d) = sum( 1 / (rrf_k + rank) ) per ogni lista
        dove rank e' la posizione del documento nella lista (1-indexed).

        rrf_k=60 e' il valore standard dalla letteratura (Cormack et al.).
        """
        scores: dict[str, tuple[float, RetrievalResult]] = {}

        # Accumula score RRF dai risultati vettoriali
        for rank, result in enumerate(vector_results):
            key = result.chunk_id or result.text[:50]
            rrf_score = 1.0 / (rrf_k + rank + 1)
            if key in scores:
                scores[key] = (scores[key][0] + rrf_score, scores[key][1])
            else:
                scores[key] = (rrf_score, result)

        # Accumula score RRF dai risultati BM25
        for rank, result in enumerate(bm25_results):
            key = result.chunk_id or result.text[:50]
            rrf_score = 1.0 / (rrf_k + rank + 1)
            if key in scores:
                scores[key] = (scores[key][0] + rrf_score, scores[key][1])
            else:
                scores[key] = (rrf_score, result)

        # Ordina per score RRF combinato e restituisci top-k
        ranked = sorted(scores.values(), key=lambda x: x[0], reverse=True)

        results = []
        for fused_score, result in ranked[:k]:
            result.score = fused_score
            results.append(result)

        return results
