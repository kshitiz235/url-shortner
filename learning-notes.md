# Learning Notes — URL Shortener

Concepts explained as we build them. Written so you can re-read later and *teach it back*.

---

## Milestone 1 — Foundation

### What is an ASGI app / FastAPI?
- **HTTP** is a request→response protocol: a client sends a request (method + path + body), the server sends back a response (status code + body).
- A **web framework** saves you from parsing raw HTTP by hand. **FastAPI** lets you map a URL path + method to a Python function ("route handler").
- **ASGI** (Asynchronous Server Gateway Interface) is the modern Python standard for how a web server talks to a web app. **Uvicorn** is the ASGI *server* that runs our FastAPI *app*. So: browser → Uvicorn → FastAPI → our function.

### Routing
- `@app.post("/api/shorten")` registers a function to handle `POST` requests to that path.
- `@app.get("/{code}")` uses a **path parameter**: the `{code}` part is captured and passed to the function as an argument. Visiting `/aB3xK` calls `redirect(code="aB3xK")`.
- **Order matters:** `/{code}` is a *catch-all* for any single path segment. Specific routes (like `/health`, `/api/shorten`) must be matched first. FastAPI matches routes in registration order, and its own `/docs` routes are registered before ours, so they win.

### Pydantic validation (why we don't trust input)
- `class ShortenRequest(BaseModel): url: HttpUrl` — Pydantic automatically parses the JSON body and **validates** that `url` is a real URL. If it isn't, FastAPI returns a `422 Unprocessable Entity` with a helpful error — we never wrote that error-handling code ourselves.
- This is the "**never trust client input**" principle enforced declaratively by types.

### HTTP redirects
- A redirect is just a response with a `3xx` status code and a `Location` header telling the browser where to go.
- We return `RedirectResponse(url=long_url)` — the browser then makes a *second* request to the original URL. This is why the short link "just works" in the address bar.

### Why in-memory first?
- We store links in a plain Python `dict` for Milestone 1. This makes the **core flow** obvious with zero setup.
- Its flaw teaches the next lesson: **data is lost on restart** and can't be shared across multiple server instances → that's exactly *why* Milestone 2 introduces a real database.

### Storage abstraction (why a separate `store.py`)
- Routes shouldn't care *how* data is stored. By hiding storage behind a small class (`save()` / `get()`), we can swap the in-memory dict for PostgreSQL later **without touching the route code**. This is the **separation of concerns** principle — and it makes the DB migration in Milestone 2 painless.

### Testing early (FastAPI TestClient)
- `TestClient(app)` lets tests call the API in-process (no running server needed) and assert on responses.
- We test: health check works, shorten→redirect round-trips, and unknown codes 404. Tests are our safety net for every future change.

---

---

## Milestone 2 — Database (PostgreSQL + SQLAlchemy ORM)

### Why the in-memory dict had to go
A dict lives in one process's RAM: **wiped on restart** and **not shared** between multiple server copies. A database gives durability + a single shared source of truth.

### What an ORM is (SQLAlchemy)
- An **ORM** (Object-Relational Mapper) maps Python classes ↔ database tables and objects ↔ rows. You write Python; it generates SQL.
- Benefits: less boilerplate, protection from **SQL injection** (values are parameterized), and **portability** — the same code ran on PostgreSQL *and* SQLite (our tests) with only the connection URL changing.

### Engine, Session, Base
- **engine** — created once; owns a *connection pool* (reuses TCP connections instead of opening one per query).
- **Session** — one "unit of work": you make changes, then `commit()` (save) or `rollback()` (undo) as a group. We use **one session per request**.
- **Base** — the parent class every table model inherits from; collects all table definitions.

### Dependency Injection (`Depends(get_db)`)
FastAPI calls `get_db()` for each request, hands the session to the route, and runs the `finally: db.close()` afterward — even if the route raises. Clean, leak-free resource management.

### Schema design & indexing
- `links` table: `id` (PK), `code` (unique, **indexed**), `long_url` (text), `created_at`.
- An **index** on `code` turns redirect lookups from "scan every row" (O(n)) into a fast tree lookup (~O(log n)). Since redirects are the hot path, this index is essential.
- `unique=True` makes the **database** the final guarantor that no two links share a code.

### Config & secrets
- The DB password comes from a gitignored `.env` file via `pydantic-settings` — **never hardcoded**. Environment variables override `.env`, which is how tests force SQLite.

---

## Milestone 3 — Base-62 short codes

### From random to deterministic
- M1/M2 used **random** codes + a retry loop on collision. As the table fills, collisions (and retries) grow.
- M3 encodes the row's **unique id** in **base-62** (`0-9a-zA-Z`, 62 symbols). Because the id is unique, the code is unique **with zero collision checks**. 6 base-62 chars ≈ 56.8 billion links.

