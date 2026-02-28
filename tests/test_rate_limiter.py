"""Test per il modulo rate_limiter — retry automatico su HTTP 429."""

from unittest.mock import MagicMock, patch

import pytest

from src.utils.rate_limiter import invoke_with_retry, RateLimitError


class TestInvokeWithRetry:
    """Test per invoke_with_retry()."""

    def test_successo_al_primo_tentativo(self):
        """Se client.invoke() funziona subito, restituisce il risultato."""
        client = MagicMock()
        client.invoke.return_value = MagicMock(text="risposta ok")

        result = invoke_with_retry(client, "domanda")

        assert result.text == "risposta ok"
        assert client.invoke.call_count == 1

    @patch("src.utils.rate_limiter.time.sleep")
    def test_retry_su_429_poi_successo(self, mock_sleep):
        """Se il primo tentativo fallisce con 429, ritenta e riesce."""
        client = MagicMock()
        client.invoke.side_effect = [
            Exception("HTTP 429 Too Many Requests"),
            MagicMock(text="risposta ok"),
        ]

        result = invoke_with_retry(client, "domanda")

        assert result.text == "risposta ok"
        assert client.invoke.call_count == 2
        mock_sleep.assert_called_once_with(2.0)  # BASE_DELAY

    @patch("src.utils.rate_limiter.time.sleep")
    def test_retry_multipli_con_backoff(self, mock_sleep):
        """Verifica exponential backoff: 2s, 4s, poi successo."""
        client = MagicMock()
        client.invoke.side_effect = [
            Exception("rate limit exceeded"),
            Exception("429 error"),
            MagicMock(text="finalmente"),
        ]

        result = invoke_with_retry(client, "domanda")

        assert result.text == "finalmente"
        assert client.invoke.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2.0)   # 2^0 * 2
        mock_sleep.assert_any_call(4.0)   # 2^1 * 2

    @patch("src.utils.rate_limiter.time.sleep")
    def test_rate_limit_error_dopo_max_retry(self, mock_sleep):
        """Se tutti i retry falliscono, solleva RateLimitError."""
        client = MagicMock()
        client.invoke.side_effect = Exception("Too Many Requests 429")

        with pytest.raises(RateLimitError, match="Rate limit Groq superato"):
            invoke_with_retry(client, "domanda", max_retries=2)

        # 1 tentativo iniziale + 2 retry = 3 chiamate totali
        assert client.invoke.call_count == 3
        assert mock_sleep.call_count == 2

    def test_errore_non_429_non_ritentato(self):
        """Errori non legati a rate limit vengono rilanciati immediatamente."""
        client = MagicMock()
        client.invoke.side_effect = ValueError("errore generico")

        with pytest.raises(ValueError, match="errore generico"):
            invoke_with_retry(client, "domanda")

        assert client.invoke.call_count == 1

    def test_errore_connessione_non_ritentato(self):
        """ConnectionError non viene confuso con un rate limit."""
        client = MagicMock()
        client.invoke.side_effect = ConnectionError("server unreachable")

        with pytest.raises(ConnectionError):
            invoke_with_retry(client, "domanda")

        assert client.invoke.call_count == 1

    @patch("src.utils.rate_limiter.time.sleep")
    def test_varianti_messaggio_429(self, mock_sleep):
        """Rileva rate limit da formati diversi di messaggio errore."""
        varianti = [
            "HTTP 429",
            "rate limit exceeded",
            "Too Many Requests",
            "rate_limit_error",
        ]
        for msg in varianti:
            client = MagicMock()
            client.invoke.side_effect = [
                Exception(msg),
                MagicMock(text="ok"),
            ]
            result = invoke_with_retry(client, "domanda")
            assert result.text == "ok", f"Non ha ritentato per messaggio: {msg}"
