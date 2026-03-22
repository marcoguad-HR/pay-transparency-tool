# PRD — Equal Value Comparator
## Pay Transparency Tool | Direttiva EU 2023/970

**Versione:** 1.0
**Data:** 21 marzo 2026
**Autori:** Marco Guadagno (Product/Business), Claude (PM/Architect)
**Status:** In revisione — in attesa approvazione Marco

---

## 1. Contesto e Problema

### 1.1 Il gap critico nel tool

Il Pay Transparency Tool oggi analizza il gender pay gap e risponde a domande sulla normativa. Ma manca il componente fondamentale: **determinare se due ruoli sono "lavoro di pari valore"** ai sensi dell'Art. 4 della Direttiva EU 2023/970.

Senza questo:
- Le aziende calcolano il gap **senza sapere quali ruoli confrontare**
- Il gap per categoria (dipartimento + livello) è un proxy grezzo, non una vera valutazione di pari valore
- Gli utenti lo chiedono esplicitamente e il RAG risponde in modo generico

### 1.2 Cosa dice la Direttiva

**Art. 4(4):** Il lavoro di pari valore è determinato sulla base di criteri oggettivi e neutri rispetto al genere, che includono almeno:

| Criterio | Articolo | Descrizione |
|----------|----------|-------------|
| **Skills** (Competenze) | Art. 4(4)(a) | Istruzione, formazione, conoscenze tecniche, capacità interpersonali |
| **Effort** (Impegno) | Art. 4(4)(b) | Sforzo fisico, mentale, emotivo richiesto dal ruolo |
| **Responsibility** (Responsabilità) | Art. 4(4)(c) | Supervisione persone, impatto finanziario, gestione dati, benessere altrui |
| **Working Conditions** (Condizioni) | Art. 4(4)(d) | Ambiente fisico, stress psicologico, orari, trasferte |

### 1.3 Cosa non esiste sul mercato

| Soluzione | Costo | Self-service? | Open-source? | Conforme Art. 4? |
|-----------|-------|:---:|:---:|:---:|
| Korn Ferry Hay | €50-200k | ❌ | ❌ | Parziale |
| Mercer IPE | €50-150k | ❌ | ❌ | Parziale |
| WTW Global Grading | €30-100k | ❌ | ❌ | Parziale |
| LOGIB (Svizzera) | Gratuito | ✅ | ✅ | ❌ (solo statistico) |
| **Nostro Equal Value Comparator** | **Gratuito** | **✅** | **✅** | **✅** |

**Opportunità**: primo tool open-source, gratuito, self-service per la comparazione di pari valore conforme alla Direttiva EU.

### 1.4 Perché è urgente

- **7 giugno 2026**: deadline recepimento nazionale della Direttiva — mancano 11 settimane
- Le aziende con >100 dipendenti devono iniziare a costruire la job architecture
- **EIGE toolkit** in uscita il 26 marzo 2026: ci allineeremo ai sub-fattori ufficiali appena disponibili
- Il design è **configurabile**: i sotto-fattori vivono in `config.yaml`, non nel codice

---

## 2. Utenti Target

### 2.1 Persona primaria: HR Manager / Compensation & Benefits

- **Profilo**: 35-50 anni, esperienza HR medio-alta, non tecnica
- **Contesto**: deve preparare il primo report di pay transparency entro giugno 2026
- **Pain point**: non sa come determinare quali ruoli sono "di pari valore" e quali no
- **Bisogno**: uno strumento semplice che produca un verdetto motivato e difendibile

### 2.2 Persona secondaria: Consulente del lavoro / Avvocato giuslavorista

- **Profilo**: supporta le aziende nella compliance
- **Bisogno**: output strutturato, citazioni normative, export per documentazione

### 2.3 Persona terziaria: Utente chat casuale

- **Profilo**: arriva dal web, chiede "cosa significa lavoro di pari valore?"
- **Bisogno**: risposta conversazionale chiara, con possibilità di approfondire nel tool dedicato

---

## 3. Requisiti Funzionali

### 3.1 MUST-HAVE (MVP)

