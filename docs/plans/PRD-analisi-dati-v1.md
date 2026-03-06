# PRD — Sezione Analisi Dati
## Pay Transparency Tool | Direttiva EU 2023/970

**Versione:** 1.0
**Data:** 4 marzo 2026
**Autori:** Marco Guadagno (Product/Business), Claude (Co-founder / CTO AI)
**Status:** In revisione

---

## 1. Contesto e Problema

### 1.1 Cosa abbiamo costruito finora (e perché)

La sezione "Analisi Dati" del tool riceve un CSV/Excel con i dati retributivi dell'azienda e restituisce un'analisi del gender pay gap conforme alla Direttiva EU 2023/970. L'attuale implementazione è **compliance-driven**: le visualizzazioni rispecchiano esattamente le 5 metriche che la Direttiva richiede di calcolare e rendicontare (Art. 9):

| Metrica | Art. Direttiva | Implementazione attuale |
|---|---|---|
| Gap medio (media) | Art. 9(c) | ✅ KPI card "Gap Medio" |
| Gap mediano | Art. 9(c) | ✅ KPI card "Gap Mediano" |
| Gap bonus/retribuzione variabile | Art. 9(b) | ✅ KPI card "Gap Bonus" |
| Distribuzione quartili | Art. 9(d) | ✅ Stacked bar Q1–Q4 |
| Gap per categoria (dipartimento+livello) | Art. 9, principio "lavoro di pari valore" | ✅ Category breakdown con barre M/F |

**Conclusione:** la scelta delle metriche è giuridicamente corretta e ben motivata. Il problema non è *cosa* mostriamo, ma *come* lo mostriamo.

### 1.2 Il Problema Reale

Abbiamo costruito un dashboard per compliance legale, ma i nostri utenti target — HR Manager e Manager aziendali italiani — **non hanno una mentalità data-driven** e useranno questo tool a partire da giugno 2026 per la prima volta in assoluto su questi dati.

Il problema è triplice:

**Problema 1 — Colori stereotipati:** Il palette attuale usa `blue-400` per gli uomini e `pink-400` per le donne. È un cliché culturale che sminuisce la professionalità del tool e rinforza inconsciamente i bias che stiamo cercando di misurare.

**Problema 2 — Mancanza di auto-esplicabilità:** "+8.3% Gap Medio" non dice nulla a un HR Manager non tecnico. Non sa se è un'emergenza o è normale. Non sa cosa fare dopo. Non sa nemmeno cosa sia la "mediana" vs la "media".

**Problema 3 — Nessuna gerarchia informativa:** L'utente vede tutti i dati sullo stesso livello. Non c'è una lettura guidata da "verdetto → evidenza → azione".

### 1.3 Perché è urgente

La deadline di compliance della Direttiva EU è il **7 giugno 2026** — 3 mesi da oggi. Le aziende con 250+ dipendenti inizieranno le prime analisi nelle prossime settimane. Se il tool non è auto-esplicativo, non verrà usato o verrà usato male, minando sia la missione (aiutare le aziende a essere compliant) che la reputazione del progetto.

---

## 2. Utenti Target

### 2.1 Persona primaria — L'HR Manager

- Lavora in un'azienda italiana con 150–500 dipendenti
- Ha responsabilità diretta sul reporting di compliance EU
- **Non è data analyst**: sa leggere Excel, ma non ha dimestichezza con statistiche avanzate
- **Ha paura delle sanzioni**: le multe possono arrivare al 4% del fatturato annuo
- **Ha poco tempo**: usa il tool 1–2 volte l'anno per produrre il report di compliance
- **Domanda principale:** "Siamo a posto? E se no, cosa devo fare?"

### 2.2 Persona secondaria — Il Manager/CFO

- Riceve il report HR in forma aggregata
- Vuole capire "in 30 secondi" se c'è un rischio legale o reputazionale
- Non tollera dati senza contesto o raccomandazioni d'azione
- **Domanda principale:** "Quanto ci costa il problema e come lo risolviamo?"

---

## 3. Analisi Critica dell'Implementazione Attuale

### 3.1 Cosa funziona bene (da preservare)

- La **struttura a card** è pulita e Mobile-first ✅
- Il **Status Banner** (Compliant/Non-Compliant) è il primo elemento — corretto ✅
- Le **barre comparative per categoria** sono leggibili ✅
- Il **threshold EU del 5%** è già integrato nella logica dei colori ✅
- Il **sort per gap decrescente** nelle categorie è già implementato ✅

