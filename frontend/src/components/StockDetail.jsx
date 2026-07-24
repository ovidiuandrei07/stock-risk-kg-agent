import { useEffect, useState } from "react";
import { fetchStockDetail } from "../api";
import RiskBadge from "./RiskBadge";
import PriceChart from "./PriceChart";

export default function StockDetail({ ticker, onBack }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setDetail(null);
    setError(null);
    fetchStockDetail(ticker)
      .then(setDetail)
      .catch((e) => setError(e.message));
  }, [ticker]);

  return (
    <div className="stock-detail">
      <button className="link-button" onClick={onBack}>
        ← Back to list
      </button>

      {error && <p className="error-note">Error: {error}</p>}
      {!detail && !error && <p className="empty-note">Loading…</p>}

      {detail && (
        <>
          <header className="stock-detail__header">
            <div>
              <h2>
                {detail.name} <span className="stock-detail__ticker">{detail.ticker}</span>
              </h2>
              <p className="stock-detail__meta">
                {detail.sector} · {detail.exchange}
              </p>
            </div>
            {detail.risk_history[0] && (
              <RiskBadge level={detail.risk_history[0].level} value={detail.risk_history[0].value} />
            )}
          </header>

          <section className="panel">
            <h3>Price history</h3>
            <PriceChart prices={detail.prices} />
          </section>

          <div className="stock-detail__grid">
            <section className="panel">
              <h3>Correlations</h3>
              {detail.correlations.length === 0 && (
                <p className="empty-note">No correlations recorded.</p>
              )}
              <ul className="correlation-list">
                {detail.correlations.map((c) => (
                  <li key={c.ticker}>
                    <span className="correlation-list__ticker">{c.ticker}</span>
                    <span className="correlation-list__name">{c.name}</span>
                    <span className="tabular">
                      {c.coefficient > 0 ? "+" : ""}
                      {c.coefficient.toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="panel">
              <h3>Risk score provenance</h3>
              {detail.risk_history.length === 0 && (
                <p className="empty-note">No risk score computed yet.</p>
              )}
              <ul className="provenance-list">
                {detail.risk_history.map((r) => (
                  <li key={r.score_id}>
                    <div className="provenance-list__top">
                      <RiskBadge level={r.level} value={r.value} />
                      <span className="text-muted">
                        {r.computed_at ? new Date(r.computed_at).toLocaleString("en-US") : ""}
                      </span>
                    </div>
                    <div className="text-muted">
                      Source: {r.source_name || "unknown"} · Computed by: {r.author || "unknown"}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
