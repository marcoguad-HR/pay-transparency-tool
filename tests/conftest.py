"""Fixture condivisi per la test suite."""

import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_df():
    """DataFrame minimale con gap noto per test del GapCalculator.

    Costruisce un dataset con un gap intenzionale del ~10% in Engineering Senior (F).
    """
    np.random.seed(42)
    data = []
    for dept in ["Engineering", "Sales"]:
        for level in ["Junior", "Senior"]:
            for _ in range(10):
                gender = np.random.choice(["M", "F"])
                base = 60000 if level == "Senior" else 35000
                salary = base * np.random.normal(1.0, 0.03)
                if gender == "F" and dept == "Engineering" and level == "Senior":
                    salary *= 0.90  # Gap intenzionale ~10%
                data.append({
                    "gender": gender,
                    "department": dept,
                    "level": level,
                    "base_salary": round(salary),
                    "bonus": round(salary * 0.1),
                })
    return pd.DataFrame(data)


@pytest.fixture
def minimal_df():
    """DataFrame con i soli campi obbligatori (gender, base_salary)."""
    return pd.DataFrame({
        "gender": ["M", "F", "M", "F", "M", "F"],
        "base_salary": [50000, 45000, 55000, 47000, 52000, 48000],
    })


@pytest.fixture
def equal_pay_df():
    """DataFrame dove M e F hanno stipendi identici (gap = 0%)."""
    return pd.DataFrame({
        "gender": ["M", "F", "M", "F", "M", "F"],
        "base_salary": [50000, 50000, 60000, 60000, 40000, 40000],
        "department": ["Eng", "Eng", "Eng", "Eng", "Eng", "Eng"],
        "level": ["Mid", "Mid", "Mid", "Mid", "Mid", "Mid"],
    })


@pytest.fixture
def sample_csv(tmp_path):
    """Crea un file CSV temporaneo valido per il DataLoader."""
    df = pd.DataFrame({
        "gender": ["M", "F", "M", "F", "M", "F"],
        "base_salary": [50000, 45000, 55000, 47000, 52000, 48000],
        "department": ["Eng", "Eng", "Eng", "Eng", "Eng", "Eng"],
        "level": ["Senior", "Senior", "Senior", "Senior", "Senior", "Senior"],
        "bonus": [5000, 4000, 6000, 4500, 5500, 4200],
    })
    path = tmp_path / "test_data.csv"
    df.to_csv(path, index=False)
    return str(path)


@pytest.fixture
def demo_csv_path():
    """Percorso del file demo CSV."""
    return "data/demo/demo_employees.csv"
