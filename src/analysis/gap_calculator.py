"""
Gap Calculator — Fase 2.3 del progetto Pay Transparency Tool.

Questo modulo calcola il gender pay gap secondo le metriche richieste
dalla Direttiva EU 2023/970 sulla trasparenza retributiva.

Cosa calcola:
1. Overall Mean Gap    — Differenza % tra stipendio medio M e F
2. Overall Median Gap  — Differenza % tra stipendio mediano M e F
3. Gap per Categoria   — Gap a parità di ruolo (dipartimento + livello)
4. Pay Quartiles       — % di M e F in ogni quartile retributivo
5. Bonus Gap           — Differenza % nei bonus tra M e F
6. Compliance Check    — Flag per gap > 5% (soglia della Direttiva)

Formula del Gender Pay Gap (GPG):
    GPG = (media_M - media_F) / media_M × 100

Interpretazione:
- GPG > 0  → gli uomini guadagnano di più (es. GPG = 8% → donne pagate 8% in meno)
- GPG = 0  → parità perfetta
- GPG < 0  → le donne guadagnano di più

La soglia EU è il 5%: se il GPG supera il 5% in una categoria e non è
giustificabile con criteri oggettivi, l'azienda deve adottare misure correttive.

Concetti Python usati qui:
- pandas groupby: raggruppa i dati per colonne e calcola statistiche
- pandas agg: applica più funzioni aggregate contemporaneamente
- pd.qcut: divide i dati in quantili (quartili = 4 gruppi uguali)
- dataclass: classi leggere per contenere risultati strutturati
"""

from dataclasses import dataclass

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("analysis.gap_calculator")


# =============================================================================
# DATACLASS PER I RISULTATI
# =============================================================================
# Usiamo dataclass per ogni tipo di risultato, così il codice che usa
# il calcolatore può accedere ai dati in modo chiaro:
#   result.gap_pct    invece di    result["gap_pct"]

@dataclass
class GapResult:
    """Risultato di un singolo calcolo di gap (overall o per categoria)."""
    gap_pct: float        # Gap percentuale (positivo = uomini pagati di più)
    male_avg: float       # Media (o mediana) uomini
    female_avg: float     # Media (o mediana) donne
    male_count: int       # Numero di uomini nel gruppo
    female_count: int     # Numero di donne nel gruppo
    is_significant: bool  # True se il gap supera la soglia EU del 5%


@dataclass
class CategoryGap:
    """Gap per una specifica categoria (dipartimento + livello)."""
    department: str
    level: str
    gap_pct: float
    male_avg: float
    female_avg: float
    male_count: int
    female_count: int
    is_significant: bool  # True se gap > 5%


@dataclass
class QuartileData:
    """Distribuzione di genere in un quartile retributivo."""
    quartile: int       # 1 (più basso) → 4 (più alto)
    min_salary: float   # Stipendio minimo nel quartile
    max_salary: float   # Stipendio massimo nel quartile
    total: int          # Totale dipendenti nel quartile
    male_count: int
    female_count: int
    male_pct: float     # % uomini nel quartile
    female_pct: float   # % donne nel quartile


@dataclass
class ComplianceResult:
    """Risultato complessivo della verifica di compliance."""
    is_compliant: bool                        # True se nessun gap > 5%
    overall_mean_gap: GapResult               # Gap medio complessivo
    overall_median_gap: GapResult             # Gap mediano complessivo
    category_gaps: list[CategoryGap]          # Gap per ogni categoria
    non_compliant_categories: list[CategoryGap]  # Categorie con gap > 5%
    quartiles: list[QuartileData]             # Distribuzione quartili
    bonus_gap: GapResult | None               # Gap bonus (None se dati mancanti)


# =============================================================================
# CLASSE PRINCIPALE
# =============================================================================

# Soglia della Direttiva EU: gap > 5% richiede giustificazione o azione
EU_THRESHOLD = 5.0


