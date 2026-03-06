# PRD — Tool Locale: Analisi Gender Pay Gap in-browser
**Versione**: 1.0
**Data**: 2026-03-04
**Autore**: Marco Guadagno & AI Co-founder
**Stato**: Draft

---

## 1. Problem Statement

Le aziende che devono analizzare il proprio gender pay gap per conformarsi alla Direttiva EU 2023/970 si trovano spesso di fronte a un blocco non tecnico ma umano: **i dati retributivi sono tra le informazioni più sensibili di un'organizzazione**, e molti responsabili HR o CFO non sono disposti a caricarli su un sistema esterno — neanche gratuito — per questioni di policy interna, GDPR, o semplicemente diffidenza.

Questo blocco psicologico e organizzativo esclude una quota significativa di potenziali utenti, proprio quelli che hanno più bisogno del tool: le aziende che non possono permettersi consulenti a €25.000 ma che allo stesso tempo non si fidano dei sistemi cloud.

La mancanza di un'alternativa locale fa sì che queste aziende rimandino l'analisi, la deleghino a consulenti costosi, o la saltino del tutto — con conseguente rischio di non conformità alla Direttiva entro il 7 giugno 2027.

---

## 2. Goals

### Obiettivi utente
- **G-01**: Un HR Manager senza competenze tecniche riesce a completare l'analisi del gap in meno di 3 minuti dal download del file.
- **G-02**: L'utente ha la certezza assoluta che nessun dato lascia il proprio computer (zero dipendenze di rete dopo il download).
- **G-03**: Il report prodotto è identico — per qualità e contenuto — a quello del portale web.

### Obiettivi di prodotto / business
- **G-04**: Rimuovere il principale blocco alla conversione per chi non carica dati sul portale.
- **G-05**: Costo di hosting e manutenzione aggiuntivo = **zero** (file statico distribuito via GitHub Releases).
- **G-06**: La feature diventa un argomento di differenziazione comunicativa ("zero upload, zero cloud") rispetto ai competitor a pagamento.

---

## 3. Non-Goals

- **NG-01 — Nessun chatbot normativo**: Il tool locale NON include il RAG/chatbot sulle normative. Quello resta esclusivo del portale. Chi vuole risposte sulla Direttiva EU deve passare dal sito.
- **NG-02 — Nessuna installazione di software**: Non è nel perimetro creare un'app desktop (Electron), un eseguibile (.exe/.app), o richiedere Python/Docker. Zero prerequisiti oltre al browser.
- **NG-03 — Nessun salvataggio/persistenza**: Il tool locale non salva dati, non crea profili, non ricorda analisi precedenti. Ogni sessione è effimera e privata per design.
- **NG-04 — Nessun aggiornamento automatico**: Non c'è meccanismo di auto-update. L'utente scarica la versione corrente; per versioni future ri-scarica il file.
- **NG-05 — Nessuna connessione a LLM in locale**: Non usiamo Ollama o modelli locali. L'analisi è pura matematica — non serve AI.

---

## 4. User Stories

### Persona primaria: HR Manager, azienda 100–500 dipendenti, Italia

**US-01 — Download e primo avvio** *(P0)*
Come HR Manager, voglio scaricare un singolo file dal sito e aprirlo nel mio browser, così da avviare l'analisi senza installare nulla e senza chiedere aiuto all'IT.

**US-02 — Caricamento CSV** *(P0)*
Come HR Manager, voglio trascinare il mio file CSV nella pagina (o selezionarlo dal mio computer), così da avviare l'analisi senza dover capire come funziona il file HTML.

**US-03 — Visualizzazione risultati** *(P0)*
Come HR Manager, voglio vedere gli stessi KPI e grafici che vedo sul portale web (gap medio, mediano, per categoria, quartili, prossimi passi), così da avere un'analisi completa anche senza caricare dati online.

**US-04 — Conferma privacy** *(P0)*
Come HR Manager, voglio vedere chiaramente nella pagina che i dati non vengono inviati a nessun server, così da poter usare il tool anche su dati sensibili senza violare le policy aziendali.

