"""
Pipeline di Ingestion — Fase 1.1 del progetto Pay Transparency Tool.

Cos'è l'ingestion?
Immagina di avere un libro di 100 pagine (la Direttiva EU).
Per poterci fare domande in modo intelligente, dobbiamo:

1. ESTRARRE il testo dal PDF                    (PyMuPDF)
2. STRUTTURARE il testo in un albero             (TextParser)
3. TAGLIARE il testo in pezzi ("chunk")          (RecursiveSplitter)
4. TRASFORMARE ogni pezzo in numeri ("embedding") (FastEmbed)
5. SALVARE i numeri in un database vettoriale     (Qdrant)

Dopo questo processo, possiamo cercare i pezzi più rilevanti
per rispondere a una domanda — è il cuore del RAG.

Concetti chiave:
- Chunk: un pezzo di testo di ~1000 caratteri. Troppo grande e
  contiene info irrilevanti; troppo piccolo e perde il contesto.
- Embedding: un vettore di 384 numeri che "cattura il significato"
  del testo. Testi simili → vettori vicini nello spazio.
- Vector DB: un database ottimizzato per cercare vettori simili
  (molto più veloce di cercare parola per parola).
"""

import pickle
import re
from pathlib import Path

# PyMuPDF — libreria per leggere i PDF ed estrarre il testo
import fitz

# FastEmbed — crea embedding (vettori numerici) dal testo, in locale e gratis
from fastembed import TextEmbedding

# Datapizza AI — framework che fornisce parser, splitter e tipi base
from datapizza.modules.parsers import TextParser
from datapizza.modules.splitters import RecursiveSplitter
from datapizza.type import Chunk, DenseEmbedding

# Datapizza AI — integrazione con Qdrant (vector database)
from datapizza.vectorstores.qdrant import QdrantVectorstore
from datapizza.core.vectorstore import VectorConfig, Distance
from datapizza.type import EmbeddingFormat

# I nostri moduli interni (creati nella Fase 0)
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger("rag.ingestion")


