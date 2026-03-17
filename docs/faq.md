# Pay Transparency Tool - FAQ

Benvenuto nelle domande frequenti del **Pay Transparency Tool**. Questo documento è organizzato per tre diverse audience: professionisti HR, implementatori tecnici e utenti generali.

**Strumento:** https://pay-transparency.marcog-ai4hr.cloud/
**Repository:** https://github.com/marcoguad-HR/pay-transparency-tool/tree/main

---

## FAQ Generali

### **1. Cos'è il Pay Transparency Tool?**

Il Pay Transparency Tool è uno strumento gratuito e open source progettato per supportare la compliance alla Direttiva UE 2023/970 sulla trasparenza retributiva. Offre due funzionalità principali:
- Un **chatbot AI** che risponde alle domande sulla normativa e sull'implementazione
- Un'**analisi del gender pay gap** che elabora i dati retributivi aziendali per identificare potenziali disparità

Lo strumento è completamente gratuito e non richiede registrazione.

### **2. È gratuito?**

Sì, completamente. Il Pay Transparency Tool è rilasciato con licenza MIT ed è un progetto open source. Non ci sono costi di abbonamento, di utilizzo o nascosti.

### **3. Chi l'ha creato?**

Il Pay Transparency Tool è stato sviluppato da **Marco Guadagno**. È un progetto open source e le contribuzioni della community sono sempre benvenute.

### **4. Devo registrarmi?**

No, non è richiesta alcuna registrazione. Puoi accedere direttamente allo strumento online e iniziare a usarlo immediatamente, oppure scaricare la versione locale.

### **5. In che lingua funziona?**

L'interfaccia e le risposte del chatbot sono interamente in **italiano**. Il chatbot comprende e può rispondere a domande sulla Direttiva sia in italiano che in inglese, rendendolo flessibile per contesti multilinguali.

### **6. È sicuro per i dati aziendali?**

Sì, la sicurezza è una priorità:
- **Versione online:** I file che carichi vengono analizzati in memoria del server e cancellati immediatamente dopo l'elaborazione. Nessun dato viene salvato persistentemente.
- **Tool locale:** Per la massima privacy, utilizza la versione locale (file HTML standalone) che non invia alcun dato a server esterni. Tutta l'elaborazione avviene nel tuo browser.

---

## FAQ per HR e Compliance

### **7. Quali aziende devono adeguarsi alla Direttiva?**

La Direttiva UE 2023/970 prevede un calendario di implementazione graduale:
- **Dal 7 giugno 2027:** Aziende con **250 o più dipendenti**
- **Dal 7 giugno 2031:** Aziende con **100-249 dipendenti**

Le aziende con meno di 100 dipendenti non sono soggette agli obblighi della Direttiva (salvo disposizioni nazionali più stringenti).

### **8. Che formato deve avere il file?**

Il Pay Transparency Tool accetta file in formato **CSV** o **Excel** (.xlsx/.xls).

**Colonne minime richieste:**
- `gender` (M/F oppure 1/0)
- `base_salary` (stipendio base)

**Colonne consigliate per un'analisi più completa:**
- `department` (reparto/funzione)
- `level` (livello/grado)

Per una documentazione dettagliata sui formati, consulta `docs/formato-dati.md` nel repository.

### **9. Cosa significa "gap superiore al 5%"?**

La Direttiva EU stabilisce una **soglia critica del 5%** per il gender pay gap. Ecco cosa significa:

Se il gap retributivo tra uomini e donne in una specifica categoria supera il 5% e **non è giustificabile con criteri oggettivi e neutrali dal punto di vista del genere**, l'azienda deve:
1. Condurre una **valutazione retributiva congiunta** (insieme ai rappresentanti dei lavoratori)
2. Identificare le cause della disparità
3. Adottare **misure correttive** entro 6 mesi
4. Monitorare continuamente il gap

Il 5% non è un limite assoluto, ma un indicatore che segnala la necessità di approfondimento.

### **10. Posso usare questo tool per il reporting ufficiale?**

Il Pay Transparency Tool fornisce un'**analisi indicativa e di pre-screening** utile per identificare potenziali problemi di disparità retributiva. Tuttavia, per il **reporting formale alla compliance** con la Direttiva, consigliamo di:
- Consultare il tuo **consulente del lavoro** o **legale** per validare i risultati
- Documentare la metodologia di calcolo utilizzata
- Integrare l'analisi del tool con le tue procedure interne di compliance

