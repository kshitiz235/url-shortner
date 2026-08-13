"""
Rate limiting — a fixed-window counter backed by Redis.

Used as a FastAPI dependency on the link-creation endpoint. For each client IP
we keep a counter in Redis that resets every window. Redis's INCR is atomic,
so concurrent requests can't miscount.

Limitation (worth knowing): a *fixed* window allows a burst at the boundary —
a client could send `limit` requests at 11:59:59 and another `limit` at
12:00:00. A sliding-window or token-bucket algorithm smooths that out; noted as
a future improvement.
"""
from fastapi import HTTPException, Request

from . import cache
from .config import settings

_KEY_PREFIX = "ratelimit:shorten:"


def enforce_rate_limit(request: Request) -> None:
    """Raise HTTP 429 if this client IP has exceeded its request budget."""
    # request.client is the (ip, port) of the caller. Behind a reverse proxy or
    # load balancer you'd read the X-Forwarded-For header instead — noted for
    # production.
    client_ip = request.client.host if request.client else "unknown"
    key = _KEY_PREFIX + client_ip

    # Atomically increment this window's counter.
    current = cache.client.incr(key)

    # On the first request of a new window, set the window's expiry.
    if current == 1:
        cache.client.expire(key, settings.rate_limit_window_seconds)

    if current > settings.rate_limit_max:
        retry_after = cache.client.ttl(key)
        if retry_after is None or retry_after < 0:
            retry_after = settings.rate_limit_window_seconds
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
