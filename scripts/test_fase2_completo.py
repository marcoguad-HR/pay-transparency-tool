"""
Test completo Fase 2 — Pipeline: CSV → DataLoader → GapCalculator → Report

Questo script testa l'intera pipeline di analisi dati della Fase 2:
1. Carica il dataset demo con PayDataLoader
2. Calcola tutti i gap con GapCalculator
3. Stampa il report formattato con PayGapReport

Se tutto funziona, nel terminale vedrai un report colorato con tabelle,
gap per categoria, quartili e il verdetto di compliance.
"""

from src.analysis.data_loader import PayDataLoader
from src.analysis.gap_calculator import GapCalculator
from src.analysis.report import PayGapReport


def main():
    print("=" * 60)
    print("TEST FASE 2 — Pipeline Analisi Dati Completa")
    print("=" * 60)

    # --- Step 1: Caricamento dati ---
    print("\n[Step 1] Caricamento dataset demo...")
    loader = PayDataLoader()
    load_result = loader.load("data/demo/demo_employees.csv")

    print(f"  Dipendenti: {load_result.n_employees}")
    print(f"  Uomini: {load_result.n_male}, Donne: {load_result.n_female}")
    print(f"  Dipartimenti: {load_result.departments}")

    # --- Step 2: Calcolo gap ---
    print("\n[Step 2] Calcolo gender pay gap...")
    calculator = GapCalculator(load_result.df)
    analysis = calculator.full_analysis()

    # --- Step 3: Report ---
    print("\n[Step 3] Generazione report...")
    report = PayGapReport(analysis)
    report.print_full_report()

    # --- Riepilogo finale ---
    print("=" * 60)
    print("TEST FASE 2 COMPLETATO")
    print("=" * 60)
    print(f"  Overall Mean Gap:     {analysis.overall_mean_gap.gap_pct:+.2f}%")
    print(f"  Overall Median Gap:   {analysis.overall_median_gap.gap_pct:+.2f}%")
    print(f"  Categorie analizzate: {len(analysis.category_gaps)}")
    print(f"  Non compliant:        {len(analysis.non_compliant_categories)}")
    print(f"  Compliance:           {'SI' if analysis.is_compliant else 'NO'}")
    if analysis.bonus_gap:
        print(f"  Bonus Gap:            {analysis.bonus_gap.gap_pct:+.2f}%")


if __name__ == "__main__":
    main()