Il tool è uno strumento di supporto, non una soluzione completa di reporting legale.

### **11. I dati dei miei dipendenti sono al sicuro?**

Sì, la protezione dei dati è garantita:

**Versione online:**
- I file caricati vengono **analizzati solo in memoria** del server
- I dati vengono **cancellati immediatamente** dopo l'elaborazione
- Nessun dato viene salvato in database o log permanenti
- Nessun dato viene condiviso con terze parti

**Versione locale:**
- I dati **non lasciano MAI il tuo browser**
- Tutta l'elaborazione avviene localmente sul tuo dispositivo
- Non c'è connessione a server esterni (eccetto per il chatbot, opzionale)

### **12. Cosa devo fare se il gap supera il 5%?**

La Direttiva UE (Art. 10) richiede un piano d'azione strutturato:

1. **Valutazione retributiva congiunta:** Condotta insieme ai rappresentanti dei lavoratori per analizzare i sistemi retributivi
2. **Identificazione delle cause:** Analizza se le disparità derivano da:
   - Diversità nei ruoli o livelli
   - Differenze di esperienza o qualifiche
   - Scelte personali di orario/posizione
   - Discriminazione strutturale
3. **Misure correttive:** Sviluppa e implementa azioni per ridurre il gap entro **6 mesi**
4. **Monitoraggio continuo:** Traccia i progressi nel tempo e aggiorna le misure se necessario

Il Pay Transparency Tool può aiutarti a identificare dove il problema è più critico.

### **13. Come interpreto la differenza tra gap medio e mediano?**

Sono due metriche complementari che raccontano storie diverse:

**Gap medio:**
- Calcolato sommando tutti gli stipendi e dividendo per il numero di persone
- È influenzato da **valori estremi** (dipendenti molto ben pagati o molto poco pagati)
- Può non essere rappresentativo se ci sono outlier significativi

**Gap mediano:**
- È lo stipendio del dipendente "nel mezzo" quando ordini tutti per stipendio
- È più **stabile e robusto** agli outlier
- Rappresenta meglio la disparità "tipica"

**Cosa dice la Direttiva:**
La Direttiva richiede di calcolare **entrambi**. Se i due gap differiscono significativamente (es. medio 15%, mediano 3%), potresti avere outlier nei dati o una distribuzione retributiva molto asimmetrica che merita approfondimento.

### **14. Cosa sono i quartili?**

I quartili dividono la popolazione in quattro gruppi uguali per livello di stipendio:

Immagina di ordinare tutti i tuoi dipendenti dal meno al più pagato:
- **Q1 (primo quartile):** I dipendenti con stipendi più bassi (0-25%)
- **Q2 (secondo quartile):** Stipendi medio-bassi (25-50%)
- **Q3 (terzo quartile):** Stipendi medio-alti (50-75%)
- **Q4 (quarto quartile):** I dipendenti con stipendi più alti (75-100%)

**Perché sono importanti:**
Se noti che le donne sono concentrate in Q1 e Q2 mentre gli uomini in Q3 e Q4, **c'è un problema di distribuzione** anche se il gap medio sembra moderato. I quartili ti mostrano la stratificazione del genere nella struttura retributiva.

### **15. Come gestisco i part-time?**

Quando inserisci i dati nel tool, il Pay Transparency Tool confronta gli stipendi così come li fornisci. Se hai **dipendenti part-time**, consigliamo di:

1. **Convertire gli stipendi in equivalente full-time** prima del caricamento
   - Esempio: uno stipendio part-time (50%) di €1.000/mese → inserisci €2.000 per un confronto equo
2. **Incluere il campo "hours_per_week"** se disponibile, per permettere al tool di normalizzare automaticamente

Questo garantisce un confronto equo e conforme ai principi della Direttiva, che non discrimina sulla base dell'orario di lavoro.

---

## FAQ Tecniche

### **16. Quale modello AI usa il chatbot?**

Il chatbot utilizza **Llama 3.3-70b-versatile** fornito tramite **Groq API**.

**Nota importante:** Non è GPT di OpenAI. Llama è un modello di linguaggio open source sviluppato da Meta, noto per la qualità e la velocità di inferenza. L'utilizzo di un modello open source consente di mantenere lo strumento completamente gratuito senza costi API.

