# Interview Notes — URL Shortener

Design decisions, tradeoffs, and likely interview questions for this project. Update as we go.

---

## Decision log

### Why FastAPI (vs Flask/Django/Go)?
- **Chosen:** FastAPI. Async-capable, automatic validation (Pydantic) and auto-generated OpenAPI docs, minimal boilerplate.
- **Alternatives:** Flask (simpler but manual validation/docs), Django (batteries-included but heavy for an API-only service), Go (fastest, best concurrency, but steeper and less reuse for our next Python project).
- **Tradeoff:** FastAPI gives excellent developer velocity and "good enough" performance; a raw Go service would squeeze out more throughput at the cost of dev speed.

### In-memory store first, database later
- **Why:** isolate and demonstrate the core flow before adding infrastructure.
- **Tradeoff:** not durable, not shareable across instances — intentionally, to motivate the DB milestone.

---

## The classic system-design talking points (prepare these)

**Q: How do you generate short codes?**
- Random codes + collision check (our M1) is simple but wastes effort at scale.
- Better: take a **monotonic numeric ID** (from a DB sequence) and **base-62 encode** it (`0-9a-zA-Z` = 62 chars). 6 base-62 chars ≈ 56 billion combinations. Deterministic, no collisions.
- At very large scale: distributed ID generation (e.g. Snowflake IDs, or pre-allocated ID ranges per server) to avoid a single DB sequence bottleneck.

**Q: How do you make redirects fast?**
- Reads ≫ writes. Cache `code → long_url` in **Redis**. On a redirect: check cache first; on miss, read DB and populate cache. Most redirects never touch the DB.

**Q: How do you handle analytics without slowing redirects?**
- Log click events **asynchronously** (fire-and-forget / background task / queue) so the redirect returns immediately. Aggregate counts separately.

**Q: How would this scale horizontally?**
- API servers are **stateless** → run many behind a load balancer. Shared state lives in Redis + Postgres. Add read replicas / sharding for the DB as it grows.

**Q: Security concerns?**
- Validate URLs; **rate-limit** creation to stop abuse; be careful about **open redirects** (we only redirect to URLs we stored, which mitigates it); never log secrets; use HTTPS in production.

**Q: What are the failure modes?**
- Cache down → fall back to DB (slower but works). DB down → creations fail, cached redirects still work. Hot key → a viral link is fine (it's cached). Collisions → handled by unique constraint + retry.

**Q: How do you rate-limit an API?**
- Fixed window (simple, Redis INCR + EXPIRE; boundary-burst weakness), sliding window (accurate, pricier), token bucket (allows controlled bursts). Return **429** + **Retry-After**. Do it in Redis so the count is atomic and shared across all API instances. Behind a proxy, key on `X-Forwarded-For`, not the socket IP.

**Q: Why base rate limiting in Redis instead of app memory?**
- App memory isn't shared across horizontally-scaled instances (each would keep its own count) and is lost on restart. Redis gives one shared, atomic, expiring counter.

---

### Why Docker + docker-compose
- **Chosen:** containerize each service; compose to orchestrate api + Postgres + Redis + web.
- **Why:** identical environment everywhere, one-command startup, host-agnostic deploy.
- **Tradeoff:** slightly more upfront setup vs. running bare processes, but pays off in reproducibility and deployment.

### Deployment approach
- Four hostable pieces: static frontend, Postgres, Redis, Python backend.
- Everything driven by env vars (`DATABASE_URL`, `REDIS_URL`, `BASE_URL`, `CORS_ORIGINS`) → config over code.
- Route A: Railway (backend+DB+Redis) + GitHub Pages/Vercel. Route B: Supabase (DB) + Upstash (Redis) + Render/Fly (backend) + GitHub Pages.
- Production hardening: platform-managed secrets, Alembic migrations instead of `create_all`, HTTPS, trust `X-Forwarded-For`.

---

## Generated interview questions (final set)

**Architecture & design**
1. Walk me through, step by step, what happens when a user visits a short URL.
2. Why is a URL shortener read-heavy, and how does that shape the design?
3. How would you scale this to millions of redirects per minute?
4. Which parts are stateless, and why does that matter for horizontal scaling?

**Short codes**
5. Explain base-62 encoding and why ~6–7 characters is "enough."
6. How do you guarantee two links never get the same code? (deterministic id encoding vs random+retry)
7. What's the flush-vs-commit trick you used to encode the row id, and why was the column nullable?

**Database**
8. Why did you index the `code` column? What does the index cost you on writes?
9. Explain the `links` ↔ `clicks` foreign-key relationship and the cascade.
10. You changed a column's nullability — how do you apply that safely to a live database? (→ migrations)

**Caching**
11. Describe the cache-aside pattern. What exactly do you cache, and for how long?
12. Why is cache invalidation "easy" in this project? When would it get hard?
13. What happens on a cache miss, and how do you avoid a cache stampede on a hot key?

**Rate limiting**
14. Compare fixed-window, sliding-window, and token-bucket. Which did you pick and why?
15. Why implement the counter in Redis instead of app memory?
16. Behind a load balancer, how do you identify the real client IP?

**Analytics**
17. How do you record a click without slowing the redirect? (BackgroundTasks; own DB session)
18. Why aggregate in SQL (`COUNT`/`GROUP BY`) instead of in Python?
19. How would this analytics pipeline evolve at high volume? (queue/stream + batch)

**Frontend & CORS**
20. Why did the browser block your API calls at first, and how does CORS fix it?
21. What is the preflight `OPTIONS` request?
22. Why is `VITE_API_BASE_URL` a build-time value, and why only `VITE_`-prefixed vars?

**Ops**
23. What does docker-compose give you over running each process by hand?
24. How do you configure the same image for dev vs production without code changes?

---

## Résumé bullets (pick 2–3)
- Built a **read-optimized URL shortener with click analytics** (FastAPI, PostgreSQL, Redis, React/TypeScript) featuring **cache-aside redirects**, **collision-free base-62 codes**, and **per-IP rate limiting**.
- Designed a **cache-aside layer (Redis)** in front of PostgreSQL that serves the redirect hot-path from memory, with a swappable client (fakeredis in tests, real Redis in prod).
- Implemented **non-blocking click analytics** via background tasks and SQL aggregation, and a **fixed-window rate limiter** returning HTTP 429.
- **Containerized the full stack with Docker Compose** (API + PostgreSQL + Redis + Nginx-served React) — one-command startup, deployable to any host via environment config.
- Wrote a **14-test suite** running the ORM code against SQLite for speed while production uses PostgreSQL.
