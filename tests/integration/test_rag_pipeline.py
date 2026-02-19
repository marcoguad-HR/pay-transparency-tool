"""Test di integrazione per il pipeline RAG.

Richiede: GROQ_API_KEY configurata + vector DB inizializzato.
Migrato da: scripts/test_fase1_completo.py
"""

import pytest

from tests.integration.conftest import requires_api, requires_vectordb


# 10 domande con keyword attese (dalla test suite originale)
RAG_TEST_CASES = [
    pytest.param(
        "What is the transposition deadline for the directive?",
        ["7 June 2026", "2026"],
        id="deadline-art34",
    ),
    pytest.param(
        "What information must employers report about the gender pay gap?",
        ["gender pay gap", "complementary", "variable", "median"],
        id="reporting-art9",
    ),
    pytest.param(
        "What is the threshold for joint pay assessment?",
        ["5%", "five", "percent"],
        id="threshold-art10",
    ),
    pytest.param(
        "What rights do job applicants have regarding pay transparency?",
        ["applicant", "initial pay", "range"],
        id="applicant-rights-art5",
    ),
    pytest.param(
        "What is the role of workers' representatives in pay transparency?",
        ["representative", "worker"],
        id="workers-representatives",
    ),
    pytest.param(
        "What are the penalties for non-compliance with the directive?",
        ["penalties", "fine", "sanction", "effective", "proportionate", "dissuasive"],
        id="penalties-art23",
    ),
    pytest.param(
        "What does the directive say about the burden of proof?",
        ["burden of proof", "respondent", "employer"],
        id="burden-of-proof-art18",
    ),
    pytest.param(
        "How does the directive define equal work or work of equal value?",
        ["equal work", "equal value", "criteria", "skills"],
        id="equal-value-art4",
    ),
    pytest.param(
        "What are the specific fines for non-compliance in Italy?",
        ["not found", "non ho trovato", "not available", "Member States"],
        id="trap-question-italy",
    ),
    pytest.param(
        "When was this directive adopted and by whom?",
        ["10 May 2023", "2023", "European Parliament", "Council"],
        id="adoption-date-art37",
    ),
]


@requires_api
@requires_vectordb
class TestRAGPipeline:
    """Test del pipeline RAG end-to-end."""

    @pytest.fixture(autouse=True, scope="class")
    def generator(self):
        """Inizializza il generator una volta per tutti i test della classe."""
        from src.rag.generator import RAGGenerator
        return RAGGenerator()

    @pytest.mark.parametrize("query,expected_keywords", RAG_TEST_CASES)
    def test_rag_answer(self, generator, query, expected_keywords):
        """Verifica che la risposta contenga almeno una keyword attesa."""
        response = generator.generate(query, top_k=5, verify=True)
        answer_lower = response.answer.lower()
        found = any(kw.lower() in answer_lower for kw in expected_keywords)
        assert found, (
            f"Nessuna keyword trovata in risposta.\n"
            f"Attese: {expected_keywords}\n"
            f"Risposta: {response.answer[:200]}"
        )

    @pytest.mark.parametrize("query,expected_keywords", RAG_TEST_CASES)
    def test_rag_confidence(self, generator, query, expected_keywords):
        """Verifica che la confidenza sia ragionevole (>= 0.5)."""
        response = generator.generate(query, top_k=5)
        assert response.confidence >= 0.5, (
            f"Confidenza troppo bassa: {response.confidence:.0%}"
        )
