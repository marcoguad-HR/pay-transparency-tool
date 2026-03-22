"""
Test per EqualValueCalculator — confronto pari valore ruoli SERW.
Scritti PRIMA del codice (TDD).
"""
import pytest
from src.analysis.equal_value_calculator import (
    RoleScores,
    CategoryScore,
    GenderWarning,
    ComparisonResult,
    EqualValueCalculator,
)


# --- Fixture ---

@pytest.fixture
def calculator():
    """Calculator con pesi e soglie default."""
    return EqualValueCalculator()


@pytest.fixture
def role_balanced():
    """Ruolo con punteggi bilanciati (tutti 3)."""
    return RoleScores(
        name="Impiegato amministrativo",
        S1=3, S2=3, S3=3, S4=3,
        E1=3, E2=3, E3=3, E4=3,
        R1=3, R2=3, R3=3, R4=3,
        W1=3, W2=3, W3=3, W4=3,
    )


@pytest.fixture
def role_technical():
    """Ruolo tecnico-specialistico."""
    return RoleScores(
        name="Ingegnere software senior",
        S1=5, S2=4, S3=5, S4=3,
        E1=1, E2=5, E3=2, E4=4,
        R1=3, R2=4, R3=1, R4=4,
        W1=1, W2=4, W3=2, W4=2,
    )


@pytest.fixture
def role_care():
    """Ruolo di cura/assistenza."""
    return RoleScores(
        name="Infermiera reparto",
        S1=4, S2=3, S3=4, S4=5,
        E1=4, E2=4, E3=5, E4=4,
        R1=2, R2=2, R3=5, R4=4,
        W1=3, W2=4, W3=5, W4=1,
    )


@pytest.fixture
def role_all_ones():
    """Ruolo con tutti punteggi minimi."""
    return RoleScores(
        name="Ruolo minimo", S1=1, S2=1, S3=1, S4=1,
        E1=1, E2=1, E3=1, E4=1, R1=1, R2=1, R3=1, R4=1,
        W1=1, W2=1, W3=1, W4=1,
    )


@pytest.fixture
def role_all_fives():
    """Ruolo con tutti punteggi massimi."""
    return RoleScores(
        name="Ruolo massimo", S1=5, S2=5, S3=5, S4=5,
        E1=5, E2=5, E3=5, E4=5, R1=5, R2=5, R3=5, R4=5,
        W1=5, W2=5, W3=5, W4=5,
    )


# ================================================================
# Test RoleScores
# ================================================================

