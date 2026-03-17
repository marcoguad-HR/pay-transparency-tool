"""Unit test per il template report markdown (WS2-B)."""

from src.analysis.gap_calculator import GapCalculator
from src.analysis.template_report import (
    generate_markdown_report,
    _gap_indicator,
    _format_disclaimer,
)


# ---------------------------------------------------------------------------
# Helper: LoadResult-like object per i test (senza caricare un vero file)
# ---------------------------------------------------------------------------

class _FakeLoadResult:
    def __init__(self, source_file="data/demo/demo_employees.csv",
                 n_employees=40, n_male=20, n_female=20):
        self.source_file = source_file
        self.n_employees = n_employees
        self.n_male = n_male
        self.n_female = n_female


class TestGapIndicator:
    """Verifica gli indicatori testuali per i diversi livelli di gap."""

    def test_nella_soglia(self):
        assert _gap_indicator(3.0) == "Nella soglia"

    def test_supera_il_5(self):
        assert _gap_indicator(7.5) == "Supera il 5%"

    def test_gap_significativo(self):
        assert _gap_indicator(12.0) == "Gap significativo"

    def test_invertito(self):
        assert _gap_indicator(-3.0) == "Invertito"

    def test_zero(self):
        assert _gap_indicator(0.0) == "Nella soglia"

    def test_soglia_esatta(self):
        assert _gap_indicator(5.0) == "Nella soglia"


class TestGenerateMarkdownReport:
    """Test del report completo."""

    def test_report_compliant(self, equal_pay_df):
        calc = GapCalculator(equal_pay_df)
        result = calc.full_analysis()
        lr = _FakeLoadResult()

        report = generate_markdown_report(result, lr)

        assert "Conforme" in report
        assert "Indicatori Principali" in report
        assert "Gap Medio" in report
        assert "Gap Mediano" in report
        assert "Prossimi Passi" in report
        assert "dataset demo" in report

    def test_report_non_compliant(self, sample_df):
        calc = GapCalculator(sample_df)
        result = calc.full_analysis()
        lr = _FakeLoadResult(n_employees=40)

        report = generate_markdown_report(result, lr)

        assert "Non Conforme" in report
        assert "Indicatori Principali" in report
        assert "Ruolo e Dipartimento" in report

    def test_report_minimal_data(self, minimal_df):
        """Report con dati minimi (senza department/level/bonus) non crasha."""
        calc = GapCalculator(minimal_df)
        result = calc.full_analysis()
        lr = _FakeLoadResult(n_employees=6, n_male=3, n_female=3)

        report = generate_markdown_report(result, lr)

        assert "Indicatori Principali" in report
        # Nessuna tabella categorie (mancano department/level)
        assert "Ruolo e Dipartimento" not in report

    def test_report_contains_markdown_tables(self, sample_df):
        """Il report contiene tabelle markdown valide."""
        calc = GapCalculator(sample_df)
        result = calc.full_analysis()
        lr = _FakeLoadResult()

        report = generate_markdown_report(result, lr)

        # Header tabella markdown
        assert "|------" in report
        assert "EUR" in report

    def test_report_has_quartiles(self, sample_df):
        """Il report include la sezione quartili."""
        calc = GapCalculator(sample_df)
        result = calc.full_analysis()
        lr = _FakeLoadResult()

        report = generate_markdown_report(result, lr)

        assert "Quartili Salariali" in report

    def test_report_has_bonus_gap(self, sample_df):
        """Il report include il bonus gap quando disponibile."""
        calc = GapCalculator(sample_df)
        result = calc.full_analysis()
        lr = _FakeLoadResult()

        report = generate_markdown_report(result, lr)

        assert "Bonus" in report

    def test_report_no_bonus_minimal(self, minimal_df):
        """Nessun crash se il bonus non c'e'."""
        calc = GapCalculator(minimal_df)
        result = calc.full_analysis()
        lr = _FakeLoadResult()

        report = generate_markdown_report(result, lr)

        assert "Gap Bonus" not in report


class TestFormatDisclaimer:
    """Verifica il disclaimer finale."""

    def test_demo_file_shows_disclaimer(self):
        text = _format_disclaimer("data/demo/demo_employees.csv")
        assert "dataset demo" in text
        assert "Analisi Dati" in text

    def test_custom_file_no_demo_disclaimer(self):
        text = _format_disclaimer("/tmp/paytool_abc123.csv")
        assert "dataset demo" not in text
        assert "server-side" in text


class TestChatRouting:
    """Verifica la logica di routing a 3 vie.

    Le keyword sets sono replicate qui per evitare di importare chat.py
    (che ha dipendenze pesanti: FastAPI, cache, analytics, ecc.).
    I valori devono restare allineati con src/web/api/chat.py.
    """

    _DATA_KEYWORDS = {
        "gap", "analisi dati", "retribuzion", "stipend", "salari",
        "bonus", "quartil", "csv", "excel", "dataset", "calcola",
        "dati retributiv", "pay gap", "gender gap",
    }
    _NORMATIVE_KEYWORDS = {
        "direttiva", "articolo", "art.", "normativa",
        "obbligh", "scadenz", "trasposizione", "sanzioni",
        "conforme", "compliance", "legge", "decreto",
    }

    @staticmethod
    def _needs_agent(text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in TestChatRouting._DATA_KEYWORDS)

    @staticmethod
    def _is_pure_data_query(text: str) -> bool:
        text_lower = text.lower()
        has_data = any(kw in text_lower for kw in TestChatRouting._DATA_KEYWORDS)
        has_normative = any(kw in text_lower for kw in TestChatRouting._NORMATIVE_KEYWORDS)
        return has_data and not has_normative

    def test_pure_data_queries(self):
        assert self._is_pure_data_query("calcola il gap") is True
        assert self._is_pure_data_query("analizza i dati retributivi") is True
        assert self._is_pure_data_query("qual e' il pay gap?") is True
        assert self._is_pure_data_query("mostra i quartili") is True
        assert self._is_pure_data_query("gender gap per categoria") is True

    def test_hybrid_queries_not_pure(self):
        assert self._is_pure_data_query("il gap e' conforme alla direttiva?") is False
        assert self._is_pure_data_query("gap retributivo e obblighi normativi") is False
        assert self._is_pure_data_query("il gap viola l'articolo 9?") is False
        assert self._is_pure_data_query("compliance del pay gap") is False

    def test_normative_queries_not_pure(self):
        assert self._is_pure_data_query("cosa dice l'art. 7?") is False
        assert self._is_pure_data_query("quali sono gli obblighi?") is False

    def test_needs_agent_consistent(self):
        # Pure data: _needs_agent=True, _is_pure_data=True → template path
        text = "calcola il gap"
        assert self._needs_agent(text) is True
        assert self._is_pure_data_query(text) is True

        # Hybrid: _needs_agent=True, _is_pure_data=False → agent path
        text = "il gap e' conforme alla direttiva?"
        assert self._needs_agent(text) is True
        assert self._is_pure_data_query(text) is False

        # Normativa: _needs_agent=False → RAG path
        text = "cosa dice l'articolo 7?"
        assert self._needs_agent(text) is False
