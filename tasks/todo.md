# Pay Transparency Tool — Task Tracker

## Current Sprint (Track A: Rafforzamento)
- [x] A1: Setup tasks/ directory e workflow files
- [x] A2: Implementare main.py (entry point con argparse)
- [x] A3: Implementare src/cli/interface.py (CLI class con handler)
- [x] A4: Migrare test scripts a pytest suite formale (56 test, 55% coverage)
- [ ] A5: Commit iniziale del progetto  <-- IN PROGRESS

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
