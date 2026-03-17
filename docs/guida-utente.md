# Guida Utente: Pay Transparency Tool

Benvenuto! Questa guida ti accompagnerà passo dopo passo nell'uso del Pay Transparency Tool, uno strumento gratuito e facile da usare per analizzare il divario salariale di genere nella tua azienda e comprendere gli obblighi della Direttiva EU 2023/970.

---

## Cos'è la Direttiva EU 2023/970?

La **Direttiva Europea 2023/970** sulla trasparenza salariale è una normativa che richiede alle aziende di adottare misure concrete per garantire parità di retribuzione tra uomini e donne. In sintesi:

- **Chi è coinvolto**: a partire da **giugno 2027**, le aziende con **250+ dipendenti** devono rispettarla; dal **2031**, anche le aziende con **100+ dipendenti**
- **Cosa richiede**: comunicazione periodica del divario retributivo di genere (sia in media che per categoria)
- **La soglia critica**: se il divario supera il **5%**, l'azienda deve fornire una giustificazione o adottare azioni correttive
- **Il bonus gap**: il divario non riguarda solo lo stipendio base, ma anche i bonus e gli incentivi
- **La collaborazione**: in caso di divario significativo, l'azienda deve consultarsi con i rappresentanti dei lavoratori per pianificare correzioni entro 6 mesi

Questo tool è qui per aiutarti a comprendere e adempiere a questi obblighi in modo semplice e veloce.

---

## Cosa fa questo strumento?

Il Pay Transparency Tool mette a tua disposizione **3 funzionalità principali**, tutte progettate per essere user-friendly:

### 1. **Assistente Normativo (Chatbot IA)**
Puoi rivolgere domande sulla Direttiva EU 2023/970 in linguaggio naturale. L'assistente risponde basandosi sul testo ufficiale della normativa in italiano e in inglese. Perfetto per chiarire dubbi su articoli specifici, scadenze, e obblighi della tua azienda.

### 2. **Analisi Dati del Pay Gap (Online)**
Carica il file CSV o Excel con i dati retributivi dei tuoi dipendenti e ottieni immediatamente un report di compliance completo: gap medio, gap mediano, analisi per categoria (dipartimento e livello), distribuzione per quartili salariali, gap sui bonus, e stato di conformità rispetto alla soglia del 5%.

### 3. **Strumento Offline Locale**
Uno file HTML indipendente che puoi scaricare e aprire nel browser senza internet. Esegue la stessa analisi di pay gap **100% nel tuo computer**: i dati non vengono mai trasmessi, perfetto per aziende con politiche dati rigorose.

**Vantaggi del tool**:
✓ Completamente gratuito e open source
✓ Nessuna registrazione richiesta
✓ Conforme al GDPR (i dati rimangono tuoi)
✓ Disponibile in italiano

---

## Come usare il Chatbot Normativo

Hai domande sulla Direttiva? L'Assistente è il tuo alleato migliore.

### Passaggi:

1. **Accedi allo strumento**
   Visita https://pay-transparency.marcog-ai4hr.cloud/

2. **Seleziona la tab "Assistente"**
   Nella parte superiore della pagina, troverai tre tab: Assistente, Analisi Dati, e Info. Clicca su "Assistente".

3. **Scrivi la tua domanda**
   Nel riquadro di testo, digita la tua domanda in italiano. Puoi fare domande specifiche o generali sulla normativa.

4. **Esempi di domande utili:**
   - "Cosa dice l'articolo 7 della Direttiva?"
   - "Quali sono gli obblighi per un'azienda con 200 dipendenti?"
   - "Entro quando devo adeguarmi?"
   - "Cos'è il reporting gap?"
   - "Che differenza c'è tra gap mediano e gap medio?"
   - "Quale deve essere il piano di azione se il divario supera il 5%?"

5. **Leggi la risposta**
   L'assistente fornisce la risposta basandosi sul testo ufficiale della Direttiva. Puoi fare domande di follow-up per approfondire.

