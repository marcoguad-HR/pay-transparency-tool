#!/bin/sh
# ===========================================================================
# daily_report.sh — Genera il report analytics giornaliero
#
# Chiamato dal timer systemd paytool-report.timer ogni giorno alle 06:00 UTC.
# Può essere eseguito anche manualmente: bash scripts/daily_report.sh
#
# Funzionalità:
#   - Attiva il venv del progetto
#   - Genera il report per le ultime 24h (data di ieri nel nome file)
#   - Stampa un sommario a stdout (catturato da journald)
#   - Invia il report via email se REPORT_EMAIL è impostata
#   - Elimina i report più vecchi di 90 giorni (retention)
# ===========================================================================

set -eu

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
DATA_DIR="${PROJECT_DIR}/data"
DB_PATH="${DATA_DIR}/analytics.db"
RETENTION_DAYS=90

# Data di ieri (il report copre le ultime 24h)
YESTERDAY="$(date -u -d 'yesterday' '+%Y%m%d')"
REPORT_FILE="${DATA_DIR}/report_${YESTERDAY}.txt"

# ---------------------------------------------------------------------------
# Attivazione venv
# ---------------------------------------------------------------------------
if [ ! -f "${VENV_DIR}/bin/python" ]; then
    echo "[ERRORE] Venv non trovato: ${VENV_DIR}/bin/python" >&2
    exit 1
fi

# Usiamo il python del venv direttamente (senza `source activate`)
PYTHON="${VENV_DIR}/bin/python"

# ---------------------------------------------------------------------------
# Generazione report
# ---------------------------------------------------------------------------
echo "=== paytool-report: inizio generazione $(date -u '+%Y-%m-%d %H:%M:%S') UTC ==="
echo "Periodo: ultime 24h (data report: ${YESTERDAY})"
echo "DB: ${DB_PATH}"
echo "Output: ${REPORT_FILE}"

# Assicurati che la directory data/ esista
mkdir -p "${DATA_DIR}"

# Genera il report (--days 1 = ultime 24h)
"${PYTHON}" "${PROJECT_DIR}/scripts/generate_report.py" \
    --days 1 \
    --db "${DB_PATH}" \
    --output "${REPORT_FILE}"

# Verifica che il file sia stato creato
if [ ! -f "${REPORT_FILE}" ]; then
    echo "[ERRORE] Il report non è stato generato: ${REPORT_FILE}" >&2
    exit 1
fi

REPORT_SIZE="$(wc -c < "${REPORT_FILE}" | tr -d ' ')"
echo "Report generato: ${REPORT_FILE} (${REPORT_SIZE} bytes)"

# Sommario a stdout (le prime 20 righe per journald)
echo ""
echo "--- SOMMARIO ---"
head -20 "${REPORT_FILE}"
echo "--- (fine sommario) ---"

# ---------------------------------------------------------------------------
# Invio email (opzionale)
# ---------------------------------------------------------------------------
if [ -n "${REPORT_EMAIL:-}" ]; then
    SUBJECT="[PayTool] Report analytics ${YESTERDAY}"
    if command -v mail >/dev/null 2>&1; then
        mail -s "${SUBJECT}" "${REPORT_EMAIL}" < "${REPORT_FILE}" \
            && echo "Email inviata a ${REPORT_EMAIL}" \
            || echo "[WARN] Invio email fallito (mail)" >&2
    elif command -v sendmail >/dev/null 2>&1; then
        {
            printf 'To: %s\nSubject: %s\nContent-Type: text/plain; charset=utf-8\n\n' \
                "${REPORT_EMAIL}" "${SUBJECT}"
            cat "${REPORT_FILE}"
        } | sendmail "${REPORT_EMAIL}" \
            && echo "Email inviata a ${REPORT_EMAIL}" \
            || echo "[WARN] Invio email fallito (sendmail)" >&2
    else
        echo "[INFO] Nessun MTA disponibile (mail/sendmail), email non inviata."
    fi
fi

# ---------------------------------------------------------------------------
# Retention: elimina report più vecchi di 90 giorni
# ---------------------------------------------------------------------------
DELETED_COUNT=0
CUTOFF_DATE="$(date -u -d "${RETENTION_DAYS} days ago" '+%Y%m%d')"

for f in "${DATA_DIR}"/report_*.txt; do
    # Salta se il glob non ha trovato nulla
    [ -e "$f" ] || continue

    # Estrai la data dal nome file (report_YYYYMMDD.txt)
    BASENAME="$(basename "$f")"
    FILE_DATE="$(echo "${BASENAME}" | sed 's/^report_//;s/\.txt$//')"

    # Verifica che sia un formato data valido (8 cifre)
    case "${FILE_DATE}" in
        [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]) ;;
        *) continue ;;
    esac

    # Confronto lessicografico (funziona con YYYYMMDD)
    if [ "${FILE_DATE}" \< "${CUTOFF_DATE}" ]; then
        rm -f "$f"
        DELETED_COUNT=$((DELETED_COUNT + 1))
    fi
done

if [ "${DELETED_COUNT}" -gt 0 ]; then
    echo "Retention: eliminati ${DELETED_COUNT} report più vecchi di ${RETENTION_DAYS} giorni"
fi

echo "=== paytool-report: completato $(date -u '+%Y-%m-%d %H:%M:%S') UTC ==="
