"""
Request/response schemas (a.k.a. "models").

Pydantic models describe the *shape* of the JSON going in and out of the API.
FastAPI uses them to (1) validate incoming data and (2) document the API
automatically. If the client sends something that doesn't fit, FastAPI returns
a helpful 422 error before our code ever runs — we get validation for free.
"""
from datetime import datetime

from pydantic import BaseModel, HttpUrl


class ShortenRequest(BaseModel):
    """The body a client sends to create a short link."""
    # HttpUrl isn't just a string — Pydantic verifies it's a valid URL.
    url: HttpUrl


class ShortenResponse(BaseModel):
    """What we send back after creating a short link."""
    code: str        # the short code, e.g. "aB3xK"
    short_url: str   # the full short URL, e.g. "http://localhost:8000/aB3xK"


class ReferrerCount(BaseModel):
    """One row of the 'top referrers' breakdown."""
    referrer: str | None
    count: int


class StatsResponse(BaseModel):
    """Click analytics for a single short link."""
    code: str
    long_url: str
    total_clicks: int
    last_clicked: datetime | None
    top_referrers: list[ReferrerCount]