### **17. Come funziona il sistema RAG?**

Il chatbot utilizza un'architettura **RAG (Retrieval-Augmented Generation)** per fornire risposte accurate e contestualizzate:

1. **Indicizzazione:** I documenti della Direttiva UE (PDF) vengono divisi in chunk di testo semanticamente coerenti
2. **Embedding:** Ogni chunk viene convertito in vettori numerici (embeddings) che catturano il significato
3. **Archiviazione vettoriale:** I vettori vengono salvati in un database vettoriale **Qdrant** per recupero veloce
4. **Retrieval:** Quando poni una domanda, il sistema:
   - Converte la tua domanda in embedding
   - Cerca i chunk più semanticamente simili nel database
   - Recupera i chunk più rilevanti
5. **Generation:** Gli chunk recuperati vengono passati al modello Llama come contesto, che genera una risposta accurata e supportata dalla normativa

Questo approccio garantisce che le risposte siano sempre supportate dai documenti ufficiali della Direttiva.

### **18. Posso installarlo in locale?**

Sì, assolutamente. Il progetto è completamente open source:

**Passaggi:**
1. Clone il repository: `git clone https://github.com/marcoguad-HR/pay-transparency-tool.git`
2. Configura la tua **Groq API key** (gratuita su https://console.groq.com)
3. Installa le dipendenze: `pip install -r requirements.txt`
4. Avvia l'applicazione secondo le istruzioni in `docs/guida-tecnica.md`

L'installazione locale ti dà pieno controllo e la massima privacy, poiché i dati non escono mai dal tuo ambiente.

### **19. Posso contribuire al progetto?**

Assolutamente sì! Le contribuzioni sono benvenute. Per partecipare al progetto:

1. Leggi il file **CONTRIBUTING.md** nel repository per le linee guida
2. Fai un fork del progetto
3. Crea un branch per la tua feature (`git checkout -b feature/miglioramento`)
4. Commit le tue modifiche
5. Invia una pull request

Che si tratti di bug fix, nuove feature, traduzioni o documentazione, ogni contributo è apprezzato.

### **20. Perché Groq e non OpenAI?**

La scelta di **Groq** è motivata da diverse considerazioni:

- **Velocità:** Groq offre inferenza estremamente veloce con latenza molto bassa (risposte in 1-3 secondi)
- **Modelli open source:** Supporta Llama e altri modelli open source, mantenendo il progetto indipendente
- **Costo:** Groq offre un tier gratuito generoso, rendendo lo strumento completamente gratuito per l'utente
- **Filosofia:** Allineato con l'etica open source del progetto
- **Trasparenza:** I modelli non sono proprietari, aumentando la fiducia

OpenAI è un'alternativa valida, ma avrebbe comportato costi per l'utente o per il maintainer, contraddetto la natura open source del progetto.

### **21. Il Tool Locale funziona offline?**

Sì, con una precisazione:

**Capacità offline complete:**
- La versione **Tool Locale** (file HTML standalone) funziona completamente offline
- Puoi scaricarlo una volta e non serve più connessione internet per usarlo
- Tutta la logica di calcolo è scritta in **JavaScript** ed eseguita direttamente nel tuo browser
- Nessuna dipendenza da server esterni

**Eccezione:**
Se utilizzi il chatbot sulla normatività, questi richiede una connessione internet (ma i dati rimangono comunque nel tuo browser, non sono inviati a servizi terzi).

### **22. Posso usare un modello diverso?**

Sì, il tool è progettato per essere flessibile. Puoi:

1. Modifica il file **config.yaml** (o la configurazione equivalente nel tuo setup)
2. Cambia il provider API (purché compatibile con l'API OpenAI o simile)
3. Supporto per provider alternativi:
   - **Groq** (default)
   - **OpenAI**
   - **Together.ai**
   - **Ollama** (esecuzione locale)
   - Qualsiasi provider con API compatibile

**Esempio di configurazione:**
```yaml
llm:
  provider: "openai"  # oppure "groq", "together", "ollama"
  model: "gpt-4"
  api_key: "your-api-key"
```

Questa flessibilità consente di adattare lo strumento alle tue preferenze e infrastruttura.

---

**Hai ancora domande?** Apri un issue su GitHub (https://github.com/marcoguad-HR/pay-transparency-tool/issues) o contatta direttamente il maintainer.
