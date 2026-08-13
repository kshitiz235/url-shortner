"""
Database plumbing: engine, session factory, base class, and a session
dependency for FastAPI.

- **engine**: owns a *pool* of connections to the database. Created once.
- **SessionLocal**: a factory that produces a Session — one "unit of work"
  (a bundle of reads/writes committed together).
- **Base**: the parent class all our ORM table models inherit from.
- **get_db**: a FastAPI dependency that hands each request its own session and
  guarantees it's closed afterward (even if the request errors).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings


def _normalize_db_url(url: str) -> str:
    """Force the psycopg (v3) driver on managed-host URLs.

    Railway/Heroku/Supabase provide connection strings like
    `postgres://...` or `postgresql://...`, which SQLAlchemy would route to
    psycopg2 (not installed). We rewrite the scheme to `postgresql+psycopg`.
    Non-Postgres URLs (e.g. sqlite) pass through untouched.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.split("://", 1)[1]
    return url


DATABASE_URL = _normalize_db_url(settings.database_url)

# SQLite (used only in tests) needs this flag because the test client touches
# the connection from more than one thread. PostgreSQL ignores it.
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    """Yield a database session, then close it when the request is done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
