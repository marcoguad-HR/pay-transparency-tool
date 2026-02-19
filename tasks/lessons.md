# Lessons Learned

## [2026-02-18] Decisioni architetturali iniziali
- **Qdrant locale**: Usato in modalità file-based (`location=None, path=vs_path`) per evitare dipendenza da server esterno. Cosine similarity per la collection.
- **FastEmbed offline**: `sentence-transformers/all-MiniLM-L6-v2` (384 dim) per embeddings locali senza costi API.
- **Groq/Llama 3.3**: Scelto per il free tier e il modello open-source. Client OpenAI-compatible via `datapizza.clients.openai.OpenAIClient`.
- **Anti-hallucination come LLM call separata**: Il verificatore usa `temperature=0.0` per output deterministico. Parsing JSON con fallback multipli (direct, substring extraction, default).
- **datapizza-ai framework**: Usato per RAG pipeline (`TextParser`, `RecursiveSplitter`, `QdrantVectorstore`) e agent (`Agent`, `@tool`). I tool devono restituire `str`, non oggetti complessi.
- **Annotated types per tool params**: `Annotated[str, "descrizione"]` è il modo in cui datapizza descrive i parametri al LLM.

## [2026-02-18] Insight da Axiomera per future implementazioni
- Il contesto organizzativo è il predittore più forte del job grade (più della tassonomia occupazionale da sola).
- La calibrazione universale è raggiungibile: stessi parametri producono risultati consistenti tra organizzazioni diverse.
- Gli indicatori di complessità comportamentale sono essenziali per l'auditabilità regolamentare (la Direttiva richiede spiegabilità, non solo accuratezza).
- Sistema progettato come "consultant productivity tool": suggerisce, il professionista verifica e approva.