### 3.2 Problemi critici da risolvere (MUST HAVE)

| Problema | Componente | Impatto |
|---|---|---|
| Palette blue/pink stereotipata | Tutti i grafici | Alto — professionalità e credibilità |
| Assenza di spiegazione delle metriche | KPI cards | Alto — comprensibilità per non-tecnici |
| "M" e "F" come label senza spiegazione | Category breakdown, Quartili | Medio-alto |
| Quartili ordinati top-to-bottom (Q1 in alto, Q4 in basso) ma Q1 = stipendi bassi | Quartile chart | Medio — controsenso visivo |
| Nessuna indicazione di cosa fare dopo | Dashboard footer | Alto — l'utente rimane bloccato |
| Assenza di threshold spiegato nel banner | Status Banner | Alto — "compliant" non dice nulla senza il 5% |

### 3.3 Opportunità di miglioramento (NICE TO HAVE)

Le visualizzazioni attuali rispondono a "qual è il gap?", ma non a:
- "Perché esiste il gap?" → serve un'analisi temporale per tenure
- "È un problema di bonus o di stipendio base?" → serve un drill-down bonus
- "Stiamo migliorando o peggiorando?" → serve un confronto storico
- "Cosa mi costa sistemarlo?" → serve un simulatore

---

## 4. Goals

### 4.1 User Goals

1. **Un HR Manager deve capire il risultato in < 10 secondi** senza aver mai usato il tool prima
2. **Il tool deve guidare l'utente verso l'azione** — non solo mostrare numeri
3. **Ogni metrica deve essere auto-esplicativa** — il testo del componente stesso spiega cosa vuol dire

### 4.2 Business Goals

1. **Differenziarsi dai tool generici** (Excel, report testuali) con un'esperienza visiva superiore
2. **Ridurre le domande di supporto** attraverso UI auto-esplicativa
3. **Aumentare la share su LinkedIn e community HR** — una dashboard bella e chiara viene condivisa
4. **Costruire la base per funzionalità premium future** (simulator, trend, esportazione) senza refactoring

---

## 5. Non-Goals (questa versione)

| Non-Goal | Motivazione |
|---|---|
| Confronto con dati di mercato esterno (benchmark) | Richiederebbe integrazione con data provider a pagamento — contrasta con il vincolo "costo zero" |
| Simulatore di aggiustamenti salariali | Feature complessa (80+ ore), non necessaria per compliance di base |
| Grafici a torta o scatter plot avanzati | Aggiungerebbero complessità cognitiva senza vantaggio per non-tecnici |
| Supporto multi-lingua (EN) | Prima lancio IT, poi internazionalizziamo |
| Dark mode | Luxury, non priorità per compliance tool |

---

## 6. Requisiti — MUST HAVE (P0)

Questi requisiti devono essere presenti al lancio. Senza di essi, il tool non risolve il problema core.

---

### MUST-01 — Ridisegno Palette Colori (Apple-Inspired, Gender-Neutral)

**Problema:** La palette attuale (blue/pink) è stereotipata e non professionale.

**Soluzione:** Sostituire con una palette semantica ispirata all'Apple Human Interface Guidelines.

**Nuova Palette:**

| Token | Nome | Hex | Tailwind | Uso |
|---|---|---|---|---|
| `--color-compliant` | System Green | `#34C759` | `emerald-500` | Gap ≤ 5%, status OK |
| `--color-warning` | System Orange | `#FF9500` | `amber-500` | Gap 5–10%, monitorare |
| `--color-alert` | System Red | `#EF4444` | `red-500` | Gap > 10%, azione immediata |
| `--color-segment-a` | Slate Dark | `#374151` | `gray-700` | Gruppo A nei grafici |
| `--color-segment-b` | Slate Medium | `#9CA3AF` | `gray-400` | Gruppo B nei grafici |
| `--color-text-primary` | Gray 900 | `#111827` | `gray-900` | Testo principale |
| `--color-text-secondary` | Gray 500 | `#6B7280` | `gray-500` | Label, didascalie |
| `--color-card-bg` | White | `#FFFFFF` | `white` | Sfondo card |
| `--color-page-bg` | Gray 50 | `#F7F7F8` | `gray-50` | Sfondo pagina (invariato) |

