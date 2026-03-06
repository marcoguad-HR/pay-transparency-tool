# Formato dei Dati – Come Preparare il Tuo File per l'Analisi

Benvenuto! Questa guida ti aiuta a preparare il file con i dati dei tuoi dipendenti per l'analisi della parità di genere negli stipendi. Non è complicato: basta seguire pochi semplici accorgimenti e il tool farà il resto.

---

## Colonne Obbligatorie

Ogni file deve contenere **almeno queste due colonne**. Senza di loro, l'analisi non può iniziare.

| Colonna | Tipo | Descrizione | Esempio |
|---------|------|-------------|---------|
| **gender** | Testo | Genere del dipendente: `M` per uomo, `F` per donna. Non importa se scrivi maiuscolo o minuscolo (m, f, M, F) — il sistema li normalizzerà automaticamente. | F |
| **base_salary** | Numero | Stipendio lordo annuale in euro. **Solo il numero**, senza il simbolo €, senza separatori di migliaia (no punti, no virgole come separatori). | 45800 |

---

## Colonne Consigliate (Facoltative, ma Utili!)

Queste colonne **non sono obbligatorie**, ma ti permettono di ottenere analisi molto più dettagliate e accurate. In particolare:

- **department** + **level** insieme creano categorie di lavoro comparabili (come richiede la direttiva UE sulla parità retributiva)
- Senza categorie, l'analisi resta generica su tutta l'azienda
- Con categorie, il tool confronta "a parità di mansione" — che è la vera parita di genere

| Colonna | Tipo | Descrizione | Esempio |
|---------|------|-------------|---------|
| **employee_id** | Testo | Codice univoco del dipendente. Utile se vuoi tracciare i risultati. | EMP001, D542, etc. |
| **department** | Testo | Reparto/funzione aziendale. Crea categorie insieme a "level". | Marketing, Ingegneria, Vendite, RU, etc. |
| **level** | Testo | Livello di seniority/responsabilità. Crea categorie insieme a "department". | Junior, Mid, Senior, Director, Lead |
| **bonus** | Numero | Bonus/incentivi annui lordi in euro, solo il numero. | 5700 |
| **total_compensation** | Numero | Compenso totale annuo (stipendio + bonus + benefit). | 52500 |
| **years_experience** | Numero | Anni di esperienza del dipendente. | 3, 7, 15 |
| **age** | Numero | Età del dipendente. | 28, 45, 62 |
| **contract_type** | Testo | Tipo di contratto. | full-time, part-time, temporary |

---

## Esempio di File (10 Dipendenti Realistici)

Copia questo esempio nel tuo editor di testo o foglio di calcolo come punto di partenza. È il formato esatto che il tool si aspetta:

```csv
employee_id,department,level,gender,base_salary,bonus,years_experience,age,contract_type
EMP001,Marketing,Junior,F,34500,5700,2,28,full-time
EMP002,Engineering,Senior,F,62700,4900,8,42,full-time
EMP003,Marketing,Junior,M,32300,5900,2,29,full-time
EMP004,Sales,Mid,M,45800,6700,5,38,full-time
EMP005,Sales,Junior,M,30800,6200,1,25,full-time
EMP006,Engineering,Senior,M,64200,5100,10,48,full-time
EMP007,HR,Mid,F,41600,3800,4,35,full-time
EMP008,Marketing,Mid,F,43900,6100,4,36,full-time
EMP009,Sales,Mid,F,44500,6500,5,39,full-time
EMP010,Engineering,Junior,M,36100,4700,2,27,full-time
```

---

## Regole Importanti

### Numeri e Simboli
- **Niente € nei numeri**: scrivi `45800`, non `€45800` o `45.800 €`
- **Niente separatori di migliaia**: scrivi `62700`, non `62.700` o `62,700`
- Usa il punto `.` come separatore decimale se necessario: `45800.50`

### Genere
- Accetta solo `M` o `F` (maiuscolo o minuscolo)
- Lettere diverse causano errore — il sistema ti avviserà

### Caratteri Speciali nei Nomi
- `department` e `level` possono contenere lettere, numeri, spazi e accenti: va bene!
- Niente simboli strani come `@`, `#`, `$`

---

## Come Esportare da Excel

Se hai i dati in Excel, segui questi semplici passi:

