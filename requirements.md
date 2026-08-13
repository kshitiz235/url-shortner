# Requirements — URL Shortener + Analytics

## Functional requirements
1. **Create short link:** Given a valid URL, return a unique short code and full short URL.
2. **Redirect:** Visiting `/{code}` redirects (HTTP 3xx) to the original URL.
3. **Reject invalid input:** Non-URL input returns a clear validation error (HTTP 422).
4. **Handle unknown codes:** Visiting a non-existent code returns HTTP 404.
5. **Analytics (later):** Each redirect records a click event (timestamp, referrer, IP → country).
6. **Stats endpoint (later):** Return click counts and breakdowns for a given code.
7. **Rate limiting (later):** Limit link creation per IP to prevent abuse.
8. **Web UI (later):** Create links and view stats in the browser.

## Non-functional requirements
- **Fast redirects:** Redirects should be served primarily from cache (target: cache the hot path).
- **Read-heavy design:** Optimize for many reads (redirects) vs few writes (creations).
- **Durability:** Links must survive server restarts (needs a real database — Milestone 2).
- **Scalability:** Design should allow horizontal scaling (stateless API + shared cache/DB).
- **Security basics:** Validate input, rate-limit abuse, avoid open-redirect pitfalls, no secrets in code.

## Out of scope (for now)
- Custom vanity domains
- User accounts / link ownership (may add later)
- Link expiration & editing