**Rationale:**
- `gray-700` vs `gray-400` è una coppia professionale, accessibile (contrasto 7:1), gender-neutral
- I colori Apple (emerald/amber/red) sono semantici: l'utente capisce lo stato senza spiegazioni
- La scelta è coerente con il sistema font già in uso (`-apple-system, BlinkMacSystemFont...`)

**Acceptance Criteria:**
- [ ] Nessun componente usa `blue-400` o `pink-400` come colore principale per i generi
- [ ] Le barre dei grafici usano `gray-700` (Gruppo A) e `gray-400` (Gruppo B)
- [ ] I colori di stato (verde/arancio/rosso) sono applicati coerentemente su tutti i componenti
- [ ] Il contrasto è WCAG AA compliant (≥ 4.5:1 su sfondo bianco)

---

### MUST-02 — Status Banner con Threshold Spiegato e Prossimi Passi

**Problema:** Il banner mostra "Compliant ✓" o "Non Compliant ✗" senza spiegare cosa significa o cosa fare.

**Soluzione:** Ristrutturare il banner in 3 zone informative.

**Layout ridisegnato:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ✓ CONFORME  |  Direttiva EU 2023/970                                       │
│                                                                             │
│  Nessun gap retributivo supera la soglia del 5% richiesta dalla Direttiva.  │
│  Puoi procedere con la pubblicazione del report annuale.                    │
│                                                                             │
│  [filename.csv]  |  [N] dipendenti  |  [N]♂ uomini · [N]♀ donne           │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Versione NON CONFORME:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ✗ NON CONFORME  |  Direttiva EU 2023/970                                   │
│                                                                             │
│  [N] categorie presentano un gap retributivo superiore al 5%.               │
│  Art. 9 Direttiva EU: è richiesta una valutazione retributiva congiunta     │
│  entro 6 mesi dalla rilevazione.                                            │
│                                                                             │
│  [filename.csv]  |  [N] dipendenti  |  [N]♂ uomini · [N]♀ donne           │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**
- [ ] Il banner mostra esplicitamente la soglia del 5%
- [ ] Il testo spiega in linguaggio naturale cosa significa lo status
- [ ] La versione NON CONFORME cita l'articolo di legge e la scadenza di 6 mesi
- [ ] Il conteggio dipendenti usa simboli ♂/♀ oppure "uomini"/"donne" scritto per esteso
- [ ] Il colore di sfondo del banner è semantico: `emerald-50` (conforme) o `red-50` (non conforme)

---

### MUST-03 — KPI Cards Auto-Esplicative con Spiegazione del Significato

**Problema:** "Gap Medio: +8.3%" non spiega cosa misura, perché esiste questa metrica, né se è un problema.

**Soluzione:** Ogni card ha un titolo chiaro, il valore, una spiegazione di una riga e un badge di status.

**Design della KPI Card (3 card in griglia):**

```
┌──────────────────────────────────────────────────────┐
│  Gap Retributivo Medio                               │
│  ─────────────────────────────────────────────────── │
│  +8.3%                        ⚠️ Supera il 5%        │
│  ─────────────────────────────────────────────────── │
│  Lo stipendio medio degli uomini è l'8.3% più alto   │
│  di quello delle donne nella stessa azienda.         │
│                                                      │
│  ▪ Uomini  €52.400          ▪ Donne  €48.030        │
└──────────────────────────────────────────────────────┘
```

**Testi per ciascuna card:**

| Card | Titolo | Spiegazione contestuale |
|---|---|---|
| Gap Medio | "Gap Retributivo Medio" | "Lo stipendio medio degli uomini è [X]% più alto di quello delle donne nella stessa azienda." |
| Gap Mediano | "Gap Retributivo Mediano" | "Il dipendente 'tipico' (a metà classifica) guadagna [X]% di più se uomo. La mediana esclude i valori estremi." |
| Gap Bonus | "Gap Retribuzione Variabile" | "Bonus e premi sono mediamente [X]% più alti per gli uomini. Include tutti i compensi non fissi." |
| Workforce (se no bonus) | "Composizione del Personale" | "L'organizzazione è composta da [N] uomini e [N] donne ([X]% / [Y]%)." |

