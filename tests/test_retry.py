"""
Test per src/utils/retry.py — call_with_retry e @with_retry decorator.

Copertura:
- Successo al primo tentativo
- Retry su 429 poi successo
- Backoff exponential: 1s, 2s, 4s
- RateLimitError dopo max_retries esauriti
- Non ritenta su errori non-429
- Decorator @with_retry funziona correttamente
"""

from unittest.mock import MagicMock, call, patch

import pytest

from src.utils.rate_limiter import RateLimitError
from src.utils.retry import call_with_retry, with_retry, _parse_retry_after


# ===========================================================================
# _parse_retry_after
# ===========================================================================

class TestParseRetryAfter:
    def test_parsa_secondi_interi(self):
        assert _parse_retry_after("please try again in 30s") == pytest.approx(31.0)

    def test_parsa_secondi_decimali(self):
        assert _parse_retry_after("Please try again in 10.47s. Visit ...") == pytest.approx(11.47)

    def test_case_insensitive(self):
        assert _parse_retry_after("PLEASE TRY AGAIN IN 5S") == pytest.approx(6.0)

    def test_aggiunge_margine_di_sicurezza(self):
        assert _parse_retry_after("try again in 20s") == pytest.approx(21.0)

    def test_nessuna_indicazione_ritorna_none(self):
        assert _parse_retry_after("HTTP 429 Too Many Requests") is None

    def test_stringa_vuota_ritorna_none(self):
        assert _parse_retry_after("") is None

    @patch("src.utils.retry.time.sleep")
    def test_usa_groq_retry_after_invece_del_backoff(self, mock_sleep):
        """Se Groq indica il retry time, usa quello invece del backoff fisso."""
        fn = MagicMock(side_effect=[
            Exception("rate limit exceeded. Please try again in 15.5s. Visit groq.com"),
            "risposta ok",
        ])
        result = call_with_retry(fn)
        assert result == "risposta ok"
        mock_sleep.assert_called_once_with(pytest.approx(16.5))  # 15.5 + 1.0 margine


# ===========================================================================
# call_with_retry
# ===========================================================================

