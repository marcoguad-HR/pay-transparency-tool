"""Test per il routing help/onboarding in chat.py."""

import pytest
from src.web.api.chat import _is_help_query, _HELP_RESPONSE


class TestHelpRouting:
    """Verifica che le query di aiuto vengano intercettate correttamente."""

    @pytest.mark.parametrize("query", [
        "come caricare i dati?",
        "come si usa questo tool?",
        "come funziona l'analisi?",
        "dove carico il file CSV?",
        "come faccio a fare l'analisi retributiva?",
        "intendo in questo tool",
        "come utilizzo il tool locale?",
        "ho bisogno di aiuto",
        "ci sono istruzioni?",
        "come si carica un file?",
        "dove posso caricare il mio CSV?",
        "guida all'uso",
        "tutorial per l'upload",
        "come carico i dati retributivi?",
        "vorrei fare un upload",
        "come funziona il caricamento?",
    ])
    def test_help_queries_detected(self, query):
        assert _is_help_query(query), f"Query non rilevata come help: '{query}'"

    @pytest.mark.parametrize("query", [
        "Cosa dice la Direttiva EU 2023/970?",
        "Quali sono gli obblighi di reporting?",
        "Qual è la scadenza per la trasposizione?",
        "Cos'è il gender pay gap?",
        "Quali sanzioni prevede la Direttiva?",
        "Il gap del 7% è conforme alla normativa?",
        "Articolo 9 della Direttiva",
    ])
    def test_normative_queries_not_help(self, query):
        assert not _is_help_query(query), f"Query normativa classificata come help: '{query}'"

    def test_help_response_contains_key_info(self):
        """La risposta help deve contenere le informazioni essenziali."""
        assert "Analisi Dati" in _HELP_RESPONSE
        assert "gender" in _HELP_RESPONSE
        assert "base_salary" in _HELP_RESPONSE
        assert "CSV" in _HELP_RESPONSE
        assert "tool locale" in _HELP_RESPONSE or "offline" in _HELP_RESPONSE
        assert "template" in _HELP_RESPONSE.lower()

    def test_help_response_not_empty(self):
        assert len(_HELP_RESPONSE) > 100
