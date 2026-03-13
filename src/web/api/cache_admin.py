"""
Cache Admin API — Endpoint per monitorare e gestire la response cache.

Endpoint esposti:
  GET  /api/cache/stats  — Statistiche: hit rate, dimensione, top queries
  POST /api/cache/flush  — Svuota la cache manualmente (utile dopo aggiornamenti)

Questi endpoint sono non autenticati: il tool gira su VPS privato senza
accesso pubblico diretto agli endpoint admin. Se in futuro si apre l'accesso,
aggiungere autenticazione con Header o Basic Auth.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.utils.cache import get_cache
from src.utils.logger import get_logger

logger = get_logger("web.api.cache_admin")

router = APIRouter()


@router.get("/api/cache/stats")
def cache_stats():
    """
    Statistiche della response cache.

    Risposta:
        {
            "hit_rate": 0.77,           # 0.0 - 1.0
            "hits": 63,
            "misses": 19,
            "total_requests": 82,
            "cache_size": 12,           # Entry attualmente in cache
            "valid_entries": 12,        # Entry non scadute
            "max_size": 500,
            "ttl_hours": 24.0,
            "similarity_threshold": 0.85,
            "top_queries": [            # Top 10 query più colpite
                {"query": "cosa dice la direttiva eu", "hits": 35},
                ...
            ]
        }
    """
    stats = get_cache().stats()
    logger.info(
        f"Cache stats: hit_rate={stats['hit_rate']:.0%}, "
        f"size={stats['cache_size']}/{stats['max_size']}"
    )
    return JSONResponse(content=stats)


@router.post("/api/cache/flush")
def cache_flush():
    """
    Svuota la cache manualmente.

    Usa quando:
    - Il contenuto della Direttiva è stato aggiornato
    - Si sospetta che le risposte cachate siano obsolete
    - Durante il debug

    Risposta:
        {"flushed": 12, "message": "Cache svuotata: 12 entry rimosse"}
    """
    count = get_cache().flush()
    logger.info(f"Cache flush via API: {count} entry rimosse")
    return JSONResponse(content={
        "flushed": count,
        "message": f"Cache svuotata: {count} entry rimosse",
    })
