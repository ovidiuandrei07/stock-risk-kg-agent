"""FastAPI presentation layer over the Stock Risk KG Agent.

Thin HTTP wrapper: every endpoint delegates to the existing src.graph / src.agent
modules, it does not duplicate any graph or LLM logic.
"""
import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agent.risk_agent import answer as agent_answer
from src.graph.connection import run_query
from src.query.text2cypher import CypherGenerationError, UnsafeCypherError

app = FastAPI(title="Stock Risk KG Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _jsonable(value: Any) -> Any:
    """Recursively convert Neo4j driver types (DateTime, Date, Node, ...) into
    plain JSON-serializable values."""
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if hasattr(value, "iso_format"):
        return value.iso_format()
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


@app.get("/api/health")
def health() -> dict:
    try:
        run_query("RETURN 1")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {e}")


@app.get("/api/stocks")
def list_stocks() -> list[dict]:
    rows = run_query(
        """
        MATCH (s:Stock)-[:BELONGS_TO]->(sector:Sector)
        OPTIONAL MATCH (s)-[:HAS_RISK]->(r:RiskScore)
        WITH s, sector, r ORDER BY r.computed_at DESC
        WITH s, sector, collect(r)[0] AS latest
        RETURN s.ticker AS ticker, s.name AS name, sector.name AS sector,
               s.listed_exchange AS exchange,
               latest.value AS risk_score, latest.level AS risk_level
        ORDER BY s.ticker
        """
    )
    return _jsonable(rows)


@app.get("/api/stocks/{ticker}")
def stock_detail(ticker: str) -> dict:
    ticker = ticker.upper()
    meta = run_query(
        """
        MATCH (s:Stock {ticker: $ticker})-[:BELONGS_TO]->(sector:Sector)
        RETURN s.ticker AS ticker, s.name AS name, sector.name AS sector,
               s.listed_exchange AS exchange
        """,
        {"ticker": ticker},
    )
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")

    prices = run_query(
        """
        MATCH (s:Stock {ticker: $ticker})-[:HAS_PRICE]->(p:PricePoint)
        RETURN p.date AS date, p.close AS close, p.volume AS volume
        ORDER BY p.date ASC
        """,
        {"ticker": ticker},
    )

    risk_history = run_query(
        """
        MATCH (s:Stock {ticker: $ticker})-[:HAS_RISK]->(r:RiskScore)
        OPTIONAL MATCH (r)-[d:DERIVED_FROM]->(src:Source)
        OPTIONAL MATCH (r)-[:COMPUTED_BY]->(auth:Author)
        RETURN r.score_id AS score_id, r.value AS value, r.level AS level,
               r.computed_at AS computed_at, src.name AS source_name,
               src.url AS source_url, auth.name AS author
        ORDER BY r.computed_at DESC
        """,
        {"ticker": ticker},
    )

    correlations = run_query(
        """
        MATCH (s:Stock {ticker: $ticker})-[c:CORRELATES_WITH]-(other:Stock)
        RETURN other.ticker AS ticker, other.name AS name,
               c.coefficient AS coefficient, c.window AS window_days
        ORDER BY abs(c.coefficient) DESC
        """,
        {"ticker": ticker},
    )

    return _jsonable(
        {
            **meta[0],
            "prices": prices,
            "risk_history": risk_history,
            "correlations": correlations,
        }
    )


class AskRequest(BaseModel):
    question: str


@app.post("/api/ask")
def ask(req: AskRequest) -> dict:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty")
    try:
        result = agent_answer(question)
    except UnsafeCypherError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except CypherGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return _jsonable(result)
