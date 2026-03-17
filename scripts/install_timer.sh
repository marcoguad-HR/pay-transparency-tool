#!/bin/sh
# ===========================================================================
# install_timer.sh — Installa il timer systemd per il report giornaliero
#
# Uso:
#   sudo bash scripts/install_timer.sh
#
# Prerequisiti:
#   - Eseguire come root (o con sudo)
#   - I file .service e .timer devono essere in deploy/systemd/
# ===========================================================================

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SYSTEMD_SRC="${PROJECT_DIR}/deploy/systemd"
SYSTEMD_DST="/etc/systemd/system"

SERVICE_NAME="paytool-report"

# ---------------------------------------------------------------------------
# Verifica permessi
# ---------------------------------------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
    echo "[ERRORE] Questo script deve essere eseguito come root." >&2
    echo "Uso: sudo $0" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Verifica file sorgente
# ---------------------------------------------------------------------------
for unit in "${SERVICE_NAME}.service" "${SERVICE_NAME}.timer"; do
    if [ ! -f "${SYSTEMD_SRC}/${unit}" ]; then
        echo "[ERRORE] File non trovato: ${SYSTEMD_SRC}/${unit}" >&2
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Rendi eseguibile lo script daily_report.sh
# ---------------------------------------------------------------------------
DAILY_SCRIPT="${PROJECT_DIR}/scripts/daily_report.sh"
if [ -f "${DAILY_SCRIPT}" ]; then
    chmod +x "${DAILY_SCRIPT}"
    echo "[OK] ${DAILY_SCRIPT} reso eseguibile"
else
    echo "[WARN] ${DAILY_SCRIPT} non trovato — assicurati che esista prima di avviare il timer" >&2
fi

# ---------------------------------------------------------------------------
# Copia unit files
# ---------------------------------------------------------------------------
echo "Copio unit files in ${SYSTEMD_DST}/ ..."
cp "${SYSTEMD_SRC}/${SERVICE_NAME}.service" "${SYSTEMD_DST}/"
cp "${SYSTEMD_SRC}/${SERVICE_NAME}.timer"   "${SYSTEMD_DST}/"
echo "[OK] File copiati"

# ---------------------------------------------------------------------------
# Reload, abilita, avvia
# ---------------------------------------------------------------------------
echo "Eseguo systemctl daemon-reload ..."
systemctl daemon-reload
echo "[OK] daemon-reload completato"

echo "Abilito ${SERVICE_NAME}.timer ..."
systemctl enable "${SERVICE_NAME}.timer"
echo "[OK] Timer abilitato"

echo "Avvio ${SERVICE_NAME}.timer ..."
systemctl start "${SERVICE_NAME}.timer"
echo "[OK] Timer avviato"

# ---------------------------------------------------------------------------
# Verifica
# ---------------------------------------------------------------------------
echo ""
echo "=== Stato del timer ==="
systemctl status "${SERVICE_NAME}.timer" --no-pager || true

echo ""
echo "=== Timer schedulati ==="
systemctl list-timers "${SERVICE_NAME}.timer" --no-pager || true

echo ""
echo "Installazione completata."
echo "Per testare manualmente: sudo systemctl start ${SERVICE_NAME}.service"
echo "Per i log: journalctl -u ${SERVICE_NAME}.service --since today"
