"""
Retry — Decorator/wrapper per chiamate a Groq con exponential backoff.

Backoff: 1s → 2s → 4s (3 retry massimi).
Retry SOLO su HTTP 429 (Rate Limit). Tutti gli altri errori propagano subito.

Questo modulo affianca rate_limiter.py (che usa BASE_DELAY=1.0s dopo il
refactor). Se vuoi wrappare una singola funzione invece di un client invoke(),
usa il decorator @with_retry.

Esempi:
    # Uso diretto (wrapper su client Groq):
    response = invoke_with_retry(client, prompt)

    # Uso come decorator:
    @with_retry
    def call_groq(client, prompt):
        return client.invoke(prompt)
"""

import functools
import re
import time

from src.utils.logger import get_logger

logger = get_logger("utils.retry")

# --- Configurazione ---
_MAX_RETRIES = 1     # Un solo retry dopo _MAX_DELAY (TPM window ~60s)
_BASE_DELAY = 1.0    # Non usato nel fallback, mantenuto per compatibilità
_MAX_DELAY = 70.0    # tetto massimo (>60s per coprire la finestra TPM di Groq)


def _parse_retry_after(error_str: str) -> float | None:
    """
    Estrae il tempo di attesa suggerito da Groq dall'errore 429.

    Groq include nei messaggi di rate limit la riga:
        'Please try again in 10.47s'
    Parsando questo valore usiamo esattamente il tempo necessario invece
    di un backoff fisso che potrebbe essere troppo breve (TPM window ~60s).
    """
    match = re.search(r"try again in (\d+(?:\.\d+)?)s", error_str, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.0  # +1s di margine di sicurezza
    return None

# Messaggio user-friendly quando tutti i retry sono esauriti
_EXHAUSTED_MSG = (
    "Il servizio è temporaneamente sovraccarico. "
    "Riprova tra qualche secondo."
)


def _is_rate_limit(exc: Exception) -> bool:
    """True se l'eccezione è un HTTP 429 / Rate Limit Groq."""
    err = str(exc).lower()
    return (
        "429" in err
        or "rate limit" in err
        or "too many requests" in err
        or "rate_limit" in err
    )


def call_with_retry(fn, *args, max_retries: int = _MAX_RETRIES, **kwargs):
    """
    Chiama fn(*args, **kwargs) con retry su rate limit.

    Args:
        fn:          callable da invocare
        *args:       argomenti posizionali per fn
        max_retries: numero massimo di retry (default: 3)
        **kwargs:    argomenti keyword per fn

    Returns:
        Il valore di ritorno di fn.

    Raises:
        RateLimitError: quando tutti i retry sono esauriti.
        Exception:      per errori non legati al rate limit (propagati subito).
    """
    from src.utils.rate_limiter import RateLimitError

    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if not _is_rate_limit(e):
                raise

            if attempt == max_retries:
                raise RateLimitError(_EXHAUSTED_MSG) from e

            groq_wait = _parse_retry_after(str(e).lower())
            delay = groq_wait if groq_wait else _MAX_DELAY
            logger.warning(
                f"Rate limit (tentativo {attempt + 1}/{max_retries + 1}). "
                f"Retry tra {delay:.1f}s... [{type(e).__name__}]"
                + (" [Groq suggested]" if groq_wait else " [backoff]")
            )
            time.sleep(delay)


def with_retry(fn=None, *, max_retries: int = _MAX_RETRIES):
    """
    Decorator: wrappa una funzione con retry su rate limit.

    Uso:
        @with_retry
        def chiama_groq(client, prompt):
            return client.invoke(prompt)

        # oppure con parametri:
        @with_retry(max_retries=5)
        def chiama_groq(client, prompt):
            return client.invoke(prompt)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return call_with_retry(func, *args, max_retries=max_retries, **kwargs)
        return wrapper

    if fn is not None:
        return decorator(fn)
    return decorator
