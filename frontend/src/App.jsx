import { useEffect, useState } from "react";
import "./App.css";
import { fetchHealth, fetchStocks } from "./api";
import StockTable from "./components/StockTable";
import StockDetail from "./components/StockDetail";
import AskPanel from "./components/AskPanel";

function App() {
  const [tab, setTab] = useState("dashboard");
  const [stocks, setStocks] = useState([]);
  const [selectedTicker, setSelectedTicker] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [health, setHealth] = useState("checking");

  useEffect(() => {
    fetchHealth()
      .then(() => setHealth("ok"))
      .catch(() => setHealth("down"));
    fetchStocks()
      .then(setStocks)
      .catch((e) => setLoadError(e.message));
  }, []);

  function selectTicker(ticker) {
    setSelectedTicker(ticker);
    setTab("dashboard");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Stock Risk KG Agent</h1>
          <p className="app-header__subtitle">
            Stock risk analysis grounded in a Neo4j knowledge graph, queried by a
            local model through a Ground → Query → Audit loop.
          </p>
        </div>
        <span className={`health-dot health-dot--${health}`} title={`Neo4j: ${health}`} />
      </header>

      <nav className="app-nav">
        <button
          className={tab === "dashboard" ? "app-nav__tab app-nav__tab--active" : "app-nav__tab"}
          onClick={() => {
            setTab("dashboard");
            setSelectedTicker(null);
          }}
        >
          Stock board
        </button>
        <button
          className={tab === "ask" ? "app-nav__tab app-nav__tab--active" : "app-nav__tab"}
          onClick={() => setTab("ask")}
        >
          Ask the model
        </button>
      </nav>

      <main className="app-main">
        {loadError && (
          <p className="error-note">
            Can't reach the backend ({loadError}). Start it with <code>uvicorn src.api.main:app</code>.
          </p>
        )}

        {tab === "dashboard" &&
          (selectedTicker ? (
            <StockDetail ticker={selectedTicker} onBack={() => setSelectedTicker(null)} />
          ) : (
            <StockTable stocks={stocks} onSelect={selectTicker} />
          ))}

        {tab === "ask" && <AskPanel />}
      </main>
    </div>
  );
}

export default App;
