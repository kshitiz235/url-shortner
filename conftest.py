"""
pytest configuration.

Two jobs:
1. Put the project root on the import path so tests can do
   `from src.app.main import app`.
2. Force a *SQLite* database for tests BEFORE the app is imported. Real
   environment variables take precedence over the `.env` file, so this makes
   tests fast and isolated — no PostgreSQL needed to run them. This works only
   because we use an ORM: the exact same app code runs on SQLite here and on
   PostgreSQL in production.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Must be set before `src.app.config` is imported anywhere.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_db.sqlite3")
