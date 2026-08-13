# URL Shortener + Analytics

A fast, scalable URL shortener with click analytics — built as a backend / system-design portfolio project.

Turn a long URL into a short code (`http://localhost:8000/aB3xK`) and redirect visitors to the original, while tracking click analytics. Designed around the reality that redirects (reads) vastly outnumber link creation (writes), so it leans on caching and efficient storage.

## Features
- Create short links via a REST API
- Fast redirects from short code → original URL, served from a Redis cache
- Collision-free base-62 short codes derived from the row id
- Click analytics (count, last click, top referrers) via `GET /api/stats/{code}`
- Rate limiting (per-IP) on link creation to prevent abuse
- Minimal web UI — *planned*

## Tech stack
Python 3.14 · FastAPI · Pydantic · PostgreSQL · Redis · Docker · pytest

## Project structure
```
url-shortener/
├── README.md            # this file — docs for anyone
├── memory.md            # current project state (for resuming work)
├── learning-notes.md    # concepts explained as we build
├── interview-notes.md   # design decisions + interview prep
├── requirements.md      # product/functional requirements
├── requirements.txt     # Python dependencies
├── conftest.py          # makes `src` importable in tests
├── src/
│   └── app/
│       ├── main.py      # FastAPI app + routes
│       ├── models.py    # request/response schemas
│       └── store.py     # storage layer (in-memory for now)
└── tests/
    └── test_main.py     # API tests
```

## Getting started
```bash
# 1. From projects/url-shortener/, create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell/CMD)
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the dev server
uvicorn src.app.main:app --reload

# 4. Open the interactive API docs
#    http://localhost:8000/docs
```

## Usage
```bash
# Create a short link
curl -X POST http://localhost:8000/api/shorten \
     -H "Content-Type: application/json" \
     -d "{\"url\": \"https://example.com/a/very/long/path\"}"
# -> {"code":"aB3xK","short_url":"http://localhost:8000/aB3xK"}

# Visit the short URL in a browser to be redirected.

# View click analytics for a code
curl http://localhost:8000/api/stats/aB3xK
# -> {"code":"aB3xK","long_url":"...","total_clicks":3,"last_clicked":"...","top_referrers":[...]}
```

## Frontend (React + Vite + TypeScript)
A separate single-page app in `frontend/` that consumes the API.

```bash
cd frontend
npm install            # first time only
npm run dev            # dev server at http://localhost:5173
```
The API base URL is configured in `frontend/.env` (`VITE_API_BASE_URL`). The
backend must be running and must allow the frontend's origin via CORS
(configured by `CORS_ORIGINS`, default `http://localhost:5173`).

To run both together: start the backend (`uvicorn ...`) in one terminal and the
frontend (`npm run dev`) in another.

## Run everything with Docker (recommended)
One command starts the backend, **real PostgreSQL**, **real Redis**, and the
frontend together:

```bash
docker compose up --build
```
- Frontend: http://localhost:8080
- Backend API + docs: http://localhost:8000/docs

(Requires Docker Desktop running.) Data persists in the `pgdata` volume between
runs. Stop with `Ctrl+C`; remove everything with `docker compose down -v`.

## Deployment
The app is four pieces: **frontend** (static), **PostgreSQL**, **Redis**, and
the **FastAPI backend** (runs Python). Everything is configured by environment
variables, so the same Docker image deploys anywhere:

| Env var | Purpose | Example (production) |
|---|---|---|
| `DATABASE_URL` | Postgres connection | `postgresql+psycopg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection | `redis://host:6379/0` |
| `BASE_URL` | Domain used in short links | `https://sho.rt` |
| `CORS_ORIGINS` | Allowed frontend origin(s) | `https://your-frontend.example` |

**Two recommended paths:**
- **Route A (simplest):** backend + Postgres + Redis on **Railway**, frontend on
  **GitHub Pages** or Vercel.
- **Route B (free mix):** Postgres on **Supabase**, Redis on **Upstash**, backend
  on **Render/Railway/Fly**, frontend on **GitHub Pages**.

**Production checklist:** set secrets via the platform (never commit `.env`),
switch `create_all()` to Alembic migrations, serve over HTTPS, and point
`CORS_ORIGINS` / `BASE_URL` at your real domains.

## Running tests
```bash
pytest
```

## Status
🚧 In active development — currently **Milestone 1 (Foundation)**. See `memory.md` for the roadmap.
