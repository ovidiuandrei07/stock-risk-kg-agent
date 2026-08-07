# Stock Risk KG Agent

A system that answers questions about stock risk ("How risky is AAPL relative to its
sector?", "Which stocks are highly correlated with NVDA and also high-risk?") by
grounding its answers in a Neo4j knowledge graph built from price history — not from
model memory. The LLM is used for a single narrow task, translating the question into
Cypher; it doesn't plan, choose tools, or act autonomously, so "agent" here means an
orchestrated pipeline, not an agentic model.

The pipeline follows a fixed three-step sequence:

1. **Ground** — resolve tickers/sectors mentioned in the question to real nodes in the
   graph (and to vector-similar nodes when the question is fuzzy, e.g. "chipmakers").
2. **Query** — the LLM translates the grounded question into Cypher
   (`src/query/text2cypher.py`), which is then executed against the graph. This is the
   only step where the model is invoked.
3. **Audit** — every answer is returned together with the Cypher that produced it and
   the `:Source` / `:Author` / `recorded_at` provenance of any `:RiskScore` used, so a
   human can verify *why* the system said what it said.

## Knowledge graph schema

Nodes:

- `(:Stock {ticker, name, sector, listed_exchange})`
- `(:PricePoint {date, close, volume})`
- `(:RiskScore {value, level, computed_at})`
- `(:Sector {name})`
- `(:Source {url, name})`
- `(:Author {name})`

Relationships:

- `(:Stock)-[:HAS_PRICE]->(:PricePoint)`
- `(:Stock)-[:BELONGS_TO]->(:Sector)`
- `(:Stock)-[:HAS_RISK]->(:RiskScore)`
- `(:Stock)-[:CORRELATES_WITH {coefficient, window}]->(:Stock)`
- `(:RiskScore)-[:DERIVED_FROM]->(:Source)`
- `(:RiskScore)-[:COMPUTED_BY]->(:Author)`

See [src/graph/schema.py](src/graph/schema.py) for the exact constraints/indexes created.

## Project layout

```
stock-risk-kg-agent/
├── project_starter.ipynb          # guided notebook with TODOs — start here
├── data/
│   ├── raw/                       # investing.com CSV exports (Date,Price,Open,High,Low,Vol.,Change %)
│   ├── processed/                 # cleaned returns_matrix.parquet
│   └── stocks-load.cypher         # generated load script (see load_graph.py)
├── src/
│   ├── ingest/                    # CSV normalization + returns calculation
│   ├── graph/                     # schema, Neo4j loading, correlations, vector index
│   ├── risk/                      # risk features, composite score, optional ML model
│   ├── query/                     # text2cypher
│   ├── provenance/                # Source/Author attachment
│   └── agent/                     # Ground -> Query -> Audit orchestration
├── tests/
└── notebooks/                     # worked demos of each stage
```

## Setup

```bash
cd stock-risk-kg-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in NEO4J_* and LLM_API_KEY
```

You need:

- A Neo4j instance (AuraDB free tier works) with the vector index feature (Neo4j 5.11+).
- A local Ollama server (`ollama serve`) with the model set in `LLM_MODEL` (default
  `gemma3:4b`) pulled, for `text2cypher`.
- CSV exports from investing.com for each ticker you care about, dropped into
  `data/raw/` as `prices_<TICKER>.csv` (the standard investing.com "Download Data"
  export format).

## Pipeline

```bash
python -m src.graph.schema                  # constraints + indexes (once, on a fresh database)
python -m src.ingest.clean_returns          # data/raw/*.csv -> data/processed/returns_matrix.parquet
python -m src.graph.load_graph              # Stock, PricePoint, Sector nodes
python -m src.graph.build_correlations      # CORRELATES_WITH edges
python -m src.graph.vector_index            # embeddings + vector index on :Stock
python -m src.risk.risk_score               # RiskScore nodes + provenance
```

Then run a question through the pipeline:

```bash
python -m src.agent.risk_agent "How risky is AAPL compared to other stocks in its sector?"
```

## Web app (front-end + back-end)

A presentation site sits on top of the pipeline above and re-uses it as-is — the
API layer only calls into `src.graph` / `src.agent`, it doesn't duplicate any logic.

```
src/api/main.py     # FastAPI wrapper: /api/stocks, /api/stocks/{ticker}, /api/ask
frontend/            # Vite + React SPA: dashboard, stock detail (price chart,
                      # correlations, risk provenance), and an "Ask the model" panel
```

Prerequisites: Neo4j running with the pipeline above already loaded, and
`ollama serve` running with `LLM_MODEL` pulled (same as the CLI pipeline).

Run both halves (two terminals):

```bash
# Terminal 1 — backend, from stock-risk-kg-agent/
source .venv/bin/activate
uvicorn src.api.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install   # first time only
npm run dev
```
