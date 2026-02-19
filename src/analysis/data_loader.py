"""
Data Loader — Fase 2.2 del progetto Pay Transparency Tool.

Questo modulo si occupa di CARICARE e VALIDARE i dati retributivi da file CSV/Excel.

Perché serve un loader separato?
In un progetto reale, i dati arrivano in formati diversi, con errori, valori mancanti,
nomi di colonne diversi. Il DataLoader fa da "guardia": controlla che i dati siano
corretti PRIMA di passarli al calcolatore. Se qualcosa non va, dà un errore chiaro.

La Direttiva EU 2023/970 richiede almeno queste informazioni:
- Genere del dipendente (M/F)
- Stipendio base
- Categoria lavorativa (per confrontare "a parità di ruolo")

Concetti Python usati qui:
- Exception personalizzate: creare i propri tipi di errore per messaggi chiari
- dataclass: modo compatto di definire classi che contengono solo dati
- pandas: libreria per manipolazione tabelle dati
- Type hints: annotazioni che indicano il tipo atteso (str, int, pd.DataFrame)
"""

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("analysis.data_loader")


# =============================================================================
# ECCEZIONI PERSONALIZZATE
# =============================================================================
# Creare eccezioni specifiche permette di catturare errori diversi
# in modo diverso. Es: "file non trovato" vs "colonna mancante".

class DataLoadError(Exception):
    """Errore generico durante il caricamento dati."""
    pass


class DataValidationError(Exception):
    """Errore di validazione: i dati esistono ma non sono corretti."""
    pass


# =============================================================================
# DATACLASS PER IL RISULTATO
# =============================================================================

@dataclass
class LoadResult:
    """
    Risultato del caricamento dati.

    Contiene il DataFrame validato + informazioni utili (metadata).
    Usare una dataclass invece di un dict rende il codice più leggibile:
      result.n_employees    invece di    result["n_employees"]
    """
    df: pd.DataFrame              # Il DataFrame con i dati validati
    n_employees: int              # Numero totale di dipendenti
    n_male: int                   # Numero di uomini
    n_female: int                 # Numero di donne
    departments: list[str]        # Lista dei dipartimenti trovati
    levels: list[str]             # Lista dei livelli trovati
    source_file: str              # Percorso del file sorgente
    warnings: list[str] = field(default_factory=list)  # Eventuali avvisi


# =============================================================================
# CLASSE PRINCIPALE
# =============================================================================

# Colonne obbligatorie: senza queste il calcolo del pay gap è impossibile
REQUIRED_COLUMNS = ["gender", "base_salary"]

# Colonne opzionali ma utili per analisi più approfondite
OPTIONAL_COLUMNS = [
    "employee_id", "department", "level", "bonus",
    "total_compensation", "years_experience", "age", "contract_type",
]

# Valori accettati per il genere
VALID_GENDERS = {"M", "F"}


