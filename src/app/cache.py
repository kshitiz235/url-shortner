"""
Cache client.

Exposes a single `client` object with the standard Redis interface
(get / set / flushall / ...). Depending on config it's either:
  - a real Redis connection (production), or
  - an in-process `fakeredis` (local dev & tests) — no server to install.

Because both speak the same API, the rest of the app never knows or cares
which one it's talking to. That's the payoff of programming to an interface.
"""
from .config import settings


def _make_client():
    url = (settings.redis_url or "").strip()
    if url in ("", "fake"):
        import fakeredis
        # decode_responses=True -> we get str back instead of bytes.
        return fakeredis.FakeStrictRedis(decode_responses=True)
    import redis
    return redis.Redis.from_url(url, decode_responses=True)


# One shared client for the whole process.
client = _make_client()
