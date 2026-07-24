import { useState } from "react";
import { askAgent } from "../api";

const EXAMPLES = [
  "Which stocks have the highest risk score right now?",
  "How risky is AAPL compared to other stocks in its sector?",
  "Which stocks are highly correlated with NVDA?",
];

function ResultsTable({ results }) {
  if (!results || results.length === 0) {
    return <p className="empty-note">No results.</p>;
  }
  const columns = Object.keys(results[0]).filter((c) => c !== "score_id");
  return (
    <div className="table-wrap">
      <table className="results-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c} className="tabular">
                  {typeof row[c] === "number" ? row[c].toFixed(2) : String(row[c] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AskPanel() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function submit(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await askAgent(q);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const grounding = result?.grounding;

  return (
    <div className="ask-panel">
      <form onSubmit={submit} className="ask-form">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask the model, e.g. Which stocks have the highest risk score right now?"
          rows={3}
        />
        <div className="ask-form__actions">
          <div className="ask-examples">
            {EXAMPLES.map((ex) => (
              <button type="button" key={ex} className="chip" onClick={() => setQuestion(ex)}>
                {ex}
              </button>
            ))}
          </div>
          <button type="submit" className="primary-button" disabled={loading || !question.trim()}>
            {loading ? "Asking…" : "Ask"}
          </button>
        </div>
      </form>

      {loading && (
        <p className="empty-note">
          The local model is generating Cypher and querying the graph — this can take a few seconds…
        </p>
      )}
      {error && <p className="error-note">Error: {error}</p>}

      {result && !loading && (
        <div className="ask-result">
          {grounding && (
            <section className="panel">
              <h3>Grounding (Ground)</h3>
              <div className="grounding-row">
                {grounding.explicit_tickers.length > 0 && (
                  <div>
                    <span className="text-muted">Explicit: </span>
                    {grounding.explicit_tickers.map((t) => (
                      <span key={t} className="chip chip--static">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                {grounding.fuzzy_tickers.length > 0 && (
                  <div>
                    <span className="text-muted">Similar: </span>
                    {grounding.fuzzy_tickers.map((t) => (
                      <span key={t} className="chip chip--static">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                {grounding.unresolved_mentions.length > 0 && (
                  <div>
                    <span className="text-muted">Unresolved: </span>
                    {grounding.unresolved_mentions.map((t) => (
                      <span key={t} className="chip chip--static chip--unresolved">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </section>
          )}

          <section className="panel">
            <h3>Generated Cypher (Query)</h3>
            <pre className="cypher-block">{result.cypher}</pre>
          </section>

          <section className="panel">
            <h3>Results</h3>
            <ResultsTable results={result.results} />
          </section>

          <section className="panel">
            <h3>Audit trail (Audit)</h3>
            {(!result.audit_trail || result.audit_trail.length === 0) && (
              <p className="empty-note">
                No result row carries a risk score id to trace.
              </p>
            )}
            <ul className="provenance-list">
              {result.audit_trail?.map((trail, i) => (
                <li key={i}>
                  <div className="text-muted">
                    Value: {trail.value} ({trail.level}) · Source: {trail.source_name} · Author:{" "}
                    {trail.author}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