| ID | Requisito | Dettaglio |
|----|-----------|-----------|
| **M-01** | Form di input strutturato per 2 ruoli | 16 sotto-fattori SERW, scala 1-5, con label descrittive e tooltip |
| **M-02** | Calcolo punteggio e confronto | Score totale per ruolo (16-80), score per categoria (4-20), differenza % |
| **M-03** | Verdetto "pari valore" | Soglia configurabile (default: differenza ≤10% verde, 11-20% giallo, >20% rosso) |
| **M-04** | Radar chart comparativo | Visualizzazione 4 assi (SERW) con overlay dei 2 ruoli (Chart.js) |
| **M-05** | Motivazione strutturata | Spiegazione testuale per ogni criterio: dove convergono, dove divergono |
| **M-06** | Integrazione chat | Keyword routing → se l'utente chiede di "confrontare ruoli" o "pari valore", il chat suggerisce il tool o risponde con RAG |
| **M-07** | Privacy | Nessun dato individuale al LLM. Solo nomi ruoli e punteggi aggregati |
| **M-08** | Analytics tracking | `tool_used="equal_value"` nel DB analytics |
| **M-09** | Gender-neutrality warnings | Alert se punteggi suggeriscono bias (es. sforzo fisico 5 ma emotivo 1) |
| **M-10** | Configurabilità sotto-fattori | Lista sub-fattori, pesi, soglia in `config.yaml` — aggiornabili senza deploy |
| **M-11** | LLM-assisted scoring (input intelligente) | 3 modalità di input per evitare compilazione manuale: (a) descrivi il ruolo a parole libere, (b) incolla la Job Description esistente, (c) dettalo con voce (Web Speech API). Il LLM suggerisce i 16 punteggi, l'utente rivede e aggiusta |
| **M-12** | Export Markdown del confronto | Report scaricabile con nomi ruoli, punteggi, radar chart, verdetto, motivazione, disclaimer legale, riferimenti normativi |

### 3.2 SHOULD-HAVE (post-MVP)

| ID | Requisito | Dettaglio |
|----|-----------|-----------|
| **S-01** | Confronto multiplo N×N | Matrice N ruoli con heatmap di pari valore |
| **S-02** | Storico confronti (localStorage) | Salvataggio locale delle comparazioni effettuate nel browser |
| **S-03** | Integrazione con gap analysis | "Hai 2 ruoli di pari valore con gap del 12% → azione correttiva necessaria" |
| **S-04** | Libreria ruoli standard ISCO-08 | Database di ~50-100 JD standard precompilate, l'utente cerca e personalizza |
| **S-05** | Export PDF formattato | Versione PDF professionale del report (oltre al Markdown MVP) |

### 3.3 WON'T-HAVE (scope esplicito)

- Job architecture completa (grading, banding, pay ranges)
- Integrazione con HRIS/payroll
- Gestione dati individuali dipendenti
- Sostituzione di sistemi professionali (Hay, Mercer, WTW)

---

## 4. Modello di Valutazione SERW

### 4.1 I 16 sotto-fattori

```
SKILLS — Competenze (25%)
  S1. Istruzione/qualifiche richieste dal ruolo          (1-5)
  S2. Esperienza richiesta (anni + complessità)          (1-5)
  S3. Conoscenze tecniche/specialistiche                 (1-5)
  S4. Capacità interpersonali e comunicative              (1-5)

EFFORT — Impegno (25%)
  E1. Impegno fisico richiesto                           (1-5)
  E2. Concentrazione mentale / complessità cognitiva     (1-5)
  E3. Impegno emotivo / gestione relazioni difficili     (1-5)
  E4. Multi-tasking / pressione sui tempi                (1-5)

RESPONSIBILITY — Responsabilità (25%)
  R1. Supervisione di persone                            (1-5)
  R2. Impatto finanziario / gestione budget              (1-5)
  R3. Responsabilità per il benessere altrui             (1-5)
  R4. Gestione dati sensibili / riservatezza             (1-5)

WORKING CONDITIONS — Condizioni di lavoro (25%)
  W1. Ambiente fisico / rischi                           (1-5)
  W2. Stress psicologico / esposizione a conflitti       (1-5)
  W3. Orari disagiati / turni / reperibilità             (1-5)
  W4. Trasferte / mobilità richiesta                     (1-5)
```

### 4.2 Scala di valutazione

