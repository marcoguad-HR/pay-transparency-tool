# Lessons Learned

## [2026-02-18] Decisioni architetturali iniziali
- **Qdrant locale**: Usato in modalità file-based (`location=None, path=vs_path`) per evitare dipendenza da server esterno. Cosine similarity per la collection.
- **FastEmbed offline**: `sentence-transformers/all-MiniLM-L6-v2` (384 dim) per embeddings locali senza costi API.
- **Groq/Llama 3.3**: Scelto per il free tier e il modello open-source. Client OpenAI-compatible via `datapizza.clients.openai.OpenAIClient`.
- **Anti-hallucination come LLM call separata**: Il verificatore usa `temperature=0.0` per output deterministico. Parsing JSON con fallback multipli (direct, substring extraction, default).
- **datapizza-ai framework**: Usato per RAG pipeline (`TextParser`, `RecursiveSplitter`, `QdrantVectorstore`) e agent (`Agent`, `@tool`). I tool devono restituire `str`, non oggetti complessi.
- **Annotated types per tool params**: `Annotated[str, "descrizione"]` è il modo in cui datapizza descrive i parametri al LLM.

## [2026-02-19] Pre-production hardening + RAG Techniques
- **Rate limiter centralizzato**: `invoke_with_retry()` in `src/utils/rate_limiter.py` wrappa tutte le chiamate Groq. Exponential backoff (2s, 4s, 8s) con max 3 retry. `RateLimitError` custom catturata dalla CLI per messaggi user-friendly.
- **Contextual Chunk Headers**: Prepend `[Article N - Title]` a ogni chunk prima dell'embedding. Il retriever propaga `article_header` nei metadata. Migliora il retrieval su documenti legali strutturati del ~28% (benchmark da NirDiamant/RAG_Techniques).
- **Fusion Retrieval (BM25 + Vector)**: Indice BM25 costruito durante ingestion (Step 6), salvato come pickle in `data/vectordb/bm25_index.pkl`. Il retriever combina i risultati con Reciprocal Rank Fusion (RRF, k=60). Fallback graceful a solo-vettoriale se BM25 non disponibile.
- **Query Transformer (Step-back Prompting)**: Genera una versione piu' ampia della query per recuperare contesto complementare. Disabilitato di default (`rag.query_transform_enabled: false`) per rispettare il rate limit Groq (ogni trasformazione = 1 LLM call extra).
- **Setup scripts**: `setup.sh` e `setup.bat` creano venv, installano deps, pre-scaricano FastEmbed (~91MB), e ricostruiscono il vectordb se mancante. Risolve il problema del fresh clone senza vectordb.
- **Pin dipendenze**: `datapizza-ai==0.0.9` pinnato per evitare breaking changes da versioni 0.x instabili.

## [2026-02-20] Frontend MVP + Bug anyio

### Frontend MVP (funzionante, non testabile per bug anyio)
- **Stack scelto**: FastAPI + Jinja2 + HTMX + Tailwind CSS (CDN). Zero JS custom, zero build system.
- **Pattern HTMX**: Gli endpoint `/api/chat` e `/api/upload` ritornano **HTML partials** (non JSON). HTMX li inietta nel DOM con `hx-swap="beforeend"`. Bisogna gestire `htmx:beforeSwap` per status non-200.
- **Thread safety**: Il `PayTransparencyRouter` viene inizializzato lazy con double-checked locking (`threading.Lock()`) perché uvicorn usa thread pool.
- **File upload**: Validazione server-side (estensioni .csv/.xlsx/.xls, max 10MB). File salvato in /tmp con cleanup in `finally`.
- **Health check**: Non crea `QdrantClient` (causerebbe file lock leak). Controlla filesystem (`data/vectordb/`) + env var `GROQ_API_KEY`.
- **PWA/Mobile rimosso dallo scope MVP** — l'utente ha detto: "MVP non deve avere usabilita da mobile ma solo front end dove testare RAG"

### Bug anyio — RISOLTO (2026-02-21)
- **Causa**: `pip install --force-reinstall anyio` dentro un venv attivo ha corrotto il bytecode cache, creando un deadlock circolare (pip → httpx → anyio → hang).
- **Fix applicato**: Ricreazione del venv da zero con Python 3.12.12 (`/opt/homebrew/bin/python3.12`).
- **Nota**: il `python3` di macOS CommandLineTools e' Python 3.9.6 — il venv va creato con il Python di Homebrew.
- openai 2.21.0 confermato compatibile con datapizza-ai 0.0.9 (constraint: `openai>=2,<3`).
- PyMuPDF mancava dal requirements.txt originale — aggiunto.

### Regole di prevenzione dipendenze
- **MAI `pip install --force-reinstall`** su pacchetti low-level (anyio, httpx, httpcore). pip stesso dipende da httpx → anyio, il che crea deadlock irrecuperabili.
- **Se il venv si corrompe**: `bash setup.sh --clean` (ricrea da zero).
- **Dopo qualsiasi `pip install`**: eseguire `make verify` (o `python scripts/verify_imports.py`) per controllare che nessun import si blocchi.
- **Dipendenze transitive critiche** (anyio, httpx, httpcore, openai) sono ora pinnate in requirements.txt con range constraint.
- **Lock file**: `requirements-lock.txt` contiene le versioni esatte risolte da pip. Per install riproducibili: `pip install -r requirements-lock.txt`.

## [2026-02-18] Insight da Axiomera per future implementazioni
- Il contesto organizzativo è il predittore più forte del job grade (più della tassonomia occupazionale da sola).
- La calibrazione universale è raggiungibile: stessi parametri producono risultati consistenti tra organizzazioni diverse.
- Gli indicatori di complessità comportamentale sono essenziali per l'auditabilità regolamentare (la Direttiva richiede spiegabilità, non solo accuratezza).
- Sistema progettato come "consultant productivity tool": suggerisce, il professionista verifica e approva.
