"""
Test per suggest_scores — parsing output LLM e composizione description.
"""
import pytest
from src.web.api.suggest_scores import parse_llm_scores, build_description


class TestBuildDescription:
    """Test per la composizione della description da role_name + job_description."""

    def test_name_only(self):
        """Solo nome ruolo → description valida."""
        result = build_description("HR Manager", "")
        assert result == "HR Manager"

    def test_name_and_jd(self):
        """Nome + JD → concatenati."""
        result = build_description("HR Manager", "Gestisce le risorse umane")
        assert "HR Manager" in result
        assert "Gestisce le risorse umane" in result

    def test_jd_only(self):
        """Solo JD → description valida."""
        result = build_description("", "Gestisce le risorse umane e i processi di selezione")
        assert result == "Gestisce le risorse umane e i processi di selezione"

    def test_both_empty_raises(self):
        """Nessun input → ValueError."""
        with pytest.raises(ValueError):
            build_description("", "")

    def test_whitespace_only_raises(self):
        """Solo spazi → ValueError."""
        with pytest.raises(ValueError):
            build_description("  ", "  ")


class TestParseLlmScores:
    """Test sul parsing dell'output LLM."""

    def test_valid_json(self):
        """JSON valido con tutti i 16 fattori → dict corretto."""
        raw = '{"S1":3,"S2":2,"S3":4,"S4":3,"E1":1,"E2":4,"E3":3,"E4":3,"R1":2,"R2":3,"R3":1,"R4":2,"W1":1,"W2":3,"W3":1,"W4":2}'
        scores = parse_llm_scores(raw)
        assert len(scores) == 16
        assert scores["S1"] == 3
        assert scores["E2"] == 4
        assert scores["W4"] == 2

    def test_json_embedded_in_text(self):
        """JSON circondato da testo → parse corretto."""
        raw = '''Ecco la mia valutazione del ruolo:

{"S1":4,"S2":3,"S3":5,"S4":3,"E1":2,"E2":4,"E3":2,"E4":3,"R1":3,"R2":4,"R3":1,"R4":3,"W1":1,"W2":3,"W3":2,"W4":2}

Spero sia utile!'''
        scores = parse_llm_scores(raw)
        assert len(scores) == 16
        assert scores["S1"] == 4
        assert scores["S3"] == 5

    def test_json_in_markdown_code_block(self):
        """JSON dentro un blocco markdown → parse corretto."""
        raw = '''```json
{"S1":3,"S2":3,"S3":3,"S4":3,"E1":3,"E2":3,"E3":3,"E4":3,"R1":3,"R2":3,"R3":3,"R4":3,"W1":3,"W2":3,"W3":3,"W4":3}
```'''
        scores = parse_llm_scores(raw)
        assert len(scores) == 16
        assert all(v == 3 for v in scores.values())

    def test_missing_factors_raises_value_error(self):
        """JSON con fattori mancanti → ValueError."""
        raw = '{"S1":3,"S2":2,"S3":4}'
        with pytest.raises(ValueError, match="mancanti"):
            parse_llm_scores(raw)

    def test_score_out_of_range_zero(self):
        """Punteggio 0 (fuori range) → ValueError."""
        raw = '{"S1":0,"S2":2,"S3":4,"S4":3,"E1":1,"E2":4,"E3":3,"E4":3,"R1":2,"R2":3,"R3":1,"R4":2,"W1":1,"W2":3,"W3":1,"W4":2}'
        with pytest.raises(ValueError, match="fuori range"):
            parse_llm_scores(raw)

    def test_score_out_of_range_six(self):
        """Punteggio 6 (fuori range) → ValueError."""
        raw = '{"S1":3,"S2":2,"S3":4,"S4":3,"E1":1,"E2":4,"E3":3,"E4":3,"R1":2,"R2":3,"R3":1,"R4":2,"W1":1,"W2":6,"W3":1,"W4":2}'
        with pytest.raises(ValueError, match="fuori range"):
            parse_llm_scores(raw)

    def test_no_json_in_text(self):
        """Testo senza JSON → ValueError."""
        raw = "Mi dispiace, non posso valutare questo ruolo senza una descrizione."
        with pytest.raises(ValueError, match="Nessun JSON"):
            parse_llm_scores(raw)

    def test_invalid_json_syntax(self):
        """JSON con sintassi errata → ValueError."""
        raw = '{"S1":3, "S2":2, "S3":}'
        with pytest.raises(ValueError):
            parse_llm_scores(raw)

    def test_all_boundary_values_min(self):
        """Tutti i punteggi a 1 (minimo) → valido."""
        raw = '{"S1":1,"S2":1,"S3":1,"S4":1,"E1":1,"E2":1,"E3":1,"E4":1,"R1":1,"R2":1,"R3":1,"R4":1,"W1":1,"W2":1,"W3":1,"W4":1}'
        scores = parse_llm_scores(raw)
        assert all(v == 1 for v in scores.values())

    def test_all_boundary_values_max(self):
        """Tutti i punteggi a 5 (massimo) → valido."""
        raw = '{"S1":5,"S2":5,"S3":5,"S4":5,"E1":5,"E2":5,"E3":5,"E4":5,"R1":5,"R2":5,"R3":5,"R4":5,"W1":5,"W2":5,"W3":5,"W4":5}'
        scores = parse_llm_scores(raw)
        assert all(v == 5 for v in scores.values())

    def test_returns_only_16_keys(self):
        """Il risultato deve avere esattamente 16 chiavi."""
        raw = '{"S1":3,"S2":3,"S3":3,"S4":3,"E1":3,"E2":3,"E3":3,"E4":3,"R1":3,"R2":3,"R3":3,"R4":3,"W1":3,"W2":3,"W3":3,"W4":3,"extra":99}'
        scores = parse_llm_scores(raw)
        assert len(scores) == 16
        assert "extra" not in scores