**Badge di status per ogni card:**
- `gap_pct < 0` → Invertito (donne guadagnano di più) — `gray-500`
- `|gap_pct| ≤ 5` → "Nella soglia EU" — `emerald-500`
- `|gap_pct| > 5 e ≤ 10` → "Supera il 5%" — `amber-500`
- `|gap_pct| > 10` → "Gap significativo" — `red-500`

**Acceptance Criteria:**
- [ ] Ogni card ha un titolo leggibile in italiano, non abbreviato
- [ ] La spiegazione di 1–2 righe è visibile senza hover o interazione
- [ ] Il badge di status è visibile nell'angolo in alto a destra della card
- [ ] I valori assoluti (€ uomini, € donne) sono mostrati come sotto-informazione
- [ ] Il simbolo "+" o "–" è esplicito nel valore percentuale

---

### MUST-04 — Category Breakdown: Label Chiare e Ordinamento Corretto

**Problema:** Le label "M" e "F" sono criptiche; manca un'indicazione esplicita di priorità d'azione.

**Soluzione:** Rinominare le label, aggiungere context line per ogni riga.

**Header della sezione (da aggiornare):**

```
Gap per Ruolo e Dipartimento
Confronto retributivo medio tra uomini e donne nello stesso ruolo.
Soglia EU > 5% = azione correttiva richiesta.
```

**Label delle barre (da rinominare):**
- `M` → `Uomini`
- `F` → `Donne`

**Aggiungere sotto ogni riga:** il numero di persone nel campione — già presente come `[N]M·[N]F`, ma da rendere più leggibile come: `12 uomini · 8 donne`.

**Nota sul campione piccolo:** Se una categoria ha < 5 persone per genere, mostrare un tag `"⚠️ Campione ridotto"` — il dato potrebbe non essere statisticamente significativo.

**Acceptance Criteria:**
- [ ] "Uomini" e "Donne" scritti per esteso nelle barre
- [ ] Header della sezione include la spiegazione della soglia 5%
- [ ] Categorie con < 5 persone per genere mostrano il warning "Campione ridotto"
- [ ] Sort rimane per gap_pct discendente (default invariato, già corretto)
- [ ] Il colore delle barre segue la nuova palette: `gray-700` (uomini), `gray-400` (donne)
- [ ] Il badge di status (🔴/🟡/🟢) è visibile accanto alla percentuale

---

### MUST-05 — Quartile Chart: Ordinamento Logico e Spiegazione

**Problema:** Q1 (stipendi più bassi) appare in cima al grafico, ma visivamente "in alto" si associa a "più alto". Controsenso cognitivo.

**Soluzione:** Invertire l'ordine visivo — Q4 in alto, Q1 in basso — oppure passare a layout orizzontale bottom-up.

**Layout ridisegnato (orizzontale, Q1 in basso):**

```
Distribuzione Quartili Salariali
Dove si concentrano uomini e donne nelle fasce retributive?

Q4 (Stipendi Alti)   €65k–€150k  [████████████████████████████████] 62% U · 38% D
Q3 (Stipendi Medio-Alti) €42k–€65k [███████████████████████████████] 58% U · 42% D
Q2 (Stipendi Medio-Bassi)€28k–€42k [██████████████████████████████] 55% U · 45% D
Q1 (Stipendi Bassi)  €15k–€28k  [██████████████████████████████] 48% U · 52% D
```

**Header ridisegnato:**

```
Distribuzione Quartili Salariali
Dove si collocano uomini e donne nelle fasce retributive?
Distribuzione ideale = 50% uomini / 50% donne in ogni fascia.
```

**Aggiungere un callout testuale automatico** basato sui dati:
- Se il gap si allarga al Q4: "Il gap è maggiore nelle fasce alte: poche donne nei ruoli senior."
- Se il gap è uniforme: "Il gap è distribuito uniformemente — non è concentrato in un livello specifico."
- Se Q1 è sbilanciato (donne > 60%): "Le donne sono sovrarappresentate nella fascia di stipendio più bassa."

**Acceptance Criteria:**
- [ ] Q4 (stipendi più alti) è il primo elemento dall'alto nell'elenco
- [ ] Ogni fascia mostra il range salariale reale (€ min – €max)
- [ ] "Q1" è etichettato come "Fascia Bassa" o "(Stipendi Bassi)" — non solo "Q1"
- [ ] Il callout interpretativo automatico appare sotto il grafico
- [ ] Colori aggiornati: `gray-700` (uomini), `gray-400` (donne)
- [ ] Il tag "squilibrio" compare se il divario supera il 15% (già implementato, mantenerlo)

