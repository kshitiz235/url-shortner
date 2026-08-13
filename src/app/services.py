"""
Service layer — logic that coordinates the cache and the database.

The route handlers stay thin; the interesting "cache-aside" decision lives
here where it's easy to read and test.
"""
from sqlalchemy.orm import Session

from . import cache, crud
from .database import SessionLocal

# How long a cached redirect lives before it must be re-read from the DB.
CACHE_TTL_SECONDS = 3600  # 1 hour
_KEY_PREFIX = "code:"


def resolve_long_url(db: Session, code: str) -> tuple[str | None, str]:
    """Resolve a short code to its long URL using the cache-aside pattern.

    Returns (long_url, cache_status) where cache_status is "HIT" or "MISS".
    long_url is None if the code doesn't exist.
    """
    key = _KEY_PREFIX + code

    # 1. Try the cache first — the fast path for the vast majority of traffic.
    cached_url = cache.client.get(key)
    if cached_url is not None:
        return cached_url, "HIT"

    # 2. Cache miss: fall back to the database.
    link = crud.get_link_by_code(db, code)
    if link is None:
        # Unknown code. (We deliberately don't cache misses here; caching
        # negative results is a valid optimization but adds complexity —
        # noted as a future improvement to prevent "cache penetration".)
        return None, "MISS"

    # 3. Populate the cache so the NEXT request for this code is a HIT.
    #    ex=TTL makes the entry auto-expire.
    cache.client.set(key, link.long_url, ex=CACHE_TTL_SECONDS)
    return link.long_url, "MISS"


def record_click(code: str, referrer: str | None, user_agent: str | None) -> None:
    """Record one click event. Runs as a background task AFTER the redirect
    response is sent, so it never adds latency to the redirect.

    It opens its own database session because the request's session has already
    been closed by the time a background task runs.

    Production note: writing a row per click is fine here, but at very high
    volume you'd instead push events to a queue/stream (e.g. Kafka) and
    aggregate them in batches to spare the database.
    """
    db = SessionLocal()
    try:
        link = crud.get_link_by_code(db, code)
        if link is None:
            return  # link vanished (e.g. deleted) — nothing to record
        crud.add_click(db, link.id, referrer, user_agent)
    finally:
        db.close()
