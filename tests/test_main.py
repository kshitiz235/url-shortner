"""
API tests for Milestone 2 (now backed by a database).

The app code is identical whether it talks to PostgreSQL or SQLite; here it
runs on a throwaway SQLite database (configured in conftest.py). Tables are
created fresh before each test and dropped after, so tests don't leak state
into one another.
"""
import pytest
from fastapi.testclient import TestClient

from src.app import cache
from src.app.config import settings
from src.app.database import Base, engine
from src.app.main import app


@pytest.fixture(autouse=True)
def fresh_database():
    """Start each test with empty tables AND an empty cache, for isolation."""
    Base.metadata.create_all(bind=engine)
    cache.client.flushall()
    yield
    Base.metadata.drop_all(bind=engine)
    cache.client.flushall()


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_shorten_then_redirect(client):
    """Creating a short link and visiting it should redirect to the original."""
    long_url = "https://example.com/a/very/long/path"

    create = client.post("/api/shorten", json={"url": long_url})
    assert create.status_code == 200
    body = create.json()
    assert "code" in body and "short_url" in body

    code = body["code"]
    redirect = client.get(f"/{code}", follow_redirects=False)
    assert redirect.status_code in (301, 302, 307, 308)
    assert redirect.headers["location"].startswith("https://example.com")


def test_link_persists_across_requests(client):
    """A created link is retrievable on a later, separate request — proving it
    lives in the database, not just in one request's memory."""
    create = client.post("/api/shorten", json={"url": "https://persist.example.com/x"})
    code = create.json()["code"]

    # A brand-new request finds it.
    lookup = client.get(f"/{code}", follow_redirects=False)
    assert lookup.status_code in (301, 302, 307, 308)


def test_redirect_is_cached_after_first_hit(client):
    """First redirect is a cache MISS (loaded from DB); the second is a HIT
    (served from cache). Proven via the X-Cache response header."""
    code = client.post(
        "/api/shorten", json={"url": "https://cache.example.com/x"}
    ).json()["code"]

    first = client.get(f"/{code}", follow_redirects=False)
    assert first.headers["x-cache"] == "MISS"

    second = client.get(f"/{code}", follow_redirects=False)
    assert second.headers["x-cache"] == "HIT"


def test_unknown_code_returns_404(client):
    response = client.get("/definitely-not-a-real-code", follow_redirects=False)
    assert response.status_code == 404


def test_invalid_url_rejected(client):
    response = client.post("/api/shorten", json={"url": "not-a-url"})
    assert response.status_code == 422


def test_clicks_are_recorded_and_aggregated(client):
    """Redirects record click events (in the background); the stats endpoint
    aggregates them by total and referrer."""
    code = client.post(
        "/api/shorten", json={"url": "https://track.example.com/x"}
    ).json()["code"]

    # Three redirects: two from google, one from twitter.
    client.get(f"/{code}", follow_redirects=False, headers={"referer": "https://google.com"})
    client.get(f"/{code}", follow_redirects=False, headers={"referer": "https://google.com"})
    client.get(f"/{code}", follow_redirects=False, headers={"referer": "https://twitter.com"})

    stats = client.get(f"/api/stats/{code}")
    assert stats.status_code == 200
    body = stats.json()

    assert body["total_clicks"] == 3
    assert body["last_clicked"] is not None
    referrers = {row["referrer"]: row["count"] for row in body["top_referrers"]}
    assert referrers["https://google.com"] == 2
    assert referrers["https://twitter.com"] == 1


def test_stats_unknown_code_returns_404(client):
    assert client.get("/api/stats/nope").status_code == 404


def test_rate_limit_blocks_excess_requests(client):
    """The first `rate_limit_max` creations succeed; the next one is blocked
    with HTTP 429 and a Retry-After header."""
    for i in range(settings.rate_limit_max):
        ok = client.post("/api/shorten", json={"url": f"https://ex.com/{i}"})
        assert ok.status_code == 200, f"request {i} should be allowed"

    blocked = client.post("/api/shorten", json={"url": "https://ex.com/over-limit"})
    assert blocked.status_code == 429
    assert "retry-after" in {k.lower() for k in blocked.headers}