---

### MUST-06 — Sezione "Prossimi Passi" (Action Guidance)

**Problema:** Dopo aver visto i risultati, l'utente non sa cosa fare. Non c'è nessuna indicazione normativa o pratica.

**Soluzione:** Aggiungere una sezione statica in fondo al risultato, condizionale allo status.

**Versione CONFORME:**

```
✅ Prossimi Passi — Azienda Conforme

• Conserva questo report come documentazione di compliance.
• Ripeti l'analisi almeno una volta l'anno (obbligatorio per aziende con 250+ dipendenti).
• Monitora le categorie con gap tra 3–5%: sono nella soglia ma potrebbero sforare.

📌 Riferimento normativo: Art. 9, Direttiva EU 2023/970
```

**Versione NON CONFORME:**

```
⚠️ Prossimi Passi — Azione Richiesta

Hai 6 mesi dalla data di rilevazione per avviare le azioni correttive.

PRIORITÀ ALTA (Gap > 10%):
1. Esegui un'analisi dettagliata del ruolo specifico
2. Documenta le ragioni oggettive della differenza (esperienza, performance, ecc.)
3. Se non giustificabile, prepara un piano di adeguamento retributivo

PRIORITÀ MEDIA (Gap 5–10%):
1. Avvia una valutazione retributiva congiunta con i rappresentanti dei dipendenti
2. Rivedi le pratiche di assunzione e promozione per i ruoli interessati
3. Documenta il processo di revisione

📌 Riferimento normativo: Art. 9-10, Direttiva EU 2023/970
```

**Acceptance Criteria:**
- [ ] La sezione è sempre visibile in fondo al risultato (non collassabile in default)
- [ ] Il testo è condizionale: diverso per aziende compliant vs non-compliant
- [ ] La versione non-compliant distingue Gap > 10% da Gap 5–10%
- [ ] È presente un link/citazione alla Direttiva EU
- [ ] Il copy è in italiano, chiaro, senza jargon legale

---

## 7. Requisiti — NICE TO HAVE (P1)

Queste funzionalità migliorano significativamente l'esperienza ma il tool funziona senza di esse. Sono candidate per la **v1.1**, post-lancio.

---

### NTH-01 — Pay Progression Trajectory (Analisi per Anzianità)

**Informazione che emerge:** "Il gap si amplia man mano che i dipendenti avanzano nella carriera?"

**Perché è utile:** Risponde alla domanda "perché esiste il gap?" — distingue se il problema è al momento dell'assunzione o si accumula nel tempo.

**Compliance value:** EU Directive Art. 9 richiede che i criteri di progressione siano gender-neutral. Questo grafico lo verifica visivamente.

**Dove inserirlo:** Dopo la sezione Category Breakdown, come sezione espandibile ("Analisi Avanzata").

**Grafico:** Dual-line chart con ribbon fill — una linea per stipendio medio uomini, una per donne, su asse X = anni nell'azienda (bucket: 0–2, 2–4, 4–6, 6–8, 8+).

```
Progressione Retributiva per Anzianità
€65k  ↗ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ Uomini
      ░░░░░░░░░░░░░░░░░░░░░░░░ (gap crescente)
€45k  ↗ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ Donne
      0–2       4–6       8–10+  anni

⚠️ Il gap si allarga negli anni: +3% a 2 anni → +12% a 8 anni.
   Suggerito: revisione dei criteri di promozione e aumento.
```

**Dati richiesti:** Aggiunta campo `hire_date` (o `years_at_company`) al CSV di input.

**Acceptance Criteria (se implementato):**
- [ ] Il grafico è in una sezione collassabile (default: chiuso)
- [ ] L'asse X è in anni di anzianità, l'asse Y in € medi
- [ ] Il callout automatico rileva se il gap aumenta nel tempo
- [ ] Funziona solo se il campo `hire_date` è presente nel CSV (altrimenti nascosto)

---

### NTH-02 — Bonus Gap Deep Dive (Eligibilità + Importo per Dipartimento)

**Informazione che emerge:** "Il gap bonus è perché le donne ricevono bonus più bassi, o perché meno donne ne hanno diritto?"

**Perché è utile:** Distingue discriminazione nell'accesso (strutturale) da discriminazione nell'importo (discrezionale). Sono problemi diversi con soluzioni diverse.

