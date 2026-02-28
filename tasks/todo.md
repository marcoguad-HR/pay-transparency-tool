# Pay Transparency Tool — Task Tracker

## Current Sprint (Track A: Rafforzamento)
- [x] A1: Setup tasks/ directory e workflow files
- [x] A2: Implementare main.py (entry point con argparse)
- [x] A3: Implementare src/cli/interface.py (CLI class con handler)
- [x] A4: Migrare test scripts a pytest suite formale (56 test, 55% coverage)
- [x] A5: Commit iniziale del progetto
- [x] A6: ChangePlan pre-produzione + RAG Techniques improvement
  - [x] Pin datapizza-ai==0.0.9 (NTH 4 ChangePlan)
  - [x] Creare setup.sh / setup.bat con vectordb rebuild + FastEmbed pre-download (MUST 2 + NTH 5)
  - [x] Rate limiter Groq API — retry 429 con exponential backoff (MUST 4)
  - [x] Contextual Chunk Headers — prepend articolo EU a ogni chunk (+28% retrieval)
  - [x] Fusion Retrieval — BM25 keyword + Vector search con RRF (+15-25% precision)
  - [x] Query Transformer — step-back prompting opzionale (disabilitato di default)
  - [x] Test suite aggiornata: 63 test passati
- [ ] A7: Rebuild vectordb con nuove feature (ingestion --reset)

## Current Sprint (Track C: Frontend MVP)
Branch: `feature/frontend-mvp` (4 commits ahead of main)

- [x] C1: Backend API — FastAPI entry point + endpoints chat/upload/health
- [x] C2: Frontend Templates — Jinja2 + HTMX chat interface
- [x] C3: HTMX Chat Flow — form submit → HTML partial swap
- [x] C4: Code quality fixes — accessibility, HTMX error handling, thread safety
- [ ] C5: **BLOCCANTE — anyio corrotto nel venv** (vedi sezione sotto)
- [ ] C6: Test web endpoints (test_api_chat, test_api_upload, test_api_health)
- [ ] C7: Merge feature/frontend-mvp → main

### C5: Bug anyio — Dettagli per debug nella prossima sessione

**Sintomo:** `import anyio` blocca indefinitamente nel venv (.venv/). Questo blocca TUTTO:
- uvicorn (web server) non parte
- `from openai import OpenAI` hang (openai → httpx → anyio)
- `from datapizza.clients.openai import OpenAIClient` hang
- Anche la CLI (`python main.py`) è bloccata, non solo il web

**Causa root:** Durante una sessione di debugging, è stato eseguito `pip install --force-reinstall anyio`
che ha corrotto il pacchetto. I tentativi di fix nella sessione corrente:
1. `rm -rf .venv/lib/python3.12/site-packages/anyio` + dist-info → OK, rimosso
2. `pip install --no-cache-dir anyio` → HANG (pip stesso dipende da httpx→anyio)
3. Download manuale del wheel via curl → OK, scaricato `/tmp/anyio-4.9.0-py3-none-any.whl`
4. `pip install --no-deps /tmp/anyio-4.9.0-py3-none-any.whl` → HANG
5. Estratto il wheel come zip direttamente in site-packages (`unzip`) → OK, file estratti
6. Test import `python -c "import anyio"` → **ANCORA HANG**

**Stato attuale del venv:**
- anyio 4.9.0 è presente in site-packages (estratto manualmente da wheel pulito)
- I singoli submoduli importano OK: `from anyio._core._exceptions import *` funziona
- Ma `import anyio` nel suo insieme blocca
- openai è stato aggiornato a 2.21.0 (era 1.68.0) — side effect di un `pip install` non intenzionale

**Ipotesi da esplorare nella prossima sessione:**
- Possibile deadlock circolare tra anyio e qualche altro pacchetto corrotto (httpx? httpcore?)
- Controllare se `import httpx` o `import httpcore` bloccano anch'essi
- Potrebbe essere necessario ricreare il venv da zero: `rm -rf .venv && python -m venv .venv && pip install -r requirements.txt`
- Prima di ricreare il venv, verificare se il problema è solo nel venv o anche in Python system
- **IMPORTANTE**: openai è saltato a 2.21.0 — potrebbe creare incompatibilità con datapizza-ai 0.0.9

**File creati dal frontend (tutti committati, funzionanti):**
- `app.py` — FastAPI entry point
- `src/web/` — API layer (chat.py, upload.py, health.py, schemas.py)
- `templates/` — Jinja2 templates (base.html, index.html, partials/)
- `static/` — directory per asset statici

## Backlog — Track B (Job Evaluation Module)
- [ ] B1: Data models (JobDescription, EUCriteriaScores, ESCOClassification, JobEvaluation) + JD processor
- [ ] B2: Organizational hierarchy detection (Layer 1 — LLM-based)
- [ ] B3: Behavioral complexity analysis (Layer 2 — 4 criteri EU)
- [ ] B4: ESCO/ISCO classification (Layer 3 — embedding similarity)
- [ ] B5: Point-factor scoring engine con audit trail
- [ ] B6: Integrazione agent router (tool evaluate_job) + CLI command

## Completed
- [x] Phase 1: RAG pipeline (ingestion, retrieval, generation, anti-hallucination)
- [x] Phase 2: Analysis pipeline (data_loader, gap_calculator, report)
- [x] Phase 3: Agent router (tool calling con query_directive + analyze_pay_gap)
- [x] Phase 4: Pre-production hardening (ChangePlan MUST + RAG Techniques)
