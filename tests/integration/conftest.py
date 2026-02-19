"""Marker e fixture per test di integrazione."""

import os

import pytest

requires_api = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY non impostata",
)

requires_vectordb = pytest.mark.skipif(
    not os.path.exists("data/vectordb/collection/eu_directive_2023_970"),
    reason="Vector DB non inizializzato (esegui prima ingestion)",
)
