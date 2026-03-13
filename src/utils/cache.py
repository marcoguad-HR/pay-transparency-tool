"""
Response Cache — Cache in memoria LRU per le risposte del RAG.

Riduce le chiamate a Groq cachando le risposte per query simili.
Con il 77% delle query ripetitive (traffico 12 marzo 2026),
questa cache può eliminare la maggior parte delle chiamate API.

Strategia:
1. Exact match  : hash(normalize(query)) → O(1), colpisce query identiche
2. Similarity   : cosine similarity degli embedding FastEmbed → colpisce
                  varianti semantiche ("cosa dice la direttiva?" ~
                  "cosa prevede la direttiva europea?")

LRU eviction via OrderedDict: quando la cache raggiunge 500 entry,
si rimuove la meno usata di recente.

TTL 24h: le risposte rimangono valide per una giornata.
"""

import hashlib
import math
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger("utils.cache")

# --- Configurazione ---
CACHE_MAX_SIZE = 500          # Entry massime (LRU eviction oltre)
CACHE_TTL_SECONDS = 24 * 3600 # 24 ore
SIMILARITY_THRESHOLD = 0.85   # Soglia cosine similarity per similarity hit


@dataclass
class CacheEntry:
    """Una entry nella cache: risposta + metadati per similarity e LRU."""
    answer: str
    query_normalized: str
    embedding: Optional[list] = None        # Embedding come list[float] (serializzabile)
    created_at: float = field(default_factory=time.time)
    hit_count: int = 0


