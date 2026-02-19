"""
Test Fase 3 — Agent Integrato.

Testa i 3 tipi di query:
1. Normativa pura → deve usare solo query_directive (RAG)
2. Dati puri → deve usare solo analyze_pay_gap
3. Ibrida → deve usare entrambi

Nota: il test richiede che l'ingestion sia già stata eseguita
(vector DB con i chunk della Direttiva EU).
"""

import time
from src.agent.router import PayTransparencyRouter


def test_query(router, query_type, question):
    """Esegue una singola query e stampa il risultato."""
    print(f"\n{'=' * 70}")
    print(f"[{query_type}] {question}")
    print("=" * 70)

    start = time.time()
    answer = router.ask(question)
    elapsed = time.time() - start

    print(f"\nRISPOSTA ({elapsed:.1f}s):")
    print("-" * 70)
    print(answer)
    print("-" * 70)

    return answer


def main():
    print("=" * 70)
    print("TEST FASE 3 — Agent Integrato Pay Transparency")
    print("=" * 70)

    # Inizializza il router (una sola volta, riutilizzato per tutte le query)
    print("\nInizializzazione agent...")
    router = PayTransparencyRouter()
    print("Agent pronto!\n")

    # --- Test 1: Query NORMATIVA (solo RAG) ---
    test_query(
        router,
        "NORMATIVA",
        "Qual è la deadline di trasposizione della Direttiva EU 2023/970?"
    )

    # --- Test 2: Query DATI (solo analisi) ---
    test_query(
        router,
        "DATI",
        "Analizza il gender pay gap dal file data/demo/demo_employees.csv e dimmi quali categorie superano la soglia del 5%."
    )

    # --- Test 3: Query IBRIDA (normativa + dati) ---
    test_query(
        router,
        "IBRIDA",
        "Il nostro dataset demo mostra un gap del 10% nella categoria Sales Mid. Cosa dice la Direttiva EU riguardo ai gap superiori al 5%? Quali azioni correttive sono richieste?"
    )

    print("\n" + "=" * 70)
    print("TEST FASE 3 COMPLETATO")
    print("=" * 70)


if __name__ == "__main__":
    main()
