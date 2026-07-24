"""Composite risk score: cross-sectional z-scores of the features in features.py,
combined into a single 0-100 value and a scazut/mediu/ridicat classification.

Writes one new :RiskScore node per stock per run (so the graph keeps a history you
can audit), attaches :DERIVED_FROM / :COMPUTED_BY provenance, and links it with
(:Stock)-[:HAS_RISK]->(:RiskScore).
"""
import os
import uuid

import pandas as pd
from dotenv import load_dotenv

from src.graph.connection import run_write
from src.graph.schema import RISK_LEVELS
from src.ingest.clean_returns import RETURNS_MATRIX_PATH
from src.provenance.attach_sources import attach_risk_score_provenance
from src.risk.features import compute_features

load_dotenv()

MARKET_TICKER = os.environ.get("MARKET_INDEX_TICKER", "SPY")

# Higher volatility/|beta|/drawdown magnitude -> more risk. Higher Sharpe -> less risk.
DEFAULT_WEIGHTS = {"volatility": 0.4, "beta": 0.2, "max_drawdown": 0.25, "sharpe": -0.15}

LOW_THRESHOLD = 33.0
HIGH_THRESHOLD = 66.0


def build_features_table(returns: pd.DataFrame) -> pd.DataFrame:
    if MARKET_TICKER not in returns.columns:
        raise ValueError(
            f"MARKET_INDEX_TICKER={MARKET_TICKER!r} not found in returns matrix. "
            "Include its CSV in data/raw/ or change MARKET_INDEX_TICKER in .env."
        )
    market_returns = returns[MARKET_TICKER]

    rows = {}
    for ticker in returns.columns:
        if ticker == MARKET_TICKER:
            continue
        rows[ticker] = compute_features(returns[ticker], market_returns)
    return pd.DataFrame.from_dict(rows, orient="index")


def compute_composite_score(features: pd.DataFrame, weights: dict = DEFAULT_WEIGHTS) -> pd.Series:
    """Z-score each feature cross-sectionally, combine per `weights`, then min-max
    scale the result to [0, 100] so it reads like a percentile-ish risk score."""
    signed = features.copy()
    signed["volatility"] = signed["volatility"]
    signed["beta"] = signed["beta"].abs()
    signed["max_drawdown"] = signed["max_drawdown"].abs()
    signed["sharpe"] = signed["sharpe"]

    z = (signed - signed.mean()) / signed.std(ddof=0)
    combined = sum(z[col] * weight for col, weight in weights.items())

    scaled = (combined - combined.min()) / (combined.max() - combined.min()) * 100
    return scaled.round(2)


def classify_risk_level(score: float, low: float = LOW_THRESHOLD, high: float = HIGH_THRESHOLD) -> str:
    if score < low:
        return RISK_LEVELS[0]  # scazut
    if score < high:
        return RISK_LEVELS[1]  # mediu
    return RISK_LEVELS[2]  # ridicat


def write_risk_scores(scores: pd.Series) -> list[str]:
    rows = [
        {
            "ticker": ticker,
            "score_id": str(uuid.uuid4()),
            "value": float(value),
            "level": classify_risk_level(value),
        }
        for ticker, value in scores.items()
    ]
    run_write(
        """
        UNWIND $rows AS row
        MATCH (s:Stock {ticker: row.ticker})
        CREATE (r:RiskScore {
            score_id: row.score_id,
            value: row.value,
            level: row.level,
            computed_at: datetime()
        })
        MERGE (s)-[:HAS_RISK]->(r)
        """,
        {"rows": rows},
    )
    return [row["score_id"] for row in rows]


def main() -> None:
    returns = pd.read_parquet(RETURNS_MATRIX_PATH)
    features = build_features_table(returns)
    scores = compute_composite_score(features)
    score_ids = write_risk_scores(scores)

    attach_risk_score_provenance(
        score_ids,
        source={"url": "local://data/processed/returns_matrix.parquet", "name": "investing.com CSV export"},
        author={"name": "risk_score.py v1"},
    )

    print(f"Wrote {len(score_ids)} RiskScore nodes with provenance.")
    print(scores.sort_values(ascending=False).head(10))


if __name__ == "__main__":
    main()
