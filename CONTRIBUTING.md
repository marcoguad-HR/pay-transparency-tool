# Come Contribuire

## Benvenuto

Grazie per l'interesse nel contribuire al Pay Transparency Tool! Siamo felici di accogliere contributi di ogni tipo: segnalazioni di bug, suggerimenti per nuove funzionalità, miglioramenti della documentazione e naturalmente contributi di codice. Insieme possiamo costruire uno strumento ancora più utile e affidabile.

## Segnalare un Bug

Se hai individuato un bug, segui questi passaggi:

1. **Controlla che il bug non sia già segnalato** - Consulta la sezione [Issues](https://github.com/marcoguadagno/pay-transparency-tool/issues) per verificare che non ci sia già una segnalazione simile.

2. **Apri una nuova Issue** con le seguenti informazioni:
   - **Descrizione chiara del problema** - Spiega cos'è andato male nel modo più dettagliato possibile
   - **Passi per riprodurlo** - Fornisci una sequenza esatta di azioni per riprodurre il bug
   - **Comportamento atteso vs comportamento ottenuto** - Descrivi cosa dovrebbe accadere e cosa accade invece
   - **Ambiente** - Specifica il sistema operativo, la versione di Python, il browser utilizzato e altre informazioni rilevanti

Questo ci aiuta a capire e risolvere il problema più velocemente.

## Proporre una Feature

Se hai un'idea per una nuova funzionalità:

1. **Apri una Issue con tag "enhancement"** - Usa il tag corretto per facilitare la categorizzazione
2. **Descrivi il problema che la feature risolve** - Spiega il caso d'uso e perché è importante
3. **Proponi la soluzione** - Illustra come immagini di implementare la feature
4. **Attendi il feedback** - Discussione preliminare prima dell'implementazione aiuta a evitare lavoro non necessario

## Contribuire con Codice

### Setup dell'ambiente di sviluppo

```bash
git clone https://github.com/marcoguadagno/pay-transparency-tool.git
cd pay-transparency-tool
bash setup.sh
cp config.yaml.example config.yaml  # aggiungi la tua GROQ_API_KEY
```

Per dettagli tecnici completi, consulta [docs/guida-tecnica.md](docs/guida-tecnica.md).

### Workflow

1. **Crea un branch dal main:**
   ```bash
   git checkout -b feature/nome-feature
   ```

2. **Fai le modifiche** al codice

3. **Assicurati che i test passino:**
   ```bash
   make test
   ```

4. **Verifica gli import:**
   ```bash
   make verify
   ```

5. **Commit con messaggi descrittivi** (vedi la sezione Convenzioni)

6. **Push e apri una Pull Request** su GitHub

### Convenzioni

#### Branch naming
- `feature/descrizione` - per nuove funzionalità
- `fix/descrizione` - per correzioni di bug
- `docs/descrizione` - per miglioramenti della documentazione

#### Commit messages
- Scritti in italiano o inglese (l'importante è la coerenza)
- Devono essere descrittivi e chiari
- Esempi:
  - `feat: aggiunto export PDF dei risultati`
  - `fix: corretto calcolo mediana con dataset piccoli`
  - `docs: migliorata documentazione della sezione RAG`

#### Stile del codice
- Segui **PEP 8** per il codice Python
- Scrivi **docstring in italiano** per coerenza con il resto del progetto
- Usa nomi di variabili e funzioni auto-esplicativi

#### Test
- Ogni nuova feature deve avere almeno un test unitario
- I test devono essere nella cartella `tests/`
- Verifica che tutti i test passino prima di aprire una Pull Request

### Struttura del progetto

Una breve guida ai principali directory:

- **src/rag/** — Pipeline RAG (Retrieval-Augmented Generation)
- **src/analysis/** — Moduli di analisi del pay gap
- **src/web/** — Endpoint API e logica web
- **src/cli/** — Interfaccia a linea di comando
- **tests/** — Test unitari e di integrazione
- **docs/** — Documentazione del progetto

## Migliorare la Documentazione

La documentazione è uno dei nostri asset più importanti e i contributi sono sempre benvenuti:

- La documentazione si trova nella cartella **docs/**
- Correggi errori di ortografia o grammatica
- Migliora la chiarezza delle spiegazioni
- Aggiungi esempi pratici quando appropriato
- Ricorda che la guida utente ([docs/guida-utente.md](docs/guida-utente.md)) deve rimanere comprensibile anche a persone non tecniche

## Code of Conduct

Questo progetto segue il [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/). Ci aspettiamo un ambiente rispettoso e inclusivo.

**Comportamenti non accettabili:**
- Linguaggio offensivo, discriminatorio o molesto
- Attacchi personali o professionali
- Qualsiasi forma di discriminazione
- Contenuti espliciti o violenti

Se osservi comportamenti inaccettabili, contatta Marco Guadagno in privato per segnalarlo.

## Domande?

- Apri una Issue con tag **"question"** se hai dubbi sullo sviluppo
- Contatta direttamente [Marco Guadagno](https://github.com/marcoguadagno) per domande generali
- Consulta la documentazione in **docs/** prima di chiedere

## Licenza

Contribuendo a questo progetto, accetti che il tuo contributo venga rilasciato sotto licenza **MIT**, la stessa licenza del progetto. Per maggiori dettagli, consulta il file [LICENSE](LICENSE).

---

Grazie ancora per il tuo interesse nel migliorare il Pay Transparency Tool. Non vediamo l'ora di collaborare con te!
