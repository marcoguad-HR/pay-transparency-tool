# Guida Tecnica - Pay Transparency Tool

**Versione**: 1.0
**Data**: Marzo 2026
**Lingua**: Italiano
**Destinatari**: Sviluppatori, DevOps, Contributor

Benvenuti nella guida tecnica del Pay Transparency Tool! Questa documentazione copre l'architettura del sistema, l'installazione, la configurazione e come contribuire al progetto.

---

## Indice

1. [Panoramica Architettura](#panoramica-architettura)
2. [Componenti Principali](#componenti-principali)
3. [Struttura del Progetto](#struttura-del-progetto)
4. [Requisiti e Dipendenze](#requisiti-e-dipendenze)
5. [Installazione Step-by-Step](#installazione-step-by-step)
6. [Configurazione](#configurazione)
7. [Esecuzione](#esecuzione)
8. [API Endpoints](#api-endpoints)
9. [Testing](#testing)
10. [Comandi Makefile](#comandi-makefile)
11. [Contribuire al Progetto](#contribuire-al-progetto)

---

## Panoramica Architettura

Il Pay Transparency Tool è una piattaforma multi-interfaccia che unisce:

- **RAG Pipeline (Retrieval-Augmented Generation)**: Chatbot AI che risponde domande sulla Direttiva EU 2023/970
- **Pay Gap Analysis**: Analizzatore statistico per calcolare il divario retributivo di genere
- **Interfacce Multiple**: Web (FastAPI), CLI, Strumento locale stand-alone
- **Routing Intelligente**: Agent che dirige le query al componente appropriato

### Diagramma Architetturale

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INTERFACCE UTENTE                               │
├──────────────┬──────────────────────┬──────────────┬────────────────────┤
│   Web UI     │   CLI Interactive    │  Local Tool  │   Agent Router     │
│  (FastAPI)   │   (main.py)          │  (HTML/JS)   │   (datapizza-ai)   │
└──────────────┴──────────────────────┴──────────────┴────────────────────┘
               │                                              │
        ┌──────▼──────────┐                        ┌─────────▼──────────┐
        │  RAG PIPELINE   │                        │ PAY GAP ANALYSIS   │
        │                 │                        │                    │
        ├─────────────────┤                        ├────────────────────┤
        │ • Ingestion     │                        │ • DataLoader       │
        │ • Retrieval     │                        │ • GapCalculator    │
        │ • Generation    │                        │ • Report Generator │
        │ • Anti-halluc.  │                        └────────────────────┘
        └────────┬────────┘
                 │
        ┌────────▼────────────────────┐
        │  STORAGE & SERVICES         │
        ├─────────────────────────────┤
        │ • Qdrant VectorDB           │
        │ • SQLite Analytics          │
        │ • Groq API (LLM)            │
        │ • FastEmbed Embeddings      │
        │ • BM25 Indexing             │
        └─────────────────────────────┘
```

---

## Componenti Principali

### 1. RAG Pipeline (AI Chatbot)

Il RAG Pipeline consente al sistema di rispondere a domande sulla normativa EU con precisione, utilizzando i documenti originali come fonte di verità.

#### Ingestion (Inserimento Dati)

**Percorso**: `src/rag/ingestion.py`

Trasforma documenti PDF e Markdown in vettori embeddings immagazzinati nel VectorDB:

1. **Caricamento**: Lettura da `data/documents/` (PDF e Markdown)
2. **Chunking**: Suddivisione in chunks di 1000 caratteri con overlap di 200 caratteri
3. **Embedding**: Conversione a vettori 384-dimensionali usando `all-MiniLM-L6-v2`
4. **Indexing**: Memorizzazione in Qdrant con metadati (sorgente, pagina, tipo)

```python
# Esempio di utilizzo
from src.rag.ingestion import DocumentIngester

ingester = DocumentIngester(config)
ingester.ingest_directory("data/documents/")
# Output: VectorDB Qdrant con collezione 'eu_directive_2023_970'
```

#### Retrieval (Ricerca)

**Percorso**: `src/rag/retriever.py`

Implementa una ricerca ibrida che combina due strategie:

- **BM25 (Full-text)**: Ricerca parole-chiave esatte e semantica superficiale
- **Vector Search**: Ricerca semantica profonda usando embeddings

La fusion avviene con weight configurable (default 0.5):

```
score_finale = (0.5 × score_bm25) + (0.5 × score_vector)
```

Top-K risultati (default 5) vengono retournati per la generazione.

```python
# Esempio
from src.rag.retriever import HybridRetriever

retriever = HybridRetriever(config)
results = retriever.retrieve("Che cos'è la parità di retribuzione?", top_k=5)
# Returns: List[RetrievedDocument] con scores
```

#### Generation (Generazione Risposte)

**Percorso**: `src/rag/generator.py`

Utilizza Groq API per generare risposte basate sui documenti recuperati:

- **Modello**: `llama-3.3-70b-versatile`
- **Temperatura**: 0.1 (risposte deterministiche, low hallucination)
- **Max Tokens**: 2048
- **Timeout**: 30 secondi
- **Rate Limiting**: Respetta limiti Groq (max 30 req/minuto nel tier free)

```python
from src.rag.generator import ResponseGenerator

gen = ResponseGenerator(config)
answer = gen.generate(
    query="Art. 7?",
    retrieved_docs=results,
    temperature=0.1
)
```

#### Anti-Hallucination (Prevenzione Allucinazioni)

**Percorso**: `src/rag/anti_hallucination.py`

Verifica che le risposte siano ancorate ai documenti fonte:

1. **Confidence Scoring**: Valuta confidenza della risposta (0-1)
2. **Source Verification**: Controlla che le affermazioni siano nei documenti
3. **Fallback**: Se confidenza < threshold (0.6), ritorna "Non so" o suggerisce di consultare la normativa

```python
from src.rag.anti_hallucination import ResponseValidator

validator = ResponseValidator(config)
is_valid, confidence = validator.validate(answer, retrieved_docs)
```

#### Query Transformation (Step-Back Prompting)

**Percorso**: `src/rag/query_transformer.py`

Opzionale (controllato da `query_transform_enabled` in config.yaml):

Trasforma query complesse in query più semplici per migliorare il retrieval:

- Input: "Quali sono gli obblighi per aziende con meno di 250 dipendenti?"
- Trasformato: "Obblighi report per dimensione aziendale"
- Beneficio: Migliore matching semantico

---

### 2. Pay Gap Analysis (Analisi Divario Retributivo)

Modulo per calcolare il divario retributivo di genere secondo Direttiva EU 2023/970.

#### DataLoader

**Percorso**: `src/analysis/data_loader.py`

Carica e valida dati di stipendi da CSV o Excel:

- **Formati supportati**: `.csv`, `.xlsx`, `.xls`
- **Colonne richieste**: `gender`, `base_salary`
- **Colonne opzionali**: `department`, `level`, `bonus`, `role`
- **Validazione**:
  - Presence check: Tutte le colonne richieste presenti
  - Type check: Salari sono numerici
  - Normalizzazione: Nomi colonne case-insensitive
  - Filtro: Esclude righe con dati incompleti

```python
from src.analysis.data_loader import DataLoader

loader = DataLoader(config)
df = loader.load("data/demo/demo_employees.csv")
# Ritorna: pandas DataFrame pulito e normalizzato
```

#### GapCalculator

**Percorso**: `src/analysis/gap_calculator.py`

Calcola metriche di divario retributivo:

**Metriche Principali**:

1. **Gender Pay Gap (GPG) Globale**:
   ```
   GPG = (media_salari_uomini - media_salari_donne) / media_salari_uomini × 100
   ```

2. **Pay Gap per Categoria** (Dipartimento + Livello):
   - Esclude categorie con < 2 persone per genere (per privacy)
   - Applica filtro EU threshold: GPG validi solo se ≥ 5%

3. **Quartili di Retribuzione**:
   - Q1 (più basso 25%)
   - Q2 (25%-50%)
   - Q3 (50%-75%)
   - Q4 (più alto 25%)

4. **Bonus Gap**:
   - Media bonus uomini vs donne
   - Percentuale dipendenti che ricevono bonus

```python
from src.analysis.gap_calculator import GapCalculator

calc = GapCalculator(config)
results = calc.calculate(df)

# Output struttura:
# {
#     'global_gap': 12.5,
#     'gap_by_category': {...},
#     'quartiles': {...},
#     'bonus_gap': {...},
#     'compliance_status': 'NON_COMPLIANT'  # se > 5%
# }
```

#### Report

**Percorso**: `src/analysis/report.py`

Formatta i risultati in output leggibile:

- **Formati**: Testo, HTML, JSON
- **Compliance**: Automaticamente valuta conformità EU (< 5% = conforme)
- **Dettagli**: Distribuzioni, tendenze, raccomandazioni

---

### 3. Interfacce

#### Web (FastAPI + HTMX + Jinja2)

**File Principale**: `app.py`

Stack tecnologico:

- **Framework**: FastAPI (async, alta performance)
- **Templating**: Jinja2 (server-side rendering)
- **Interattività**: HTMX (senza React/Vue, progressive enhancement)
- **File Statici**: CSS, JavaScript, Favicon in `static/`

**Router Principali**:

| File | Endpoint | Metodo | Descrizione |
|------|----------|--------|-------------|
| `src/web/api/chat.py` | `/api/chat` | POST | Chat AI con assistente |
| `src/web/api/upload.py` | `/api/upload` | POST | Upload CSV/Excel per analisi gap |
| `src/web/api/health.py` | `/api/health` | GET | Health check JSON |

**Rotte Principali**:

```
GET  /              → Homepage (form chat + upload)
POST /api/chat      → Processa chat, ritorna HTML fragment
POST /api/upload    → Processa file, ritorna risultati analisi
GET  /api/health    → {"status": "ok", "version": "1.0"}
```

**Esempio Chat HTMX** (template):

```html
<form hx-post="/api/chat" hx-target="#response">
    <textarea name="text" placeholder="Fai una domanda..."></textarea>
    <button type="submit">Invia</button>
</form>
<div id="response"></div>
```

Il server ritorna un HTML fragment che HTMX inserisce nel DOM senza page reload.

#### CLI (Command Line Interface)

**File Principale**: `main.py`

Dispatcher di comandi per uso da terminale:

```bash
python main.py ask "Che cosa dice l'articolo 7?"
python main.py analyze --file data/demo/demo_employees.csv
python main.py ingest
```

**Implementazione**: `src/cli/interface.py`

- Gestisce I/O terminale con `rich` (colori, tabelle formattate)
- Supporta modalità interattiva (agent)
- Logging strutturato con timestamp

#### Local Tool (Stand-Alone)

**File**: `static/local-tool.html` e `pay-gap-analyzer.html`

Analyzer interattivo che funziona senza server:

- HTML/CSS/JavaScript puro
- Carica CSV/Excel in memoria
- Calcola gap localmente (algoritmo JS)
- Niente esposizione dati al cloud

Uso: Apri il file nel browser, carica un CSV, ottieni risultati istantaneamente.

#### Agent Router

**File**: `src/agent/router.py`

Classe `PayTransparencyRouter` (402 linee) che implementa la logica di routing intelligente:

```python
from src.agent.router import PayTransparencyRouter

router = PayTransparencyRouter(config)

# Router automaticamente sceglie il modulo giusto:
response = router.route_query("Qual è il divario retributivo medio?")
# → Dirige a PAY GAP ANALYSIS se rileva numeri/statistiche
# → Dirige a RAG se riconosce domande sulla normativa
```

Utilizza il framework `datapizza-ai` per pattern matching e decision tree.

---

## Struttura del Progetto

```
pay-transparency-tool/
│
├── app.py                          # Entry point FastAPI
├── main.py                         # Entry point CLI
├── Makefile                        # Comandi di utilità
├── config.yaml.example             # Config template
├── .env.example                    # Environment template
├── setup.sh                        # Script setup automatico
├── requirements.txt                # Dipendenze Python
├── requirements-lock.txt           # Frozen dependencies (pip freeze)
│
├── src/
│   ├── rag/                        # RAG Pipeline
│   │   ├── ingestion.py           # Document ingestion → VectorDB
│   │   ├── retriever.py           # Hybrid BM25+Vector search
│   │   ├── generator.py           # LLM response generation (Groq)
│   │   ├── query_transformer.py   # Step-back prompting (opzionale)
│   │   └── anti_hallucination.py  # Response verification
│   │
│   ├── analysis/                   # Pay Gap Analysis
│   │   ├── data_loader.py         # CSV/Excel → DataFrame
│   │   ├── gap_calculator.py      # Calcoli divario retributivo
│   │   └── report.py              # Formattazione risultati
│   │
│   ├── web/                        # Web Interface (FastAPI)
│   │   ├── api/
│   │   │   ├── chat.py            # POST /api/chat
│   │   │   ├── upload.py          # POST /api/upload
│   │   │   └── health.py          # GET /api/health
│   │   └── ...
│   │
│   ├── cli/                        # CLI Interface
│   │   └── interface.py           # Command dispatcher
│   │
│   ├── agent/                      # Smart Router
│   │   └── router.py              # PayTransparencyRouter
│   │
│   └── utils/                      # Utilità Condivise
│       ├── config.py              # Singleton config loader (YAML)
│       ├── logger.py              # Structured logging
│       ├── rate_limiter.py        # Groq API rate limiting
│       └── analytics.py           # Usage tracking (SQLite)
│
├── data/
│   ├── documents/                 # Sorgenti dati
│   │   ├── CELEX_32023L0970_EN_TXT.pdf
│   │   ├── CELEX_32023L0970_IT_TXT.pdf
│   │   ├── checklist.md
│   │   ├── faq.md
│   │   ├── glossario.md
│   │   ├── obblighi_per_dimensione.md
│   │   └── timeline.md
│   │
│   ├── vectordb/                  # Qdrant VectorDB (generato)
│   │   └── [storage Qdrant locale]
│   │
│   ├── analytics.db               # SQLite usage tracking
│   │
│   └── demo/
│       └── demo_employees.csv     # Dataset di esempio
│
├── templates/                      # Jinja2 templates (FastAPI)
│   ├── base.html
│   ├── chat.html
│   ├── upload.html
│   └── results.html
│
├── static/                         # File statici
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   ├── local-tool.html            # Analyzer stand-alone
│   └── pay-gap-analyzer.html      # Alternativa
│
├── tests/                          # Suite di test
│   ├── conftest.py
│   ├── test_ingestion.py
│   ├── test_retriever.py
│   ├── test_generator.py
│   ├── test_data_loader.py
│   ├── test_gap_calculator.py
│   └── integration/
│       ├── test_rag_pipeline.py
│       └── test_analysis_pipeline.py
│
├── docs/
│   ├── guida-tecnica.md          # Questa guida
│   ├── guida-utente.md           # Per utenti finali
│   └── api-reference.md          # Documentazione API
│
└── .github/
    └── workflows/                 # CI/CD (opzionale)
        └── test.yml
```

---

## Requisiti e Dipendenze

### Requisiti di Sistema

- **Python**: 3.11 o superiore
- **OS**: Linux, macOS, Windows (con WSL2 consigliato)
- **RAM**: Minimo 2GB (consigliato 4GB+ per VectorDB)
- **Disk**: Minimo 500MB (per venv + dipendenze + VectorDB)

### Chiave API Esterna

- **Groq API Key** (gratuita):
  - Registrati su https://console.groq.com
  - Genera una chiave dalla dashboard
  - Limiti free tier: 30 richieste/minuto, 14000 token/minuto
  - Modello disponibile: `llama-3.3-70b-versatile`

### Dipendenze Python (per Categoria)

#### Core AI/RAG
```
datapizza-ai>=0.2.0      # Framework agent e router
fastembed>=0.2.20        # Fast embedding model loader
qdrant-client>=2.7.0     # Vector database client (local)
rank-bm25>=0.2.2         # BM25 full-text search
```

#### LLM Integration
```
groq>=0.4.1              # Groq API client
openai>=1.3.0            # OpenAI client (usato da Groq)
```

#### Data Processing
```
pandas>=2.0.0            # DataFrames e manipolazione dati
openpyxl>=3.10.0         # Excel file reading
PyMuPDF>=1.23.0          # PDF parsing
```

#### Web Framework
```
fastapi>=0.104.0         # Web framework asincrono
uvicorn>=0.24.0          # ASGI server
jinja2>=3.1.0            # Template engine
python-multipart>=0.0.6  # Form data parsing
```

#### CLI e Utilities
```
rich>=13.0.0             # Terminal formatting (colori, tabelle)
PyYAML>=6.0              # YAML config parsing
python-dotenv>=1.0.0     # .env file loading
```

#### Development (opzionale)
```
pytest>=7.0.0            # Unit testing
pytest-cov>=4.1.0        # Coverage reports
black>=23.0.0            # Code formatting
```

**Installa tutto con**: `pip install -r requirements.txt`

---

## Installazione Step-by-Step

### 1. Clona il Repository

```bash
git clone https://github.com/marcoguadagno/pay-transparency-tool.git
cd pay-transparency-tool
```

### 2. Copia i File di Configurazione

```bash
# Config YAML per RAG/Analysis
cp config.yaml.example config.yaml

# Environment variables
cp .env.example .env
```

### 3. Configura le API Keys

Edita `.env` e aggiungi la tua Groq API key:

```bash
# .env
GROQ_API_KEY=gsk_your_actual_key_here_from_groq_console
```

Edita anche `config.yaml` e verifica le impostazioni (vedi sezione Configurazione).

### 4. Esegui Setup Automatico

```bash
bash setup.sh
```

Questo script:

- Crea un virtual environment `.venv/`
- Installa tutte le dipendenze da `requirements.txt`
- Costruisce il VectorDB Qdrant (`data/vectordb/`)
- Ingesta i documenti dalla cartella `data/documents/`
- Verifica l'importazione di moduli critici

**Alternativa Manuale**:

```bash
# Crea venv
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# oppure: .venv\Scripts\activate  (Windows)

# Installa dipendenze
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Ingesta documenti
python main.py ingest

# Verifica setup
python -c "from src.rag.retriever import HybridRetriever; print('✓ Setup OK')"
```

### 5. Verifica l'Installazione

```bash
# Health check
curl http://localhost:8000/api/health  # Dopo aver avviato il server

# O dal Python:
python -c "
from src.utils.config import Config
from src.rag.retriever import HybridRetriever
config = Config.load()
print('✓ Config caricato')
print(f'  LLM: {config.llm.model}')
print(f'  VectorDB: {config.vectorstore.location}')
"
```

---

## Configurazione

### config.yaml

File centrale che controlla il comportamento del sistema. Creato da `config.yaml.example`.

#### Sezione LLM

```yaml
llm:
  provider: groq                              # Provider LLM
  model: llama-3.3-70b-versatile             # Modello per generazione
  temperature: 0.1                            # Low: risposte deterministiche
  max_tokens: 2048                            # Lunghezza max risposta
  timeout: 30                                 # Timeout request (sec)
```

**Nota**: Temperatura bassa (0.1) è ideale per evitare allucinazioni in ambito legale/regolatorio.

#### Sezione Embeddings

```yaml
embeddings:
  model_name: sentence-transformers/all-MiniLM-L6-v2
  dimensions: 384                             # Dimensione vettori
  batch_size: 32                              # Per ingestion batch
```

**Nota**: `all-MiniLM-L6-v2` è il miglior compromesso tra velocità e qualità. Lite ma efficace.

#### Sezione VectorStore

```yaml
vectorstore:
  type: qdrant                                # Solo Qdrant supportato
  location: ./data/vectordb                   # Path locale VectorDB
  collection_name: eu_directive_2023_970     # Nome collezione
  vector_size: 384                            # Deve matchare embeddings
  similarity_metric: cosine                   # Distance metric
```

#### Sezione RAG

```yaml
rag:
  chunk_size: 1000                            # Lunghezza chunk documenti (char)
  chunk_overlap: 200                          # Overlap tra chunks
  top_k: 5                                    # N. documenti retrivati
  confidence_threshold: 0.6                   # Min. confidenza risposta
  fusion_weight: 0.5                          # Weight BM25 vs Vector (0-1)
  query_transform_enabled: false              # Step-back prompting
```

#### Sezione Analysis

```yaml
analysis:
  eu_threshold: 5.0                           # Threshold conformità EU (%)
  min_category_size: 2                        # Min. persone per genere/categoria
  report_format: html                         # Output: html, json, text
```

#### Sezione Logging

```yaml
logging:
  level: INFO                                 # DEBUG, INFO, WARNING, ERROR
  format: json                                # json o text
  file: logs/app.log                          # Path log file
```

### .env

File per secrets e variabili sensibili. **Non committare in git**.

```bash
# API Keys
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx        # Obbligatorio

# Optional: Overrides da config.yaml
VECTORDB_PATH=./data/vectordb
LOG_LEVEL=INFO
```

### Variabili d'Ambiente Avanzate

Per override da linea di comando:

```bash
# Avvia con config alternativa
CONFIG_FILE=config.prod.yaml python app.py

# Overrides temporanei
GROQ_API_KEY=gsk_xxx VECTORDB_PATH=/mnt/data python main.py ask "..."
```

---

## Esecuzione

### Web Interface (FastAPI)

```bash
# Via Makefile
make web

# O manualmente
source .venv/bin/activate
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Accedi a: **http://localhost:8000**

Funzionalità:
- **Chat AI**: Fai domande sulla Direttiva EU 2023/970
- **Upload**: Carica CSV/Excel per analizzare divario retributivo
- **Health**: Verifica sistema su `/api/health`

### CLI Interface

#### Modalità Interattiva (Agent)

```bash
# Via Makefile
make cli

# O manualmente
python main.py
# → Entra in ciclo interattivo ">" per domande
```

Comandi:
```
> Qual è il GPG?
> Dammi l'art. 5
> analyze data/mydata.csv
> exit
```

#### Modalità Single Query

```bash
# Domanda RAG
python main.py ask "Cosa dice l'articolo 7?"

# Analisi divario retributivo
python main.py analyze --file data/demo/demo_employees.csv

# Ingesta documenti (ricrea VectorDB)
python main.py ingest
```

### Local Tool (Analyzer Stand-Alone)

Apri il file nel browser:

```bash
# Opzione 1: Apri direttamente
open static/local-tool.html  # macOS
xdg-open static/local-tool.html  # Linux
start static\local-tool.html  # Windows

# Opzione 2: Servi localmente (consigliato)
python -m http.server 8080
# Accedi a: http://localhost:8080/static/local-tool.html
```

---

## API Endpoints

### Chat API

**POST** `/api/chat`

Invia una domanda all'assistente AI. Utilizza retrieval da VectorDB + generazione LLM.

**Request** (Form data):
```
text=Che cosa dice l'articolo 7 della Direttiva?
```

**Response** (HTML fragment):
```html
<div class="response">
  <p>L'articolo 7 stabilisce che...</p>
  <ul class="sources">
    <li>Fonte: CELEX_32023L0970_IT_TXT.pdf (pag. 12)</li>
  </ul>
</div>
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "text=Quali sono gli obblighi per aziende con 250+ dipendenti?"
```

### Upload API (Pay Gap Analysis)

**POST** `/api/upload`

Carica un CSV/Excel per analizzare il divario retributivo di genere.

**Request**:
```
File: demo_employees.csv (multipart/form-data)
```

**File CSV Format** (richiesto):
```csv
gender,base_salary,department,level,bonus
Female,45000,Engineering,Senior,5000
Male,50000,Engineering,Senior,5500
Female,40000,Sales,Junior,0
Male,42000,Sales,Junior,0
```

**Response** (HTML):
```html
<div class="analysis-results">
  <h2>Gender Pay Gap Analysis</h2>
  <p><strong>Overall GPG:</strong> 8.5%</p>
  <p class="status non-compliant">Status: NON-COMPLIANT (> 5%)</p>
  <table>
    <tr><th>Category</th><th>Gap %</th><th>Status</th></tr>
    <tr><td>Engineering/Senior</td><td>10.0%</td><td>Non-Compliant</td></tr>
  </table>
</div>
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@data/demo/demo_employees.csv"
```

### Health Check API

**GET** `/api/health`

Verifica lo stato del sistema.

**Response** (JSON):
```json
{
  "status": "ok",
  "version": "1.0",
  "components": {
    "vectordb": "connected",
    "groq_api": "reachable",
    "analytics_db": "ready"
  },
  "timestamp": "2026-03-06T14:23:45Z"
}
```

**cURL Example**:
```bash
curl http://localhost:8000/api/health | jq
```

---

## Testing

### Struttura Test

```
tests/
├── conftest.py                # Fixtures pytest condivise
├── test_ingestion.py          # Unit: ingestion pipeline
├── test_retriever.py          # Unit: hybrid search
├── test_generator.py          # Unit: LLM generation
├── test_data_loader.py        # Unit: CSV/Excel parsing
├── test_gap_calculator.py     # Unit: gap calculations
└── integration/
    ├── test_rag_pipeline.py   # Integration: end-to-end RAG
    └── test_analysis_pipeline.py  # Integration: end-to-end Analysis
```

### Esegui Test

```bash
# Tutti i test
make test

# O manualmente
source .venv/bin/activate
pytest tests/ -v

# Con coverage report
pytest tests/ --cov=src --cov-report=html
# Apri: htmlcov/index.html
```

### Test Specifici

```bash
# Solo unit test RAG
pytest tests/test_retriever.py -v

# Solo integration test
pytest tests/integration/ -v

# Con output verboso
pytest tests/ -vv -s
```

### Fixture di Test Importanti (conftest.py)

```python
@pytest.fixture
def config():
    """Carica config.yaml per test"""
    return Config.load()

@pytest.fixture
def sample_df():
    """Crea DataFrame di test con dati stipendi"""
    return pd.DataFrame({
        'gender': ['Male', 'Female', 'Male', 'Female'],
        'base_salary': [50000, 45000, 48000, 42000],
        'department': ['Eng', 'Eng', 'Sales', 'Sales']
    })

@pytest.fixture
def vector_db(config):
    """VectorDB di test (in-memory o locale temp)"""
    # Setup VectorDB per test
    yield vectordb_instance
    # Cleanup
```

### Test Coverage Target

- **RAG Pipeline**: ≥ 85% coverage
- **Analysis Module**: ≥ 90% coverage (logica numerica critica)
- **Web API**: ≥ 70% coverage (endpoint principales)

---

## Comandi Makefile

File: `Makefile` (in root)

| Comando | Descrizione |
|---------|-------------|
| `make setup` | Crea venv, installa deps, costruisce VectorDB |
| `make setup-clean` | Ricrea venv da zero (cancella vecchio) |
| `make test` | Esegui unit test con pytest |
| `make test-integration` | Esegui solo integration test |
| `make test-cov` | Test con coverage report (genera htmlcov/) |
| `make verify` | Verifica import critici (fallisce se broken) |
| `make web` | Avvia FastAPI server (localhost:8000) |
| `make cli` | Avvia CLI agent interattivo |
| `make freeze` | Aggiorna requirements-lock.txt (pip freeze) |
| `make clean` | Rimuove __pycache__, .pyc, htmlcov |
| `make report` | Report statistiche utilizzo ultimi 30 giorni (da analytics.db) |
| `make report-weekly` | Report utilizzo ultimi 7 giorni |
| `make lint` | Run black + flake8 (se configurati) |
| `make help` | Mostra questo elenco |

**Esempi**:

```bash
# Setup da zero
make setup-clean && make verify && make test

# Sviluppo locale
make web  # In una shell
make test-cov  # In un'altra per TDD

# Produzione
make freeze  # Update dependencies
git add requirements-lock.txt
git commit -m "Update frozen dependencies"
```

---

## Contribuire al Progetto

Benvenuti i contributi! Ecco come partecipare:

### 1. Fork e Clone

```bash
# Fork su GitHub, poi:
git clone https://github.com/YOUR_USERNAME/pay-transparency-tool.git
cd pay-transparency-tool
git remote add upstream https://github.com/marcoguadagno/pay-transparency-tool.git
```

### 2. Crea un Branch Feature

```bash
git checkout -b feature/tua-feature
# o per bug fix:
git checkout -b fix/nome-bug
```

### 3. Setup Locale

```bash
make setup
source .venv/bin/activate
```

### 4. Sviluppa e Testa

```bash
# Modifica il codice
# ...

# Esegui test
make test

# Verifica import
make verify

# Formato codice (se black è installato)
black src/ tests/
```

### 5. Commit Semantico

Segui [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git add .
git commit -m "feat: aggiungi step-back prompting per RAG"
# o
git commit -m "fix: correggi calcolo GPG per categorie < 2 persone"
# o
git commit -m "docs: aggiorna guida tecnica"
```

### 6. Push e Pull Request

```bash
git push origin feature/tua-feature
# Accedi a GitHub e crea Pull Request verso `main`
```

### 7. Code Review

- Almeno 1 review richiesto
- CI/CD tests devono passare (vedi `.github/workflows/`)
- Descrivi chiaramente cosa cambia e perché

### Linee Guida Codice

- **Linguaggio**: Python 3.11+, type hints
- **Style**: PEP 8 (enforzato da black)
- **Tests**: 80%+ coverage per nuovo codice
- **Docs**: Docstrings Google-style per funzioni
- **Commit**: Atomici e descrittivi

### Aree di Contribuzione

1. **RAG Enhancement**:
   - Migliori modelli embedding
   - Strategie retrieval alternative
   - Multi-language support

2. **Analysis Features**:
   - Nuove metriche pay gap
   - Visualizzazioni avanzate
   - Export report migliorati

3. **Web UI**:
   - Responsive design mobile
   - Accessibilità (WCAG 2.1)
   - Temi dark/light

4. **Documentazione**:
   - Traduzioni (ES, DE, FR)
   - Tutorial video
   - Esempi pratici

5. **DevOps**:
   - Docker support
   - Kubernetes deployment
   - CI/CD improvements

### Contatti

- **Issues**: GitHub Issues per bug report e feature request
- **Discussions**: GitHub Discussions per domande
- **Email**: Per questioni sensibili, contatta il maintainer

---

## Troubleshooting

### Problema: Groq API key non funziona

**Soluzione**:
```bash
# Verifica .env
cat .env | grep GROQ_API_KEY

# Testa API direttamente
python -c "
import os
from groq import Groq
key = os.getenv('GROQ_API_KEY')
if not key:
    print('❌ GROQ_API_KEY non impostato')
else:
    print('✓ GROQ_API_KEY trovato (primi 10 char):', key[:10])
    client = Groq(api_key=key)
    try:
        resp = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': 'test'}],
            max_tokens=100
        )
        print('✓ API funziona!')
    except Exception as e:
        print(f'❌ Errore: {e}')
"
```

### Problema: VectorDB non caricato

**Soluzione**:
```bash
# Ricrea VectorDB
rm -rf data/vectordb/
python main.py ingest

# Verifica
python -c "
from src.rag.retriever import HybridRetriever
from src.utils.config import Config
config = Config.load()
r = HybridRetriever(config)
print(f'✓ VectorDB loaded, collection: {r.collection_name}')
"
```

### Problema: Port 8000 già in uso

**Soluzione**:
```bash
# Cambia porta
uvicorn app:app --port 8001

# O trova processo che usa porta 8000
lsof -i :8000
kill -9 <PID>
```

### Problema: Test fallisce con "ModuleNotFoundError"

**Soluzione**:
```bash
# Assicurati che .venv sia attivato
source .venv/bin/activate
# o: source .venv/bin/activate.csh (tcsh)
# o: .venv\Scripts\activate (Windows)

# Reinstalla in development mode
pip install -e .

# Esegui test
pytest tests/ -v
```

### Problema: PDF/Markdown non ingestion

**Soluzione**:
```bash
# Verifica file esistono
ls -la data/documents/

# Check permessi lettura
cat data/documents/CELEX_32023L0970_IT_TXT.pdf > /dev/null

# Riingesta con debug
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.rag.ingestion import DocumentIngester
from src.utils.config import Config
config = Config.load()
ingester = DocumentIngester(config)
ingester.ingest_directory('data/documents/')
" 2>&1 | tail -50
```

---

## Risorse Aggiuntive

### Documentazione Interna

- **guida-utente.md**: Per utenti finali (come usare il tool)
- **api-reference.md**: Documentazione API dettagliata
- **config.yaml.example**: Template config commentato

### Link Esterni

- **Groq API**: https://console.groq.com
- **Qdrant Docs**: https://qdrant.tech/documentation/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Direttiva EU 2023/970**: https://eur-lex.europa.eu/eli/dir/2023/970/oj/ita

### Tool Online Suggeriti

- **JSON Formatter**: https://jsoncrack.com/
- **YAML Validator**: https://www.yamllint.com/
- **CSV Viewer**: https://www.convertcsv.com/csv-viewer-editor.htm

---

## FAQ Sviluppatori

**D: Posso usare un altro LLM oltre Groq?**

R: Attualmente il sistema è ottimizzato per Groq, ma il codice in `src/rag/generator.py` può essere esteso. Per usare OpenAI, Azure, o simili, modifica la classe `ResponseGenerator`. Contribution welcome!

**D: Come aggiungo nuovi documenti?**

R: Metti i file PDF/Markdown in `data/documents/` e esegui `python main.py ingest`. Il sistema li scaricherà, creerà embeddings e li salverà in Qdrant.

**D: Posso deployare in produzione con SQLite?**

R: SQLite per analytics è OK per deployment piccoli. Per volumi alti, considera PostgreSQL. VectorDB Qdrant è persisted a disco, quindi OK anche in prod.

**D: Come riduco l'uso API Groq?**

R: Configura `top_k` più basso (es. 3 invece di 5) e aumenta `confidence_threshold` (es. 0.7). Risparmia tokens non generando risposte bassa confidenza.

**D: Supporta Italian + English simultaneamente?**

R: Sì, il VectorDB ha documenti in entrambe le lingue. Funziona automaticamente con ricerca semantica.

---

## Versione e Changelog

**Current**: v1.0 (Marzo 2026)

### v1.0 Highlights
- RAG pipeline completo con Qdrant + Groq
- Pay Gap Analysis con conformità EU
- Web interface FastAPI + HTMX
- CLI interattiva
- Local analyzer stand-alone
- Test suite con ≥ 80% coverage

### Prossime Release (Roadmap)
- [ ] Multi-language support avanzato
- [ ] Docker containerization
- [ ] Kubernetes helm charts
- [ ] Advanced analytics dashboard
- [ ] Excel export con formule
- [ ] Webhook per integrazioni terze

---

**Buona sviluppo! Grazie per il tuo contributo al Pay Transparency Tool.** 🚀

*Per domande, apri un issue su GitHub: https://github.com/marcoguadagno/pay-transparency-tool/issues*
