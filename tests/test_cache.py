"""
Test per src/utils/cache.py — ResponseCache.

Copertura:
- Exact hit / miss
- TTL expiry
- LRU eviction a max_size
- Normalize: lowercase, punteggiatura, spazi
- Similarity matching (con embedding mock)
- Flush
- Stats: hit_rate, cache_size, top_queries
- Thread safety di base (singleton)
"""

import math
import time
from unittest.mock import MagicMock, patch

import pytest

from src.utils.cache import ResponseCache, get_cache


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def cache():
    """ResponseCache fresca per ogni test (non usa il singleton).
    FastEmbed disabilitato: i test unitari usano solo exact match.
    I test di similarity injettano il loro mock esplicitamente.
    """
    c = ResponseCache(max_size=5, ttl_seconds=3600, similarity_threshold=0.85)
    c._embedder_failed = True  # evita caricamento FastEmbed nei test unitari
    return c


@pytest.fixture
def tiny_cache():
    """Cache con max_size=3 per testare LRU eviction facilmente.
    FastEmbed disabilitato: impedisce che query simili colpiscano la cache
    per similarity invece di seguire il comportamento LRU atteso.
    """
    c = ResponseCache(max_size=3, ttl_seconds=3600, similarity_threshold=0.85)
    c._embedder_failed = True
    return c


# ===========================================================================
# Normalizzazione
# ===========================================================================

class TestNormalize:
    def test_lowercase(self):
        assert ResponseCache.normalize("COSA DICE LA DIRETTIVA") == "cosa dice la direttiva"

    def test_strip_whitespace(self):
        assert ResponseCache.normalize("  domanda  ") == "domanda"

    def test_rimuove_punteggiatura(self):
        normalized = ResponseCache.normalize("Cosa dice la Direttiva EU 2023/970?")
        assert "?" not in normalized
        assert "/" not in normalized
        assert "." not in normalized

    def test_normalizza_spazi_multipli(self):
        normalized = ResponseCache.normalize("domanda   con   spazi")
        assert normalized == "domanda con spazi"

    def test_query_vuota(self):
        assert ResponseCache.normalize("") == ""

    def test_query_identica_dopo_normalizzazione(self):
        q1 = "Cosa dice la Direttiva?"
        q2 = "cosa dice la direttiva"
        assert ResponseCache.normalize(q1) == ResponseCache.normalize(q2)


# ===========================================================================
# Get / Set — Exact match
# ===========================================================================

class TestExactMatch:
    def test_miss_su_cache_vuota(self, cache):
        assert cache.get("qualsiasi domanda") is None

    def test_hit_dopo_set(self, cache):
        cache.set("cosa dice la direttiva?", "La Direttiva EU 2023/970 prevede...")
        result = cache.get("cosa dice la direttiva?")
        assert result == "La Direttiva EU 2023/970 prevede..."

    def test_hit_con_query_normalizzata_diversa(self, cache):
        """Exact hit anche se la query ha punteggiatura o maiuscole diverse."""
        cache.set("Cosa dice la Direttiva EU?", "risposta")
        assert cache.get("cosa dice la direttiva eu") == "risposta"
        assert cache.get("COSA DICE LA DIRETTIVA EU?") == "risposta"

    def test_miss_su_query_diversa(self, cache):
        cache.set("cosa dice la direttiva", "risposta")
        assert cache.get("quali sono le sanzioni") is None

    def test_hit_incrementa_hit_count(self, cache):
        cache.set("domanda", "risposta")
        cache.get("domanda")
        cache.get("domanda")
        with cache._lock:
            key = cache._hash(cache.normalize("domanda"))
            assert cache._cache[key].hit_count == 2


# ===========================================================================
# TTL expiry
# ===========================================================================

