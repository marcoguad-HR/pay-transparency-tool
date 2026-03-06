# 🚀 Deploy Guide — Pay Transparency Tool su Hostinger VPS

## Prerequisiti
- Accesso SSH al VPS (`ssh root@<IP_VPS>`)
- Sottodominio DNS già configurato (A record → IP del VPS)
- Chiave API Groq (ottienila su [console.groq.com/keys](https://console.groq.com/keys))

---

## STEP 1 — Configura il sottodominio DNS su Hostinger (2 min)

1. Entra su **hPanel** → **Domains** → il tuo dominio → **DNS Zone**
2. Aggiungi un record **A**:
   - Host: `pay-transparency` (o il nome che preferisci)
   - Points to: `<IP_VPS>`
   - TTL: 3600
3. Salva — la propagazione DNS richiede 5-30 minuti

> Il tuo tool sarà raggiungibile su: `https://pay-transparency.TUODOMINIO.com`

---

## STEP 2 — Setup iniziale del VPS (3 min, da terminale Mac)

```bash
# Esegui come root sul VPS — installa tutto il necessario
ssh root@<IP_VPS> "bash -s" < scripts/deploy/deploy_server.sh
```

Questo script:
- Aggiorna il sistema
- Installa Python 3.12, nginx, certbot
- Crea l'utente `paytool`
- Configura nginx e il service systemd

---

## STEP 3 — Copia i file dal Mac al VPS (2-5 min)

```bash
# Dalla root del progetto sul Mac
bash scripts/deploy/rsync_to_server.sh <IP_VPS>
```

Questo script copia:
- Tutto il codice sorgente (esclude .venv, .env, cache)
- Il vectordb già popolato (Qdrant + BM25, ~3MB)

---

## STEP 4 — Configura l'app sul VPS (5 min)

```bash
# Connettiti come utente paytool
ssh paytool@<IP_VPS>
cd /home/paytool/pay-transparency-tool

# Setup virtualenv, dipendenze e avvio servizio
bash scripts/deploy/setup_venv.sh
```

**⚠️ Imposta la GROQ_API_KEY:**
```bash
nano .env
# Sostituisci il valore con la tua vera chiave:
# GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

Riavvia il servizio dopo aver salvato:
```bash
sudo systemctl restart paytool
```

---

## STEP 5 — Configura il dominio in nginx (1 min)

```bash
# Sul VPS come root
sudo nano /etc/nginx/sites-available/paytool
```

Sostituisci `YOUR_DOMAIN` con il tuo sottodominio:
```nginx
server_name pay-transparency.TUODOMINIO.com;
```

Salva e ricarica nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## STEP 6 — SSL con Let's Encrypt (2 min)

```bash
# Assicurati che il DNS si sia propagato prima!
# Testa con: ping pay-transparency.TUODOMINIO.com

sudo certbot --nginx -d pay-transparency.TUODOMINIO.com
# Segui le istruzioni → email → accetta TOS → Yes per redirect HTTPS
```

Certbot configura automaticamente il rinnovo automatico. ✅

---

## Verifica finale

```bash
# Controlla che il servizio giri
sudo systemctl status paytool

# Controlla i log
sudo journalctl -u paytool -n 50

# Test endpoint health
curl https://pay-transparency.TUODOMINIO.com/api/health
```

Dovresti vedere: `{"status": "ok", ...}`

---

## URL del tool dopo il deploy

| Pagina | URL |
|--------|-----|
| **App principale** (chatbot + upload) | `https://pay-transparency.TUODOMINIO.com/` |
| **Tool locale** (zero upload, statico) | `https://pay-transparency.TUODOMINIO.com/tool` |

---

## Comandi utili post-deploy

```bash
# Riavviare il servizio
sudo systemctl restart paytool

# Aggiornare il codice (dal Mac)
bash scripts/deploy/rsync_to_server.sh <IP_VPS>
ssh paytool@<IP_VPS> "sudo systemctl restart paytool"

# Vedere i log in tempo reale
sudo journalctl -u paytool -f

# Stato nginx
sudo systemctl status nginx
sudo nginx -t
```

---

## Troubleshooting

### Il servizio non parte
```bash
sudo journalctl -u paytool -n 100 --no-pager
```
Cause comuni: GROQ_API_KEY non impostata, `config.yaml` mancante, errore import.

### nginx 502 Bad Gateway
Il servizio uvicorn non è in esecuzione:
```bash
sudo systemctl restart paytool
sudo systemctl status paytool
```

### SSL: "domain not found"
Il DNS non si è ancora propagato. Aspetta 5-30 minuti e riprova.

### Upload CSV fallisce
Controlla i permessi della directory uploads:
```bash
chown -R paytool:paytool /home/paytool/pay-transparency-tool/data/
chmod -R 755 /home/paytool/pay-transparency-tool/data/
```