**US-05 — Errore CSV non valido** *(P0)*
Come HR Manager, voglio ricevere un messaggio chiaro e non tecnico se il mio CSV ha colonne mancanti o formato errato, così da poter correggere senza dover cercare documentazione tecnica.

**US-06 — Template CSV di esempio** *(P1)*
Come HR Manager, voglio poter scaricare un file CSV di esempio già compilato, così da capire esattamente il formato richiesto prima di preparare il mio file reale.

**US-07 — Link al portale** *(P1)*
Come HR Manager che ha appena completato l'analisi, voglio vedere un invito a visitare il portale per fare domande sulla normativa, così da avere un percorso naturale verso il chatbot senza sentirmi "abbandonato" dopo l'analisi.

---

## 5. Requirements

### Must-Have / P0 — Il file non è distribuibile senza questi

**LOC-01 — Architettura: Single HTML File**
Il tool è un singolo file `.html` autocontenuto. Non richiede connessione internet dopo il download. Tutte le dipendenze (CSS, logica di analisi, icone) sono incluse inline o caricate da CDN pubblici (Tailwind CDN, Papa Parse CDN) al primo avvio — oppure, nella versione fully-offline, inlined nel file.

*Acceptance criteria:*
- [ ] Il file funziona senza connessione internet (fully-offline build)
- [ ] Il file ha dimensione < 500KB
- [ ] Si apre in Chrome, Firefox, Safari, Edge senza configurazione aggiuntiva
- [ ] Non scrive nulla su localStorage, cookie, o qualsiasi forma di storage

**LOC-02 — CSV Parser lato browser**
Usa PapaParse (libreria JS) per leggere e validare il file CSV. Il parsing avviene interamente nel browser; il contenuto del file non viene mai inviato a nessun server.

Colonne CSV attese (allineate con il portale):
| Colonna | Tipo | Obbligatoria | Note |
|---|---|---|---|
| `gender` | stringa `M`/`F` | ✅ | Case-insensitive |
| `base_salary` | numero | ✅ | Lordo annuo in €, senza separatori |
| `department` | stringa | ⚠ consigliata | Per analisi per categoria |
| `level` | stringa | ⚠ consigliata | Per analisi per categoria |
| `bonus` | numero | ❌ opzionale | Se assente, si mostra composizione personale |

*Acceptance criteria:*
- [ ] File con sole colonne `gender` e `base_salary` produce un'analisi parziale valida (senza category breakdown)
- [ ] File con colonne errate mostra errore in italiano, non tecnico
- [ ] File con encoding UTF-8 e UTF-8 BOM (Excel italiano) sono entrambi supportati
- [ ] Separatori `,` e `;` (Excel italiano) sono entrambi supportati

**LOC-03 — Logica di analisi in JavaScript**
Reimplementazione in JavaScript puro delle seguenti funzioni di `gap_calculator.py`:
- `overall_mean_gap()` — media M vs F
- `overall_median_gap()` — mediana M vs F
- `gap_by_category()` — gap per (department, level), con filtro campione < 2 per genere
- `pay_quartiles()` — distribuzione Q1–Q4 con % per genere
- `bonus_gap()` — gap sui bonus, opzionale
- `full_analysis()` — oggetto di compliance result complessivo

Formula gap: `GPG = (media_M - media_F) / media_M × 100`
Soglia EU: `5.0%` (identica al backend Python)

*Acceptance criteria:*
- [ ] Dato lo stesso CSV, i risultati JS e Python differiscono di meno di 0.1% (floating point tolerance)
- [ ] Categorie con < 2 dipendenti per genere vengono escluse
- [ ] Il flag `is_significant` segue la stessa soglia del 5% del backend