class TestRoleScores:
    """Test sulla dataclass RoleScores."""

    def test_creation_with_16_factors(self):
        """Un RoleScores deve avere name + 16 fattori SERW."""
        role = RoleScores(
            name="Test",
            S1=1, S2=2, S3=3, S4=4,
            E1=1, E2=2, E3=3, E4=4,
            R1=1, R2=2, R3=3, R4=4,
            W1=1, W2=2, W3=3, W4=4,
        )
        assert role.name == "Test"
        assert role.S1 == 1
        assert role.W4 == 4

    def test_all_factors_accessible(self):
        """Tutti i 16 fattori devono essere accessibili come attributi."""
        role = RoleScores(
            name="X", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3,
            R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        factors = [
            role.S1, role.S2, role.S3, role.S4,
            role.E1, role.E2, role.E3, role.E4,
            role.R1, role.R2, role.R3, role.R4,
            role.W1, role.W2, role.W3, role.W4,
        ]
        assert len(factors) == 16
        assert all(f == 3 for f in factors)


# ================================================================
# Test validazione punteggi
# ================================================================

class TestValidation:
    """Test sulla validazione dei punteggi (range 1-5)."""

    def test_valid_scores_no_error(self, calculator, role_balanced):
        """Punteggi validi (1-5) non sollevano eccezioni."""
        calculator.validate_scores(role_balanced)  # non deve sollevare

    def test_score_zero_raises_value_error(self, calculator):
        """Punteggio 0 deve sollevare ValueError."""
        role = RoleScores(
            name="Invalid", S1=0, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        with pytest.raises(ValueError, match="S1"):
            calculator.validate_scores(role)

    def test_score_six_raises_value_error(self, calculator):
        """Punteggio 6 deve sollevare ValueError."""
        role = RoleScores(
            name="Invalid", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=6, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        with pytest.raises(ValueError, match="E3"):
            calculator.validate_scores(role)

    def test_negative_score_raises_value_error(self, calculator):
        """Punteggio negativo deve sollevare ValueError."""
        role = RoleScores(
            name="Invalid", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=-1, W2=3, W3=3, W4=3,
        )
        with pytest.raises(ValueError, match="W1"):
            calculator.validate_scores(role)

    def test_boundary_values_valid(self, calculator):
        """Punteggi 1 e 5 (boundary) sono validi."""
        role = RoleScores(
            name="Boundary", S1=1, S2=5, S3=1, S4=5,
            E1=1, E2=5, E3=1, E4=5, R1=1, R2=5, R3=1, R4=5,
            W1=1, W2=5, W3=1, W4=5,
        )
        calculator.validate_scores(role)  # non deve sollevare


# ================================================================
# Test calcolo score
# ================================================================

class TestScoreCalculation:
    """Test sul calcolo degli score per categoria e totale."""

    def test_category_scores_count(self, calculator, role_balanced):
        """Devono esserci esattamente 4 category scores."""
        cats = calculator.calculate_category_scores(role_balanced)
        assert len(cats) == 4

    def test_category_scores_labels(self, calculator, role_balanced):
        """Le 4 categorie sono skills, effort, responsibility, working_conditions."""
        cats = calculator.calculate_category_scores(role_balanced)
        categories = {c.category for c in cats}
        assert categories == {"skills", "effort", "responsibility", "working_conditions"}

    def test_category_score_balanced(self, calculator, role_balanced):
        """Ruolo con tutti 3: ogni categoria ha score = 12 (3*4)."""
        cats = calculator.calculate_category_scores(role_balanced)
        for cat in cats:
            assert cat.score == 12
            assert cat.max_score == 20

    def test_category_score_skills(self, calculator, role_technical):
        """Skills dell'ingegnere: S1=5, S2=4, S3=5, S4=3 → 17."""
        cats = calculator.calculate_category_scores(role_technical)
        skills = next(c for c in cats if c.category == "skills")
        assert skills.score == 17

    def test_category_score_effort(self, calculator, role_care):
        """Effort dell'infermiera: E1=4, E2=4, E3=5, E4=4 → 17."""
        cats = calculator.calculate_category_scores(role_care)
        effort = next(c for c in cats if c.category == "effort")
        assert effort.score == 17

    def test_total_score_balanced(self, calculator, role_balanced):
        """Ruolo con tutti 3: score totale = 48 (3*16, con pesi uguali)."""
        total = calculator.calculate_total_score(role_balanced)
        assert total == 48.0

    def test_total_score_all_ones(self, calculator, role_all_ones):
        """Ruolo con tutti 1: score totale = 16."""
        total = calculator.calculate_total_score(role_all_ones)
        assert total == 16.0

    def test_total_score_all_fives(self, calculator, role_all_fives):
        """Ruolo con tutti 5: score totale = 80."""
        total = calculator.calculate_total_score(role_all_fives)
        assert total == 80.0

    def test_total_score_technical(self, calculator, role_technical):
        """Ingegnere: somma = 5+4+5+3+1+5+2+4+3+4+1+4+1+4+2+2 = 50."""
        total = calculator.calculate_total_score(role_technical)
        assert total == 50.0

    def test_total_score_care(self, calculator, role_care):
        """Infermiera: somma = 4+3+4+5+4+4+5+4+2+2+5+4+3+4+5+1 = 59."""
        total = calculator.calculate_total_score(role_care)
        assert total == 59.0


# ================================================================
# Test confronto e verdetto
# ================================================================

class TestComparison:
    """Test sul confronto tra 2 ruoli e sul verdetto."""

    def test_equal_scores_equal_verdict(self, calculator, role_balanced):
        """Stessi punteggi → diff 0% → pari valore."""
        role_a = role_balanced
        role_b = RoleScores(
            name="Clone", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        result = calculator.compare(role_a, role_b)
        assert result.difference_pct == 0.0
        assert result.verdict == "equal"

    def test_pari_valore_threshold(self, calculator):
        """Diff <= 10% → verdict 'equal'."""
        # Score A = 50, Score B = 46 → diff = 4/50*100 = 8% → equal
        role_a = RoleScores(
            name="A", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=4, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=4, W4=3,
        )
        role_b = RoleScores(
            name="B", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=2, W3=3, W4=3,
        )
        result = calculator.compare(role_a, role_b)
        # A=50, B=46, diff=4/50*100=8%
        assert result.verdict == "equal"
        assert "PARI VALORE" in result.verdict_label

    def test_maybe_threshold(self, calculator):
        """Diff 11-20% → verdict 'maybe'."""
        # Score A = 60, Score B = 50 → diff = 10/60*100 = 16.67% → maybe
        role_a = RoleScores(
            name="A", S1=4, S2=4, S3=4, S4=4,
            E1=4, E2=4, E3=4, E4=4, R1=4, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        role_b = RoleScores(
            name="B", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=4, W4=3,
        )
        result = calculator.compare(role_a, role_b)
        # A=57, B=49 → diff=8/57*100 = 14.04% → maybe
        assert result.verdict == "maybe"

    def test_not_equal_threshold(self, calculator):
        """Diff > 20% → verdict 'not_equal'."""
        role_a = RoleScores(
            name="A", S1=5, S2=5, S3=5, S4=5,
            E1=5, E2=5, E3=5, E4=5, R1=5, R2=5, R3=5, R4=5,
            W1=5, W2=5, W3=5, W4=5,
        )
        role_b = RoleScores(
            name="B", S1=2, S2=2, S3=2, S4=2,
            E1=2, E2=2, E3=2, E4=2, R1=2, R2=2, R3=2, R4=2,
            W1=2, W2=2, W3=2, W4=2,
        )
        result = calculator.compare(role_a, role_b)
        # A=80, B=32 → diff=48/80*100 = 60% → not_equal
        assert result.verdict == "not_equal"
        assert result.difference_pct == 60.0

    def test_difference_pct_formula(self, calculator):
        """Verifica formula: |A-B| / max(A,B) * 100."""
        role_a = RoleScores(
            name="A", S1=5, S2=5, S3=5, S4=5,
            E1=5, E2=5, E3=5, E4=5, R1=5, R2=5, R3=5, R4=5,
            W1=5, W2=5, W3=5, W4=5,
        )
        role_b = RoleScores(
            name="B", S1=1, S2=1, S3=1, S4=1,
            E1=1, E2=1, E3=1, E4=1, R1=1, R2=1, R3=1, R4=1,
            W1=1, W2=1, W3=1, W4=1,
        )
        result = calculator.compare(role_a, role_b)
        # A=80, B=16 → |80-16|/80*100 = 80%
        assert result.difference_pct == 80.0

    def test_result_has_category_scores(self, calculator, role_balanced, role_technical):
        """Il risultato deve avere category_scores per entrambi i ruoli."""
        result = calculator.compare(role_balanced, role_technical)
        assert len(result.category_scores_a) == 4
        assert len(result.category_scores_b) == 4

    def test_result_stores_roles(self, calculator, role_balanced, role_technical):
        """Il risultato deve contenere i due ruoli originali."""
        result = calculator.compare(role_balanced, role_technical)
        assert result.role_a.name == "Impiegato amministrativo"
        assert result.role_b.name == "Ingegnere software senior"

    def test_compare_validates_scores(self, calculator):
        """compare() deve validare i punteggi prima del calcolo."""
        role_ok = RoleScores(
            name="OK", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        role_bad = RoleScores(
            name="Bad", S1=0, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        with pytest.raises(ValueError):
            calculator.compare(role_ok, role_bad)


# ================================================================
# Test edge cases
# ================================================================

class TestEdgeCases:
    """Test su casi limite."""

    def test_identical_roles_pari_valore(self, calculator, role_balanced):
        """Due ruoli con punteggi identici → pari valore, diff 0%."""
        clone = RoleScores(
            name="Clone", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        result = calculator.compare(role_balanced, clone)
        assert result.verdict == "equal"
        assert result.difference_pct == 0.0

    def test_extreme_scores_all_ones_vs_all_fives(self, calculator, role_all_ones, role_all_fives):
        """Tutti 1 vs tutti 5 → not_equal, massima differenza."""
        result = calculator.compare(role_all_ones, role_all_fives)
        assert result.verdict == "not_equal"
        # 16 vs 80 → diff = 64/80*100 = 80%
        assert result.difference_pct == 80.0

    def test_symmetric_comparison(self, calculator, role_technical, role_care):
        """compare(A,B) e compare(B,A) devono dare stessa diff% e verdetto."""
        result_ab = calculator.compare(role_technical, role_care)
        result_ba = calculator.compare(role_care, role_technical)
        assert result_ab.difference_pct == result_ba.difference_pct
        assert result_ab.verdict == result_ba.verdict


# ================================================================
# Test gender-neutrality warnings
# ================================================================

class TestGenderWarnings:
    """Test sui warning di gender-neutrality."""

    def test_no_warnings_balanced(self, calculator, role_balanced):
        """Ruolo bilanciato non genera warning."""
        warnings = calculator.check_gender_warnings(role_balanced)
        assert len(warnings) == 0

    def test_warning_emotional_effort(self, calculator):
        """E1 >= 4 e E3 <= 2 → warning sforzo emotivo sottovalutato."""
        role = RoleScores(
            name="Test", S1=3, S2=3, S3=3, S4=3,
            E1=4, E2=3, E3=2, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        warnings = calculator.check_gender_warnings(role)
        codes = [w.code for w in warnings]
        assert "effort_emotional_undervalued" in codes

    def test_warning_emotional_effort_boundary(self, calculator):
        """E1=5, E3=1 → warning (caso estremo)."""
        role = RoleScores(
            name="Test", S1=3, S2=3, S3=3, S4=3,
            E1=5, E2=3, E3=1, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        warnings = calculator.check_gender_warnings(role)
        codes = [w.code for w in warnings]
        assert "effort_emotional_undervalued" in codes

    def test_no_warning_emotional_when_balanced(self, calculator):
        """E1=3, E3=3 → nessun warning emotivo."""
        role = RoleScores(
            name="Test", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        warnings = calculator.check_gender_warnings(role)
        codes = [w.code for w in warnings]
        assert "effort_emotional_undervalued" not in codes

    def test_warning_wellbeing(self, calculator):
        """R2 >= 4 e R3 <= 2 → warning benessere sottovalutato."""
        role = RoleScores(
            name="Test", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=4, R3=2, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        warnings = calculator.check_gender_warnings(role)
        codes = [w.code for w in warnings]
        assert "responsibility_wellbeing_undervalued" in codes

    def test_warning_psychological_stress(self, calculator):
        """W1 >= 4 e W2 <= 2 → warning stress psicologico sottovalutato."""
        role = RoleScores(
            name="Test", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=4, W2=2, W3=3, W4=3,
        )
        warnings = calculator.check_gender_warnings(role)
        codes = [w.code for w in warnings]
        assert "working_conditions_psychological_undervalued" in codes

    def test_warning_category_dominance(self, calculator):
        """Un fattore > 40% del totale categoria → warning dominanza."""
        # Skills: S1=5, S2=1, S3=1, S4=1 → totale=8, S1=5/8=62.5% > 40%
        role = RoleScores(
            name="Test", S1=5, S2=1, S3=1, S4=1,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        warnings = calculator.check_gender_warnings(role)
        codes = [w.code for w in warnings]
        assert any("dominance" in c for c in codes)

    def test_no_dominance_warning_when_even(self, calculator):
        """Fattori uguali in una categoria → nessun warning dominanza."""
        role = RoleScores(
            name="Test", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        warnings = calculator.check_gender_warnings(role)
        codes = [w.code for w in warnings]
        assert not any("dominance" in c for c in codes)

    def test_multiple_warnings(self, calculator):
        """Un ruolo puo' avere warning multipli."""
        # E1=5, E3=1 → warning emotivo
        # R2=5, R3=1 → warning benessere
        # W1=5, W2=1 → warning stress
        role = RoleScores(
            name="Bias multipli", S1=3, S2=3, S3=3, S4=3,
            E1=5, E2=3, E3=1, E4=3, R1=3, R2=5, R3=1, R4=3,
            W1=5, W2=1, W3=3, W4=3,
        )
        warnings = calculator.check_gender_warnings(role)
        assert len(warnings) >= 3

    def test_comparison_combines_warnings(self, calculator):
        """Il confronto combina i warnings di entrambi i ruoli."""
        role_a = RoleScores(
            name="A", S1=3, S2=3, S3=3, S4=3,
            E1=5, E2=3, E3=1, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        role_b = RoleScores(
            name="B", S1=3, S2=3, S3=3, S4=3,
            E1=3, E2=3, E3=3, E4=3, R1=3, R2=5, R3=1, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        result = calculator.compare(role_a, role_b)
        codes = [w.code for w in result.warnings]
        assert "effort_emotional_undervalued" in codes
        assert "responsibility_wellbeing_undervalued" in codes

    def test_warning_severity_is_valid(self, calculator):
        """Severity deve essere 'warning' o 'info'."""
        role = RoleScores(
            name="Test", S1=3, S2=3, S3=3, S4=3,
            E1=5, E2=3, E3=1, E4=3, R1=3, R2=3, R3=3, R4=3,
            W1=3, W2=3, W3=3, W4=3,
        )
        warnings = calculator.check_gender_warnings(role)
        for w in warnings:
            assert w.severity in ("warning", "info")