| Livello | Significato | Esempio (S1 — Istruzione) |
|:---:|-------------|---------------------------|
| 1 | Minimo | Nessun titolo specifico richiesto |
| 2 | Basso | Diploma o equivalente |
| 3 | Medio | Laurea triennale o esperienza equivalente |
| 4 | Alto | Laurea magistrale + specializzazione |
| 5 | Massimo | Post-laurea, certificazioni avanzate, expertise rara |

### 4.3 Calcolo del verdetto

```
Score_ruolo = Σ (peso_categoria × Σ sotto-fattori_categoria)

Default: peso = 25% per ogni categoria (gender-neutral)

Differenza% = |Score_A - Score_B| / max(Score_A, Score_B) × 100

Verdetto:
  ≤ 10%  → "Ruoli di PARI VALORE" (verde)
  11-20% → "Potenzialmente comparabili — approfondire" (giallo)
  > 20%  → "Ruoli NON di pari valore" (rosso)
```

### 4.4 Gender-neutrality checks (ILO guidelines)

Il sistema genera warning automatici quando:
- E1 (fisico) ≥ 4 ma E3 (emotivo) ≤ 2 → *"Attenzione: lo sforzo emotivo potrebbe essere sottovalutato"*
- R2 (budget) ≥ 4 ma R3 (benessere) ≤ 2 → *"Attenzione: la responsabilità per il benessere altrui potrebbe essere sottovalutata"*
- W1 (fisico) ≥ 4 ma W2 (psicologico) ≤ 2 → *"Attenzione: lo stress psicologico potrebbe essere sottovalutato"*
- Un fattore vale >40% del totale di categoria → *"Attenzione: un singolo fattore domina la valutazione"*

Queste regole derivano dalle raccomandazioni ILO per la job evaluation gender-neutral.

### 4.5 Allineamento EIGE (26 marzo 2026)

I sotto-fattori sono **configurabili via `config.yaml`**:

```yaml
equal_value:
  threshold_equal: 10        # % max differenza per "pari valore"
  threshold_maybe: 20        # % max per "potenzialmente comparabile"
  categories:
    skills:
      weight: 0.25
      factors:
        - id: S1
          label: "Istruzione/qualifiche richieste"
          description: "Livello di istruzione formale richiesto dal ruolo"
        - id: S2
          label: "Esperienza richiesta"
          # ...
    effort:
      weight: 0.25
      # ...
```

Quando EIGE pubblicherà il toolkit, aggiorneremo solo questo file YAML.

---

## 5. Architettura Tecnica

### 5.1 Integrazione nell'architettura esistente

```
                     ┌─────────────────────────────────┐
                     │         index.html               │
                     │  Tab: Assistente | Analisi | ⭐NEW: Comparatore │
                     └──────┬──────────┬───────────┬────┘
                            │          │           │
                     ┌──────▼──┐  ┌────▼────┐  ┌──▼──────────┐
                     │ /api/   │  │ /api/   │  │ /api/       │
                     │ chat    │  │ upload  │  │ compare     │  ⭐ NEW
                     └──┬──┬──┘  └────┬────┘  └──┬──────────┘
                        │  │          │           │
            ┌───────────┘  │     ┌────▼────┐  ┌──▼──────────┐
            │              │     │ gap_    │  │ equal_value_ │  ⭐ NEW
       ┌────▼────┐   ┌────▼──┐  │calc.py  │  │ calculator.py│
       │ RAG     │   │Agent  │  └─────────┘  └──────────────┘
       │Pipeline │   │Router │
       └─────────┘   └───┬───┘
                          │
                    ┌─────▼─────┐
                    │ 3 tools:  │
                    │ query_dir │
                    │ analyze   │
                    │ ⭐eval_eq │  ⭐ NEW
                    └───────────┘
```

### 5.2 Nuovi file