6. **Ricorda**
   Per analizzare i dati retributivi specifici della tua azienda, usa la tab "Analisi Dati" (vedi sezione successiva).

---

## Come analizzare il Pay Gap (versione online)

Vuoi scoprire il divario salariale nella tua azienda? Segui questa procedura.

### Passaggi:

1. **Prepara il tuo file di dati**
   Prima di tutto, prepara un file CSV o Excel con i dati retributivi. Per i dettagli sul formato esatto, consulta la documentazione [formato-dati.md](formato-dati.md).

   **Minimo richiesto**: una colonna "genere" (M/F) e una "stipendio_base"
   **Consigliato**: aggiungi anche "dipartimento" e "livello" per un'analisi per categoria più dettagliata

2. **Accedi allo strumento**
   Visita https://pay-transparency.marcog-ai4hr.cloud/

3. **Vai alla tab "Analisi Dati"**
   Clicca sulla tab "Analisi Dati" in alto.

4. **Carica il file**
   Trascina il tuo file CSV/Excel nella zona designata oppure clicca per sfogliare il tuo computer e selezionare il file.

5. **Attendi l'analisi**
   Ci vorranno pochi secondi. Il tool processerà i dati e genererà il report.

6. **Leggi i risultati**
   Una volta completata l'analisi, vedrai:
   - **Banner di conformità**: Verde se il divario è inferiore al 5%, Rosso se supera la soglia
   - **Card KPI**: i principali indicatori (gap medio, gap mediano, gap bonus)
   - **Analisi per categoria**: divario calcolato per ogni combinazione dipartimento+livello
   - **Distribuzione per quartili**: mostra se le donne sono concentrate in fasce salariali più basse
   - **Sezione "Prossimi Passi"**: raccomandazioni pratiche in base ai risultati

7. **Scarica il report** (opzionale)
   Potrai scaricare un file PDF del report per conservarlo o condividerlo con stakeholder interni.

---

## Come usare lo Strumento Locale (offline)

Se preferisci mantenere i dati completamente isolati e offline, usa il tool locale.

### Passaggi:

1. **Scarica il file**
   Vai al repository GitHub del progetto e scarica il file `local-tool.html` nella cartella "tools" o "standalone".

2. **Apri il file nel browser**
   Doppio-click sul file `local-tool.html` oppure trascinalo nella finestra del browser.

3. **Carica il tuo file CSV**
   Una volta aperto, vedrai l'interfaccia per caricare il file. Seleziona il tuo CSV/Excel.

4. **Leggi i risultati**
   I risultati appariranno istantaneamente nel browser. L'analisi è identica a quella online.

5. **Nessun dato inviato**
   Tutto avviene **nel tuo computer**. Nessun dato viene trasmesso, salvato su server remoti, o condiviso. Puoi analizzare dati sensibili senza preoccupazioni.

6. **Condividi offline**
   Puoi copiare il file `local-tool.html` su altri computer e usarlo ovunque.

---

## Come preparare il file CSV

Un buon file di dati è la base di un'analisi accurata. Ecco cosa ti serve.

### Requisiti minimi:

Il tuo file deve contenere almeno due colonne:
- **genere** (o "gender"): valori M o F
- **stipendio_base** (o "base_salary"): l'importo dello stipendio annuale o mensile

### Colonne consigliate:

Per un'analisi più ricca e aderente ai requisiti della Direttiva, aggiungi:
- **dipartimento** (o "department"): es. "Vendite", "IT", "HR", "Produzione"
- **livello** (o "level"): es. "Junior", "Senior", "Manager", "Dirigente"

### Colonne facoltative:

- **bonus** (o "bonus_amount"): importo totale dei bonus annuali
- **id_dipendente** (o "employee_id"): identificativo univoco (mantenuto anonimo nell'analisi)

### Esempio di struttura CSV:

```
id_dipendente,genere,dipartimento,livello,stipendio_base,bonus
001,M,IT,Senior,45000,5000
002,F,IT,Senior,44000,4500
003,F,Vendite,Junior,28000,2000
004,M,Vendite,Junior,28500,2200
```

**Per dettagli completi sul formato**, consulta [formato-dati.md](formato-dati.md).

---

## Come leggere i risultati

Una volta completata l'analisi, riceverai un report con vari indicatori. Ecco cosa significa ciascuno.

### **Gap Medio (Mean Gap)**
È la **differenza percentuale media tra lo stipendio degli uomini e quello delle donne**. Se il risultato è +3%, significa che in media gli uomini guadagnano il 3% in più. Se è negativo (-2%), le donne guadagnano in media il 2% in più.

*Nota*: il gap medio può essere influenzato da pochi stipendi molto alti o molto bassi.

### **Gap Mediano (Median Gap)**
È simile al gap medio, ma usa il **valore centrale** anziché la media. È **meno sensibile ai valori estremi** e spesso è un indicatore più affidabile della reale situazione retributiva.

*Esempio*: se hai 5 donne con stipendi 25k, 30k, 32k, 35k, 40k, la mediana è 32k. Se gli uomini hanno mediana 33k, il gap mediano è circa +3%.

### **Gap per Categoria (Category-Specific Gap)**
La Direttiva richiede che tu analizzi il divario **all'interno di ogni combinazione dipartimento + livello**. Questo è il vero fulcro della normativa: confronti donne e uomini che svolgono mansioni simili nello stesso dipartimento.

*Esempio*:
- IT Senior: gap +2% (conforme)
- IT Junior: gap +8% (non conforme, > 5%)
- Vendite Manager: gap -1% (conforme)

### **Quartili (Salary Quartiles)**
Il report mostra come sono distribuiti uomini e donne nelle quattro fasce salariali (Q1 più basso, Q4 più alto).

*Cosa rivela*: se le donne sono concentrate nei quartili inferiori e gli uomini in quelli superiori, c'è un problema strutturale che potrebbe non emergere dal semplice gap percentuale.

*Esempio*:
- Q1 (fascia bassa): 60% donne, 40% uomini
- Q4 (fascia alta): 30% donne, 70% uomini

### **Soglia del 5%**
Qualsiasi categoria (dipartimento + livello) con un gap superiore al **5%** è considerata **non conforme** dalla Direttiva, a meno che l'azienda non sia in grado di fornire una giustificazione oggettiva (es. differenze di esperienza, competenze specifiche, antigüedad, ecc.).

### **Gap sui Bonus**
Simile al gap salariale, ma applicato ai bonus e agli incentivi. Un divario significativo nei bonus amplifica il divario complessivo.

### **Banner di Conformità**
- **Verde**: tutte le categorie hanno gap ≤ 5% oppure gap complessivo < 5% → **CONFORME**
- **Giallo**: alcune categorie sopra il 5%, ma con giustificazione possibile → **CAUTION**
- **Rosso**: divario significativo, divario senza giustificazione → **NON CONFORME**

---

## Cosa fare se il divario supera il 5%

Se l'analisi mostra che il gap è superiore al 5% in una o più categorie, ecco i prossimi passi secondo la Direttiva:

### **1. Valutazione Congiunta**
Devi **consultarti con i rappresentanti dei lavoratori** (sindacati, RSU, delegati) per:
- Analizzare le cause del divario
- Identificare fattori legittimi (esperienza, anzianità, qualifiche, ecc.)
- Proporre azioni correttive

### **2. Piano di Azione**
Se il divario non è giustificabile, devi adottare **misure concrete entro 6 mesi**, come:
- Ajustamenti salariali mirati
- Revisione dei criteri di promozione
- Programmi di sviluppo di carriera per il genere sottorappresentato
- Trasparenza negli scatti di stipendio

### **3. Documentazione**
Conserva tutta la documentazione della valutazione e delle azioni intraprese. Potrebbe esserti richiesta durante i controlli ufficiali.

### **4. Monitoraggio**
Ripeti l'analisi del pay gap periodicamente (almeno annualmente) per verificare che le azioni correttive stiano funzionando.

---

## Glossario

Ecco una spiegazione semplice dei termini tecnici utilizzati nel tool e nella Direttiva.

**Gender Pay Gap (Divario Salariale di Genere)**
La differenza percentuale tra la retribuzione media degli uomini e quella delle donne, calcolata come (stipendio_donne - stipendio_uomini) / stipendio_uomini × 100.

**Mediana**
Il valore centrale di un insieme di dati. Se ordini gli stipendi dal più basso al più alto e prendi il valore nel mezzo, quello è la mediana. È meno sensibile ai valori estremi rispetto alla media.

**Media (Media Aritmetica)**
La somma di tutti i valori divisa per il numero di valori. Più sensibile ai valori molto alti o molto bassi (outlier).

**Quartile**
Divisione dei dati in 4 gruppi uguali. Q1 contiene il 25% più basso, Q4 il 25% più alto. Utile per visualizzare la distribuzione dei salari.

**Soglia 5% (Five Percent Threshold)**
Il limite stabilito dalla Direttiva EU 2023/970. Se il divario di genere supera il 5% in una categoria, l'azienda deve fornire una giustificazione o adottare azioni correttive.

**Compliance (Conformità)**
Lo stato di aderenza ai requisiti della normativa. Un'azienda è "in compliance" quando rispetta tutti gli obblighi della Direttiva.

**RAG (Retrieval-Augmented Generation)**
La tecnologia che alimenta l'Assistente del tool. Permette al chatbot di rispondere alle tue domande basandosi direttamente sul testo ufficiale della Direttiva, garantendo accuratezza e affidabilità.

**Bonus Gap**
La differenza percentuale negli incentivi e nei bonus percepiti da uomini e donne. Include tutto ciò che non è stipendio base.

**Corrective Action (Azione Correttiva)**
Le misure concrete che un'azienda deve intraprendere entro 6 mesi se il divario di genere è significativo e non giustificabile.

---

## Domande Frequenti (FAQ)

### "I miei dati sono davvero al sicuro?"

**Sì, al 100%.**
- **Versione online**: i dati caricati vengono analizzati in memoria e cancellati non appena l'analisi è completata. Non vengono salvati su server.
- **Versione offline**: il tool locale non invia nessun dato a nessuno. Tutto avviene nel tuo browser, offline.

Consigliamo di usare la versione offline se hai dati particolarmente sensibili.

### "Devo registrarmi o creare un account?"

**No, zero registrazione richiesta.**
Accedi semplicemente a https://pay-transparency.marcog-ai4hr.cloud/ e inizia a usare il tool. Nessun login, nessuna password.

### "Il tool è gratuito?"

**Sì, completamente gratuito e open source.**
Il Pay Transparency Tool è un progetto pubblico. Puoi usarlo senza costi, senza limiti, e senza sottoscrizioni nascoste.

### "Posso usare questo tool per il reporting ufficiale alla Direttiva?"

**Il tool fornisce un'analisi indicativa e affidabile**, ma per il reporting ufficiale alle autorità, consigliamo di:
- Validare i risultati con un consulente del lavoro o un esperto di compliance
- Conservare la documentazione dell'analisi e delle azioni intraprese
- Assicurarti che il tuo file di dati sia completo e accurato

Il tool è perfetto per analisi interne e pianificazione, ma il reporting ufficiale dovrebbe essere gestito con supervisione legale/professionale.

### "Che succede se il divario supera il 5%?"

Secondo la Direttiva:
1. Devi **informare i rappresentanti dei lavoratori**
2. Devi **analizzare le cause** insieme a loro entro 3 mesi
3. Se il divario non è giustificabile, devi **adottare azioni correttive entro 6 mesi** (ajustamenti salariali, revisione processi, ecc.)
4. Devi **documentare tutto** e ripetere l'analisi periodicamente

Vedi la sezione "Cosa fare se il divario supera il 5%" per i dettagli.

### "Posso usare il tool per dipendenti part-time?"

**Sì, ma normalizza i dati.**
Il tool analizza i dati come li carichi. Se hai part-time, assicurati di **annualizzare gli stipendi** (convertire part-time a equivalente full-time annuale) prima di caricare il file, altrimenti il confronto non sarà equo.

### "Quale versione dovrei usare: online o offline?"

**Usare la versione online se**:
- Preferisci semplicità e non vuoi scaricare nulla
- Non hai problemi a caricare dati su server (certificati GDPR)
- Vuoi visualizzare il report con grafica e statistiche avanzate

**Usare la versione offline se**:
- Hai politiche dati rigorose e preferisci zero trasmissione
- Lavori in un ambiente senza internet stabile
- Vuoi massima privacy e controllo locale
- Devi analizzare dati particolarmente sensibili

Entrambe le versioni producono risultati identici.

### "Come faccio a contattarvi se ho problemi?"

Il tool è open source. Puoi:
- Aprire una segnalazione (issue) sul repository GitHub
- Consultare la documentazione completa nel progetto
- Contattare il team di supporto tramite i canali indicati nel repository

### "Quali versioni di Excel/CSV supportate?"

**CSV**: qualsiasi formato CSV standard (separato da virgola o punto e virgola, il tool dovrebbe riconoscere automaticamente).
**Excel**: file .xlsx (Excel 2007+). Se hai file .xls più vecchi, converti prima a .xlsx.

### "Il tool supporta altre lingue?"

Attualmente:
- **Assistente**: italiano e inglese (basato su Direttiva IT + EN)
- **Interfaccia**: italiano
- **Report**: italiano

L'Assistente capisce domande in italiano e risponde in italiano. Le domande in inglese vengono tradotte internamente.

### "Posso fare un'analisi per anno multiple (2023, 2024, 2025) per vedere il trend?"

**Sì, carica un file separato per ogni anno.**
Esegui l'analisi 3 volte (una per ogni annualità) e confronta i risultati. Noterai se il divario sta migliorando o peggiorando nel tempo.

---

## Supporto e Risorse Aggiuntive

### Documentazione Tecnica
- **[formato-dati.md](formato-dati.md)**: Guida dettagliata al formato dei dati e validazione
- **[guida-tecnica.md](guida-tecnica.md)**: Per sviluppatori che vogliono comprendere l'architettura del tool

### Risorse Esterne
- **[Direttiva EU 2023/970 (Testo Ufficiale)](https://eur-lex.europa.eu/eli/dir/2023/970/oj)**: Il documento normativo completo in EN
- **[EIGE (European Institute for Gender Equality)](https://eige.europa.eu/)**: Risorse e linee guida su pay transparency
- **[Commissione Europea - Gender Pay Gap](https://ec.europa.eu/eurostat/)**: Dati statistici e comparazioni tra paesi

### Contatti
Per segnalazioni, suggerimenti, o problemi:
- **Repository GitHub**: [pay-transparency-tool](https://github.com/marcoguad-HR/pay-transparency-tool/tree/main)
- **Email**: [contatto di supporto, se disponibile]

---

## Note Finali

Grazie per aver scelto il Pay Transparency Tool. Questo strumento è stato sviluppato per **demistificare la conformità alla Direttiva EU 2023/970** e rendere l'analisi del divario salariale di genere **accessibile a tutti**, indipendentemente dalle competenze tecniche.

Ricorda:
- **La trasparenza retributiva è un diritto** dei lavoratori e un obbligo delle aziende
- **La parità di genere negli stipendi è un valore** che beneficia sia l'azienda che i dipendenti
- **Questo tool ti aiuta, ma non sostituisce una consulenza legale** per il reporting ufficiale

Se il divario emerge, non scoraggiarti. La Direttiva dà alle aziende il tempo e lo spazio per **pianificare e implementare azioni correttive costruttive**. Il dialogo con i rappresentanti dei lavoratori è la chiave.

Buona analisi! 🚀

---

**Versione**: 1.0
**Data**: Marzo 2026
**Licenza**: Open Source (vedi LICENSE nel repository)