class PayDataLoader:
    """
    Carica e valida file CSV/Excel con dati retributivi.

    Il loader verifica:
    1. Che il file esista e sia leggibile
    2. Che le colonne obbligatorie siano presenti
    3. Che i valori siano validi (genere M/F, stipendi > 0, ecc.)
    4. Che ci siano sia uomini che donne nel dataset

    Uso:
        loader = PayDataLoader()
        result = loader.load("data/demo/demo_employees.csv")
        print(f"Caricati {result.n_employees} dipendenti")
        df = result.df  # Il DataFrame pronto per l'analisi
    """

    def load(self, file_path: str) -> LoadResult:
        """
        Carica un file CSV o Excel e lo valida.

        Args:
            file_path: percorso del file (.csv o .xlsx)

        Returns:
            LoadResult con il DataFrame validato e i metadata

        Raises:
            DataLoadError: se il file non esiste o non è leggibile
            DataValidationError: se i dati non passano le validazioni
        """
        path = Path(file_path)
        logger.info(f"Caricamento dati da: {path}")

        # --- Step 1: Leggi il file ---
        df = self._read_file(path)

        # --- Step 2: Normalizza i nomi delle colonne ---
        df = self._normalize_columns(df)

        # --- Step 3: Validazioni ---
        warnings = []
        self._validate_required_columns(df)
        self._validate_gender(df)
        self._validate_salary(df)
        warnings.extend(self._check_optional_columns(df))
        warnings.extend(self._check_data_quality(df))

        # --- Step 4: Prepara il risultato ---
        result = LoadResult(
            df=df,
            n_employees=len(df),
            n_male=len(df[df["gender"] == "M"]),
            n_female=len(df[df["gender"] == "F"]),
            departments=sorted(df["department"].unique().tolist()) if "department" in df.columns else [],
            levels=sorted(df["level"].unique().tolist()) if "level" in df.columns else [],
            source_file=str(path),
            warnings=warnings,
        )

        logger.info(f"Caricati {result.n_employees} dipendenti "
                     f"({result.n_male} M, {result.n_female} F)")

        if warnings:
            for w in warnings:
                logger.warning(w)

        return result

    def _read_file(self, path: Path) -> pd.DataFrame:
        """
        Step 1: Legge il file CSV o Excel in un DataFrame pandas.

        Supporta:
        - .csv → pd.read_csv()
        - .xlsx / .xls → pd.read_excel() (richiede openpyxl)

        Raises:
            DataLoadError: se il file non esiste o il formato non è supportato
        """
        if not path.exists():
            raise DataLoadError(f"File non trovato: {path}")

        suffix = path.suffix.lower()

        if suffix == ".csv":
            df = pd.read_csv(path)
        elif suffix in (".xlsx", ".xls"):
            df = pd.read_excel(path)
        else:
            raise DataLoadError(
                f"Formato file non supportato: '{suffix}'. "
                f"Usa .csv o .xlsx"
            )

        if df.empty:
            raise DataLoadError(f"Il file è vuoto: {path}")

        logger.info(f"  Letto file {suffix}: {len(df)} righe, {len(df.columns)} colonne")
        return df

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Step 2: Normalizza i nomi delle colonne.

        I file reali possono avere colonne come "Base Salary", "GENDER",
        "base-salary". Normalizziamo tutto in minuscolo con underscore.

        Esempio:
            "Base Salary" → "base_salary"
            "GENDER"      → "gender"
            "Employee ID" → "employee_id"
        """
        # str.lower() → minuscolo, str.strip() → rimuove spazi
        # str.replace(" ", "_") → spazi → underscore
        # str.replace("-", "_") → trattini → underscore
        df.columns = (
            df.columns
            .str.lower()
            .str.strip()
            .str.replace(" ", "_", regex=False)
            .str.replace("-", "_", regex=False)
        )
        return df

    def _validate_required_columns(self, df: pd.DataFrame) -> None:
        """
        Step 3a: Verifica che le colonne obbligatorie siano presenti.

        Senza "gender" e "base_salary" non possiamo calcolare niente.
        """
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]

        if missing:
            available = ", ".join(df.columns.tolist())
            raise DataValidationError(
                f"Colonne obbligatorie mancanti: {missing}. "
                f"Colonne trovate nel file: {available}"
            )

    def _validate_gender(self, df: pd.DataFrame) -> None:
        """
        Step 3b: Verifica che la colonna gender contenga valori validi.

        La Direttiva richiede il confronto M vs F, quindi servono entrambi.
        """
        # Normalizza: maiuscolo, rimuovi spazi
        df["gender"] = df["gender"].astype(str).str.upper().str.strip()

        # Controlla valori non validi
        unique_genders = set(df["gender"].unique())
        invalid = unique_genders - VALID_GENDERS

        if invalid:
            raise DataValidationError(
                f"Valori non validi nella colonna 'gender': {invalid}. "
                f"Valori accettati: {VALID_GENDERS}"
            )

        # Controlla che ci siano entrambi i generi
        if "M" not in unique_genders:
            raise DataValidationError("Nessun dipendente maschio (M) nel dataset")
        if "F" not in unique_genders:
            raise DataValidationError("Nessuna dipendente femmina (F) nel dataset")

    def _validate_salary(self, df: pd.DataFrame) -> None:
        """
        Step 3c: Verifica che gli stipendi siano numeri positivi.
        """
        # Converti in numerico (se qualcuno ha messo "50,000" come stringa)
        df["base_salary"] = pd.to_numeric(df["base_salary"], errors="coerce")

        # Controlla valori nulli (NaN) — "coerce" li crea se la conversione fallisce
        null_count = df["base_salary"].isna().sum()
        if null_count > 0:
            raise DataValidationError(
                f"{null_count} valori non numerici nella colonna 'base_salary'. "
                f"Tutti gli stipendi devono essere numeri."
            )

        # Controlla valori negativi o zero
        invalid_count = (df["base_salary"] <= 0).sum()
        if invalid_count > 0:
            raise DataValidationError(
                f"{invalid_count} stipendi sono <= 0. "
                f"Tutti gli stipendi devono essere positivi."
            )

    def _check_optional_columns(self, df: pd.DataFrame) -> list[str]:
        """
        Step 3d: Segnala quali colonne opzionali mancano (warning, non errore).

        Non blocchiamo il caricamento, ma avvisiamo l'utente che certe
        analisi non saranno possibili.
        """
        warnings = []
        missing_optional = [col for col in OPTIONAL_COLUMNS if col not in df.columns]

        if missing_optional:
            warnings.append(
                f"Colonne opzionali mancanti: {missing_optional}. "
                f"Alcune analisi avanzate non saranno disponibili."
            )

        return warnings

    def _check_data_quality(self, df: pd.DataFrame) -> list[str]:
        """
        Step 3e: Controlli di qualità sui dati (warning, non errori bloccanti).

        Segnala situazioni sospette ma non impossibili.
        """
        warnings = []

        # Check 1: dataset troppo piccolo per analisi statistiche significative
        if len(df) < 50:
            warnings.append(
                f"Dataset molto piccolo ({len(df)} dipendenti). "
                f"I risultati statistici potrebbero non essere affidabili."
            )

        # Check 2: forte squilibrio di genere (>80% un genere)
        n_male = len(df[df["gender"] == "M"])
        n_female = len(df[df["gender"] == "F"])
        ratio = max(n_male, n_female) / len(df)
        if ratio > 0.80:
            majority = "uomini" if n_male > n_female else "donne"
            warnings.append(
                f"Forte squilibrio di genere: {ratio:.0%} {majority}. "
                f"Questo potrebbe influenzare l'affidabilità dei calcoli."
            )

        # Check 3: stipendi sospettamente alti o bassi
        median_salary = df["base_salary"].median()
        if median_salary < 10000:
            warnings.append(
                f"Stipendio mediano molto basso (€{median_salary:,.0f}). "
                f"Verificare che i dati siano in euro annui."
            )
        if median_salary > 500000:
            warnings.append(
                f"Stipendio mediano molto alto (€{median_salary:,.0f}). "
                f"Verificare che i dati siano in euro annui."
            )

        # Check 4: bonus con valori nulli (se la colonna esiste)
        if "bonus" in df.columns:
            null_bonus = df["bonus"].isna().sum()
            if null_bonus > 0:
                warnings.append(
                    f"{null_bonus} dipendenti senza valore bonus. "
                    f"Verranno esclusi dall'analisi dei bonus."
                )

        return warnings