| File | Layer | Responsabilità |
|------|-------|----------------|
| `src/analysis/equal_value_calculator.py` | Backend | Dataclass SERW, calcolo score, verdetto, gender warnings |
| `src/web/api/compare.py` | API | Endpoint POST `/api/compare`, validazione, rendering |
| `src/web/api/suggest_scores.py` | API | Endpoint POST `/api/suggest-scores` — LLM analizza JD e suggerisce punteggi |
| `templates/partials/equal_value_result.html` | Frontend | Risultato comparazione (radar chart, verdetto, breakdown) |
| `templates/partials/equal_value_form.html` | Frontend | Form 2-step: input JD + revisione punteggi pre-compilati |
| `tests/test_equal_value_calculator.py` | Test | Unit test per calcolo, soglie, gender warnings |
| `tests/test_suggest_scores.py` | Test | Test per parsing LLM → punteggi strutturati |
| `data/documents/guida_pari_valore.md` | RAG KB | Guida "come valutare il pari valore" per il RAG |

### 5.3 Modifiche a file esistenti

| File | Modifica |
|------|----------|
| `src/web/api/chat.py` | Aggiungere `_EQUAL_VALUE_KEYWORDS` + routing alla 4a via |
| `src/agent/router.py` | Aggiungere tool `evaluate_equal_value()` |
| `templates/index.html` | Aggiungere 3° tab "Comparatore" |
| `app.py` | Montare router `compare.py` |
| `config.yaml.example` | Aggiungere sezione `equal_value` |

### 5.4 Flusso dati

```
WIDGET (Form HTMX)                    CHAT (Testo libero)
       │                                     │
       ▼                                     ▼
  STEP 1: Input ruoli                 _is_equal_value_query()
  (scrivi / incolla JD / voce)               │
       │                               ┌─────▼──────┐
       ▼                               │ Sì: sugge- │
  POST /api/suggest-scores             │ risci tool  │
  (text JD → LLM → 16 punteggi)       │ + RAG Art.4 │
       │                               └─────────────┘
       ▼
  STEP 2: Rivedi punteggi
  (utente aggiusta slider)
       │
       ▼
  POST /api/compare
  (form-encoded:
   role_a_name, role_b_name,
   role_a_S1..W4,
   role_b_S1..W4)
       │
       ▼
  EqualValueCalculator
       │
       ├─► Score per ruolo (16-80)
       ├─► Score per categoria (4-20)
       ├─► Differenza %
       ├─► Verdetto (pari/forse/no)
       ├─► Gender warnings
       ├─► Breakdown per sotto-fattore
       │
       ▼
  equal_value_result.html
  (HTMX partial → swap in page)
       │
       ├─► Analytics: tool_used="equal_value"
       └─► [Scarica Report] → Markdown export
```

---

## 6. Design System (da UI/UX Pro Max)

### 6.1 Stile visivo

Generato con UI/UX Pro Max skill. Stile: **Trust & Authority** (compliance SaaS).

| Proprietà | Valore | Razionale |
|-----------|--------|-----------|
| **Stile primario** | Trust & Authority | Certificati, credenziali, metriche — perfetto per compliance |
| **Typography** | Plus Jakarta Sans (300-700) | Friendly, modern, SaaS, clean, professional |
| **Palette primaria** | #0891B2 (cyan-600) | Fresh, professionale, trust |
| **Palette secondaria** | #22D3EE (cyan-400) | Accento, hover, elementi secondari |
| **CTA** | #22C55E (green-500) | Azione positiva, conferma |
| **Background** | #ECFEFF (cyan-50) | Light, pulito, distingue dal bianco puro |
| **Text** | #164E63 (cyan-900) | Contrasto alto su sfondo cyan |
| **Verdetto verde** | #22C55E | Pari valore confermato |
| **Verdetto giallo** | #F59E0B | Da approfondire |
| **Verdetto rosso** | #EF4444 | Non pari valore |
| **Chart** | Radar/Spider (Chart.js) | Multi-Variable Comparison — 4 assi SERW |
| **Effetti** | Badge hover, metric pulse, smooth stat reveal | Professionale ma vivo |
| **Anti-pattern** | NO emoji come icone, NO gradients AI purple/pink | SVG icons (Lucide) |

### 6.2 Font Import