class TestTTL:
    def test_entry_scaduta_ritorna_none(self):
        """TTL=1s: dopo 1.1s la entry deve essere scaduta."""
        c = ResponseCache(max_size=10, ttl_seconds=1)
        c._embedder_failed = True  # evita caricamento FastEmbed (lento, non necessario qui)
        c.set("domanda", "risposta")
        assert c.get("domanda") == "risposta"

        time.sleep(1.1)

        assert c.get("domanda") is None

    def test_entry_non_scaduta_ritorna_risposta(self):
        """TTL=60s: subito dopo set, deve funzionare."""
        c = ResponseCache(max_size=10, ttl_seconds=60)
        c._embedder_failed = True  # evita caricamento FastEmbed (lento, non necessario qui)
        c.set("domanda", "risposta")
        assert c.get("domanda") == "risposta"

    def test_entry_scaduta_rimossa_dalla_cache(self):
        """Dopo TTL, la entry scaduta viene rimossa dalla cache."""
        c = ResponseCache(max_size=10, ttl_seconds=1)
        c._embedder_failed = True  # evita caricamento FastEmbed (lento, non necessario qui)
        c.set("domanda", "risposta")
        time.sleep(1.1)
        c.get("domanda")  # questo dovrebbe rimuovere la entry scaduta
        with c._lock:
            assert len(c._cache) == 0


# ===========================================================================
# LRU eviction
# ===========================================================================

class TestLRU:
    def test_eviction_quando_piena(self, tiny_cache):
        """Con max_size=3: quando aggiungi la 4a entry, la 1a viene rimossa."""
        tiny_cache.set("q1", "r1")
        tiny_cache.set("q2", "r2")
        tiny_cache.set("q3", "r3")

        assert tiny_cache.get("q1") == "r1"  # accedo q1 → diventa la più recente

        tiny_cache.set("q4", "r4")  # q2 è ora la meno recente → evictata

        assert tiny_cache.get("q2") is None  # evictata
        assert tiny_cache.get("q3") == "r3"  # ancora presente
        assert tiny_cache.get("q4") == "r4"  # nuova

    def test_size_non_supera_max(self, tiny_cache):
        """La cache non supera mai max_size."""
        for i in range(10):
            tiny_cache.set(f"query {i}", f"risposta {i}")
            with tiny_cache._lock:
                assert len(tiny_cache._cache) <= 3

    def test_update_entry_esistente_non_aumenta_size(self, tiny_cache):
        """Aggiornare una entry esistente non aumenta la dimensione."""
        tiny_cache.set("q1", "r1")
        tiny_cache.set("q2", "r2")
        tiny_cache.set("q1", "r1 aggiornata")  # update, non insert
        with tiny_cache._lock:
            assert len(tiny_cache._cache) == 2


# ===========================================================================
# Similarity matching (con embedding mock)
# ===========================================================================

