"""
Rate Limiter — Gestione del rate limit Groq API con retry automatico.

Il free tier di Groq ha limiti stretti:
- 14.400 richieste/giorno
- 30 richieste/minuto
- 6.000 token/minuto

Quando i limiti vengono superati, l'API restituisce HTTP 429.
Questo modulo fornisce:
- invoke_with_retry(): wrapper per client.invoke() con exponential backoff
- RateLimitError: eccezione quando tutti i retry sono esauriti

Perche' un modulo dedicato?
Senza questo, ogni file che chiama Groq (generator, anti_hallucination, agent)
dovrebbe duplicare la stessa logica try/except. Centralizzando qui,
ogni call site cambia solo: client.invoke(prompt) -> invoke_with_retry(client, prompt)
"""

import re
import time

from src.utils.logger import get_logger

logger = get_logger("utils.rate_limiter")

# --- Configurazione retry ---
MAX_RETRIES = 1       # Un solo retry dopo MAX_DELAY (TPM window ~60s)
BASE_DELAY = 1.0      # Non usato nel fallback, mantenuto per compatibilità
MAX_DELAY = 70.0      # Attesa fallback (>60s per coprire la finestra TPM)


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


class RateLimitError(Exception):
    """
    Eccezione sollevata quando tutti i retry per rate limit sono esauriti.

    Usata dalla CLI per mostrare un messaggio user-friendly invece di
    un traceback tecnico incomprensibile.
    """
    pass


def invoke_with_retry(client, prompt: str, max_retries: int = MAX_RETRIES):
    """
    Chiama client.invoke(prompt) con retry automatico su HTTP 429.

    Strategia: exponential backoff (1s, 2s, 4s, ...) fino a MAX_DELAY.

    Args:
        client: istanza di datapizza OpenAIClient (Groq)
        prompt: il prompt da inviare al LLM
        max_retries: numero massimo di retry (default: 3)

    Returns:
        L'oggetto response da client.invoke()

    Raises:
        RateLimitError: quando tutti i retry sono esauriti
        Exception: per errori non legati al rate limit (propagati immediatamente)

    Esempio:
        from src.utils.rate_limiter import invoke_with_retry

        response = invoke_with_retry(self.client, user_prompt)
        answer = response.text
    """
    for attempt in range(max_retries + 1):
        try:
            return client.invoke(prompt)
        except Exception as e:
            error_str = str(e).lower()

            # Rileva errori di rate limit da vari formati possibili
            is_rate_limit = (
                "429" in error_str
                or "rate limit" in error_str
                or "too many requests" in error_str
                or "rate_limit" in error_str
            )

            if not is_rate_limit:
                # Non e' un rate limit — rilancia subito senza retry
                raise

            if attempt == max_retries:
                # Ultimo tentativo fallito — solleva RateLimitError
                raise RateLimitError(
                    "Rate limit Groq superato dopo "
                    f"{max_retries} tentativi. "
                    "Attendi qualche minuto e riprova. "
                    "Free tier: 30 req/min, 14.400 req/giorno."
                ) from e

            # Usa il retry time suggerito da Groq se disponibile,
            # altrimenti exponential backoff standard.
            groq_wait = _parse_retry_after(error_str)
            delay = groq_wait if groq_wait else MAX_DELAY
            logger.warning(
                f"Rate limit raggiunto (tentativo {attempt + 1}/{max_retries + 1}). "
                f"Retry tra {delay:.1f}s..."
                + (" [Groq suggested]" if groq_wait else " [backoff]")
            )
            time.sleep(delay)