**LOC-04 — UI identica al portale**
Il dashboard HTML del tool locale deve essere visivamente e funzionalmente identico alla sezione "Analisi" del portale (basato su `upload_result.html`):
- Status Banner (Conforme / Non Conforme) con spiegazione soglia 5%
- KPI Cards (Gap Medio, Gap Mediano, Gap Bonus o Composizione)
- Category Breakdown con barre orizzontali, label "Uomini"/"Donne", warning campione ridotto
- Quartile Chart con Q4 in alto, range salariali, callout automatico
- Sezione "Prossimi Passi" condizionale su compliance status
- Palette colori: gray-700 (uomini), gray-400 (donne), emerald/amber/red semantici

*Acceptance criteria:*
- [ ] Tutti i 6 componenti MUST del PRD "Analisi Dati v1" sono presenti e funzionanti
- [ ] Il design è identico al portale (stesso Tailwind, stesse classi, stessi colori)
- [ ] Il layout è responsive e funziona su schermi 1024px+

**LOC-05 — Banner Privacy ben visibile**
Nella parte alta della pagina, prima del drag-and-drop, è presente un banner che comunica esplicitamente che i dati non lasciano il browser. Il messaggio deve essere comprensibile a un non tecnico.

Testo suggerito (modificabile):
*"🔒 I tuoi dati non lasciano mai questo computer. L'analisi avviene interamente nel tuo browser — nessun file viene inviato a server esterni."*

*Acceptance criteria:*
- [ ] Il banner è visibile senza scroll sulla maggior parte dei monitor (≥ 768px di altezza viewport)
- [ ] Il testo è in italiano
- [ ] Il colore del banner è coerente con la palette (emerald/verde per trasmettere sicurezza)

**LOC-06 — Gestione errori CSV in italiano semplice**
I messaggi di errore devono essere comprensibili a un HR Manager non tecnico. Nessun messaggio tipo "TypeError: cannot read property 'gender' of undefined".

Errori gestiti e relativi messaggi:
| Situazione | Messaggio mostrato |
|---|---|
| File non CSV | "Questo file non sembra un CSV. Prova a esportare da Excel come 'CSV UTF-8'." |
| Colonna `gender` mancante | "La colonna 'gender' è obbligatoria. Assicurati che il tuo file abbia una colonna con i valori M/F." |
| Colonna `base_salary` mancante | "La colonna 'base_salary' è obbligatoria. Deve contenere lo stipendio lordo annuo in euro." |
| CSV vuoto o 0 righe valide | "Il file sembra vuoto o non contiene dati validi." |
| Tutti M o tutte F | "Il file non contiene dipendenti di entrambi i generi. L'analisi del gap richiede dati di uomini e donne." |

*Acceptance criteria:*
- [ ] Nessun messaggio di errore tecnico esposto all'utente
- [ ] L'errore è mostrato inline (non come alert/popup del browser)
- [ ] Dopo l'errore, l'utente può riprovare con un altro file senza ricaricare la pagina

---

### Nice-to-Have / P1 — Valore aggiunto per v1.1

**LOC-07 — CSV Template di esempio**
Bottone "Scarica CSV di esempio" che fa scaricare un file `esempio-dati.csv` precompilato con 20 righe di dati fittizi ma realistici (5 dipartimenti, 2 livelli, bonus opzionale).

**LOC-08 — CTA verso il portale post-analisi**
Dopo la visualizzazione dei risultati, una sezione in fondo alla pagina con: *"Hai domande sulla Direttiva EU? Il nostro chatbot risponde gratuitamente →"* con link al portale.

**LOC-09 — Stampa / Salva come PDF**
Bottone "Salva report" che triggera `window.print()` con CSS ottimizzato per stampa (nasconde elementi UI, pagina A4, intestazione con data analisi).

**LOC-10 — Indicatore "Analizzati N dipendenti"**
Piccola notifica dopo il parsing che mostra quante righe sono state lette, quante scartate (per genere non valido, salary null, ecc.) prima di mostrare i risultati.

---

### Future Considerations / P2 — Non in scope v1, ma architettura deve supportarle

