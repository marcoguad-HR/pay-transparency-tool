"""
Test set completo Fase 1 — 10 domande sulla Direttiva EU 2023/970.

Verifica che il pipeline RAG (ingestion → retriever → generator → anti-hallucination)
risponda correttamente ad almeno 8 domande su 10.

Esegui con:
    cd ~/Desktop/pay-transparency-tool
    source .venv/bin/activate
    python scripts/test_fase1_completo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.generator import RAGGenerator
from src.utils.logger import get_logger

logger = get_logger("test_fase1")

# 10 domande con risposte attese (per validazione manuale)
TEST_QUESTIONS = [
    {
        "query": "What is the transposition deadline for the directive?",
        "expected_keywords": ["7 June 2026", "2026"],
        "description": "Deadline trasposizione — Art. 34",
    },
    {
        "query": "What information must employers report about the gender pay gap?",
        "expected_keywords": ["gender pay gap", "complementary", "variable", "median"],
        "description": "Obblighi reporting — Art. 9",
    },
    {
        "query": "What is the threshold for joint pay assessment?",
        "expected_keywords": ["5%", "five", "percent"],
        "description": "Soglia valutazione congiunta — Art. 10",
    },
    {
        "query": "What rights do job applicants have regarding pay transparency?",
        "expected_keywords": ["applicant", "initial pay", "range"],
        "description": "Diritti candidati — Art. 5",
    },
    {
        "query": "What is the role of workers' representatives in pay transparency?",
        "expected_keywords": ["representative", "worker"],
        "description": "Ruolo rappresentanti lavoratori",
    },
    {
        "query": "What are the penalties for non-compliance with the directive?",
        "expected_keywords": ["penalties", "fine", "sanction", "effective", "proportionate", "dissuasive"],
        "description": "Sanzioni — Art. 23",
    },
    {
        "query": "What does the directive say about the burden of proof?",
        "expected_keywords": ["burden of proof", "respondent", "employer"],
        "description": "Onere della prova — Art. 18",
    },
    {
        "query": "How does the directive define equal work or work of equal value?",
        "expected_keywords": ["equal work", "equal value", "criteria", "skills"],
        "description": "Definizione lavoro uguale valore — Art. 4",
    },
    {
        "query": "What are the specific fines for non-compliance in Italy?",
        "expected_keywords": ["not found", "non ho trovato", "not available", "Member States"],
        "description": "TRABOCCHETTO — info su Italia non presente",
    },
    {
        "query": "When was this directive adopted and by whom?",
        "expected_keywords": ["10 May 2023", "2023", "European Parliament", "Council"],
        "description": "Data adozione — Art. 37",
    },
]


def check_keywords(answer: str, keywords: list[str]) -> bool:
    """Controlla se almeno una keyword è presente nella risposta."""
    answer_lower = answer.lower()
    return any(kw.lower() in answer_lower for kw in keywords)


def main():
    logger.info("=== TEST SET FASE 1 — 10 DOMANDE ===\n")

    generator = RAGGenerator()

    passed = 0
    failed = 0
    results_summary = []

    for i, test in enumerate(TEST_QUESTIONS, 1):
        query = test["query"]
        expected = test["expected_keywords"]
        desc = test["description"]

        print(f"\n{'─'*60}")
        print(f"[{i}/10] {desc}")
        print(f"Domanda: {query}")

        response = generator.generate(query, top_k=5, verify=True)

        # Controlla se la risposta contiene almeno una keyword attesa
        has_keywords = check_keywords(response.answer, expected)

        # La risposta è "buona" se:
        # - Contiene le keyword attese
        # - È verificata O ha confidenza >= 50%
        is_good = has_keywords and (response.verified or response.confidence >= 0.5)

        status = "PASS" if is_good else "FAIL"
        if is_good:
            passed += 1
        else:
            failed += 1

        verified_str = "SI" if response.verified else ("NO" if response.verified is False else "?")

        print(f"Risposta: {response.answer[:150]}...")
        print(f"Confidenza: {response.confidence:.0%} | Verificata: {verified_str} | {status}")

        results_summary.append({
            "n": i,
            "desc": desc,
            "status": status,
            "confidence": response.confidence,
            "verified": response.verified,
        })

    # Riepilogo finale
    print(f"\n{'='*60}")
    print(f"RIEPILOGO: {passed}/10 PASS, {failed}/10 FAIL")
    print(f"{'='*60}")

    for r in results_summary:
        v = "V" if r["verified"] else ("X" if r["verified"] is False else "?")
        print(f"  [{r['status']}] {r['n']:2d}. {r['desc']:<50} "
              f"conf={r['confidence']:.0%} ver={v}")

    target = 8
    if passed >= target:
        print(f"\nOBIETTIVO RAGGIUNTO: {passed}/{10} >= {target}/{10}")
    else:
        print(f"\nOBIETTIVO NON RAGGIUNTO: {passed}/{10} < {target}/{10}")

    logger.info("=== TEST COMPLETATO ===")


if __name__ == "__main__":
    main()