class DirectiveIngestion:
    """
    Gestisce l'ingestion dei documenti della Direttiva EU nel vector database.

    Pipeline:  PDF → testo → parsing → chunking → embedding → Qdrant

    Uso:
        ingestion = DirectiveIngestion()
        ingestion.ingest("data/documents/CELEX_32023L0970_EN_TXT.pdf")
    """

    def __init__(self):
        """
        Inizializza tutti i componenti della pipeline.

        Legge i parametri dalla configurazione (config.yaml.example):
        - embeddings.model_name → modello per creare gli embedding
        - embeddings.dimensions → dimensione dei vettori (384 per MiniLM)
        - vectorstore.location → dove salvare il database su disco
        - vectorstore.collection_name → nome della "tabella" nel DB
        - rag.chunk_size → dimensione massima di ogni chunk
        - rag.chunk_overlap → quanti caratteri di sovrapposizione tra chunk
        """
        config = Config.get_instance()

        # --- Configurazione ---
        emb_config = config.embeddings_config
        vs_config = config.vectorstore_config
        rag_config = config.rag_config

        self.collection_name = vs_config.get("collection_name", "eu_directive_2023_970")
        self.vector_dimensions = emb_config.get("dimensions", 384)

        # --- 1. Modello di embedding (locale, gratis) ---
        # TextEmbedding di FastEmbed scarica il modello la prima volta (~90MB)
        # e lo salva in cache. Le volte successive è istantaneo.
        model_name = emb_config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
        logger.info(f"Caricamento modello embedding: {model_name}")
        self.embedder = TextEmbedding(model_name=model_name)

        # --- 2. Parser: testo grezzo → albero strutturato ---
        # TextParser analizza il testo e lo organizza in:
        # DOCUMENT → PARAGRAPH → SENTENCE
        # Questo aiuta lo splitter a tagliare in punti sensati.
        self.parser = TextParser()

        # --- 3. Splitter: albero → lista di chunk ---
        # RecursiveSplitter scende nell'albero e raggruppa le frasi
        # fino a raggiungere max_char. L'overlap fa sì che ogni chunk
        # condivida un po' di testo col precedente, per non perdere contesto.
        #
        # Esempio con chunk_size=100 e overlap=20:
        #   Chunk 1: "Il gender pay gap è la differenza tra lo stipendio medio..."
        #   Chunk 2: "...tra lo stipendio medio degli uomini e delle donne che..."
        #            ↑ overlap: queste parole appaiono in entrambi i chunk
        chunk_size = rag_config.get("chunk_size", 1000)
        chunk_overlap = rag_config.get("chunk_overlap", 200)
        self.splitter = RecursiveSplitter(max_char=chunk_size, overlap=chunk_overlap)
        logger.info(f"Splitter configurato: chunk_size={chunk_size}, overlap={chunk_overlap}")

        # --- 4. Vector Store: dove salviamo i vettori ---
        # Qdrant in modalità locale: salva i dati su disco nella cartella
        # specificata (es. ./data/vectordb). Non serve un server esterno!
        #
        # Nota tecnica: QdrantVectorstore richiede "host" o "location".
        # Per lo storage locale su file, passiamo location=None e path=<cartella>.
        # Il path viene poi inoltrato a QdrantClient che crea i file.
        vs_path = vs_config.get("location", "./data/vectordb")
        self.vectorstore = QdrantVectorstore(location=None, path=vs_path)
        logger.info(f"Qdrant configurato: path={vs_path}")

    def ingest(self, path: str) -> int:
        """
        Esegue la pipeline su un file singolo (.pdf, .md, .txt) o una cartella.

        Se path è una cartella, processa tutti i .pdf, .md e .txt al suo interno
        e ricostruisce l'indice BM25 con tutti i chunk in un'unica passata.

        Returns:
            Numero totale di chunk creati e salvati nel vector DB.
        """
        input_path = Path(path)
        if input_path.is_dir():
            return self._ingest_directory(input_path)
        return self._ingest_single_file(str(input_path))

    def _ingest_directory(self, dir_path: Path) -> int:
        """Processa tutti i file .pdf, .md e .txt in una cartella."""
        files_by_ext = {
            ".pdf": sorted(dir_path.glob("*.pdf")),
            ".md":  sorted(dir_path.glob("*.md")),
            ".txt": sorted(dir_path.glob("*.txt")),
        }
        total = sum(len(v) for v in files_by_ext.values())
        logger.info(f"Inizio ingestion cartella: {dir_path} — {total} file trovati")
        for ext, files in files_by_ext.items():
            if files:
                logger.info(f"  {ext}: {len(files)} file ({', '.join(f.name for f in files)})")

        if total == 0:
            logger.warning("Nessun file .pdf, .md o .txt trovato nella cartella")
            return 0

        all_chunks: list[Chunk] = []
        for ext, files in files_by_ext.items():
            for file_path in files:
                all_chunks.extend(self._extract_embed_store(str(file_path)))

        if all_chunks:
            self._build_bm25_index(all_chunks)
        logger.info(f"Ingestion cartella completata! {len(all_chunks)} chunk totali da {total} file")
        return len(all_chunks)

    def _ingest_single_file(self, file_path: str) -> int:
        """Processa un singolo file e aggiorna l'indice BM25."""
        logger.info(f"Inizio ingestion: {file_path}")
        chunks = self._extract_embed_store(file_path)
        if chunks:
            self._build_bm25_index(chunks)
            logger.info(f"Ingestion completata! {len(chunks)} chunk salvati in Qdrant")
        return len(chunks)

    def _extract_embed_store(self, file_path: str) -> list[Chunk]:
        """Steps 1–5 per un singolo file: estrai → parse → chunk → embed → store."""
        file_path = str(Path(file_path))
        ext = Path(file_path).suffix.lower()

        if ext == ".pdf":
            text = self._extract_text(file_path)
        elif ext in (".md", ".txt"):
            text = self._extract_text_from_markdown(file_path)
        else:
            raise ValueError(f"Formato non supportato: {ext}. Usa .pdf, .md o .txt")

        node = self._parse_text(text, source=file_path)
        chunks = self._split_into_chunks(node, source=file_path)
        chunks = self._add_chunk_headers(chunks)
        chunks = self._embed_chunks(chunks)
        self._store_chunks(chunks)
        return chunks

    def _extract_text(self, pdf_path: str) -> str:
        """
        Step 1: Estrae tutto il testo da un file PDF.

        Usa PyMuPDF (importato come 'fitz') per leggere ogni pagina
        del PDF e concatenare il testo.

        Perché PyMuPDF? È veloce, leggero e gestisce bene i PDF
        istituzionali come quelli di EUR-Lex.
        """
        logger.info("Step 1/5: Estrazione testo dal PDF...")

        # fitz.open() apre il PDF come un oggetto "documento"
        doc = fitz.open(pdf_path)
        num_pages = len(doc)  # Salva il numero di pagine prima di chiudere

        full_text = ""
        for page in doc:
            # get_text() estrae il testo dalla pagina
            page_text = page.get_text()
            full_text += page_text

        doc.close()  # Chiudi il file quando hai finito

        # Rimuovi spazi multipli e righe vuote in eccesso
        # (i PDF istituzionali spesso hanno formattazione strana)
        lines = full_text.split("\n")
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        clean_text = "\n".join(cleaned_lines)

        logger.info(f"  Estratti {len(clean_text)} caratteri da {num_pages} pagine")
        return clean_text

    def _extract_text_from_markdown(self, file_path: str) -> str:
        """
        Step 1 (alternativo): Legge il testo da un file .md o .txt come testo UTF-8.

        A differenza dei PDF, non richiede librerie esterne — usa solo open().
        Applica la stessa pulizia dei PDF: compatta righe vuote eccessive.
        """
        logger.info(f"Step 1/5: Lettura file testo: {file_path}")
        with open(file_path, encoding="utf-8") as f:
            text = f.read()

        # Compatta righe vuote consecutive (max 2) come per i PDF
        lines = text.split("\n")
        cleaned: list[str] = []
        empty_count = 0
        for line in lines:
            if line.strip() == "":
                empty_count += 1
                if empty_count <= 2:
                    cleaned.append(line)
            else:
                empty_count = 0
                cleaned.append(line)

        clean_text = "\n".join(cleaned)
        logger.info(f"  Letti {len(clean_text)} caratteri da {file_path}")
        return clean_text

    def _parse_text(self, text: str, source: str) -> object:
        """
        Step 2: Analizza il testo e crea un albero strutturato.

        TextParser organizza il testo in una gerarchia:
        DOCUMENT → PARAGRAPH → SENTENCE

        Il metadata 'source' ci permette di sapere da quale file
        viene ogni chunk — utile per citare la fonte nelle risposte.
        """
        logger.info("Step 2/5: Parsing del testo...")

        # parse() prende il testo (stringa) e restituisce un Node
        # (nodo dell'albero). Il metadata viene propagato ai chunk.
        node = self.parser.parse(text, metadata={"source": source})

        logger.info("  Albero del documento creato")
        return node

    def _split_into_chunks(self, node, source: str = "") -> list[Chunk]:
        """
        Step 3: Taglia l'albero in pezzi (chunk) di dimensione gestibile.

        Ogni chunk sarà poi trasformato in un vettore e salvato nel DB.
        Il RecursiveSplitter rispetta la struttura dell'albero:
        cerca di non tagliare a metà frase.
        """
        logger.info("Step 3/5: Chunking del testo...")

        # split() prende un Node e restituisce una lista di Chunk.
        # Ogni Chunk ha: .id (univoco), .text (il contenuto), .metadata
        chunks = self.splitter.split(node)

        # Il RecursiveSplitter NON propaga i metadata del Node ai Chunk.
        # Dobbiamo aggiungere manualmente la fonte a ogni chunk,
        # così quando cerchiamo sappiamo da quale documento viene.
        for chunk in chunks:
            if chunk.metadata is None:
                chunk.metadata = {}
            chunk.metadata["source"] = source

        # Mostra un esempio per capire cosa contiene un chunk
        if chunks:
            logger.info(f"  Creati {len(chunks)} chunk")
            logger.info(f"  Esempio chunk[0] ({len(chunks[0].text)} car.): "
                        f"'{chunks[0].text[:80]}...'")

        return chunks

    def _add_chunk_headers(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Step 3.5: Aggiunge header contestuali a ogni chunk.

        Rileva il tipo di file dal metadata 'source' e delega:
        - .pdf      → _add_pdf_article_headers (pattern "Article N")
        - .md / .txt → _add_markdown_headers   (pattern "# Heading")
        """
        logger.info("Step 3.5: Aggiunta header contestuali ai chunk...")
        if not chunks:
            return chunks

        source = (chunks[0].metadata or {}).get("source", "")
        ext = Path(source).suffix.lower() if source else ""

        if ext in (".md", ".txt"):
            return self._add_markdown_headers(chunks)
        return self._add_pdf_article_headers(chunks)

    def _add_pdf_article_headers(self, chunks: list[Chunk]) -> list[Chunk]:
        """Header per PDF Direttiva EU: pattern 'Article N\\nTitolo'."""
        article_pattern = re.compile(
            r'Article\s+(\d+)\s*\n\s*([^\n]+)', re.IGNORECASE
        )
        current_header = ""
        headers_found = 0

        for chunk in chunks:
            match = article_pattern.search(chunk.text)
            if match:
                current_header = f"Article {match.group(1)} - {match.group(2).strip()}"
                headers_found += 1
            if current_header:
                chunk.text = f"[{current_header}]\n{chunk.text}"
                if chunk.metadata is None:
                    chunk.metadata = {}
                chunk.metadata["article_header"] = current_header

        logger.info(f"  {headers_found} articoli rilevati, "
                    f"header aggiunti a {len(chunks)} chunk")
        return chunks

    def _add_markdown_headers(self, chunks: list[Chunk]) -> list[Chunk]:
        """Header per file Markdown: pattern '# Heading' e '## Heading'."""
        md_header_pattern = re.compile(r'^(#{1,2})\s+(.+)$', re.MULTILINE)
        current_header = ""
        headers_found = 0

        for chunk in chunks:
            match = md_header_pattern.search(chunk.text)
            if match:
                level = "Sezione" if len(match.group(1)) == 1 else "Sottosezione"
                current_header = f"{level}: {match.group(2).strip()}"
                headers_found += 1
            if current_header:
                chunk.text = f"[{current_header}]\n{chunk.text}"
                if chunk.metadata is None:
                    chunk.metadata = {}
                chunk.metadata["article_header"] = current_header

        logger.info(f"  {headers_found} sezioni Markdown rilevate, "
                    f"header aggiunti a {len(chunks)} chunk")
        return chunks

    def _embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Step 4: Trasforma il testo di ogni chunk in un vettore numerico.

        Cos'è un embedding?
        È una lista di 384 numeri (per il modello MiniLM) che "cattura
        il significato" del testo. Due testi che parlano dello stesso
        argomento avranno vettori vicini nello spazio a 384 dimensioni.

        Esempio semplificato (in realtà sono 384 numeri, non 3):
        "gender pay gap" → [0.82, -0.15, 0.43, ...]
        "divario salariale" → [0.79, -0.12, 0.45, ...]  ← vicino!
        "previsioni meteo"  → [-0.31, 0.67, -0.22, ...] ← lontano!

        Usiamo FastEmbed che funziona in locale (nessuna API, nessun costo).
        """
        logger.info("Step 4/5: Creazione embedding...")

        # Estrai il testo da ogni chunk per passarlo all'embedder
        texts = [chunk.text for chunk in chunks]

        # embed() è un GENERATORE (produce risultati uno alla volta).
        # list() lo converte in una lista completa di vettori numpy.
        vectors = list(self.embedder.embed(texts))

        # Associa ogni vettore al suo chunk
        for chunk, vector in zip(chunks, vectors):
            # DenseEmbedding wrappa il vettore con un nome ("dense")
            # che corrisponde alla configurazione del vector DB.
            # .tolist() converte da numpy array a lista Python.
            chunk.embeddings = [
                DenseEmbedding(name="dense", vector=vector.tolist())
            ]

        logger.info(f"  {len(chunks)} embedding creati "
                    f"(dimensione vettore: {len(vectors[0])})")
        return chunks

    def _store_chunks(self, chunks: list[Chunk]):
        """
        Step 5: Salva i chunk con i loro embedding nel vector database.

        Qdrant è un database specializzato per cercare vettori simili.
        Quando poi faremo una domanda, calcoleremo il suo embedding
        e Qdrant troverà i chunk con vettori più vicini.

        Prima di salvare, dobbiamo creare una "collection" (come una
        tabella in un database tradizionale).
        """
        logger.info("Step 5/5: Salvataggio in Qdrant...")

        # Crea la collection se non esiste già.
        # VectorConfig specifica:
        # - name="dense" → deve corrispondere al nome nell'embedding
        # - dimensions=384 → dimensione del vettore MiniLM
        # - distance=COSINE → metrica per misurare la "vicinanza"
        #   (cosine similarity: 1.0 = identici, 0.0 = irrilevanti)
        self.vectorstore.create_collection(
            collection_name=self.collection_name,
            vector_config=[
                VectorConfig(
                    name="dense",
                    format=EmbeddingFormat.DENSE,
                    dimensions=self.vector_dimensions,
                    distance=Distance.COSINE,
                )
            ],
        )

        # Salva tutti i chunk nella collection
        self.vectorstore.add(chunks, collection_name=self.collection_name)

        logger.info(f"  {len(chunks)} chunk salvati nella collection "
                    f"'{self.collection_name}'")

    def _build_bm25_index(self, chunks: list[Chunk]):
        """
        Step 6: Costruisce e salva un indice BM25 per la fusion retrieval.

        BM25 e' un algoritmo classico di ranking basato su keyword:
        trova i documenti che contengono le parole esatte della query,
        pesate per frequenza (TF) e rarità (IDF).

        Combinato con la ricerca vettoriale (dense), cattura la terminologia
        legale specifica ("transposition deadline", "Article 10") che gli
        embedding potrebbero non matchare esattamente.

        L'indice viene salvato come pickle accanto al vectordb.
        """
        from rank_bm25 import BM25Okapi

        logger.info("Step 6/6: Costruzione indice BM25...")

        # Tokenizzazione semplice: lowercase + split su spazi
        # Sufficiente per testo legale in inglese
        corpus = [chunk.text.lower().split() for chunk in chunks]

        bm25 = BM25Okapi(corpus)

        # Salva indice BM25 + testi e metadata dei chunk per il retrieval
        bm25_data = {
            "bm25": bm25,
            "chunk_texts": [chunk.text for chunk in chunks],
            "chunk_ids": [str(chunk.id) for chunk in chunks],
            "chunk_metadata": [chunk.metadata or {} for chunk in chunks],
        }

        bm25_path = Path(self._get_bm25_path())
        bm25_path.parent.mkdir(parents=True, exist_ok=True)

        with open(bm25_path, "wb") as f:
            pickle.dump(bm25_data, f)

        logger.info(f"  Indice BM25 salvato: {bm25_path}")

    def _get_bm25_path(self) -> str:
        """Restituisce il percorso del file indice BM25."""
        config = Config.get_instance()
        vs_path = config.vectorstore_config.get("location", "./data/vectordb")
        return f"{vs_path}/bm25_index.pkl"

    def reset(self):
        """
        Cancella la collection e ricrea da zero.
        Utile durante lo sviluppo per ricominciare l'ingestion.
        """
        try:
            self.vectorstore.delete_collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' eliminata")
        except Exception:
            logger.info(f"Collection '{self.collection_name}' non esisteva, nulla da eliminare")