**LOC-11 — Multi-lingua**: Il file HTML ha tutti i testi in italiano hardcoded. La struttura deve prevedere l'uso di oggetti `i18n` (JSON di testi per lingua) che rendano possibile una futura versione EN/FR/DE senza riscrivere la logica.

**LOC-12 — Versione offline completa senza CDN**: Una build alternativa "fully-offline" con tutte le dipendenze JS/CSS inlined nel file, per ambienti aziendali con firewall che bloccano CDN esterni. Stessa funzionalità, file più grande (~700KB).

---

## 6. Success Metrics

| Metrica | Target v1 (30 giorni) | Come misuriamo |
|---|---|---|
| Download del file HTML | ≥ 50 download/mese | GitHub Releases download count |
| Task completion rate | ≥ 80% degli utenti che aprono il file completano l'analisi | Non misurabile direttamente (privacy-first) — proxy: supporto richieste su "come si usa" |
| Errori CSV segnalati | < 20% degli utenti segnala problemi col CSV | Feedback form sul portale |
| Tempo al primo risultato | < 3 minuti dal download | Test qualitativo su 5 utenti non tecnici |

*Nota*: Per design il tool locale non traccia analytics. Le metriche di adoption sono misurate indirettamente (download GitHub, accessi alla pagina di download sul portale, feedback qualitativo).

---

## 7. Open Questions

| # | Domanda | Chi risponde | Blocking? |
|---|---|---|---|
| OQ-01 | Distribuiamo il file via GitHub Releases o direttamente dal sito (link statico)? La scelta impatta il tracking dei download. | Marco (strategico) | No — decidiamo prima della distribuzione |
| OQ-02 | La build v1 può dipendere da CDN (Tailwind, PapaParse) o deve essere fully-offline sin dal primo rilascio? Alcune aziende con ambienti IT restrittivi potrebbero non raggiungere i CDN. | Marco (audience target) | **Sì** — impatta architettura |
| OQ-03 | Il CSV di esempio (LOC-07) deve usare dati completamente fittizi o possiamo usare nomi di aziende/dipartimenti realistici italiani? | Marco | No |
| OQ-04 | Versione terminologica: il file HTML usa "Uomini/Donne" o "Gruppo A/Gruppo B" (questione aperta dal PRD Analisi Dati)? | Marco | No — allineare alla decisione del portale |
| OQ-05 | Come gestiamo valori `gender` non-binari o non standard nel CSV (es. "X", "NB", "altro")? Silently skippati o warning? | Marco + legale | No — ma meglio decidere prima del lancio |

---

## 8. Timeline Considerations

**Hard deadline**: 7 giugno 2026 — prima scadenza per la trasposizione italiana della Direttiva. Il tool deve essere disponibile almeno 60 giorni prima per dare tempo alle aziende di usarlo.
**Target rilascio**: **fine marzo 2026** (4 settimane da oggi).

### Fasi suggerite

**Fase 1 — Core (1–2 settimane)**
LOC-01, LOC-02, LOC-03: Single HTML file + CSV parser + logica JS
Output: file funzionante ma senza styling

**Fase 2 — UI (3–5 giorni)**
LOC-04, LOC-05, LOC-06: Dashboard identico al portale + banner privacy + gestione errori
Output: file distribuibile

**Fase 3 — Polish + Distribuzione (2–3 giorni)**
LOC-07, LOC-08: CSV template + CTA portale + pagina di download sul sito
Output: feature completa e comunicata agli utenti

---

## 9. Riferimenti

- PRD Analisi Dati v1: `docs/plans/PRD-analisi-dati-v1.md`
- Template dashboard portale: `templates/partials/upload_result.html`
- Logica Python di riferimento: `src/analysis/gap_calculator.py`
- Direttiva EU 2023/970, Art. 9 (metriche obbligatorie) e Art. 10 (azioni correttive)
- PapaParse docs: https://www.papaparse.com/docs
- Tailwind CDN: https://cdn.tailwindcss.com