### `flush` vs `commit` (the two-step insert)
We can't know a row's `id` until it's inserted. So:
1. `db.add(link); db.flush()` — sends the INSERT and populates `link.id`, but doesn't finalize the transaction.
2. `link.code = base62.encode(link.id); db.commit()` — sets the code and makes it permanent.
- **flush** = "send the SQL now (get generated values)"; **commit** = "make it permanent." The `code` column is nullable *only* to permit that instant between the two steps.

### Schema change → why migrations exist
Changing `code` from NOT NULL to nullable means the existing table must be updated. Our dev setup uses `create_all()`, which only creates *missing* tables — it won't alter an existing one. In development we just drop & recreate the table. In production you can't drop live data — that's exactly why real projects use a **migration tool (Alembic)** to version and apply schema changes safely. (Planned as a future improvement.)

### A caveat worth knowing
Early ids give very short codes ("1", "2"). In production you'd typically add a large **offset** (start ids high) so codes have a uniform, less-guessable length, and you'd keep a **reserved-word list** so a generated code can never equal a real route like `docs` or `health`.

---

---

## Milestone 4 — Caching with Redis (fast redirects)

### Why cache at all
Redirects are ~99% of traffic and the database is the slowest/most-contended component. Serving redirects from an in-memory cache keeps the DB free for the rare writes and lets the system handle huge read volumes.

### The cache-aside pattern (what we implemented)
On a redirect (`services.resolve_long_url`):
1. **Check Redis** for `code:<code>`. If present → **HIT**, return immediately.
2. **Miss** → query Postgres. If not found, return 404.
3. **Populate** Redis with the result and a **TTL**, so the *next* request is a HIT.

The `X-Cache: HIT|MISS` response header makes this visible in the browser/curl.

### TTL (time-to-live)
Each cache entry auto-expires (we use 1 hour, `ex=3600`). This bounds memory use and means stale data can't live forever. Tuning the TTL trades freshness vs DB load.

### Cache invalidation (and why we mostly dodge it)
"There are only two hard things in CS: cache invalidation and naming things." Our links are **immutable** (a code always maps to the same URL), so there's nothing to invalidate — the easiest correct cache. If we ever allowed editing/deleting a link, we'd have to delete its cache key too.

### Programming to an interface (swappable client)
`cache.py` returns either `fakeredis` (dev/tests, no install) or real Redis — both speak the same API, so the app code is identical. Same trick as the ORM (SQLite vs Postgres). At deployment we just set `REDIS_URL=redis://...`.

### Advanced topics we noted but skipped
- **Caching negative lookups** (missing codes) to prevent "cache penetration" attacks.
- **Cache stampede** protection when a hot key expires and many requests miss at once.

---

---

## Milestone 5 — Rate limiting

### Why
`POST /api/shorten` writes to the database. Left unprotected, one client could flood it with junk and degrade the service for everyone. Rate limiting caps requests per client per time window.

### The three classic algorithms
- **Fixed window** (what we built): count requests per clock window, reset each window. Simple; weakness = a **burst at the boundary** (up to 2× the limit across the seam).
- **Sliding window**: track a rolling window for smoother, more accurate limiting. More complex/expensive.
- **Token bucket**: tokens refill at a steady rate; each request spends one. Allows controlled bursts — popular for public APIs.

### How ours works (`ratelimit.enforce_rate_limit`)
A FastAPI **dependency** on the create route:
1. `INCR ratelimit:shorten:<ip>` — atomic increment in Redis.
2. If it's the first hit (`== 1`), set the key's TTL to the window length.
3. If the count exceeds the limit, raise **HTTP 429 Too Many Requests** with a **`Retry-After`** header.

Because `INCR` is atomic, concurrent requests can't miscount — a key reason to do this in Redis rather than app memory (which also wouldn't be shared across servers).

### Correct HTTP semantics
- **429** is the standard "too many requests" status.
- **Retry-After** tells a well-behaved client how long to wait.

### Production note
`request.client.host` is the direct caller. Behind a proxy/load balancer, the real client IP is in the **`X-Forwarded-For`** header — you'd read that instead (and only trust it from known proxies).

---

---

## Milestone 6 — Click Analytics

### Foreign keys & relationships
- New `clicks` table with `link_id` → `links.id` (a **foreign key**): "many clicks belong to one link."
- `index=True` on `link_id` makes "count clicks for this link" fast.
- `ON DELETE CASCADE` + SQLAlchemy `relationship(cascade="all, delete-orphan")` means deleting a link cleans up its clicks automatically.
- The ORM `relationship()` lets us navigate both ways in Python: `link.clicks` and `click.link`.

