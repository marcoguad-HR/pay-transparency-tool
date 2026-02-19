"""Unit test per Config."""

import pytest

from src.utils.config import Config


class TestConfig:
    """Test del modulo di configurazione."""

    def setup_method(self):
        """Reset del singleton prima di ogni test."""
        Config._instance = None

    def test_singleton_pattern(self):
        """get_instance ritorna la stessa istanza."""
        c1 = Config.get_instance()
        c2 = Config.get_instance()
        assert c1 is c2

    def test_loads_config(self):
        """Carica la configurazione (da yaml o example)."""
        config = Config.get_instance()
        assert config.llm_config is not None
        assert isinstance(config.llm_config, dict)

    def test_llm_config_has_model(self):
        """La sezione llm contiene il modello."""
        config = Config.get_instance()
        llm = config.llm_config
        assert "model" in llm

    def test_embeddings_config(self):
        """La sezione embeddings è un dict."""
        config = Config.get_instance()
        assert isinstance(config.embeddings_config, dict)

    def test_vectorstore_config(self):
        """La sezione vectorstore è un dict."""
        config = Config.get_instance()
        assert isinstance(config.vectorstore_config, dict)

    def test_rag_config(self):
        """La sezione rag è un dict."""
        config = Config.get_instance()
        assert isinstance(config.rag_config, dict)

    def test_api_key_property(self):
        """api_key ritorna una stringa (vuota se non configurata)."""
        config = Config.get_instance()
        assert isinstance(config.api_key, str)

    def test_fallback_to_example(self, tmp_path):
        """Se config.yaml non esiste, usa config.yaml.example."""
        Config._instance = None
        # Usa un path che non esiste ma il cui .example sì
        config = Config("config.yaml")
        # Dovrebbe aver caricato config.yaml.example
        assert config.llm_config is not None

    def test_empty_config(self, tmp_path):
        """Se nessun file config esiste, ritorna dict vuoti."""
        Config._instance = None
        config = Config(str(tmp_path / "nonexistent.yaml"))
        assert config.llm_config == {}
        assert config.embeddings_config == {}
        assert config.vectorstore_config == {}
        assert config.rag_config == {}
