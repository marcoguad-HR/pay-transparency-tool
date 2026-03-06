.PHONY: setup setup-clean test verify web cli freeze report report-weekly report-save help

help:  ## Mostra comandi disponibili
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup:  ## Setup venv e installa dipendenze
	bash setup.sh

setup-clean:  ## Ricrea venv da zero (nuclear option)
	bash setup.sh --clean

test:  ## Esegui tutti gli unit test
	.venv/bin/python -m pytest tests/ -v --tb=short --ignore=tests/integration

verify:  ## Verifica che tutti gli import critici funzionino
	.venv/bin/python scripts/verify_imports.py

web:  ## Avvia il frontend web (uvicorn)
	.venv/bin/uvicorn app:app --reload --host 127.0.0.1 --port 8000

cli:  ## Avvia la CLI agent interattiva
	.venv/bin/python main.py agent

freeze:  ## Aggiorna requirements-lock.txt con le versioni attuali
	.venv/bin/pip freeze > requirements-lock.txt
	@echo "requirements-lock.txt aggiornato"

report:  ## Report utilizzo ultimi 30 giorni
	.venv/bin/python scripts/generate_report.py

report-weekly:  ## Report utilizzo ultimi 7 giorni
	.venv/bin/python scripts/generate_report.py --days 7

report-save:  ## Salva report su file con data odierna
	.venv/bin/python scripts/generate_report.py --output data/report_$(shell date +%Y%m%d).txt
