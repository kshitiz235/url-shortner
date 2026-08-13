// API client: every call to the FastAPI backend lives here, with TypeScript
// types describing the shapes the backend returns. Keeping this in one file
// means components don't deal with fetch/URLs directly.

// The backend base URL comes from an environment variable so we don't hardcode
// it (localhost in dev, a real domain in production). Vite exposes vars that
// start with VITE_ on `import.meta.env`.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface ShortenResponse {
  code: string;
  short_url: string;
}

export interface ReferrerCount {
  referrer: string | null;
  count: number;
}

export interface StatsResponse {
  code: string;
  long_url: string;
  total_clicks: number;
  last_clicked: string | null;
  top_referrers: ReferrerCount[];
}

/** Create a short link for a URL. */
export async function shortenUrl(url: string): Promise<ShortenResponse> {
  const res = await fetch(`${API_BASE}/api/shorten`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    // Turn backend status codes into friendly messages.
    if (res.status === 422) throw new Error("That doesn't look like a valid URL.");
    if (res.status === 429) throw new Error("Rate limit reached — please slow down.");
    throw new Error(`Something went wrong (HTTP ${res.status}).`);
  }
  return res.json();
}

/** Fetch click analytics for a short code. */
export async function getStats(code: string): Promise<StatsResponse> {
  const res = await fetch(`${API_BASE}/api/stats/${encodeURIComponent(code)}`);

  if (res.status === 404) throw new Error("No link found for that code.");
  if (!res.ok) throw new Error(`Something went wrong (HTTP ${res.status}).`);
  return res.json();
}

export { API_BASE };
