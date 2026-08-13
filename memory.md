# Project Memory — URL Shortener + Analytics

> The single source of truth for the **current state** of this project.
> Read this first when resuming. (README = docs for others, learning-notes = concepts, interview-notes = interview prep.)

## Project goal
Build a scalable URL shortener with click analytics — a classic **system-design** project that demonstrates backend engineering: fast redirects, caching, rate limiting, database indexing, and analytics. Resume target: Backend / Full-stack. This is **Project #4**; **Project #1 (RAG Knowledge Assistant)** comes next.

## Technology stack
- **Language:** Python 3.14
- **API framework:** FastAPI (+ Uvicorn ASGI server)
- **Validation:** Pydantic v2
- **Database (Milestone 2+):** PostgreSQL
- **Cache / rate limiting (Milestone 4+):** Redis
- **Frontend (Milestone 7):** minimal HTML/JS (React optional later)
- **Testing:** pytest + FastAPI TestClient (httpx)
- **Packaging/deploy (Milestone 8):** Docker

## Architecture (target)
Two hot paths:
- **Write path (rare):** `POST /api/shorten` → generate unique code → store {code → long_url} → return short URL.
- **Read path (constant):** `GET /{code}` → check Redis → miss → Postgres → cache it → log click (async) → HTTP redirect.
Design principle: reads vastly outnumber writes, so cache aggressively and never let analytics logging slow the redirect.

