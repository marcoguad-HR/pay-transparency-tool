#!/usr/bin/env bash
# setup.sh — Setup automatico per Pay Transparency Tool
#
# Cosa fa:
# 1. Crea un virtual environment Python (se non esiste)
# 2. Installa le dipendenze da requirements.txt
# 3. Verifica che tutti gli import critici funzionino
# 4. Pre-scarica il modello FastEmbed (~91 MB, solo al primo avvio)
# 5. Ricostruisce il vector database se mancante (ingestion PDF)
#
# Flags:
#   --clean    Ricrea il venv da zero (nuclear option per problemi di dipendenze)
#
# Uso:
#   bash setup.sh          # Setup normale
#   bash setup.sh --clean  # Ricrea venv da zero

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

CLEAN=false
if [[ "${1:-}" == "--clean" ]]; then
    CLEAN=true
fi

# Trova Python 3.12+ (Homebrew o sistema)
PYTHON=""
for candidate in /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 python3.12 python3; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERRORE: Python >= 3.10 non trovato. Installalo con: brew install python@3.12"
    exit 1
fi

echo "=== Pay Transparency Tool — Setup ==="
echo ""
echo "Python: $($PYTHON --version)"
echo ""

# --- 1. Virtual environment ---
if [ "$CLEAN" = true ] && [ -d ".venv" ]; then
    echo "Flag --clean: rimozione venv esistente..."
    rm -rf .venv
    echo "Venv rimosso."
fi

if [ ! -d ".venv" ]; then
    echo "Creazione virtual environment..."
    "$PYTHON" -m venv .venv
    echo "Virtual environment creato in .venv/"
else
    echo "Virtual environment esistente trovato."
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# --- 2. Dipendenze ---
echo ""
echo "Installazione dipendenze..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "Dipendenze installate."

# --- 3. Verifica import critici ---
echo ""
echo "Verifica import critici..."
python scripts/verify_imports.py

# --- 4. Pre-download modello FastEmbed ---
# FastEmbed scarica il modello MiniLM-L6 (~91 MB da Hugging Face) al primo import.
# Lo facciamo qui con feedback visivo, invece di lasciare che succeda silenziosamente
# alla prima query (dove su reti lente potrebbe sembrare che il tool si sia bloccato).
echo ""
echo "Download modello ML (solo al primo avvio, ~91 MB)..."
python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2')"
echo "Modello pronto."

# --- 5. Ricostruzione vector database ---
# Il vectordb non e' nel repository Git (e' in .gitignore).
# Dopo un fresh clone, va ricostruito dal PDF sorgente.
VECTORDB_PATH="data/vectordb/collection/eu_directive_2023_970"
PDF_EN="data/documents/CELEX_32023L0970_EN_TXT.pdf"

echo ""
if [ ! -d "$VECTORDB_PATH" ]; then
    echo "Vector database non trovato. Ricostruzione dal PDF..."
    if [ -f "$PDF_EN" ]; then
        python main.py ingest "$PDF_EN" --reset
        echo "Vector database ricostruito."
    else
        echo "ATTENZIONE: PDF non trovato in $PDF_EN"
        echo "Scaricalo con:  python scripts/download_directive.py"
        echo "Poi esegui:     python main.py ingest $PDF_EN --reset"
    fi
else
    echo "Vector database esistente. Ricostruzione saltata."
fi

# --- Fine ---
echo ""
echo "=== Setup completato! ==="
echo ""
echo "Per iniziare:"
echo "  source .venv/bin/activate"
echo "  python main.py agent          # CLI interattiva"
echo "  uvicorn app:app --reload      # Web frontend"
echo ""
echo "Se qualcosa non funziona:"
echo "  bash setup.sh --clean         # Ricrea il venv da zero"