class TestCallWithRetry:
    def test_successo_al_primo_tentativo(self):
        """Funzione che ha successo subito → chiamata una volta sola."""
        fn = MagicMock(return_value="ok")
        result = call_with_retry(fn, "arg1", kw="val")
        assert result == "ok"
        fn.assert_called_once_with("arg1", kw="val")

    @patch("src.utils.retry.time.sleep")
    def test_retry_su_429_poi_successo(self, mock_sleep):
        """Fallisce con 429 al 1° tentativo, riesce al 2°."""
        fn = MagicMock(side_effect=[
            Exception("HTTP 429 Too Many Requests"),
            "risposta ok",
        ])

        result = call_with_retry(fn)

        assert result == "risposta ok"
        assert fn.call_count == 2
        mock_sleep.assert_called_once_with(1.0)  # backoff: 1s

    @patch("src.utils.retry.time.sleep")
    def test_backoff_exponential_1_2_4(self, mock_sleep):
        """Verifica backoff esatto: 1s, 2s, 4s su 3 retry."""
        fn = MagicMock(side_effect=[
            Exception("rate limit"),
            Exception("429"),
            Exception("Too Many Requests"),
            "successo",
        ])

        result = call_with_retry(fn, max_retries=3)

        assert result == "successo"
        assert fn.call_count == 4
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(1.0)   # 1^0 * 1 → 1s
        mock_sleep.assert_any_call(2.0)   # 2^1 * 1 → 2s
        mock_sleep.assert_any_call(4.0)   # 2^2 * 1 → 4s

    @patch("src.utils.retry.time.sleep")
    def test_rate_limit_error_dopo_max_retries(self, mock_sleep):
        """Tutti i retry esauriti → RateLimitError con messaggio user-friendly."""
        fn = MagicMock(side_effect=Exception("429"))

        with pytest.raises(RateLimitError) as exc_info:
            call_with_retry(fn, max_retries=3)

        assert "temporaneamente sovraccarico" in str(exc_info.value).lower() or \
               "sovraccarico" in str(exc_info.value)
        assert fn.call_count == 4  # 1 iniziale + 3 retry

    def test_no_retry_su_errore_generico(self):
        """ValueError o altri errori non-429 non vengono ritentati."""
        # NOTA: il messaggio non deve contenere "rate", "limit", "429" altrimenti
        # _is_rate_limit() lo classificherebbe erroneamente come 429.
        fn = MagicMock(side_effect=ValueError("errore di validazione campo"))

        with pytest.raises(ValueError, match="errore di validazione campo"):
            call_with_retry(fn)

        fn.assert_called_once()

    def test_no_retry_su_connection_error(self):
        """ConnectionError non viene ritentato (non è un 429)."""
        fn = MagicMock(side_effect=ConnectionError("server unreachable"))

        with pytest.raises(ConnectionError):
            call_with_retry(fn)

        fn.assert_called_once()

    @patch("src.utils.retry.time.sleep")
    def test_varianti_messaggio_429(self, mock_sleep):
        """Rileva rate limit da formati diversi di messaggio."""
        varianti = [
            "HTTP 429",
            "rate limit exceeded",
            "Too Many Requests",
            "rate_limit_error",
        ]
        for msg in varianti:
            fn = MagicMock(side_effect=[Exception(msg), "ok"])
            result = call_with_retry(fn)
            assert result == "ok", f"Non ha ritentato per messaggio: {msg}"

    @patch("src.utils.retry.time.sleep")
    def test_max_retries_custom(self, mock_sleep):
        """Rispetta max_retries passato come argomento."""
        fn = MagicMock(side_effect=Exception("429"))

        with pytest.raises(RateLimitError):
            call_with_retry(fn, max_retries=1)

        assert fn.call_count == 2  # 1 iniziale + 1 retry
        assert mock_sleep.call_count == 1

    def test_argomenti_passati_correttamente(self):
        """Gli argomenti vengono passati alla funzione wrapped."""
        fn = MagicMock(return_value="ok")
        call_with_retry(fn, "pos1", "pos2", key1="val1", key2="val2")
        fn.assert_called_once_with("pos1", "pos2", key1="val1", key2="val2")


# ===========================================================================
# @with_retry decorator
# ===========================================================================

class TestWithRetryDecorator:
    def test_decorator_senza_parametri(self):
        """@with_retry senza parentesi funziona correttamente."""
        @with_retry
        def mia_funzione(x):
            return x * 2

        assert mia_funzione(5) == 10

    @patch("src.utils.retry.time.sleep")
    def test_decorator_ritenta_su_429(self, mock_sleep):
        """Il decorator wrappa la funzione con retry su 429."""
        call_count = [0]

        @with_retry
        def chiama_groq():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("HTTP 429")
            return "risposta"

        result = chiama_groq()
        assert result == "risposta"
        assert call_count[0] == 2

    def test_decorator_con_max_retries(self):
        """@with_retry(max_retries=1) rispetta il parametro."""
        @with_retry(max_retries=1)
        def sempre_rate_limit():
            raise Exception("429")

        with pytest.raises(RateLimitError):
            sempre_rate_limit()

    def test_decorator_preserva_nome_funzione(self):
        """@with_retry preserva __name__ e __doc__ della funzione originale."""
        @with_retry
        def mia_funzione():
            """Docstring originale."""
            return "ok"

        assert mia_funzione.__name__ == "mia_funzione"
        assert mia_funzione.__doc__ == "Docstring originale."

    def test_decorator_non_ritenta_su_errori_generici(self):
        """Il decorator non ritenta su errori non-429."""
        @with_retry
        def funzione_con_errore():
            raise TypeError("tipo sbagliato")

        with pytest.raises(TypeError):
            funzione_con_errore()