**Compliance value:** La Direttiva EU richiede di riportare separatamente la retribuzione variabile. Questo approfondimento dimostra due livelli di analisi.

**Dove inserirlo:** Immediatamente dopo i KPI cards, in una sotto-sezione espandibile "Analisi Bonus".

**Layout:** Small multiples — una mini-card per dipartimento con due sub-metriche: % eligibilità e importo medio.

```
Analisi Bonus per Dipartimento

[Sales]                    [Engineering]           [HR]
Eligibilità Bonus:         Eligibilità Bonus:       Eligibilità Bonus:
Uomini: 95%               Uomini: 92%             Uomini: 87%
Donne:  72% ⚠️             Donne:  91% ✅            Donne:  85% ✅

Importo Medio:             Importo Medio:           Importo Medio:
Uomini: €3.880            Uomini: €2.140          Uomini: €1.950
Donne:  €3.200 (17% gap)⚠️ Donne: €2.150 (ok)✅    Donne:  €1.890 (ok)✅
```

**Dati richiesti:** Campo `is_bonus_eligible` (boolean) opzionale nel CSV.

**Acceptance Criteria (se implementato):**
- [ ] Visibile solo se la colonna `bonus` è presente nel CSV
- [ ] Distingue "% eleggibili" da "importo medio" come due metriche separate
- [ ] Il badge ⚠️ appare se il gap eligibilità o importo supera il 5%
- [ ] Ordinato per gap totale decrescente (dipartimenti più critici prima)

---

### NTH-03 — Compa-Ratio Distribution (Confronto con Banda Salariale Interna)

**Informazione che emerge:** "Quanti dipendenti sono al di sotto, dentro, o sopra la banda salariale prevista per il loro ruolo? Le donne sono sistematicamente al di sotto?"

**Perché è utile:** Consente all'azienda di costruire una difesa oggettiva ("paghiamo in base alla banda salariale interna, non al genere") e identifica chi è a rischio di attrition per sottopagamento.

**Dove inserirlo:** In una sezione "Analisi Avanzata" collassabile, dopo i Quartili.

**Grafico:** Histogram divergente centrato sul 100% (= midpoint della banda).

```
Distribuzione Compa-Ratio per Genere (Senior Engineer)

Sotto banda    ←───────────100% (midpoint)───────────→    Sopra banda

    3 Donne  [●────────────│]                  ← sotto al 95%
    2 Uomini        [●─────│]                  ← tra 95-100%
    4 Uomini              [│──●]               ← tra 100-105%
    2 Donne               [│──────●]           ← sopra al 105%

Media donne: 96% | Media uomini: 102%
⚠️ Le donne tendono a essere pagate sotto al midpoint della banda.
```

**Dati richiesti:** Campo `salary_band_midpoint` nel CSV (o derivabile da `level` se le bande sono note).

**Acceptance Criteria (se implementato):**
- [ ] Visibile solo se `salary_band_midpoint` è presente nel CSV
- [ ] Centrato visivamente su 100% (= midpoint banda)
- [ ] I due colori gender-neutral (gray-700 / gray-400) coerenti con il resto
- [ ] Callout automatico se la media compa-ratio donne < 97% (segnale di pay compression sistematica)

---

### NTH-04 — Export Report EU-Compliant (PDF/Excel)

**Informazione che emerge:** Il tool produce il dato, ma non il documento da consegnare alle autorità.

**Perché è utile:** La Direttiva richiede la pubblicazione del report (Art. 9). Avere un export pronto elimina un passaggio manuale e riduce gli errori.

**Dove inserirlo:** Pulsante "Esporta Report" nella barra superiore della sezione Analisi Dati.

**Output:** PDF (preferito) o Excel con le stesse 5 metriche EU, formattato con intestazione aziendale.

