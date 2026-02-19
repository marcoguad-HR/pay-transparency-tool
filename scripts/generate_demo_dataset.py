"""
Generazione Dataset Demo — Fase 2.1 del progetto Pay Transparency Tool.

Questo script genera un file CSV con 500 dipendenti fittizi per testare
il nostro calcolatore di gender pay gap.

Perché un dataset sintetico?
- Ci serve per testare il GapCalculator PRIMA di usare dati reali
- Inseriamo gap salariali INTENZIONALI in certe categorie, così possiamo
  verificare che il calcolatore trovi esattamente quei numeri
- Un dataset reale avrebbe problemi di privacy; qui generiamo tutto noi

Gap intenzionali inseriti (uomini pagati di più rispetto alle donne):
- Engineering, Senior   → ~8%
- Sales, Mid            → ~12%
- Finance, Director     → ~6%
- Tutte le altre        → ~1-2% (gap piccolo, "fisiologico")

Concetti Python usati qui:
- numpy.random: generazione numeri casuali con distribuzione controllata
- pandas.DataFrame: tabella dati (come un foglio Excel in Python)
- List comprehension: modo compatto di creare liste
- f-string: stringhe con variabili inserite (es. f"Ciao {nome}")
- Seed random: fissa il "dado" così otteniamo sempre gli stessi numeri
"""

import numpy as np    # Libreria per calcoli numerici e numeri casuali
import pandas as pd   # Libreria per tabelle dati (DataFrame)
from pathlib import Path


# =============================================================================
# CONFIGURAZIONE DEL DATASET
# =============================================================================
# Questi parametri definiscono la struttura aziendale fittizia.
# Ogni dipendente ha: dipartimento, livello, genere, stipendio base, bonus.

# Seed: fissa il generatore casuale per avere SEMPRE gli stessi dati.
# Così ogni volta che rigeneriamo il dataset, i numeri sono identici
# e possiamo confrontarli con sicurezza.
RANDOM_SEED = 42

# Quanti dipendenti totali
NUM_EMPLOYEES = 500

# Struttura aziendale: dipartimento → lista di livelli
# Ogni dipartimento ha livelli con uno stipendio base diverso.
DEPARTMENTS = {
    "Engineering": {
        "Junior":   {"base_salary": 35000, "employees": 35},
        "Mid":      {"base_salary": 50000, "employees": 30},
        "Senior":   {"base_salary": 70000, "employees": 24},
        "Lead":     {"base_salary": 85000, "employees": 12},
    },
    "Sales": {
        "Junior":   {"base_salary": 30000, "employees": 30},
        "Mid":      {"base_salary": 45000, "employees": 36},
        "Senior":   {"base_salary": 60000, "employees": 18},
        "Director": {"base_salary": 80000, "employees": 8},
    },
    "Finance": {
        "Junior":   {"base_salary": 33000, "employees": 24},
        "Mid":      {"base_salary": 48000, "employees": 28},
        "Senior":   {"base_salary": 65000, "employees": 18},
        "Director": {"base_salary": 90000, "employees": 14},
    },
    "HR": {
        "Junior":   {"base_salary": 30000, "employees": 28},
        "Mid":      {"base_salary": 42000, "employees": 22},
        "Senior":   {"base_salary": 55000, "employees": 12},
        "Director": {"base_salary": 75000, "employees": 8},
    },
    "Marketing": {
        "Junior":   {"base_salary": 32000, "employees": 32},
        "Mid":      {"base_salary": 46000, "employees": 28},
        "Senior":   {"base_salary": 62000, "employees": 18},
        "Director": {"base_salary": 82000, "employees": 12},
    },
    "Operations": {
        "Junior":   {"base_salary": 28000, "employees": 22},
        "Mid":      {"base_salary": 40000, "employees": 18},
        "Senior":   {"base_salary": 55000, "employees": 14},
        "Director": {"base_salary": 72000, "employees": 10},
    },
}

# Gap salariali intenzionali: (dipartimento, livello) → gap percentuale.
# Es. 0.08 significa che le donne guadagnano ~8% in meno degli uomini.
# Questi sono i valori che il GapCalculator DEVE trovare (circa).
INTENTIONAL_GAPS = {
    ("Engineering", "Senior"):  0.08,   # 8% — supera la soglia EU del 5%
    ("Sales", "Mid"):           0.12,   # 12% — ben sopra la soglia
    ("Finance", "Director"):    0.06,   # 6% — poco sopra la soglia
}