class ResponseCache:
    """
    Cache LRU in memoria per le risposte LLM del RAG.

    Thread-safe. OrderedDict garantisce ordinamento per recency (LRU).

    Uso:
        cache = get_cache()
        if (cached := cache.get(query)):
            return cached
        answer = llm.generate(query)
        cache.set(query, answer)
    """

    def __init__(
        self,
        max_size: int = CACHE_MAX_SIZE,
        ttl_seconds: int = CACHE_TTL_SECONDS,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._sim_threshold = similarity_threshold
        self._hits = 0
        self._misses = 0
        self._embedder = None   # lazy init: non caricare FastEmbed finché non serve
        self._embedder_failed = False

    # ------------------------------------------------------------------
    # Normalizzazione e hashing
    # ------------------------------------------------------------------

    @staticmethod
    def normalize(query: str) -> str:
        """Lowercase, strip, rimuovi punteggiatura, normalizza spazi."""
        q = query.lower().strip()
        q = re.sub(r"[^\w\s]", "", q)
        q = re.sub(r"\s+", " ", q).strip()
        return q

    @staticmethod
    def _hash(normalized: str) -> str:
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Embedding per similarity matching
    # ------------------------------------------------------------------

    def _get_embedder(self):
        """
        Lazy init: riutilizza il TextEmbedding già caricato nel Retriever singleton.
        Evita di caricare FastEmbed due volte in memoria.
        """
        if self._embedder is not None or self._embedder_failed:
            return self._embedder
        try:
            from src.rag.retriever import DirectiveRetriever
            retriever = DirectiveRetriever()
            self._embedder = retriever.embedder
            logger.info("Cache: embedder FastEmbed caricato per similarity matching")
        except Exception as e:
            logger.warning(f"Cache: embedder non disponibile, solo exact match ({e})")
            self._embedder_failed = True
        return self._embedder

    def _embed(self, text: str) -> Optional[list]:
        """Ritorna l'embedding come list[float], o None se non disponibile."""
        embedder = self._get_embedder()
        if embedder is None:
            return None
        try:
            vectors = list(embedder.embed([text]))
            if not vectors:
                return None
            emb = vectors[0]
            # Supporta sia numpy array (.tolist()) sia plain list Python
            return emb.tolist() if hasattr(emb, "tolist") else list(emb)
        except Exception as e:
            logger.debug(f"Cache: embed fallito: {e}")
            return None

    @staticmethod
    def _cosine_similarity(a: list, b: list) -> float:
        """Cosine similarity tra due vettori float puri (no numpy)."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ------------------------------------------------------------------
    # Get / Set
    # ------------------------------------------------------------------

    def get(self, query: str) -> Optional[str]:
        """
        Cerca la risposta in cache.

        1. Exact match  (O(1)) — query normalizzata identica
        2. Similarity   (O(n)) — cosine similarity >= SIMILARITY_THRESHOLD

        Ritorna None se non trova nulla o se la entry è scaduta.
        """
        normalized = self.normalize(query)
        key = self._hash(normalized)
        now = time.time()

        with self._lock:
            # --- Exact match ---
            if key in self._cache:
                entry = self._cache[key]
                if now - entry.created_at < self._ttl:
                    entry.hit_count += 1
                    self._cache.move_to_end(key)    # LRU: sposta in fondo
                    self._hits += 1
                    logger.info(
                        f"Cache HIT (exact) [{self._hits} hits totali]: "
                        f"'{normalized[:60]}'"
                    )
                    return entry.answer
                else:
                    del self._cache[key]
                    logger.debug(f"Cache: entry TTL scaduta rimossa: '{normalized[:40]}'")

            # --- Similarity match ---
            query_emb = self._embed(normalized)
            if query_emb is not None:
                for k, entry in list(self._cache.items()):
                    if now - entry.created_at >= self._ttl:
                        continue
                    if entry.embedding is not None:
                        sim = self._cosine_similarity(query_emb, entry.embedding)
                        if sim >= self._sim_threshold:
                            entry.hit_count += 1
                            self._cache.move_to_end(k)
                            self._hits += 1
                            logger.info(
                                f"Cache HIT (similarity {sim:.2f}) [{self._hits} hits totali]: "
                                f"'{normalized[:50]}' ~ '{entry.query_normalized[:50]}'"
                            )
                            return entry.answer

            self._misses += 1
            logger.info(f"Cache MISS [{self._misses} misses totali]: '{normalized[:60]}'")
            return None

    def set(self, query: str, answer: str) -> None:
        """Salva la risposta in cache con il suo embedding per similarity."""
        normalized = self.normalize(query)
        key = self._hash(normalized)
        embedding = self._embed(normalized)

        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self._max_size:
                evicted_key, evicted = self._cache.popitem(last=False)
                logger.debug(f"Cache LRU eviction: '{evicted.query_normalized[:50]}'")

            self._cache[key] = CacheEntry(
                answer=answer,
                query_normalized=normalized,
                embedding=embedding,
                created_at=time.time(),
            )
            logger.debug(
                f"Cache SET: '{normalized[:60]}' "
                f"({len(self._cache)}/{self._max_size} entries)"
            )

    # ------------------------------------------------------------------
    # Stats e amministrazione
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Statistiche della cache per l'endpoint /api/cache/stats."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = round(self._hits / total, 3) if total > 0 else 0.0
            now = time.time()

            valid_entries = sum(
                1 for e in self._cache.values()
                if now - e.created_at < self._ttl
            )

            top_queries = sorted(
                [
                    {"query": e.query_normalized[:80], "hits": e.hit_count}
                    for e in self._cache.values()
                    if e.hit_count > 0
                ],
                key=lambda x: -x["hits"],
            )[:10]

            return {
                "hit_rate": hit_rate,
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total,
                "cache_size": len(self._cache),
                "valid_entries": valid_entries,
                "max_size": self._max_size,
                "ttl_hours": round(self._ttl / 3600, 1),
                "similarity_threshold": self._sim_threshold,
                "top_queries": top_queries,
            }

    def flush(self) -> int:
        """Svuota la cache. Ritorna il numero di entry rimosse."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info(f"Cache flush manuale: {count} entry rimosse")
            return count


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_cache_instance: Optional[ResponseCache] = None
_cache_lock = threading.Lock()


def get_cache() -> ResponseCache:
    """Ritorna il singleton ResponseCache (thread-safe, lazy init)."""
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = ResponseCache()
                logger.info(
                    f"ResponseCache inizializzata: "
                    f"max={CACHE_MAX_SIZE}, ttl={CACHE_TTL_SECONDS//3600}h, "
                    f"sim_threshold={SIMILARITY_THRESHOLD}"
                )
    return _cache_instance
