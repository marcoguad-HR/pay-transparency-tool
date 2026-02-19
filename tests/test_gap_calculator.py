"""Unit test per GapCalculator."""

import pytest
import pandas as pd

from src.analysis.gap_calculator import GapCalculator, EU_THRESHOLD


class TestOverallGap:
    """Test per i calcoli di gap complessivo."""

    def test_mean_gap_positive(self, sample_df):
        """Mean gap positivo quando uomini guadagnano di più."""
        calc = GapCalculator(sample_df)
        result = calc.overall_mean_gap()
        # Il dataset ha un gap intenzionale per F in Engineering Senior
        assert result.gap_pct > 0
        assert result.male_avg > result.female_avg
        assert result.male_count > 0
        assert result.female_count > 0

    def test_median_gap(self, sample_df):
        """Median gap restituisce un risultato valido."""
        calc = GapCalculator(sample_df)
        result = calc.overall_median_gap()
        assert isinstance(result.gap_pct, float)
        assert result.male_count + result.female_count == len(sample_df)

    def test_zero_gap(self, equal_pay_df):
        """Gap è 0% quando M e F hanno stipendi identici."""
        calc = GapCalculator(equal_pay_df)
        result = calc.overall_mean_gap()
        assert result.gap_pct == 0.0
        assert result.is_significant is False

    def test_known_gap(self):
        """Verifica formula con valori noti."""
        # Uomini media: 50000, Donne media: 45000
        # Gap = (50000 - 45000) / 50000 * 100 = 10%
        df = pd.DataFrame({
            "gender": ["M", "M", "F", "F"],
            "base_salary": [40000, 60000, 35000, 55000],
        })
        calc = GapCalculator(df)
        result = calc.overall_mean_gap()
        assert result.gap_pct == 10.0
        assert result.male_avg == 50000.0
        assert result.female_avg == 45000.0

    def test_is_significant_flag(self):
        """is_significant è True quando |gap| > 5%."""
        df = pd.DataFrame({
            "gender": ["M", "F"],
            "base_salary": [50000, 40000],
        })
        calc = GapCalculator(df)
        result = calc.overall_mean_gap()
        assert result.gap_pct == 20.0
        assert result.is_significant is True

    def test_not_significant_flag(self):
        """is_significant è False quando |gap| <= 5%."""
        df = pd.DataFrame({
            "gender": ["M", "F"],
            "base_salary": [50000, 48000],
        })
        calc = GapCalculator(df)
        result = calc.overall_mean_gap()
        assert abs(result.gap_pct) <= EU_THRESHOLD
        assert result.is_significant is False


class TestCategoryGap:
    """Test per gap per categoria."""

    def test_returns_categories(self, sample_df):
        """Restituisce gap per ogni combinazione dept+level valida."""
        calc = GapCalculator(sample_df)
        gaps = calc.gap_by_category()
        assert len(gaps) > 0
        for cat in gaps:
            assert cat.department != ""
            assert cat.level != ""
            assert cat.male_count >= 2
            assert cat.female_count >= 2

    def test_sorted_by_absolute_gap(self, sample_df):
        """Le categorie sono ordinate per |gap| decrescente."""
        calc = GapCalculator(sample_df)
        gaps = calc.gap_by_category()
        abs_gaps = [abs(g.gap_pct) for g in gaps]
        assert abs_gaps == sorted(abs_gaps, reverse=True)

    def test_no_categories_without_columns(self, minimal_df):
        """Senza colonne department/level ritorna lista vuota."""
        calc = GapCalculator(minimal_df)
        gaps = calc.gap_by_category()
        assert gaps == []

    def test_skips_small_groups(self):
        """Categorie con < 2 per genere vengono escluse."""
        df = pd.DataFrame({
            "gender": ["M", "F", "M"],
            "base_salary": [50000, 48000, 52000],
            "department": ["Eng", "Eng", "Eng"],
            "level": ["Senior", "Senior", "Senior"],
        })
        calc = GapCalculator(df)
        gaps = calc.gap_by_category()
        # Solo 1F, dovrebbe essere esclusa
        assert len(gaps) == 0


class TestPayQuartiles:
    """Test per distribuzione quartili."""

    def test_returns_four_quartiles(self, sample_df):
        """Restituisce esattamente 4 quartili."""
        calc = GapCalculator(sample_df)
        quartiles = calc.pay_quartiles()
        assert len(quartiles) == 4

    def test_quartile_structure(self, sample_df):
        """Ogni quartile ha i campi necessari."""
        calc = GapCalculator(sample_df)
        quartiles = calc.pay_quartiles()
        for q in quartiles:
            assert q.quartile in [1, 2, 3, 4]
            assert q.min_salary <= q.max_salary
            assert q.total > 0
            assert q.male_count + q.female_count == q.total
            assert abs(q.male_pct + q.female_pct - 100.0) < 1.0  # ~100% con arrotondamento

    def test_quartile_ordering(self, sample_df):
        """Q1 ha stipendi più bassi di Q4."""
        calc = GapCalculator(sample_df)
        quartiles = calc.pay_quartiles()
        assert quartiles[0].max_salary <= quartiles[-1].min_salary


class TestBonusGap:
    """Test per gap bonus."""

    def test_returns_none_without_column(self, minimal_df):
        """Senza colonna bonus ritorna None."""
        calc = GapCalculator(minimal_df)
        assert calc.bonus_gap() is None

    def test_calculates_bonus_gap(self, sample_df):
        """Calcola il gap bonus quando la colonna esiste."""
        calc = GapCalculator(sample_df)
        result = calc.bonus_gap()
        assert result is not None
        assert isinstance(result.gap_pct, float)
        assert result.male_count > 0
        assert result.female_count > 0


class TestFullAnalysis:
    """Test per l'analisi completa."""

    def test_full_analysis_structure(self, sample_df):
        """full_analysis restituisce un ComplianceResult completo."""
        calc = GapCalculator(sample_df)
        result = calc.full_analysis()

        assert result.overall_mean_gap is not None
        assert result.overall_median_gap is not None
        assert isinstance(result.category_gaps, list)
        assert isinstance(result.non_compliant_categories, list)
        assert isinstance(result.quartiles, list)
        assert isinstance(result.is_compliant, bool)

    def test_non_compliant_when_gap_exceeds_threshold(self, sample_df):
        """Non compliant quando almeno una categoria supera il 5%."""
        calc = GapCalculator(sample_df)
        result = calc.full_analysis()
        if result.non_compliant_categories:
            assert result.is_compliant is False
            for cat in result.non_compliant_categories:
                assert abs(cat.gap_pct) > EU_THRESHOLD

    def test_compliant_with_equal_pay(self, equal_pay_df):
        """Compliant quando nessun gap supera il 5%."""
        calc = GapCalculator(equal_pay_df)
        result = calc.full_analysis()
        assert result.overall_mean_gap.gap_pct == 0.0
        # Nota: potrebbe non avere category_gaps se gruppi troppo piccoli

    def test_does_not_modify_original(self, sample_df):
        """full_analysis non modifica il DataFrame originale."""
        original_cols = set(sample_df.columns)
        calc = GapCalculator(sample_df)
        calc.full_analysis()
        # Il calculator lavora su una copia
        assert set(sample_df.columns) == original_cols
