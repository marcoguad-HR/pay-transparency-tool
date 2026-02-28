#!/usr/bin/env python3
"""
verify_imports.py -- Smoke test post-install.

Verifica che tutti gli import critici funzionino senza bloccarsi.
Ogni import gira in un processo separato con timeout per rilevare hang.

Uso:
    python scripts/verify_imports.py

Exit code 0 = tutto OK, 1 = almeno un fallimento.
"""

import importlib
import multiprocessing
import sys
import time

# (module_path, friendly_name, timeout_seconds)
CRITICAL_IMPORTS = [
    ("anyio", "anyio", 5),
    ("httpx", "httpx", 5),
    ("httpcore", "httpcore", 5),
    ("openai", "openai", 10),
    ("fastapi", "FastAPI", 5),
    ("uvicorn", "uvicorn", 5),
    ("fastembed", "FastEmbed", 15),
    ("datapizza.clients.openai", "datapizza OpenAI client", 10),
    ("datapizza.agents", "datapizza Agent", 10),
    ("datapizza.vectorstores.qdrant", "datapizza Qdrant", 10),
    ("rich", "Rich", 5),
    ("yaml", "PyYAML", 5),
    ("pandas", "pandas", 10),
    ("fitz", "PyMuPDF", 5),
]


def _try_import(module_path, result_queue):
    """Worker: importa il modulo e segnala il risultato."""
    try:
        importlib.import_module(module_path)
        result_queue.put(("ok", None))
    except Exception as e:
        result_queue.put(("error", str(e)))


def verify_import(module_path, name, timeout_sec):
    """Testa un singolo import con timeout. Ritorna True se OK."""
    queue = multiprocessing.Queue()
    proc = multiprocessing.Process(target=_try_import, args=(module_path, queue))
    proc.start()
    proc.join(timeout=timeout_sec)

    if proc.is_alive():
        proc.terminate()
        proc.join(2)
        print(f"  HANG  {name} ({module_path}) -- non completato in {timeout_sec}s")
        return False

    if queue.empty():
        print(f"  FAIL  {name} ({module_path}) -- processo terminato senza risultato")
        return False

    status, error = queue.get()
    if status == "ok":
        print(f"  OK    {name}")
        return True
    else:
        print(f"  ERROR {name} ({module_path}) -- {error}")
        return False


def main():
    print("=== Verifica Import ===\n")
    start = time.time()
    results = []

    for module_path, name, timeout_sec in CRITICAL_IMPORTS:
        ok = verify_import(module_path, name, timeout_sec)
        results.append((name, ok))

    elapsed = time.time() - start
    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    print(f"\n=== Risultato: {passed}/{total} OK ({elapsed:.1f}s) ===")

    if passed < total:
        failed = [name for name, ok in results if not ok]
        print(f"\nFalliti: {', '.join(failed)}")
        print("\nFix consigliato: bash setup.sh --clean")
        sys.exit(1)
    else:
        print("\nTutti gli import OK. Ambiente sano.")
        sys.exit(0)


if __name__ == "__main__":
    main()
