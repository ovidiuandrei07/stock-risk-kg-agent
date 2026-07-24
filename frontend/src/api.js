const BASE_URL = "http://localhost:8000";

async function request(path, options) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res.json();
}

export function fetchHealth() {
  return request("/api/health");
}

export function fetchStocks() {
  return request("/api/stocks");
}

export function fetchStockDetail(ticker) {
  return request(`/api/stocks/${encodeURIComponent(ticker)}`);
}

export function askAgent(question) {
  return request("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}
