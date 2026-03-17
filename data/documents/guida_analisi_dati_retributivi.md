# Guida all'Analisi dei Dati Retributivi

## Come utilizzare la funzione di analisi gender pay gap del Pay Transparency Tool

> **Nota**: Questa guida spiega come preparare i dati e utilizzare la funzione di analisi del gender pay gap, sia tramite il portale web che tramite il tool locale offline.

---

## Sezione 1 — Preparazione dei dati

### Come devo preparare il file per l'analisi?

Il tool accetta file in formato **CSV** o **Excel** (.xlsx, .xls). Il modo più semplice è partire dal template Excel scaricabile dalla pagina "Analisi Dati" del portale.

**Colonne obbligatorie:**
- **gender**: il genere del dipendente, con valori `M` (uomo) o `F` (donna). Non è case-sensitive (accetta anche `m`, `f`, `Male`, `Female`).
- **base_salary**: lo stipendio lordo annuo in euro. Inserire solo il numero, senza simbolo € e senza separatori delle migliaia (es. `48000`, non `€48.000`).

**Colonne consigliate (per analisi completa):**
- **department**: il dipartimento di appartenenza (es. "Engineering", "Marketing", "HR"). Permette l'analisi del gap per categoria, obbligatoria per la compliance con la Direttiva EU 2023/970.
- **level**: il livello aziendale (es. "Junior", "Mid", "Senior", "Lead", "Director"). Insieme a `department`, permette il breakdown dettagliato richiesto dalla Direttiva.

**Colonne opzionali:**
- **employee_id**: identificativo univoco del dipendente. Utile per il tracking interno, non usato nell'analisi.
- **bonus**: premio variabile annuo lordo in euro. Se presente, il tool calcola anche il gap sulla retribuzione variabile (Art. 3, Direttiva 2023/970).

---

### Come esporto i dati dal mio sistema HR o da Excel?

1. **Da Excel**: Apri il file, seleziona "File > Salva con nome", scegli il formato **"CSV UTF-8 (delimitato da virgola)"**. In alternativa, salva direttamente come `.xlsx` e caricalo sul tool.
2. **Da sistemi HR** (SAP, Workday, Zucchetti, ADP, ecc.): cerca la funzione di esportazione dati o reportistica. Esporta i campi: genere, stipendio base annuo, dipartimento e livello. Salva come CSV o Excel.
3. **Importante per Excel italiano**: Excel in italiano usa il punto e virgola (`;`) come separatore CSV. Il tool lo gestisce automaticamente, quindi puoi esportare con le impostazioni predefinite.

---

### Quanti dipendenti servono per un'analisi significativa?

- **Minimo tecnico**: 2 dipendenti per genere (almeno 2 uomini e 2 donne).
- **Minimo consigliato**: 50 dipendenti totali per risultati statisticamente significativi.
- **Per l'analisi per categoria**: servono almeno 2 persone per genere in ogni combinazione dipartimento+livello. I gruppi più piccoli vengono automaticamente esclusi dall'analisi per categoria.
- **Nota**: la Direttiva EU 2023/970 richiede il reporting obbligatorio per aziende con 100+ dipendenti (dal 2027) e 250+ dipendenti (dal 2027).

---

## Sezione 2 — Utilizzo del tool

### Come carico il file sul portale web?

1. Vai sulla pagina principale del tool e clicca sulla tab **"Analisi Dati"** in alto.
2. Vedrai due opzioni:
   - **"Carica e analizza"** (viola): il file viene elaborato sul server in memoria temporanea e cancellato subito dopo.
   - **"I dati restano nel tuo PC"** (verde): scarica il tool locale che analizza tutto nel browser senza inviare nulla.
3. Se non hai ancora un file pronto, clicca su **"Scarica il template Excel"** in basso per ottenere un modello precompilato.
4. Seleziona il tuo file CSV o Excel. L'analisi parte automaticamente.
5. In pochi secondi vedrai la dashboard completa con tutti i risultati.

---

### Cosa fa il tool locale offline?

Il tool locale è un singolo file HTML che puoi scaricare e aprire nel tuo browser. Funziona **completamente offline**: nessun dato lascia il tuo computer. L'analisi avviene interamente nel browser tramite JavaScript. È ideale per aziende con policy restrittive sui dati o per chi preferisce non caricare dati sensibili su server esterni.

---

## Sezione 3 — Interpretazione dei risultati

### Cosa significano gap medio e gap mediano?