1. **Apri il tuo file** in Excel con la tabella dei dipendenti
2. **Seleziona tutta la tabella** (inclusa l'intestazione con i nomi delle colonne)
3. **File** → **Salva con nome**
4. **Scegli il formato**:
   - Per massima compatibilità: **CSV UTF-8 (*.csv)**
   - Oppure mantieni **Excel (*.xlsx)** — il tool lo legge direttamente
5. **Salva** con un nome chiaro, tipo `dipendenti_2026.csv`
6. **Carica il file** nello strumento

### Nota per Utenti Excel Italiana
Se Excel ti chiede se vuoi mantenere il formato Excel: **scegli CSV**. Usa **virgola come separatore** (il tool lo riconosce automaticamente, anche se il tuo Excel locale usa il punto e virgola).

---

## Formato del File

| Aspetto | Dettaglio |
|---------|-----------|
| **Estensioni accettate** | `.csv`, `.xlsx`, `.xls` |
| **Codifica consigliata** | UTF-8 (standard moderno) oppure UTF-8 BOM (quello di Excel) |
| **Separatore CSV** | Virgola `,` (consigliato). Il tool accetta anche `;` (Excel italiano) |
| **Riga intestazione** | Obbligatoria — la prima riga deve contenere i nomi delle colonne |
| **Dimensione massima file** | 10 MB |

---

## Errori Comuni e Come Risolverli

Quando carichi il file, il tool controlla che tutto sia giusto. Ecco i problemi più frequenti e le soluzioni:

| Problema | Causa Probabile | Soluzione |
|----------|-----------------|-----------|
| **"La colonna 'gender' è obbligatoria"** | Colonna `gender` mancante o scritto diversamente | Aggiungi una colonna intitolata esattamente `gender` |
| **"La colonna 'base_salary' è obbligatoria"** | Colonna `base_salary` mancante o scritto diversamente | Aggiungi una colonna intitolata esattamente `base_salary` |
| **Errore su valori di gender** | Hai scritto lettere diverse da M o F (es. Maschio, Woman, etc.) | Usa solo `M` o `F` per ogni riga |
| **"Valori non numerici nella colonna 'base_salary'"** | Hai scritto testo, simboli o spazi invece di numeri | Usa solo numeri: `45800`, non `€45.800` o `45800 euro` |
| **Errore su stipendi negativi o zero** | Base salary ≤ 0 | Controlla che tutti gli stipendi siano positivi |
| **File vuoto o illeggibile** | Il file non contiene dati o è corrotto | Verifica che il file sia in formato CSV/Excel valido |
| **Solo un genere presente** | Tutti i dipendenti hanno lo stesso genere | L'analisi di parità richiede almeno due generi nei dati |

---

## Avvisi su Qualità dei Dati

Il tool accetta il file anche se si verificano le situazioni sotto — **non ti blocca** — ma ti avvisa che i risultati potrebbero essere meno affidabili:

| Situazione | Cosa Significa | Cosa Fare |
|-----------|----------------|-----------|
| **Meno di 50 dipendenti** | Dataset piccolo | I risultati sono indicativi, non statisticamente robusti. Bene comunque per una prima analisi. |
| **Squilibrio di genere > 80%** | Uno dei due generi rappresenta oltre l'80% | L'analisi è possibile, ma meno significativa per bilancio. Utile comunque per consapevolezza. |
| **Stipendio mediano < €10k o > €500k** | Dati potenzialmente anomali | Verifica: gli stipendi sono annui lordi? Contengono valute diverse? |

---

## File di Esempio

Vuoi vedere un vero file di esempio già caricato nel tool? Trova `demo_employees.csv` qui nel repository:

📁 **[data/demo/demo_employees.csv](../data/demo/demo_employees.csv)**

Scaricalo e usalo come template per il tuo file!

---

## Domande Frequenti

**D: Posso aggiungere altre colonne oltre a quelle elencate?**
R: Sì! Il tool ignora le colonne che non conosce. Aggiungile pure se ti servono per i tuoi registri interni.

**D: Devo includere tutte le colonne consigliate?**
R: No. `department` e `level` sono i più utili per analisi accurate. Le altre sono opzionali.

**D: Quali dipendenti devo includere?**
R: Includi tutti quelli dell'azienda (o della sede) che vuoi analizzare. Posizioni esecutive, dirigenza, tutti.

**D: Posso caricare dati storici (anni precedenti)?**
R: Sì, il tool analizza un file alla volta. Se vuoi confrontare nel tempo, carica file diversi in sessioni separate.

**D: I dati sono anonimi nel tool?**
R: Sì, il tool non memorizza i tuoi file. Viene elaborato solo per l'analisi e poi cancellato.

---

## Prossimo Passo

Una volta preparato il file, torna alla **[Guida Utente](guida-utente.md)** per scoprire come caricarlo e interpretare i risultati dell'analisi.

Buona analisi! 📊
