#!/usr/bin/env bash
# =============================================================================
# setup_venv.sh — Configura il venv Python e l'app sul VPS
#
# USO (sul VPS, come utente paytool):
#   cd /home/paytool/pay-transparency-tool
#   bash scripts/deploy/setup_venv.sh
#
# Cosa fa:
#   1. Crea il virtualenv Python 3.12
#   2. Installa tutte le dipendenze da requirements-lock.txt
#   3. Verifica che il vectordb esista
#   4. Chiede di configurare il file .env (GROQ_API_KEY)
#   5. Avvia il service uvicorn
# =============================================================================

set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Pay Transparency Tool — App Setup sul VPS        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
info "Directory progetto: ${APP_DIR}"
echo ""

# ── Verifica di essere nella directory giusta ─────────────────────────────────
[ -f "${APP_DIR}/app.py" ] || error "app.py non trovato. Sei nella directory giusta? (${APP_DIR})"

# ── 1. Crea virtualenv ────────────────────────────────────────────────────────
info "Creo virtualenv Python 3.12..."
python3.12 -m venv "${APP_DIR}/.venv"
source "${APP_DIR}/.venv/bin/activate"
pip install --upgrade pip --quiet
info "Virtualenv creato e attivato."

# ── 2. Installa dipendenze ────────────────────────────────────────────────────
info "Installo dipendenze (potrebbe richiedere qualche minuto)..."
if [ -f "${APP_DIR}/requirements-lock.txt" ]; then
    pip install -r "${APP_DIR}/requirements-lock.txt" --quiet
    info "Dipendenze installate da requirements-lock.txt."
else
    pip install -r "${APP_DIR}/requirements.txt" --quiet
    info "Dipendenze installate da requirements.txt."
fi

# ── 3. Verifica vectordb ──────────────────────────────────────────────────────
if [ -d "${APP_DIR}/data/vectordb/collection" ] && [ -f "${APP_DIR}/data/vectordb/bm25_index.pkl" ]; then
    info "Vectordb presente e completo."
else
    warning "Vectordb non trovato o incompleto in data/vectordb/"
    warning "Devi copiarlo dal Mac con rsync_to_server.sh oppure rieseguire l'ingestion."
fi

# ── 4. Configura .env ─────────────────────────────────────────────────────────
if [ -f "${APP_DIR}/.env" ]; then
    info "File .env trovato."
    # Controlla che GROQ_API_KEY non sia il placeholder
    if grep -q "your-api-key-here" "${APP_DIR}/.env"; then
        warning "ATTENZIONE: .env contiene ancora il placeholder 'your-api-key-here'!"
        warning "Aggiornalo con la tua vera GROQ_API_KEY:"
        echo "     nano ${APP_DIR}/.env"
        echo ""
    fi
else
    warning "File .env non trovato. Lo creo dal template..."
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env" 2>/dev/null || echo "GROQ_API_KEY=your-api-key-here" > "${APP_DIR}/.env"
    warning "⚠️  IMPORTANTE: configura la tua GROQ_API_KEY prima di avviare il servizio!"
    warning "   nano ${APP_DIR}/.env"
    echo ""
    echo "  Ottieni la tua chiave su: https://console.groq.com/keys"
    echo ""
fi

# ── 5. Configura config.yaml ──────────────────────────────────────────────────
if [ ! -f "${APP_DIR}/config.yaml" ]; then
    info "Copio config.yaml da example..."
    cp "${APP_DIR}/config.yaml.example" "${APP_DIR}/config.yaml"
fi

# ── 6. Assicura permessi corretti ─────────────────────────────────────────────
chmod -R 755 "${APP_DIR}"
chmod 600 "${APP_DIR}/.env" 2>/dev/null || true
info "Permessi configurati."

# ── 7. Avvia il service ───────────────────────────────────────────────────────
info "Abilito e avvio il service paytool..."
sudo systemctl enable paytool
sudo systemctl restart paytool
sleep 2

# Verifica che sia partito
if systemctl is-active --quiet paytool; then
    info "Service paytool avviato con successo!"
else
    warning "Il service non è partito. Controlla i log:"
    echo "     sudo journalctl -u paytool -n 50"
fi

# ── Fine ───────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║             ✅ App configurata!                       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Verifica lo stato del servizio:"
echo "  sudo systemctl status paytool"
echo ""
echo "  Vedi i log in tempo reale:"
echo "  sudo journalctl -u paytool -f"
echo ""
echo "  Test rapido (dovrebbe rispondere OK):"
echo "  curl http://127.0.0.1:8001/api/health"
echo ""
echo "  ⚠️  Ricorda di:"
echo "  1. Aggiornare /etc/nginx/sites-available/paytool con il tuo dominio"
echo "  2. Eseguire: sudo certbot --nginx -d YOUR_DOMAIN"
echo ""
