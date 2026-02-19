"""Unit test per PayGapReport."""

from io import StringIO

import pytest
from rich.console import Console

from src.analysis.gap_calculator import GapCalculator
from src.analysis.report import PayGapReport


class TestPayGapReport:
    """Verifica che il report venga generato senza errori."""

    def _capture_report(self, result) -> str:
        """Cattura l'output del report in una stringa."""
        report = PayGapReport(result)
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        # Sovrascriviamo il modulo console per catturare l'output
        import src.analysis.report as report_module
        original = report_module.console
        report_module.console = console
        try:
            report.print_full_report()
        finally:
            report_module.console = original
        return buf.getvalue()

    def test_full_report_renders(self, sample_df):
        """Il report completo viene generato senza errori."""
        calc = GapCalculator(sample_df)
        result = calc.full_analysis()
        output = self._capture_report(result)
        assert "GENDER PAY GAP REPORT" in output
        assert "Gap Retributivo Complessivo" in output

    def test_report_shows_compliance_status(self, sample_df):
        """Il report mostra lo stato di compliance."""
        calc = GapCalculator(sample_df)
        result = calc.full_analysis()
        output = self._capture_report(result)
        assert "COMPLIANT" in output or "NON COMPLIANT" in output

    def test_report_shows_quartiles(self, sample_df):
        """Il report include la sezione quartili."""
        calc = GapCalculator(sample_df)
        result = calc.full_analysis()
        output = self._capture_report(result)
        assert "Quartil" in output

    def test_report_with_equal_pay(self, equal_pay_df):
        """Report con parità di genere non crasha."""
        calc = GapCalculator(equal_pay_df)
        result = calc.full_analysis()
        output = self._capture_report(result)
        assert "GENDER PAY GAP REPORT" in output

    def test_report_minimal_data(self, minimal_df):
        """Report con dati minimi (senza department/level/bonus) non crasha."""
        calc = GapCalculator(minimal_df)
        result = calc.full_analysis()
        output = self._capture_report(result)
        assert "GENDER PAY GAP REPORT" in output
