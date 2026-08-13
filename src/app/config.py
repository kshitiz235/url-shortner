"""
Application configuration.

Instead of hard-coding things like the database password or base URL, we load
them from the environment (or a local `.env` file). This is a security basic:
**secrets never live in source code**. pydantic-settings validates them and
gives us a typed `settings` object to import anywhere.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads a local `.env` file if present. Real environment variables take
    # precedence over the file (that's how tests force a SQLite database).
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # SQLAlchemy connection URL, e.g.
    #   postgresql+psycopg://user:password@localhost:5432/urlshortener
    database_url: str

    # Base URL used to build the full short link returned to clients.
    base_url: str = "http://localhost:8000"

    # Cache connection. The special value "fake" uses an in-process fakeredis
    # (no install needed). For real Redis use a URL like
    #   redis://localhost:6379/0
    redis_url: str = "fake"

    # Rate limiting for POST /api/shorten: at most `rate_limit_max` requests
    # per `rate_limit_window_seconds` per client IP.
    rate_limit_max: int = 10
    rate_limit_window_seconds: int = 60

    # Browser origins allowed to call this API (CORS). Comma-separated.
    # The Vite dev server runs on :5173 by default.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# A single, importable settings instance for the whole app.
settings = Settings()
