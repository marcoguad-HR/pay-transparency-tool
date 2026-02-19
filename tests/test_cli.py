"""Unit test per la CLI (con mock dei moduli pesanti)."""

import argparse
from unittest.mock import patch, MagicMock

import pytest

from src.cli.interface import CLI


class TestCLIDispatch:
    """Test del dispatch dei comandi."""

    def setup_method(self):
        self.cli = CLI()

    def test_dispatch_unknown_command(self, capsys):
        """Comando sconosciuto mostra errore."""
        args = argparse.Namespace(command="unknown")
        self.cli.dispatch(args)
        captured = capsys.readouterr()
        assert "sconosciuto" in captured.out.lower() or "unknown" in captured.out.lower()

    @patch("src.cli.interface.CLI._handle_analyze")
    def test_dispatch_routes_analyze(self, mock_handler):
        """Il comando analyze viene ruotato al handler corretto."""
        args = argparse.Namespace(command="analyze")
        self.cli.dispatch(args)
        mock_handler.assert_called_once_with(args)

    @patch("src.cli.interface.CLI._handle_query")
    def test_dispatch_routes_query(self, mock_handler):
        """Il comando query viene ruotato al handler corretto."""
        args = argparse.Namespace(command="query")
        self.cli.dispatch(args)
        mock_handler.assert_called_once_with(args)

    @patch("src.cli.interface.CLI._handle_ingest")
    def test_dispatch_routes_ingest(self, mock_handler):
        """Il comando ingest viene ruotato al handler corretto."""
        args = argparse.Namespace(command="ingest")
        self.cli.dispatch(args)
        mock_handler.assert_called_once_with(args)

    @patch("src.cli.interface.CLI._handle_agent")
    def test_dispatch_routes_agent(self, mock_handler):
        """Il comando agent viene ruotato al handler corretto."""
        args = argparse.Namespace(command="agent")
        self.cli.dispatch(args)
        mock_handler.assert_called_once_with(args)


class TestCLIAnalyze:
    """Test del handler analyze (il più testabile senza API)."""

    def setup_method(self):
        self.cli = CLI()

    def test_analyze_full_runs(self, demo_csv_path, capsys):
        """analyze --type full produce output."""
        args = argparse.Namespace(
            command="analyze",
            file_path=demo_csv_path,
            analysis_type="full",
        )
        self.cli.dispatch(args)
        captured = capsys.readouterr()
        assert "GENDER PAY GAP REPORT" in captured.out

    def test_analyze_compliance_runs(self, demo_csv_path, capsys):
        """analyze --type compliance produce output."""
        args = argparse.Namespace(
            command="analyze",
            file_path=demo_csv_path,
            analysis_type="compliance",
        )
        self.cli.dispatch(args)
        captured = capsys.readouterr()
        assert "Compliance" in captured.out or "COMPLIANT" in captured.out

    def test_analyze_bad_file(self, capsys):
        """analyze con file inesistente mostra errore."""
        args = argparse.Namespace(
            command="analyze",
            file_path="nonexistent.csv",
            analysis_type="full",
        )
        self.cli.dispatch(args)
        captured = capsys.readouterr()
        assert "Errore" in captured.out or "errore" in captured.out


class TestCLIErrorHandling:
    """Test della gestione errori."""

    def setup_method(self):
        self.cli = CLI()

    @patch("src.cli.interface.CLI._handle_ingest", side_effect=Exception("test error"))
    def test_exception_shows_error(self, mock_handler, capsys):
        """Eccezioni vengono catturate e mostrate all'utente."""
        args = argparse.Namespace(command="ingest")
        self.cli.dispatch(args)
        captured = capsys.readouterr()
        assert "Errore" in captured.out
