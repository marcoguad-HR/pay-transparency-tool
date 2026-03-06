# Changelog

Tutte le modifiche rilevanti al progetto sono documentate in questo file.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it-IT/1.1.0/),
e il progetto aderisce al [Semantic Versioning](https://semver.org/lang/it/).

---

## [1.0.0] — 2026-03-06

Prima release pubblica del Pay Transparency Tool.

### Aggiunto

- **Chatbot RAG** sulla Direttiva EU 2023/970 con supporto documenti IT/EN
  - Pipeline RAG: FastEmbed (MiniLM-L6-v2) + Qdrant (locale) + BM25 Fusion Retrieval
  - LLM: Groq API con Llama 3.3-70b-versatile
  - Meccanismi anti-allucinazione e confidence scoring
  - Step-back prompting opzionale per query complesse
- **Analisi Gender Pay Gap** completa
  - Gap medio e mediano complessivo
  - Gap per categoria (dipartimento + livello)
  - Distribuzione per quartili retributivi
  - Analisi bonus gap
  - Verifica compliance con soglia EU del 5%
- **Interfaccia web** moderna con FastAPI + HTMX + Jinja2 + Tailwind CSS
  - Tab "Assistente" per chat con il chatbot normativo
  - Tab "Analisi Dati" per upload CSV/Excel e visualizzazione risultati
  - Design responsive con effetti frosted glass
- **Tool locale offline** (single HTML file)
  - Analisi pay gap interamente nel browser
  - Zero dati inviati a server esterni
  - Funziona senza connessione internet dopo il download
- **Interfaccia CLI** con comandi: `ingest`, `query`, `analyze`, `agent`
- **Agent Router** intelligente per routing automatico query → RAG o analisi dati
- **API REST**: `/api/chat`, `/api/upload`, `/api/health`
- **Sistema di analytics** per monitoraggio utilizzo
- **Rate limiter** per gestione limiti API Groq
- **Dataset demo** con 500 dipendenti fittizi per test
- **Documentazione completa**: guida utente, guida tecnica, formato dati, FAQ
- **10 moduli di test** (unit + integration)
- **Makefile** con comandi per setup, test, avvio, report

### Stack tecnologico

- Python 3.11+ / FastAPI / HTMX / Jinja2 / Tailwind CSS
- FastEmbed + Qdrant + BM25 (retrieval ibrido)
- Groq API + Llama 3.3-70b-versatile
- pandas + openpyxl (analisi dati)
- Licenza MIT

---

[1.0.0]: https://github.com/marcoguadagno/pay-transparency-tool/releases/tag/v1.0.0