class TestSimilarityMatch:
    def _make_cache_with_embedder(self, vec_a, vec_b):
        """
        Crea una cache con embedder mockato che ritorna vec_a per la prima
        chiamata (set) e vec_b per la seconda (get).
        """
        c = ResponseCache(max_size=10, ttl_seconds=3600, similarity_threshold=0.85)
        call_count = [0]

        def mock_embed(texts):
            call_count[0] += 1
            vec = vec_a if call_count[0] <= 1 else vec_b
            return iter([vec])

        mock_embedder = MagicMock()
        mock_embedder.embed.side_effect = mock_embed
        c._embedder = mock_embedder
        return c

    def test_similarity_hit_con_vettori_simili(self):
        """Due vettori con cosine similarity > 0.85 → cache hit."""
        # Vettori quasi identici → similarity ~1.0
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.99, 0.1, 0.0]

        c = ResponseCache(max_size=10, ttl_seconds=3600, similarity_threshold=0.85)
        call_count = [0]

        def mock_embed(texts):
            call_count[0] += 1
            return iter([v1 if call_count[0] <= 1 else v2])

        mock_embedder = MagicMock()
        mock_embedder.embed.side_effect = mock_embed
        c._embedder = mock_embedder

        c.set("cosa dice la direttiva", "risposta sulla direttiva")
        # Query diversa ma semanticamente simile
        result = c.get("cosa prevede la direttiva europea")
        assert result == "risposta sulla direttiva"

    def test_similarity_miss_con_vettori_distanti(self):
        """Due vettori con cosine similarity < 0.85 → cache miss."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]  # ortogonali → similarity 0.0

        call_count = [0]

        def mock_embed(texts):
            call_count[0] += 1
            return iter([v1 if call_count[0] <= 1 else v2])

        c = ResponseCache(max_size=10, ttl_seconds=3600, similarity_threshold=0.85)
        mock_embedder = MagicMock()
        mock_embedder.embed.side_effect = mock_embed
        c._embedder = mock_embedder

        c.set("cosa dice la direttiva", "risposta")
        result = c.get("quali sono le sanzioni")
        assert result is None

    def test_cosine_similarity_vettori_identici(self):
        v = [1.0, 2.0, 3.0]
        assert ResponseCache._cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_cosine_similarity_vettori_ortogonali(self):
        assert ResponseCache._cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0, abs=1e-6)

    def test_cosine_similarity_vettore_zero(self):
        assert ResponseCache._cosine_similarity([0.0, 0.0], [1.0, 2.0]) == pytest.approx(0.0, abs=1e-6)

    def test_no_similarity_senza_embedder(self):
        """Se l'embedder non è disponibile, non fa similarity matching."""
        c = ResponseCache(max_size=10, ttl_seconds=3600, similarity_threshold=0.85)
        c._embedder_failed = True  # simula embedder non disponibile

        c.set("cosa dice la direttiva", "risposta")
        # Senza embedding, solo exact match è possibile
        result = c.get("cosa prevede la direttiva europea")
        assert result is None  # MISS: non fa similarity senza embedder


# ===========================================================================
# Flush
# ===========================================================================

class TestFlush:
    def test_flush_svuota_la_cache(self, cache):
        cache.set("q1", "r1")
        cache.set("q2", "r2")
        count = cache.flush()
        assert count == 2
        assert cache.get("q1") is None
        assert cache.get("q2") is None

    def test_flush_resetta_statistiche(self, cache):
        cache.set("q1", "r1")
        cache.get("q1")
        cache.flush()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0

    def test_flush_cache_vuota(self, cache):
        count = cache.flush()
        assert count == 0


# ===========================================================================
# Stats
# ===========================================================================

class TestStats:
    def test_stats_iniziali(self, cache):
        s = cache.stats()
        assert s["hit_rate"] == 0.0
        assert s["hits"] == 0
        assert s["misses"] == 0
        assert s["cache_size"] == 0
        assert s["max_size"] == 5

    def test_stats_dopo_hit_e_miss(self, cache):
        cache.set("domanda", "risposta")
        cache.get("domanda")      # HIT
        cache.get("altra domanda")  # MISS

        s = cache.stats()
        assert s["hits"] == 1
        assert s["misses"] == 1
        assert s["hit_rate"] == pytest.approx(0.5, abs=0.001)
        assert s["total_requests"] == 2
        assert s["cache_size"] == 1

    def test_stats_top_queries(self, cache):
        cache.set("domanda popolare", "risposta")
        for _ in range(5):
            cache.get("domanda popolare")

        s = cache.stats()
        assert len(s["top_queries"]) == 1
        assert s["top_queries"][0]["hits"] == 5

    def test_stats_ttl_e_max_size(self, cache):
        s = cache.stats()
        assert s["ttl_hours"] == pytest.approx(1.0, abs=0.1)
        assert s["max_size"] == 5
        assert s["similarity_threshold"] == 0.85


# ===========================================================================
# Singleton
# ===========================================================================

class TestSingleton:
    def test_get_cache_ritorna_stessa_istanza(self):
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2

    def test_get_cache_ritorna_response_cache(self):
        assert isinstance(get_cache(), ResponseCache)