```html
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

### 6.3 Accessibilità (WCAG AAA target)

- Contrasto minimo 4.5:1 per testo normale
- Touch target minimo 44x44px
- Focus ring visibile su tutti gli elementi interattivi
- `prefers-reduced-motion` rispettato
- Tabella dati come alternativa accessibile al radar chart
- `cursor-pointer` su tutti gli elementi cliccabili
- Transizioni smooth 150-300ms

### 6.4 Layout widget (wireframe concettuale)

```
┌─────────────────────────────────────────────────────┐
│  COMPARATORE PARI VALORE                             │
│  Art. 4, Direttiva EU 2023/970                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  STEP 1 — INSERISCI I RUOLI                        │
│                                                     │
│  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │ RUOLO A              │  │ RUOLO B              │ │
│  │ [Nome ruolo       ]  │  │ [Nome ruolo       ]  │ │
│  │                      │  │                      │ │
│  │ Come vuoi descriverlo?│  │ Come vuoi descriverlo?│ │
│  │ ┌────┐ ┌────┐ ┌────┐│  │ ┌────┐ ┌────┐ ┌────┐│ │
│  │ │ Scrivi│ │Incolla│ │Voce ││  │ │ Scrivi│ │Incolla│ │Voce ││ │
│  │ └────┘ └────┘ └────┘│  │ └────┘ └────┘ └────┘│ │
│  │                      │  │                      │ │
│  │ [                  ] │  │ [                  ] │ │
│  │ [  Descrivi il     ] │  │ [  Descrivi il     ] │ │
│  │ [  ruolo...        ] │  │ [  ruolo...        ] │ │
│  │                      │  │                      │ │
│  │ [ANALIZZA CON AI ->] │  │ [ANALIZZA CON AI ->] │ │
│  └──────────────────────┘  └──────────────────────┘ │
│                                                     │
│  STEP 2 — RIVEDI I PUNTEGGI (pre-compilati da AI)  │
│                                                     │
│  ┌──────────────────┐  ┌──────────────────┐         │
│  │ RUOLO A           │  │ RUOLO B           │        │
│  ├──────────────────┤  ├──────────────────┤         │
│  │ COMPETENZE        │  │ COMPETENZE        │        │
│  │ S1 ●●●○○  [3]    │  │ S1 ●●●●○  [4]    │        │
│  │ S2 ●●○○○  [2]    │  │ S2 ●●●○○  [3]    │        │
│  │ S3 ●●●●○  [4]    │  │ S3 ●●●○○  [3]    │        │
│  │ S4 ●●●○○  [3]    │  │ S4 ●●●●○  [4]    │        │
│  ├──────────────────┤  ├──────────────────┤         │
│  │ IMPEGNO           │  │ IMPEGNO           │        │
│  │ E1 ●○○○○  [1]    │  │ E1 ●●○○○  [2]    │        │
│  │ E2 ●●●●○  [4]    │  │ E2 ●●●○○  [3]    │        │
│  │ E3 ●●●○○  [3]    │  │ E3 ●●●●○  [4]    │        │
│  │ E4 ●●●○○  [3]    │  │ E4 ●●●○○  [3]    │        │
│  ├──────────────────┤  ├──────────────────┤         │
│  │ RESPONSABILITÀ    │  │ RESPONSABILITÀ    │        │
│  │ ...               │  │ ...               │        │
│  ├──────────────────┤  ├──────────────────┤         │
│  │ CONDIZIONI        │  │ CONDIZIONI        │        │
│  │ ...               │  │ ...               │        │
│  └──────────────────┘  └──────────────────┘         │
│                                                     │
│  ┌─────────────────────────────────────────┐        │
│  │         [  CONFRONTA  ]                  │        │
│  └─────────────────────────────────────────┘        │
│                                                     │
├─────────────────────────────────────────────────────┤
│  RISULTATO                                          │
│                                                     │
│  ┌─────────┐  ┌─────────────────────────────┐       │
│  │  RADAR  │  │ VERDETTO                     │       │
│  │  CHART  │  │ ━━━━━━━━━━━━━━━━━━━━━━━━━   │       │
│  │  (4 assi│  │ 🟢 RUOLI DI PARI VALORE     │       │
│  │  SERW)  │  │ Differenza: 8.3%             │       │
│  │         │  │                               │       │
│  │  ── A   │  │ Score Ruolo A: 52/80 (65%)   │       │
│  │  ── B   │  │ Score Ruolo B: 48/80 (60%)   │       │
│  └─────────┘  │                               │       │
│               │ ⚠️ Warning gender-neutrality:  │       │
│               │ E1 (fisico) alto ma E3         │       │
│               │ (emotivo) basso nel Ruolo A    │       │
│               └─────────────────────────────────┘      │
│                                                     │
│  DETTAGLIO PER CATEGORIA                            │
│  ┌────────────┬──────┬──────┬──────┐                │
│  │ Categoria  │ A    │ B    │ Diff │                │
│  ├────────────┼──────┼──────┼──────┤                │
│  │ Competenze │ 12   │ 14   │ -14% │                │
│  │ Impegno    │ 11   │ 12   │  -8% │                │
│  │ Responsab. │ 15   │ 12   │ +25% │ ⚠️             │
│  │ Condizioni │ 14   │ 10   │ +40% │ 🔴             │
│  └────────────┴──────┴──────┴──────┘                │
│                                                     │
│  MOTIVAZIONE                                        │
│  I due ruoli presentano punteggi complessivi        │
│  comparabili (differenza 8.3%), tuttavia si         │
│  rilevano divergenze significative nelle             │
│  Condizioni di lavoro (+40%). Si consiglia di       │
│  approfondire se le differenze nelle condizioni     │
│  giustificano un trattamento retributivo diverso.   │
│                                                     │
│  📄 Art. 4(4), Direttiva EU 2023/970               │
│  📄 ILO — Promoting Equity (2008)                  │
└─────────────────────────────────────────────────────┘
```

### 6.3 Responsiveness

- **Desktop (>1024px)**: layout 2 colonne affiancate per i ruoli
- **Tablet (768-1024px)**: 2 colonne compresse
- **Mobile (<768px)**: layout 1 colonna, ruoli impilati, form a step (wizard)

---

## 7. Metriche di Successo

| Metrica | Target MVP (30gg) | Misurazione |
|---------|:-:|-------------|
| Comparazioni effettuate | ≥50 | Analytics `tool_used="equal_value"` |
| Conversion da chat | ≥20% | Utenti che da chat vanno al widget |
| Tempo medio compilazione | <5 min | Analisi response_time_ms |
| Bounce rate form | <40% | Form iniziati vs completati |
| GitHub stars/forks | +20 | GitHub API |

---

## 8. Rischi e Mitigazioni

| Rischio | Impatto | Probabilità | Mitigazione |
|---------|:---:|:---:|-------------|
| EIGE cambia i sotto-fattori | Medio | Media | Config YAML → aggiornamento senza deploy |
| Form troppo complesso per utente non esperto | Alto | Alta | Tooltip esplicativi, esempi concreti, wizard mobile |
| Utente usa il verdetto come parere legale | Alto | Media | Disclaimer chiaro: "strumento orientativo, non sostitutivo di consulenza" |
| Sotto-fattori non coprono casi limite | Medio | Bassa | Peso configurabile + possibilità aggiungere fattori custom |

---

## 9. Roadmap Implementazione

| Fase | Cosa | Chi | Quando | Dipendenze |
|:---:|------|:---:|--------|------------|
| 1 | PRD + Design review | PM + UX | 21 mar | — |
| 2 | Backend: calculator + API + test | Backend | 22-23 mar | PRD approvato |
| 3 | Frontend: form + risultato + chart | Frontend | 22-23 mar | PRD approvato |
| 4 | Integrazione chat routing | Backend | 24 mar | Fase 2 |
| 5 | RAG: guida pari valore | Backend | 24 mar | — |
| 6 | QA + code review | Tutti | 25 mar | Fase 2-5 |
| 7 | Allineamento EIGE | PM + HR | 27 mar | Toolkit EIGE |
| 8 | Deploy produzione | DevOps | 28 mar | Fase 6-7 |

---

## 10. Disclaimer legale (da inserire nel tool)

> **⚠️ Nota importante**: Questo strumento fornisce un'analisi orientativa basata sui criteri dell'Art. 4 della Direttiva EU 2023/970. Non sostituisce una valutazione professionale del lavoro (job evaluation) né costituisce parere legale. Per una classificazione formale dei ruoli, si consiglia di rivolgersi a consulenti specializzati in compensation & benefits o a studi legali giuslavoristici.

---

*Documento prodotto con il supporto di: ricerca benchmark HR (ILO, EIGE, Hay, Mercer, WTW), analisi codebase architettonica, UI/UX Pro Max design system.*
