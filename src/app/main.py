"""
URL Shortener — FastAPI application (Milestone 2: Database).

The core flow is unchanged from Milestone 1, but links are now stored in a real
database (PostgreSQL in production, SQLite in tests) instead of an in-memory
dict — so they survive restarts and can be shared across server instances.

    1. POST /api/shorten  -> create a short code, persisted to the database
    2. GET  /{code}       -> look up the code in the database and redirect

Run it with:   uvicorn src.app.main:app --reload
Then open:     http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from . import crud, ratelimit, services
from .config import settings
from .database import Base, engine, get_db
from .models import ReferrerCount, ShortenRequest, ShortenResponse, StatsResponse

# Import tables so they're registered on `Base` before we create them below.
from . import tables  # noqa: F401  (imported for its side effect)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once on startup. Creates any missing tables.

    This is fine for development. In production you'd manage schema changes
    with a migration tool (e.g. Alembic) so changes are versioned and
    reviewable — noted as a future improvement.
    """
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="URL Shortener", version="0.2.0", lifespan=lifespan)

# CORS: browsers block cross-origin requests (our React app on :5173 calling
# this API on :8000) unless the server explicitly allows the origin. We also
# expose the custom X-Cache header so the frontend could read it if needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Cache"],
)


@app.get("/health")
def health() -> dict:
    """Liveness check — used by tests and deployment platforms."""
    return {"status": "ok"}


@app.post(
    "/api/shorten",
    response_model=ShortenResponse,
    dependencies=[Depends(ratelimit.enforce_rate_limit)],
)
def shorten(payload: ShortenRequest, db: Session = Depends(get_db)) -> ShortenResponse:
    """Create a short link for the given URL and persist it.

    The `enforce_rate_limit` dependency runs first and raises HTTP 429 if this
    client IP has made too many creation requests in the current window.
    """
    link = crud.create_link(db, str(payload.url))
    return ShortenResponse(code=link.code, short_url=f"{settings.base_url}/{link.code}")


@app.get("/api/stats/{code}", response_model=StatsResponse)
def stats(code: str, db: Session = Depends(get_db)) -> StatsResponse:
    """Return click analytics for a short code (total, last click, referrers)."""
    link = crud.get_link_by_code(db, code)
    if link is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    data = crud.get_click_stats(db, link)
    return StatsResponse(
        code=link.code,
        long_url=link.long_url,
        total_clicks=data["total_clicks"],
        last_clicked=data["last_clicked"],
        top_referrers=[ReferrerCount(**row) for row in data["top_referrers"]],
    )


@app.get("/{code}")
def redirect(
    code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Look up a short code and redirect to its URL, or 404.

    Uses the cache-aside pattern (see services.resolve_long_url): Redis first,
    database on a miss. The `X-Cache` response header exposes HIT/MISS so you
    can watch the cache working. A click event is recorded in the background so
    analytics never slow the redirect down.

    NOTE: this catch-all route must stay registered AFTER the specific routes
    above (and FastAPI's own /docs). `db` is injected per-request by `get_db`.
    """
    long_url, cache_status = services.resolve_long_url(db, code)
    if long_url is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    # Record the click AFTER the response is sent — zero added latency.
    background_tasks.add_task(
        services.record_click,
        code,
        request.headers.get("referer"),   # note: HTTP misspells it "referer"
        request.headers.get("user-agent"),
    )

    response = RedirectResponse(url=long_url)
    response.headers["X-Cache"] = cache_status
    return response