## Important decisions
- **Python + FastAPI** chosen over Go/Node for continuity with the next project (#1 RAG is also Python) and gentle learning curve. (Decided 2026-08-13.)
- Folder: `projects/url-shortener/`.
- Milestone 1 uses an **in-memory dict store** so the core flow is visible before adding DB complexity.
- Short codes: random 6-char for M1; will switch to **base-62 encoding of a numeric ID** in Milestone 3 (deterministic, collision-free).

## Milestones
1. **Foundation** — API skeleton: shorten + redirect, in-memory store.  ← CURRENT
2. Database — PostgreSQL, schema, persistence, indexing.
3. Short-code generation — base-62 encoding, collision handling.
4. Caching — Redis for fast redirects.
5. Rate limiting — protect the create endpoint.
6. Analytics — click tracking + stats endpoint.
7. Frontend — minimal UI.
8. Testing, error handling & deployment — Docker + docs.

## Current progress
- [x] Project structure created
- [x] Doc files created (memory/README/learning-notes/interview-notes/requirements)
- [x] Milestone 1 code written
- [x] venv created (.venv), deps installed (fastapi 0.141, uvicorn 0.52, pydantic 2.13, pytest 9.1)
- [x] **Milestone 1 VERIFIED** — 4/4 tests pass (health, shorten→redirect, 404, 422 validation)
- [x] **Milestone 2: Database VERIFIED** — 5/5 tests pass; user confirmed links persist in real PostgreSQL and survive restart. DB `urlshortener` created, `.env` configured with local Postgres creds.
- [x] **Milestone 3: base-62 short codes VERIFIED** — user confirmed codes 1,2,3 derived from ids, stored in Postgres. 10/10 tests pass.
- [x] **Milestone 4: Redis caching** — code complete, 11/11 tests pass. Cache-aside pattern in `services.resolve_long_url`, `cache.py` swappable client (fakeredis dev / real Redis prod), 1h TTL, `X-Cache: HIT|MISS` header. No schema change → user just restarts to verify.
- [x] **Milestone 5: Rate limiting** — code complete, 12/12 tests pass. Fixed-window counter in `ratelimit.py` (Redis INCR + EXPIRE), applied to POST /api/shorten as a dependency, returns 429 + Retry-After. Defaults: 10 req / 60s per IP (configurable). No schema change → restart to verify.
- [x] **Milestone 6: Click Analytics** — code complete, 14/14 tests pass. New `clicks` table (FK link_id→links.id, indexed, cascade), background click logging via BackgroundTasks (records referrer + user-agent, off the redirect path), `GET /api/stats/{code}` aggregates total/last/top-referrers via SQL COUNT/MAX/GROUP BY. Adds a table → `create_all` makes it on restart (no reset).
- [x] **Milestone 7: React frontend VERIFIED** — separate `frontend/` app (React + Vite + TS). Shorten panel + analytics panel. Backend CORS added (CORSMiddleware, config `cors_origins`). Typed API client `frontend/src/api.ts`. Builds clean; verified live end-to-end in browser (create link + view click stats). Frontend :5173, backend :8000.
- [x] **Milestone 8: Docker & deployment** — code complete, compose validated (`docker compose config` OK). Backend `Dockerfile`, `.dockerignore`, frontend multi-stage `Dockerfile` + `nginx.conf`, `docker-compose.yml` (db+redis+api+web, healthchecks, pgdata volume). Real Redis via REDIS_URL. Docs finalized: README (Docker + deployment guide Routes A/B), interview-notes (24 Qs + résumé bullets), learning-notes M8. PENDING VERIFY: user starts Docker Desktop then `docker compose up --build`.

## 🎉 PROJECT CORE COMPLETE — all 8 milestones built. 14 tests passing.
Deployment target: undecided (build-Docker-now chosen). User considering Railway (Route A) vs Supabase+Upstash+Render+GitHub Pages (Route B). Docker is host-agnostic; finalize target when deploying.
Possible future work: Alembic migrations (replace create_all), custom domain for BASE_URL, negative-cache/stampede protection, sliding-window rate limit, analytics via queue/stream, user accounts, link expiry/editing.

## Docker commands
```bash
docker compose up --build      # start whole stack (frontend :8080, api :8000)
docker compose down -v         # stop and wipe volumes
```

## Database structure (current)
- `links(id PK, code UNIQUE indexed nullable, long_url, created_at)`
- `clicks(id PK, link_id FK→links.id indexed, clicked_at, referrer, user_agent)`

## New files (M4–M6)
- `cache.py` — Redis/fakeredis client (chosen via `REDIS_URL`, default "fake")
- `services.py` — cache-aside `resolve_long_url` (url + HIT/MISS) + `record_click` (background, own session)
- `ratelimit.py` — fixed-window rate limiter dependency (`enforce_rate_limit`)

## Endpoints
- `POST /api/shorten` (rate-limited) · `GET /{code}` (redirect, cached, logs click) · `GET /api/stats/{code}` · `GET /health` · `GET /docs`

## Design note
- We intentionally allow the same URL to be shortened to multiple codes (no dedup) so per-code analytics stay separate. Dedup-by-URL-hash is a documented alternative.

## Completed features
- Create short link (`POST /api/shorten`) with URL validation
- Redirect (`GET /{code}` → 307) with 404 on unknown codes
- Health check (`GET /health`)
- **Database persistence via SQLAlchemy ORM** (Postgres in prod, SQLite in tests)
- Config via `.env` (pydantic-settings), per-request DB sessions (Depends), indexed unique `code` column

## Milestone 2 architecture notes
- Files: `config.py` (settings), `database.py` (engine/session/Base/get_db), `tables.py` (Link model), `crud.py` (create_link/get_link_by_code), `main.py` (routes via Depends).
- `store.py` (in-memory) removed — logic moved to DB layer.
- Env: PostgreSQL 18 running locally on :5432. psycopg 3.3.4, SQLAlchemy 2.0.52.
- DB name planned: `urlshortener`, user `postgres` (least-privilege dedicated role noted as future improvement).
- Schema mgmt: `create_all()` on startup for now; Alembic migrations = future improvement.

## Remaining features
- Persistence, base-62 codes, caching, rate limiting, analytics, frontend, deployment.

## Known bugs
- None yet. Note: `GET /{code}` is a catch-all route; must stay registered AFTER specific routes and reserved paths handled in later milestones.

## Important commands
```bash
# From projects/url-shortener/  (after venv is set up & activated)
uvicorn src.app.main:app --reload         # run dev server at http://localhost:8000
pytest                                     # run tests
```
Interactive API docs auto-served at http://localhost:8000/docs

## Environment requirements
- Python 3.14 (installed). Virtual environment in `.venv/`.
- Later: PostgreSQL, Redis (likely via Docker).

## APIs / services used
- None external yet. (Future: none required for core; deployment target TBD.)

## Database structure
- Not built yet. Planned tables (Milestone 2):
  - `links(id PK, code UNIQUE, long_url, created_at)`
  - `clicks(id PK, link_id FK, clicked_at, referrer, ip, country)`

## Learning topics covered
- REST API basics, FastAPI routing, Pydantic validation, in-memory storage, HTTP redirects, project structure. (See learning-notes.md.)

## Learning topics remaining
- Base-62 encoding, DB indexing, caching strategy & TTLs, rate-limiting algorithms, async analytics, Docker, deployment.

## Next recommended task
Finish Milestone 1: install dependencies into a venv, run the server, verify shorten + redirect work, then move to Milestone 2 (database).
