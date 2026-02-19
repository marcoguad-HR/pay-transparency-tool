"""Unit test per PayDataLoader."""

import pytest
import pandas as pd

from src.analysis.data_loader import PayDataLoader, DataLoadError, DataValidationError


class TestPayDataLoader:
    """Test di caricamento e validazione dati."""

    def setup_method(self):
        self.loader = PayDataLoader()

    # --- Caricamento riuscito ---

    def test_load_valid_csv(self, sample_csv):
        """Carica un CSV valido e verifica i campi del LoadResult."""
        result = self.loader.load(sample_csv)
        assert result.n_employees == 6
        assert result.n_male == 3
        assert result.n_female == 3
        assert "Eng" in result.departments
        assert "Senior" in result.levels
        assert result.df is not None

    def test_load_demo_csv(self, demo_csv_path):
        """Carica il dataset demo reale."""
        result = self.loader.load(demo_csv_path)
        assert result.n_employees > 100
        assert result.n_male > 0
        assert result.n_female > 0
        assert len(result.departments) > 0

    # --- Errori di caricamento ---

    def test_file_not_found(self):
        """File inesistente solleva DataLoadError."""
        with pytest.raises(DataLoadError, match="non trovato"):
            self.loader.load("file_che_non_esiste.csv")

    def test_unsupported_format(self, tmp_path):
        """Formato non supportato solleva DataLoadError."""
        path = tmp_path / "data.json"
        path.write_text('{"key": "value"}')
        with pytest.raises(DataLoadError, match="non supportato"):
            self.loader.load(str(path))

    def test_empty_file(self, tmp_path):
        """File CSV vuoto solleva DataLoadError."""
        path = tmp_path / "empty.csv"
        path.write_text("gender,base_salary\n")
        with pytest.raises(DataLoadError, match="vuoto"):
            self.loader.load(str(path))

    # --- Errori di validazione ---

    def test_missing_required_columns(self, tmp_path):
        """Colonne obbligatorie mancanti sollevano DataValidationError."""
        df = pd.DataFrame({"name": ["Alice"], "salary": [50000]})
        path = tmp_path / "bad_columns.csv"
        df.to_csv(path, index=False)
        with pytest.raises(DataValidationError, match="obbligatorie mancanti"):
            self.loader.load(str(path))

    def test_invalid_gender_values(self, tmp_path):
        """Valori di genere non validi sollevano DataValidationError."""
        df = pd.DataFrame({
            "gender": ["M", "X", "F"],
            "base_salary": [50000, 45000, 48000],
        })
        path = tmp_path / "bad_gender.csv"
        df.to_csv(path, index=False)
        with pytest.raises(DataValidationError, match="non validi"):
            self.loader.load(str(path))

    def test_only_male(self, tmp_path):
        """Solo uomini nel dataset solleva DataValidationError."""
        df = pd.DataFrame({
            "gender": ["M", "M", "M"],
            "base_salary": [50000, 55000, 52000],
        })
        path = tmp_path / "only_male.csv"
        df.to_csv(path, index=False)
        with pytest.raises(DataValidationError, match="femmina"):
            self.loader.load(str(path))

    def test_negative_salary(self, tmp_path):
        """Stipendi negativi sollevano DataValidationError."""
        df = pd.DataFrame({
            "gender": ["M", "F"],
            "base_salary": [50000, -1000],
        })
        path = tmp_path / "negative_salary.csv"
        df.to_csv(path, index=False)
        with pytest.raises(DataValidationError, match="<= 0"):
            self.loader.load(str(path))

    def test_non_numeric_salary(self, tmp_path):
        """Stipendi non numerici sollevano DataValidationError."""
        df = pd.DataFrame({
            "gender": ["M", "F"],
            "base_salary": [50000, "abc"],
        })
        path = tmp_path / "non_numeric.csv"
        df.to_csv(path, index=False)
        with pytest.raises(DataValidationError, match="non numerici"):
            self.loader.load(str(path))

    # --- Normalizzazione colonne ---

    def test_column_normalization(self, tmp_path):
        """Colonne con formattazione diversa vengono normalizzate."""
        df = pd.DataFrame({
            "Gender": ["M", "F"],
            "Base Salary": [50000, 48000],
        })
        path = tmp_path / "messy_cols.csv"
        df.to_csv(path, index=False)
        result = self.loader.load(str(path))
        assert "gender" in result.df.columns
        assert "base_salary" in result.df.columns

    def test_column_normalization_dashes(self, tmp_path):
        """Trattini nei nomi colonna vengono convertiti in underscore."""
        df = pd.DataFrame({
            "gender": ["M", "F"],
            "base-salary": [50000, 48000],
        })
        path = tmp_path / "dashes.csv"
        df.to_csv(path, index=False)
        result = self.loader.load(str(path))
        assert "base_salary" in result.df.columns

    # --- Warning di qualità ---

    def test_small_dataset_warning(self, tmp_path):
        """Dataset piccolo genera warning."""
        df = pd.DataFrame({
            "gender": ["M", "F", "M"],
            "base_salary": [50000, 48000, 52000],
        })
        path = tmp_path / "small.csv"
        df.to_csv(path, index=False)
        result = self.loader.load(str(path))
        assert any("piccolo" in w.lower() or "small" in w.lower() for w in result.warnings)

    def test_gender_imbalance_warning(self, tmp_path):
        """Forte squilibrio di genere genera warning."""
        data = [{"gender": "M", "base_salary": 50000 + i * 100} for i in range(9)]
        data.append({"gender": "F", "base_salary": 48000})
        df = pd.DataFrame(data)
        path = tmp_path / "imbalance.csv"
        df.to_csv(path, index=False)
        result = self.loader.load(str(path))
        assert any("squilibrio" in w.lower() for w in result.warnings)
