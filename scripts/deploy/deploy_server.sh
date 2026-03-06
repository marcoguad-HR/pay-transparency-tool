#!/usr/bin/env bash
# =============================================================================
# deploy_server.sh — Setup VPS Hostinger (sicuro per server con n8n esistente)
#
# USO (dal Mac):
#   ssh root@76.13.133.101 "bash -s" < scripts/deploy/deploy_server.sh
#
# ⚠️  SICURO per server con servizi esistenti (n8n, ecc.):
#   - NON fa apt-get upgrade (non disturba servizi in esecuzione)
#   - NON tocca nginx sites esistenti (aggiunge solo il nuovo)
#   - NON rimuove il sito default nginx
#   - uvicorn gira su porta 8001 (evita conflitti con altri servizi su 8000)
# =============================================================================

set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }

APP_USER="paytool"
APP_DIR="/home/${APP_USER}/pay-transparency-tool"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║      Pay Transparency Tool — VPS Setup               ║"
echo "║      (modalità sicura — non tocca servizi esistenti) ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. Solo apt update + installa pacchetti mancanti (NO upgrade) ─────────────
# NON facciamo apt-get upgrade per non disturbare n8n e altri servizi
info "Aggiorno lista pacchetti (solo update, niente upgrade)..."
apt-get update -qq

info "Installo pacchetti necessari (skippa quelli già presenti)..."
apt-get install -y -qq \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    nginx \
    certbot \
    python3-certbot-nginx \
    rsync \
    curl \
    build-essential

info "Pacchetti pronti."

# ── 2. Crea utente applicazione (idempotente) ─────────────────────────────────
if id "${APP_USER}" &>/dev/null; then
    warning "Utente '${APP_USER}' esiste già. Salto creazione."
else
    info "Creo utente '${APP_USER}'..."
    useradd -m -s /bin/bash "${APP_USER}"
    info "Utente '${APP_USER}' creato."
fi

# ── 3. Configura SSH keys per paytool (copia da root, no password) ────────────
if [ -f /root/.ssh/authorized_keys ]; then
    info "Configuro SSH keys per '${APP_USER}'..."
    mkdir -p "/home/${APP_USER}/.ssh"
    cp /root/.ssh/authorized_keys "/home/${APP_USER}/.ssh/"
    chown -R "${APP_USER}:${APP_USER}" "/home/${APP_USER}/.ssh"
    chmod 700 "/home/${APP_USER}/.ssh"
    chmod 600 "/home/${APP_USER}/.ssh/authorized_keys"
    info "SSH keys configurate — puoi fare: ssh ${APP_USER}@76.13.133.101"
fi

# ── 4. Crea directory progetto ────────────────────────────────────────────────
info "Creo directory progetto..."
mkdir -p "${APP_DIR}/data/vectordb"
mkdir -p "${APP_DIR}/data/uploads"
mkdir -p "${APP_DIR}/data/reports"
chown -R "${APP_USER}:${APP_USER}" "/home/${APP_USER}"
info "Directory pronte."

# ── 5. Installa service systemd ───────────────────────────────────────────────
# Porta 8001 (non 8000) per evitare conflitti con eventuali altri servizi
info "Installo service systemd per uvicorn (porta 8001)..."

cat > /etc/systemd/system/paytool.service << EOF
[Unit]
Description=Pay Transparency Tool (FastAPI + uvicorn)
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8001 --workers 2
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=paytool

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
info "Service 'paytool' installato (porta interna 8001)."

# ── 6. Aggiungi nginx site (NON tocca siti esistenti come n8n) ────────────────
info "Aggiungo nginx site per paytool (siti esistenti non modificati)..."

cat > /etc/nginx/sites-available/paytool << 'NGINX_EOF'
# Pay Transparency Tool — nginx virtual host
# Dominio: pay-transparency.marcog-ai4hr.cloud
# Interno: proxy a uvicorn su 127.0.0.1:8001

server {
    listen 80;
    server_name pay-transparency.marcog-ai4hr.cloud;

    # Dimensione massima upload CSV
    client_max_body_size 10M;

    # ── local-tool.html — servito direttamente (statico, veloce) ──────────
    location = /tool {
        alias /home/paytool/pay-transparency-tool/local-tool.html;
        add_header Cache-Control "no-cache, must-revalidate";
        add_header X-Content-Type-Options nosniff;
    }

    # ── Static files (CSS, JS) ────────────────────────────────────────────
    location /static/ {
        alias /home/paytool/pay-transparency-tool/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # ── Tutto il resto → FastAPI (uvicorn porta 8001) ─────────────────────
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout generosi per le chiamate RAG
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
    }
}
NGINX_EOF

# Abilita il sito (solo paytool, non tocca altri)
ln -sf /etc/nginx/sites-available/paytool /etc/nginx/sites-enabled/paytool

# Verifica config nginx prima di ricaricare
if nginx -t 2>/dev/null; then
    systemctl reload nginx
    info "nginx ricaricato — sito paytool attivo su porta 80."
else
    warning "Errore nella config nginx. Controlla con: nginx -t"
fi

# ── Fine ───────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║         ✅ Setup VPS completato!                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Passi successivi:"
echo ""
echo "  1. Dal Mac, copia i file:"
echo "     bash scripts/deploy/rsync_to_server.sh 76.13.133.101"
echo ""
echo "  2. Sul VPS, configura l'app:"
echo "     ssh ${APP_USER}@76.13.133.101"
echo "     cd ${APP_DIR}"
echo "     bash scripts/deploy/setup_venv.sh"
echo ""
echo "  3. SSL con Let's Encrypt:"
echo "     sudo certbot --nginx -d pay-transparency.marcog-ai4hr.cloud"
echo ""
