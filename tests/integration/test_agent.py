"""Test di integrazione per l'Agent Router.

Richiede: GROQ_API_KEY configurata + vector DB inizializzato.
Migrato da: scripts/test_fase3_agent.py
"""

import pytest

from tests.integration.conftest import requires_api, requires_vectordb


@requires_api
@requires_vectordb
class TestAgentRouter:
    """Test end-to-end dell'agent con routing automatico."""

    @pytest.fixture(autouse=True, scope="class")
    def router(self):
        """Inizializza il router una volta per tutti i test della classe."""
        from src.agent.router import PayTransparencyRouter
        return PayTransparencyRouter()

    def test_normative_query(self, router):
        """Query normativa usa il RAG (query_directive)."""
        answer = router.ask(
            "Qual è la deadline di trasposizione della Direttiva EU 2023/970?"
        )
        assert answer is not None
        assert len(answer) > 50
        assert any(kw in answer.lower() for kw in ["2026", "trasposizione", "deadline"])

    def test_data_query(self, router):
        """Query dati usa analyze_pay_gap."""
        answer = router.ask(
            "Analizza il gender pay gap dal file data/demo/demo_employees.csv "
            "e dimmi quali categorie superano la soglia del 5%."
        )
        assert answer is not None
        assert len(answer) > 50
        assert any(kw in answer.lower() for kw in ["gap", "%", "categori"])

    def test_hybrid_query(self, router):
        """Query ibrida usa entrambi i tool."""
        answer = router.ask(
            "Il nostro dataset demo mostra un gap del 10% nella categoria Sales Mid. "
            "Cosa dice la Direttiva EU riguardo ai gap superiori al 5%? "
            "Quali azioni correttive sono richieste?"
        )
        assert answer is not None
        assert len(answer) > 100