class GapCalculator:
    """
    Calcola il gender pay gap da un DataFrame di dati retributivi.

    Uso:
        calculator = GapCalculator(df)
        result = calculator.full_analysis()
        print(f"Gap complessivo: {result.overall_mean_gap.gap_pct:.1f}%")
        print(f"Compliant: {result.is_compliant}")
    """

    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: DataFrame con almeno le colonne "gender" e "base_salary".
                Colonne opzionali: "department", "level", "bonus".
        """
        self.df = df.copy()  # Copia per non modificare l'originale

    # =========================================================================
    # METODI PUBBLICI — Le 5 metriche principali
    # =========================================================================

    def overall_mean_gap(self) -> GapResult:
        """
        Calcola il gender pay gap complessivo usando la MEDIA.

        La media è la somma di tutti gli stipendi diviso il numero di dipendenti.
        È la metrica più usata e richiesta dalla Direttiva EU.

        Formula: GPG = (media_M - media_F) / media_M × 100

        Esempio con numeri semplici:
            Uomini: [40000, 60000] → media = 50000
            Donne:  [35000, 55000] → media = 45000
            GPG = (50000 - 45000) / 50000 × 100 = 10%
        """
        logger.info("Calcolo overall mean gap...")
        return self._calculate_gap(self.df, use_median=False)

    def overall_median_gap(self) -> GapResult:
        """
        Calcola il gender pay gap complessivo usando la MEDIANA.

        La mediana è il valore "centrale" quando ordini tutti gli stipendi.
        È meno sensibile ai valori estremi (outlier) rispetto alla media.

        Esempio:
            Stipendi: [30000, 40000, 50000, 60000, 200000]
            Media:   76000  (distorta dal 200000)
            Mediana: 50000  (il valore al centro)

        Per questo la Direttiva EU chiede ENTRAMBE le metriche.
        """
        logger.info("Calcolo overall median gap...")
        return self._calculate_gap(self.df, use_median=True)

    def gap_by_category(self) -> list[CategoryGap]:
        """
        Calcola il gap per ogni combinazione di dipartimento + livello.

        Questo è il calcolo PIÙ IMPORTANTE per la Direttiva EU: il confronto
        deve avvenire "a parità di lavoro o di lavoro di pari valore".

        Se un'azienda ha:
        - Engineering Senior: uomini 70000€, donne 64000€ → gap 8.6%
        - HR Junior: uomini 30000€, donne 30000€ → gap 0%

        Il gap del 8.6% in Engineering Senior è quello che la Direttiva EU
        vuole evidenziare e che l'azienda deve giustificare.

        Nota: categorie con meno di 2 dipendenti per genere vengono escluse
        perché il calcolo non sarebbe statisticamente significativo.
        """
        logger.info("Calcolo gap per categoria (dipartimento + livello)...")

        if "department" not in self.df.columns or "level" not in self.df.columns:
            logger.warning("Colonne 'department' e/o 'level' mancanti. "
                           "Gap per categoria non disponibile.")
            return []

        results = []

        # groupby raggruppa il DataFrame per combinazioni di (department, level).
        # Ogni gruppo contiene solo i dipendenti di quel dipartimento+livello.
        for (dept, level), group in self.df.groupby(["department", "level"]):
            males = group[group["gender"] == "M"]
            females = group[group["gender"] == "F"]

            # Skippa categorie troppo piccole (< 2 per genere)
            if len(males) < 2 or len(females) < 2:
                continue

            gap_result = self._calculate_gap(group, use_median=False)

            results.append(CategoryGap(
                department=dept,
                level=level,
                gap_pct=gap_result.gap_pct,
                male_avg=gap_result.male_avg,
                female_avg=gap_result.female_avg,
                male_count=gap_result.male_count,
                female_count=gap_result.female_count,
                is_significant=gap_result.is_significant,
            ))

        # Ordina per gap decrescente (i più critici prima)
        results.sort(key=lambda x: abs(x.gap_pct), reverse=True)

        logger.info(f"  {len(results)} categorie analizzate")
        return results

    def pay_quartiles(self) -> list[QuartileData]:
        """
        Calcola la distribuzione di genere nei 4 quartili retributivi.

        Cos'è un quartile?
        Ordiniamo tutti i 500 dipendenti per stipendio e li dividiamo in 4 gruppi
        uguali da ~125 persone:
        - Q1: il 25% con gli stipendi più bassi
        - Q2: il 25% successivo
        - Q3: il 25% successivo
        - Q4: il 25% con gli stipendi più alti

        La Direttiva EU chiede questa analisi perché rivela se le donne sono
        concentrate nei quartili bassi. Es:
        - Q1 (bassi): 80% donne → le donne tendono ad avere stipendi bassi
        - Q4 (alti):  20% donne → poche donne tra i più pagati

        Questo è un segnale di squilibrio anche se il gap medio fosse basso.
        """
        logger.info("Calcolo distribuzione quartili...")

        # pd.qcut divide in quantili: 4 = quartili, labels = nomi dei gruppi
        # Ogni dipendente viene assegnato al suo quartile in base allo stipendio.
        self.df["_quartile"] = pd.qcut(
            self.df["base_salary"],
            q=4,
            labels=[1, 2, 3, 4],
            duplicates="drop"  # Gestisce il caso di molti stipendi uguali
        )

        results = []

        for q in sorted(self.df["_quartile"].unique()):
            group = self.df[self.df["_quartile"] == q]
            males = group[group["gender"] == "M"]
            females = group[group["gender"] == "F"]
            total = len(group)

            results.append(QuartileData(
                quartile=int(q),
                min_salary=float(group["base_salary"].min()),
                max_salary=float(group["base_salary"].max()),
                total=total,
                male_count=len(males),
                female_count=len(females),
                male_pct=round(len(males) / total * 100, 1) if total > 0 else 0,
                female_pct=round(len(females) / total * 100, 1) if total > 0 else 0,
            ))

        # Rimuovi la colonna temporanea
        self.df.drop(columns=["_quartile"], inplace=True)

        logger.info(f"  {len(results)} quartili calcolati")
        return results

    def bonus_gap(self) -> GapResult | None:
        """
        Calcola il gender pay gap sui bonus.

        La Direttiva EU (Art. 9, paragrafo 1, lettera g) richiede informazioni
        sulla retribuzione complementare (bonus, benefit, ecc.).

        Returns:
            GapResult se la colonna "bonus" esiste, None altrimenti.
        """
        if "bonus" not in self.df.columns:
            logger.info("Colonna 'bonus' non presente. Analisi bonus non disponibile.")
            return None

        logger.info("Calcolo bonus gap...")

        # Filtra solo chi ha bonus > 0 (esclude chi non ha bonus)
        df_with_bonus = self.df[self.df["bonus"] > 0].copy()

        if len(df_with_bonus) == 0:
            logger.warning("Nessun dipendente con bonus > 0")
            return None

        # Usa la colonna "bonus" al posto di "base_salary" per il calcolo
        males = df_with_bonus[df_with_bonus["gender"] == "M"]["bonus"]
        females = df_with_bonus[df_with_bonus["gender"] == "F"]["bonus"]

        if len(males) == 0 or len(females) == 0:
            return None

        male_avg = float(males.mean())
        female_avg = float(females.mean())
        gap_pct = (male_avg - female_avg) / male_avg * 100 if male_avg > 0 else 0.0

        result = GapResult(
            gap_pct=round(gap_pct, 2),
            male_avg=round(male_avg, 2),
            female_avg=round(female_avg, 2),
            male_count=len(males),
            female_count=len(females),
            is_significant=abs(gap_pct) > EU_THRESHOLD,
        )

        logger.info(f"  Bonus gap: {result.gap_pct}%")
        return result

    def full_analysis(self) -> ComplianceResult:
        """
        Esegue l'analisi completa e restituisce il risultato di compliance.

        Questo è il metodo "entry point" che chiama tutti gli altri metodi
        e combina i risultati in un unico oggetto ComplianceResult.

        L'azienda è "compliant" se NESSUNA categoria ha un gap > 5%.
        """
        logger.info("Avvio analisi completa del gender pay gap...")

        # Calcola tutte le metriche
        mean_gap = self.overall_mean_gap()
        median_gap = self.overall_median_gap()
        cat_gaps = self.gap_by_category()
        quartiles = self.pay_quartiles()
        b_gap = self.bonus_gap()

        # Identifica le categorie non compliant (gap > 5%)
        non_compliant = [c for c in cat_gaps if c.is_significant]

        # L'azienda è compliant se nessuna categoria supera la soglia
        is_compliant = len(non_compliant) == 0

        result = ComplianceResult(
            is_compliant=is_compliant,
            overall_mean_gap=mean_gap,
            overall_median_gap=median_gap,
            category_gaps=cat_gaps,
            non_compliant_categories=non_compliant,
            quartiles=quartiles,
            bonus_gap=b_gap,
        )

        status = "COMPLIANT" if is_compliant else "NON COMPLIANT"
        logger.info(f"Analisi completata — Stato: {status}")
        logger.info(f"  Overall mean gap: {mean_gap.gap_pct}%")
        logger.info(f"  Overall median gap: {median_gap.gap_pct}%")
        logger.info(f"  Categorie analizzate: {len(cat_gaps)}")
        logger.info(f"  Categorie non compliant: {len(non_compliant)}")

        return result

    # =========================================================================
    # METODI PRIVATI — Logica di calcolo interna
    # =========================================================================

    def _calculate_gap(self, df: pd.DataFrame, use_median: bool = False) -> GapResult:
        """
        Calcola il gap su un DataFrame (o un suo sottoinsieme).

        Questo è il metodo "base" usato da tutti i metodi pubblici.
        La formula è sempre la stessa:
            GPG = (valore_M - valore_F) / valore_M × 100

        Args:
            df: DataFrame con colonne "gender" e "base_salary"
            use_median: se True usa la mediana, se False usa la media
        """
        males = df[df["gender"] == "M"]["base_salary"]
        females = df[df["gender"] == "F"]["base_salary"]

        if len(males) == 0 or len(females) == 0:
            return GapResult(
                gap_pct=0.0, male_avg=0.0, female_avg=0.0,
                male_count=len(males), female_count=len(females),
                is_significant=False,
            )

        # Scelta: media o mediana
        if use_median:
            male_value = float(males.median())
            female_value = float(females.median())
        else:
            male_value = float(males.mean())
            female_value = float(females.mean())

        # Formula del gender pay gap
        if male_value > 0:
            gap_pct = (male_value - female_value) / male_value * 100
        else:
            gap_pct = 0.0

        return GapResult(
            gap_pct=round(gap_pct, 2),
            male_avg=round(male_value, 2),
            female_avg=round(female_value, 2),
            male_count=len(males),
            female_count=len(females),
            is_significant=abs(gap_pct) > EU_THRESHOLD,
        )
