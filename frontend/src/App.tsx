// The main React component. It renders two panels:
//   1) a form to shorten a URL, and
//   2) a lookup to view a code's click analytics.
//
// React idea in one line: the UI is a function of *state*. When we call a
// setter (e.g. setResult), React re-renders the parts that depend on it.

import { useState } from "react";
import {
  API_BASE,
  getStats,
  shortenUrl,
  type ShortenResponse,
  type StatsResponse,
} from "./api";
import "./App.css";

export default function App() {
  return (
    <div className="page">
      <header className="header">
        <h1>🔗 URL Shortener</h1>
        <p className="subtitle">Shorten links and track their clicks.</p>
      </header>

      <main className="panels">
        <ShortenPanel />
        <StatsPanel />
      </main>

      <AboutPanel />

      <footer className="footer">
        FastAPI + PostgreSQL + Redis backend · React + Vite frontend
      </footer>
    </div>
  );
}

function ShortenPanel() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<ShortenResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault(); // stop the browser's default form navigation
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await shortenUrl(url.trim());
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function copyShortUrl() {
    if (!result) return;
    await navigator.clipboard.writeText(result.short_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <section className="card">
      <h2>Shorten a URL</h2>
      <form onSubmit={handleSubmit} className="form">
        <input
          type="url"
          placeholder="https://example.com/a/very/long/link"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
        />
        <button type="submit" disabled={loading || url.trim() === ""}>
          {loading ? "Shortening…" : "Shorten"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="result">
          <span className="result-label">Your short link:</span>
          <div className="result-row">
            <a href={result.short_url} target="_blank" rel="noreferrer">
              {result.short_url}
            </a>
            <button className="ghost" onClick={copyShortUrl}>
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <span className="hint">
            Code: <code>{result.code}</code> — paste it into the analytics panel →
          </span>
        </div>
      )}
    </section>
  );
}

function StatsPanel() {
  const [code, setCode] = useState("");
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setStats(null);
    setLoading(true);
    try {
      const data = await getStats(code.trim());
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <h2>Click analytics</h2>
      <form onSubmit={handleSubmit} className="form">
        <input
          type="text"
          placeholder="short code, e.g. 1"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          required
        />
        <button type="submit" disabled={loading || code.trim() === ""}>
          {loading ? "Loading…" : "Look up"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {stats && (
        <div className="stats">
          <div className="stat-grid">
            <div className="stat">
              <span className="stat-number">{stats.total_clicks}</span>
              <span className="stat-caption">total clicks</span>
            </div>
            <div className="stat">
              <span className="stat-number">
                {stats.last_clicked
                  ? new Date(stats.last_clicked).toLocaleString()
                  : "—"}
              </span>
              <span className="stat-caption">last click</span>
            </div>
          </div>

          <p className="stats-url">
            →{" "}
            <a href={stats.long_url} target="_blank" rel="noreferrer">
              {stats.long_url}
            </a>
          </p>

          <h3>Top referrers</h3>
          {stats.top_referrers.length === 0 ? (
            <p className="hint">No clicks yet.</p>
          ) : (
            <table className="referrers">
              <thead>
                <tr>
                  <th>Referrer</th>
                  <th>Clicks</th>
                </tr>
              </thead>
              <tbody>
                {stats.top_referrers.map((row, i) => (
                  <tr key={i}>
                    <td>{row.referrer ?? "(direct / none)"}</td>
                    <td>{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      <p className="api-note">
        API: <code>{API_BASE}</code>
      </p>
    </section>
  );
}

// A showcase panel: click to reveal everything the project is built with and
// the engineering concepts it demonstrates. Turns the live app into a portfolio
// piece.
const GITHUB_URL = "https://github.com/kshitiz235/url-shortner";

const STACK: { group: string; items: string[] }[] = [
  {
    group: "Backend",
    items: ["Python 3.14", "FastAPI", "SQLAlchemy ORM", "PostgreSQL", "Redis", "Pydantic"],
  },
  { group: "Frontend", items: ["React", "TypeScript", "Vite"] },
  {
    group: "DevOps / Infra",
    items: ["Docker", "docker-compose", "Nginx", "Railway", "GitHub Actions", "GitHub Pages"],
  },
];

const FEATURES: string[] = [
  "Collision-free base-62 short codes derived from the database id",
  "Cache-aside redirects served from Redis for a fast read path",
  "Per-IP rate limiting on link creation (HTTP 429 + Retry-After)",
  "Click analytics: total clicks, last click, and top referrers",
  "Asynchronous click logging that never slows the redirect",
  "Typed REST API with auto-generated OpenAPI docs",
  "14 automated tests (pytest) running on SQLite for speed",
];

const CONCEPTS: string[] = [
  "REST API design & dependency injection",
  "Relational schema design, indexing & foreign keys",
  "Caching strategy, TTLs & cache invalidation",
  "Rate-limiting algorithms (fixed window)",
  "CORS & the browser same-origin policy",
  "Containerization & config-over-code deployment",
];

function AboutPanel() {
  const [open, setOpen] = useState(false);

  return (
    <section className="about">
      <button className="about-toggle" onClick={() => setOpen((o) => !o)}>
        {open ? "▾  Hide details" : "▸  How this was built — tech stack & features"}
      </button>

      {open && (
        <div className="about-body">
          <p className="about-intro">
            A read-optimized <strong>URL shortener with click analytics</strong>, built full-stack
            from scratch: a Python API, a real database and cache, a React frontend, and a
            containerized, cloud-deployed setup.
          </p>

          <div className="about-flow">
            Browser → React&nbsp;(GitHub&nbsp;Pages) → FastAPI&nbsp;(Railway) → Redis&nbsp;cache
            ⇄ PostgreSQL
          </div>

          <h3>Tech stack</h3>
          <div className="about-stack">
            {STACK.map((col) => (
              <div key={col.group} className="stack-col">
                <span className="stack-group">{col.group}</span>
                <div className="chips">
                  {col.items.map((item) => (
                    <span key={item} className="chip">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="about-cols">
            <div>
              <h3>Key features</h3>
              <ul>
                {FEATURES.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Engineering concepts</h3>
              <ul>
                {CONCEPTS.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          </div>

          <a className="about-github" href={GITHUB_URL} target="_blank" rel="noreferrer">
            View source on GitHub →
          </a>
        </div>
      )}
    </section>
  );
}