# Percentuale bonus rispetto allo stipendio base.
# Il bonus avrà anch'esso un gap in alcune categorie.
BONUS_PERCENTAGE_RANGE = (0.05, 0.20)  # Tra 5% e 20% dello stipendio


def generate_dataset() -> pd.DataFrame:
    """
    Genera il dataset completo con 500 dipendenti.

    Come funziona:
    1. Per ogni (dipartimento, livello) crea N dipendenti
    2. Assegna genere casuale (~50/50)
    3. Lo stipendio base ha una variazione casuale ±10%
    4. Per le categorie con gap intenzionale, abbassa lo stipendio delle donne
    5. Genera bonus proporzionale allo stipendio

    Returns:
        pd.DataFrame con colonne:
        employee_id, department, level, gender, base_salary,
        bonus, total_compensation, years_experience, age, contract_type
    """
    # Fissa il seed: da questo punto, tutti i numeri "casuali" sono determinati
    np.random.seed(RANDOM_SEED)

    # Lista dove accumuliamo i dati di ogni dipendente (un dict per riga)
    employees = []
    employee_id = 1

    for dept_name, levels in DEPARTMENTS.items():
        for level_name, level_config in levels.items():
            base = level_config["base_salary"]
            n = level_config["employees"]

            # Cerca se questa combinazione ha un gap intenzionale
            gap = INTENTIONAL_GAPS.get((dept_name, level_name), 0.015)
            # 0.015 = 1.5% di default per le categorie senza gap specifico

            for _ in range(n):
                # --- Genere: ~50/50 ---
                gender = np.random.choice(["M", "F"])

                # --- Stipendio base con variazione ±10% ---
                # np.random.normal(1.0, 0.10) genera un numero attorno a 1.0
                # con deviazione standard 0.10 (cioè quasi sempre tra 0.80 e 1.20)
                variation = np.random.normal(1.0, 0.10)
                salary = base * variation

                # --- Applica il gap se è donna ---
                # Questo simula il gender pay gap reale: a parità di ruolo,
                # le donne vengono pagate meno. Il gap è percentuale:
                # se gap=0.08 e salary=70000, la donna prende 70000 * 0.92 = 64400
                if gender == "F":
                    salary = salary * (1 - gap)

                # Arrotonda allo stipendio a centinaia (più realistico)
                salary = round(salary / 100) * 100

                # --- Bonus: tra 5% e 20% dello stipendio ---
                bonus_pct = np.random.uniform(*BONUS_PERCENTAGE_RANGE)

                # Anche il bonus ha un piccolo gap per le donne
                # (la Direttiva EU chiede di analizzare anche i bonus)
                if gender == "F":
                    bonus_pct = bonus_pct * (1 - gap * 0.5)  # Gap bonus = metà del gap salariale

                bonus = round(salary * bonus_pct / 100) * 100

                # --- Total compensation = stipendio + bonus ---
                total = salary + bonus

                # --- Anni di esperienza (correlati al livello) ---
                # Livelli più alti → più esperienza (con variazione casuale)
                exp_ranges = {
                    "Junior": (0, 3),
                    "Mid": (3, 7),
                    "Senior": (7, 15),
                    "Lead": (10, 20),
                    "Director": (12, 25),
                }
                exp_min, exp_max = exp_ranges.get(level_name, (0, 10))
                experience = np.random.randint(exp_min, exp_max + 1)

                # --- Età (correlata all'esperienza) ---
                # Età = 22 (fine studi) + esperienza + variazione casuale ±3
                age = 22 + experience + np.random.randint(-3, 4)
                age = max(22, min(65, age))  # Clamp tra 22 e 65

                # --- Tipo contratto ---
                # 85% full-time, 10% part-time, 5% temporary
                contract = np.random.choice(
                    ["full-time", "part-time", "temporary"],
                    p=[0.85, 0.10, 0.05]
                )

                employees.append({
                    "employee_id": f"EMP{employee_id:04d}",
                    "department": dept_name,
                    "level": level_name,
                    "gender": gender,
                    "base_salary": salary,
                    "bonus": bonus,
                    "total_compensation": total,
                    "years_experience": experience,
                    "age": age,
                    "contract_type": contract,
                })
                employee_id += 1

    # Crea il DataFrame (tabella) da una lista di dizionari
    df = pd.DataFrame(employees)

    # Mescola le righe per non avere tutti i dipendenti di un dipartimento insieme
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    return df