### Async logging with BackgroundTasks (don't slow the redirect)
- Writing a click row costs time. We schedule it with FastAPI **`BackgroundTasks`**, which runs *after* the response is sent — the visitor gets their redirect instantly, the DB write happens behind the scenes.
- The background function opens its **own** DB session, because the request's session (`get_db`) is already closed once the response goes out.

### Aggregation in the database (not in Python)
- The stats endpoint uses SQL `COUNT`, `MAX`, and `GROUP BY ... ORDER BY ... LIMIT` to compute totals and top referrers. Letting the database aggregate is far cheaper than loading every row into Python.

### HTTP header trivia
- The referrer header is historically **misspelled "Referer"** in the HTTP spec — so we read `request.headers.get("referer")`.

### Production evolution (interview gold)
- A row-per-click INSERT is fine for a learning project, but at scale you'd push click events to a **queue/stream (e.g. Kafka)** and aggregate in batches, sparing the primary database. That's the natural next step for real analytics pipelines.

---

---

## Milestone 7 — React frontend (separate app)

### Two apps, not one
The frontend (`frontend/`, React + Vite + TypeScript on :5173) and the backend (FastAPI on :8000) are **independent services** that talk over HTTP. This mirrors real production setups and is the stronger full-stack story.

### React in one sentence
The UI is a **function of state**. `useState` holds a value (e.g. the shorten result); calling its setter re-renders just the parts that depend on it. No manual DOM manipulation.

### Vite + TypeScript
- **Vite**: instant dev server with hot-module reload, and a `tsc -b && vite build` production bundler (we saw it output a ~61 KB gzipped bundle).
- **TypeScript**: our `api.ts` types (`ShortenResponse`, `StatsResponse`) mean the compiler catches shape mismatches before runtime.

### CORS — the key security concept
Browsers enforce the **Same-Origin Policy**: JS on `http://localhost:5173` may not call `http://localhost:8000` unless the server **opts in**. We added `CORSMiddleware` listing allowed origins. The browser first sends a **preflight `OPTIONS`** request; the server answers with `Access-Control-Allow-Origin`, and only then does the real request go through. (We verified this preflight by hand with curl.)

### Env-based config
The API URL comes from `VITE_API_BASE_URL` (in `frontend/.env`), exposed as `import.meta.env.VITE_API_BASE_URL`. Only `VITE_`-prefixed vars reach the browser — a guardrail so server secrets can't leak into client code.

### Async data flow
Form submit → `fetch()` the API → `await` JSON → `setState` → React re-renders with the result. Errors (422 invalid URL, 429 rate-limited, 404 unknown code) are mapped to friendly messages in `api.ts`.

---

---

## Milestone 8 — Docker & deployment

### Why Docker
A container bundles your code **and its exact environment** (Python version, deps, config) into an image that runs identically everywhere — killing "works on my machine." An **image** is the frozen blueprint; a **container** is a running instance.

### The Dockerfile (backend)
- Start from `python:3.14-slim`, install `requirements.txt` **as its own layer** (Docker caches it, so rebuilds skip re-installing unless deps change), then copy `src`.
- `CMD` runs uvicorn on `0.0.0.0` with `--proxy-headers` so it trusts `X-Forwarded-For` from a reverse proxy → rate limiting sees the real client IP.

### Multi-stage build (frontend)
- **Stage 1** uses Node to `npm run build` the React app into static files.
- **Stage 2** copies just those files into a tiny `nginx:alpine` image — the final image has no Node or source, only assets. Nginx serves them and does SPA routing (`try_files … /index.html`).
- Gotcha: Vite bakes `VITE_API_BASE_URL` in at **build time**, so it's passed as a Docker build `ARG`.

### docker-compose (orchestration)
- Declares four services: `db` (Postgres + a **volume** so data persists), `redis`, `api`, `web`.
- Services find each other by **name** on the compose network (`db`, `redis`) — not `localhost`.
- **Health checks** + `depends_on: condition: service_healthy` make the api wait until Postgres/Redis are actually ready.
- This is where **real Redis replaces fakeredis** — just by setting `REDIS_URL`.

### Config over code (the deployment payoff)
Every environment-specific value is an env var: `DATABASE_URL`, `REDIS_URL`, `BASE_URL`, `CORS_ORIGINS`. To deploy, you change env vars — **not code**. `BASE_URL` becomes your real domain, so short links become `https://yourdomain/e`.

### 12-factor & production hardening (noted)
- Secrets come from the platform's env vars, never a committed `.env`.
- Replace `create_all()` with **Alembic migrations** for safe schema changes on live data.
- Behind a proxy, trust `X-Forwarded-For` (done via uvicorn flags).
- Serve over HTTPS (managed platforms provide TLS).