**Dati richiesti:** Nome azienda, anno di riferimento (input opzionale dall'utente).

**Acceptance Criteria (se implementato):**
- [ ] Export attivabile con un click, senza configurazione obbligatoria
- [ ] Il documento include tutte e 5 le metriche EU richieste dall'Art. 9
- [ ] Include data di generazione e periodo di riferimento
- [ ] Export in PDF (priorità) o Excel

---

## 8. Metriche di Successo

### 8.1 Leading Indicators (misurabili entro 2 settimane dal lancio)

| Metrica | Target | Come misuriamo |
|---|---|---|
| % sessioni che arrivano in fondo alla dashboard senza chiudere | > 70% | Analytics logger (già implementato) |
| Tempo medio sulla pagina Analisi Dati | > 90 secondi | Analytics logger |
| % upload con errore (file non riconosciuto) | < 10% | Error rate nel log |
| Rimbalzo immediato dalla pagina (< 10 sec) | < 15% | Analytics logger |

### 8.2 Lagging Indicators (misurabili in 30–60 giorni)

| Metrica | Target | Come misuriamo |
|---|---|---|
| NPS qualitativo HR Manager | > 8/10 | Raccolta manuale feedback |
| Menzioni/condivisioni su LinkedIn | 5+ in 30 giorni | Monitoring manuale |
| Richieste feature aggiuntive (segnale di engagement) | 3+ richieste documentate | GitHub issues / email dirette |

---

## 9. Open Questions

| Domanda | Owner | Blocking? |
|---|---|---|
| Dobbiamo mostrare "uomini/donne" o terminologia EU più neutra (es. "Gruppo A / Gruppo B")? | Marco (legal) | ⚠️ Pre-lancio |
| Il threshold del 5% è sempre fisso o varia per dimensione aziendale? | Claude (research) | No — attualmente fisso per tutti |
| L'export PDF (NTH-04) deve includere firma digitale o timbro aziendale? | Marco | No — v2 |
| Dobbiamo aggiungere un campo `data_riferimento` all'upload (es. "analisi al 31/12/2025")? | Marco | ⚠️ Importante per report ufficiale |
| I simboli ♂/♀ sono legalmente appropriati nella UI? Preferire scritto esteso? | Marco (UX + legal) | No — ma da decidere prima del lancio |

---

## 10. Timeline e Fasi

### Fase 1 — MUST HAVE (Obiettivo: fine marzo 2026)

| Task | Stima | Note |
|---|---|---|
| MUST-01: Nuova palette colori | 2h | CSS token update + propagazione template |
| MUST-02: Ridisegno Status Banner | 2h | Template HTML + copy |
| MUST-03: KPI Cards auto-esplicative | 3h | Aggiornare template + aggiungere testi |
| MUST-04: Category Breakdown label | 1h | Rinomina label + warning campione piccolo |
| MUST-05: Quartile Chart riordinato | 2h | Logica sort + callout automatico |
| MUST-06: Sezione Prossimi Passi | 2h | Template condizionale + copy normativo |
| **Totale stimato** | **~12h** | |

### Fase 2 — NICE TO HAVE (Obiettivo: aprile/maggio 2026)

| Task | Stima | Priorità |
|---|---|---|
| NTH-01: Pay Progression Trajectory | 12h | Alta (se `hire_date` disponibile) |
| NTH-02: Bonus Gap Deep Dive | 8h | Media |
| NTH-04: Export PDF/Excel | 10h | Alta (percepita come must da molti HR) |
| NTH-03: Compa-Ratio | 15h | Bassa (richiede dati aggiuntivi) |

---

## 11. Riferimenti

### Normativi
- [Direttiva EU 2023/970 — Testo Ufficiale](https://eur-lex.europa.eu/eli/dir/2023/970/oj/ita)
- [Consiglio UE — Pay Transparency](https://www.consilium.europa.eu/en/policies/pay-transparency/)
- [Jackson Lewis — Come prepararsi agli obblighi EU](https://www.jacksonlewis.com/insights/how-prepare-your-company-now-eu-pay-transparency-obligations)

### Design
- [Apple Human Interface Guidelines — Color](https://developer.apple.com/design/human-interface-guidelines/color)
- [WCAG 2.1 AA — Contrasto colori](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)

### HR Analytics
- [AIHR — Pay Equity Analysis](https://www.aihr.com/blog/pay-equity-analysis/)
- [Compport — Global Compensation Analytics Dashboard](https://www.compport.com/blog/how-global-enterprises-build-compensation-analytics-dashboards)
- [SplashBI — HR Metrics Dashboards 2025](https://splashbi.com/blog/6-essential-hr-metrics-dashboards-you-need-in-2025/)

---

*Documento generato in sessione di co-design: Marco Guadagno + Claude (AI Co-founder)*
*Versione 1.0 — 4 marzo 2026*