def verify_gaps(df: pd.DataFrame) -> None:
    """
    Verifica che i gap intenzionali siano presenti nel dataset.

    Questa funzione è una "sanity check": dopo aver generato i dati,
    controlliamo che i gap che volevamo inserire ci siano davvero.

    La formula del gender pay gap (GPG) è:
    GPG = (media_uomini - media_donne) / media_uomini × 100

    Se GPG > 0, gli uomini guadagnano di più (il caso più comune).
    Se GPG < 0, le donne guadagnano di più.
    """
    print("\n" + "=" * 60)
    print("VERIFICA GAP INTENZIONALI")
    print("=" * 60)

    # --- Gap complessivo (overall) ---
    male_mean = df[df["gender"] == "M"]["base_salary"].mean()
    female_mean = df[df["gender"] == "F"]["base_salary"].mean()
    overall_gap = (male_mean - female_mean) / male_mean * 100
    print(f"\nGap complessivo (overall): {overall_gap:.1f}%")
    print(f"  Media uomini: €{male_mean:,.0f}")
    print(f"  Media donne:  €{female_mean:,.0f}")

    # --- Gap per categoria (dipartimento + livello) ---
    print(f"\n{'Dipartimento':<15} {'Livello':<10} {'Gap %':>8} {'M medio':>10} "
          f"{'F medio':>10} {'N.M':>5} {'N.F':>5} {'Atteso':>8}")
    print("-" * 80)

    for dept in sorted(df["department"].unique()):
        for level in ["Junior", "Mid", "Senior", "Lead", "Director"]:
            subset = df[(df["department"] == dept) & (df["level"] == level)]
            if len(subset) == 0:
                continue

            males = subset[subset["gender"] == "M"]["base_salary"]
            females = subset[subset["gender"] == "F"]["base_salary"]

            if len(males) == 0 or len(females) == 0:
                continue

            gap_pct = (males.mean() - females.mean()) / males.mean() * 100
            expected = INTENTIONAL_GAPS.get((dept, level), 0.015) * 100

            # Flag: "!!!" se il gap trovato è molto diverso dall'atteso
            flag = "OK" if abs(gap_pct - expected) < 3.0 else "!!!"

            print(f"{dept:<15} {level:<10} {gap_pct:>7.1f}% "
                  f"€{males.mean():>9,.0f} €{females.mean():>9,.0f} "
                  f"{len(males):>5} {len(females):>5} "
                  f"{expected:>6.1f}%  {flag}")

    # --- Distribuzione genere ---
    print(f"\n{'Distribuzione genere:'}")
    gender_counts = df["gender"].value_counts()
    for g, count in gender_counts.items():
        label = "Uomini" if g == "M" else "Donne"
        print(f"  {label}: {count} ({count/len(df)*100:.1f}%)")

    # --- Distribuzione contratti ---
    print(f"\n{'Distribuzione contratti:'}")
    contract_counts = df["contract_type"].value_counts()
    for c, count in contract_counts.items():
        print(f"  {c}: {count} ({count/len(df)*100:.1f}%)")


def main():
    """Entry point dello script."""
    print("Generazione dataset demo per Pay Transparency Tool")
    print("=" * 50)

    # Genera il dataset
    df = generate_dataset()
    print(f"\nDataset generato: {len(df)} dipendenti")
    print(f"Colonne: {', '.join(df.columns)}")

    # Verifica che i gap siano corretti
    verify_gaps(df)

    # Salva il CSV nella cartella data/demo/
    output_dir = Path(__file__).parent.parent / "data" / "demo"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "demo_employees.csv"
    df.to_csv(output_path, index=False)
    print(f"\nDataset salvato in: {output_path}")
    print(f"Dimensione file: {output_path.stat().st_size / 1024:.1f} KB")

    # Mostra le prime 5 righe come anteprima
    print(f"\nAnteprima (prime 5 righe):")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()
