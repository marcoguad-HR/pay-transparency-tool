#!/usr/bin/env bash
# =============================================================================
# rsync_to_server.sh — Copia il progetto dal Mac al VPS Hostinger
#
# USO (dalla root del progetto):
#   bash scripts/deploy/rsync_to_server.sh <IP_VPS>
#
# Esempio:
#   bash scripts/deploy/rsync_to_server.sh 185.123.45.67
#
# Cosa fa:
#   1. Copia tutto il codice sorgente (esclude venv, cache, file sensibili)
#   2. Copia il vectordb (Qdrant + BM25) — già generato in locale
#
# La prima volta chiede la password root del VPS.
# Dopo aver configurato le SSH keys non serve più la password.
# =============================================================================

set -e  # Fermati se un comando fallisce

# ── Colori per output ─────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ── Parametri ─────────────────────────────────────────────────────────────────
VPS_IP="${1:?Uso: bash scripts/deploy/rsync_to_server.sh <IP_VPS>}"
VPS_USER="paytool"           # Utente sul VPS (creato da deploy_server.sh)
REMOTE_DIR="/home/paytool/pay-transparency-tool"
LOCAL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"  # Root del progetto

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║      Pay Transparency Tool — Deploy to Hostinger     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
info "Sorgente locale: ${LOCAL_DIR}"
info "Destinazione:    ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}"
echo ""

# ── Prima esecuzione: usa root per creare l'utente paytool ────────────────────
# Controlla se l'utente paytool esiste già
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${VPS_USER}@${VPS_IP}" exit 2>/dev/null; then
    warning "Utente '${VPS_USER}' non ancora configurato. Provo con root..."
    warning "Assicurati di aver eseguito prima: bash scripts/deploy/deploy_server.sh ${VPS_IP}"
    echo ""
fi

# ── rsync codice sorgente ─────────────────────────────────────────────────────
info "Copio codice sorgente (escludo venv, cache, file sensibili)..."

rsync -avz --progress \
    --exclude='.venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='.env' \
    --exclude='data/vectordb/' \
    --exclude='data/uploads/' \
    --exclude='data/reports/' \
    --exclude='.pytest_cache/' \
    --exclude='*.egg-info/' \
    --exclude='.DS_Store' \
    --exclude='tasks/' \
    --exclude='docs/' \
    --exclude='tests/' \
    --exclude='scripts/deploy/' \
    "${LOCAL_DIR}/" \
    "${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/"

echo ""
info "Codice sorgente copiato."

# ── rsync vectordb (già popolato in locale) ────────────────────────────────────
info "Copio vectordb (Qdrant + BM25) — potrebbe richiedere qualche minuto..."

rsync -avz --progress \
    "${LOCAL_DIR}/data/vectordb/" \
    "${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/data/vectordb/"

echo ""
info "Vectordb copiato."

# ── Fine ───────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║            ✅ Sync completato!                        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Passo successivo sul VPS:"
echo "  ssh ${VPS_USER}@${VPS_IP}"
echo "  cd ${REMOTE_DIR}"
echo "  bash scripts/deploy/setup_venv.sh"
echo ""
