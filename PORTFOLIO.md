# URL Shortener + Analytics — Project Write-up

> A read-optimized URL shortener with click analytics — built full-stack and deployed to the cloud.

**🔗 Live demo:** https://kshitiz235.github.io/url-shortner/
**💻 Source:** https://github.com/kshitiz235/url-shortner

---

## Overview
A production-style URL shortener that turns long links into short codes, redirects
visitors instantly, and tracks click analytics. It's designed around the reality
that a shortener is **read-heavy** — redirects vastly outnumber link creation — so
it leans on a Redis cache in front of PostgreSQL to keep the redirect path fast.
Built end-to-end: a Python API, a relational database and cache, a typed React
frontend, and a containerized, cloud-deployed setup.

## Tech stack
- **Backend:** Python 3.14, FastAPI, SQLAlchemy (ORM), Pydantic
- **Data:** PostgreSQL (storage) · Redis (cache + rate-limit counters)
- **Frontend:** React, TypeScript, Vite
- **DevOps / Infra:** Docker, docker-compose, Nginx, Railway (backend + managed
  Postgres + Redis), GitHub Actions → GitHub Pages (frontend)
- **Testing:** pytest (14 tests)

## Key features
- **Collision-free base-62 short codes** derived from the database row id
- **Cache-aside redirects** served from Redis for a fast read path
- **Per-IP rate limiting** on link creation (HTTP 429 + `Retry-After`)
- **Click analytics** — total clicks, last click, and top referrers
- **Asynchronous click logging** (background tasks) that never slows the redirect
- **Typed REST API** with auto-generated OpenAPI/Swagger docs

## Engineering highlights
- Designed a **cache-aside layer** so the hot redirect path is served from memory,
  falling back to PostgreSQL only on a miss (with a visible `X-Cache: HIT/MISS` header).
- Implemented **deterministic base-62 code generation** from an auto-increment id —
  unique by construction, no random collision retries.
- Modeled a **`links` ↔ `clicks` foreign-key relationship** with an indexed lookup
  column and SQL aggregation (`COUNT` / `GROUP BY`) for analytics.
- Built a **fixed-window rate limiter** using atomic Redis `INCR`/`EXPIRE`.
- **Containerized the whole stack** with docker-compose (API + Postgres + Redis +
  Nginx-served React) and deployed it via **config-over-code** (all environment-specific
  values are env vars), so the same image runs locally and in the cloud.
- Wrote the ORM code to run against **SQLite in tests** (fast, zero-setup) while
  production uses **PostgreSQL** — same code, swappable database.

## Architecture
```
Browser → React (GitHub Pages) → FastAPI (Railway) → Redis cache ⇄ PostgreSQL
                                        └── background task → clicks table (analytics)
```

## Résumé bullets
- Built and deployed a full-stack, read-optimized URL shortener (FastAPI, PostgreSQL,
  Redis, React/TypeScript) with cache-aside redirects, base-62 codes, and per-IP rate limiting.
- Containerized the stack with Docker Compose and deployed to Railway + GitHub Pages
  using environment-based configuration.
- Implemented non-blocking click analytics via background tasks and SQL aggregation.

## Possible future work
- Custom short domain (e.g. `sho.rt/abc`) via DNS + `BASE_URL`
- Alembic migrations (replacing dev-time `create_all`)
- Id offset for longer, non-enumerable codes
- Analytics via a queue/stream (e.g. Kafka) at higher volume