- **Gap retributivo medio (mean gender pay gap)**: è la differenza percentuale tra la retribuzione media degli uomini e quella delle donne. Formula: `(media_uomini - media_donne) / media_uomini × 100`. Può essere influenzato da pochi stipendi molto alti o molto bassi.
- **Gap retributivo mediano (median gender pay gap)**: è la differenza percentuale calcolata sulla mediana (il valore centrale). È più robusto agli estremi e dà una misura più rappresentativa della differenza "tipica".
- **Esempio**: se il gap medio è 12% ma il gap mediano è 5%, probabilmente ci sono pochi uomini con stipendi molto alti che "tirano su" la media.

**Fonte**: Art. 9, par. 1, lett. a) e b), Direttiva (UE) 2023/970 — entrambe le metriche sono obbligatorie nel reporting.

---

### Cosa significa la soglia del 5%?

La Direttiva EU 2023/970 stabilisce che se il **gap retributivo medio o mediano** in una categoria di lavoratori supera il **5%** e il datore di lavoro non può giustificarlo con criteri oggettivi e neutri rispetto al genere, è obbligatorio avviare una **valutazione retributiva congiunta** con i rappresentanti dei lavoratori entro 6 mesi (Art. 10).

- **Gap < 5%**: l'azienda è conforme alla soglia. Si consiglia comunque un monitoraggio annuale.
- **Gap 5-10%**: attenzione. È necessario verificare se il gap è giustificabile con fattori oggettivi (anzianità, competenze certificate, ecc.). Se non giustificabile, serve la valutazione congiunta.
- **Gap > 10%**: il gap è significativo. Si raccomanda un piano d'azione correttivo prioritario.

**Fonte**: Art. 9, par. 2 e Art. 10, Direttiva (UE) 2023/970.

---

### Cosa sono i quartili retributivi?

I quartili dividono tutti i dipendenti in 4 gruppi uguali ordinati per retribuzione:
- **Q1 (basso)**: il 25% dei dipendenti con retribuzione più bassa
- **Q2**: dal 25° al 50° percentile
- **Q3**: dal 50° al 75° percentile
- **Q4 (alto)**: il 25% dei dipendenti con retribuzione più alta

Per ogni quartile, il tool mostra la distribuzione percentuale uomini/donne. Se le donne sono sovrarappresentate in Q1 (stipendi bassi) e sottorappresentate in Q4 (stipendi alti), è un segnale di disuguaglianza retributiva strutturale.

**Fonte**: Art. 9, par. 1, lett. f), Direttiva (UE) 2023/970 — il reporting sui quartili è obbligatorio.

---

### Cosa devo fare se il gap supera il 5%?

Secondo la Direttiva EU 2023/970 (Art. 10):

1. **Entro 6 mesi**: avviare una valutazione retributiva congiunta con i rappresentanti dei lavoratori.
2. **Nella valutazione**: analizzare le cause del gap, le differenze nei criteri di classificazione, e sviluppare misure correttive.
3. **Possibili giustificazioni oggettive**: anzianità di servizio, qualifiche certificate specifiche per il ruolo, condizioni di mercato documentate, sede geografica (se previsto dal CCNL).
4. **Se non giustificabile**: adeguare le retribuzioni e documentare il piano correttivo.

---

## Sezione 4 — Privacy e sicurezza dei dati

### I miei dati sono al sicuro?

- **Sul portale web**: il file caricato viene elaborato in memoria RAM e cancellato immediatamente dopo l'analisi. Non viene salvato su disco. I dati individuali (nomi, stipendi singoli) non vengono mai inviati a servizi esterni.
- **Con il tool locale offline**: i dati non lasciano MAI il tuo computer. L'analisi avviene interamente nel browser, senza alcuna connessione di rete.
- **Nel chatbot**: il chatbot risponde a domande sulla normativa consultando il testo della Direttiva EU. Non ha accesso ai dati retributivi caricati per l'analisi.

---

### Posso usare il tool con dati reali della mia azienda?

Sì. Il tool è progettato per analizzare dati retributivi reali in modo sicuro. Se la tua azienda ha policy restrittive sull'invio di dati a server esterni, usa il **tool locale offline** che analizza tutto nel browser senza inviare nulla.

**Fonte**: Art. 12, Direttiva (UE) 2023/970 — i dati personali trattati ai fini degli articoli 9 e 10 non possono essere usati per altri scopi.
