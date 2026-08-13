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
