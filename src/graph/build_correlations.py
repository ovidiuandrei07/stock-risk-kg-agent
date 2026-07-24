"""Compute pairwise return correlations and write them as CORRELATES_WITH edges.

Only pairs with |coefficient| >= CORRELATION_THRESHOLD are written, using the last
CORRELATION_WINDOW_DAYS rows of the returns matrix.
"""
import os

import pandas as pd
from dotenv import load_dotenv

from src.graph.connection import run_write
from src.ingest.clean_returns import RETURNS_MATRIX_PATH

load_dotenv()

THRESHOLD = float(os.environ.get("CORRELATION_THRESHOLD", 0.5))
WINDOW_DAYS = int(os.environ.get("CORRELATION_WINDOW_DAYS", 90))


def compute_correlation_pairs(
    returns: pd.DataFrame, window_days: int = WINDOW_DAYS, threshold: float = THRESHOLD
) -> list[dict]:
    windowed = returns.tail(window_days)
    corr = windowed.corr()

    pairs = []
    tickers = corr.columns.tolist()
    for i, a in enumerate(tickers):
        for b in tickers[i + 1 :]:
            coefficient = corr.loc[a, b]
            if pd.isna(coefficient) or abs(coefficient) < threshold:
                continue
            pairs.append({"a": a, "b": b, "coefficient": round(float(coefficient), 4)})
    return pairs


def write_correlation_edges(pairs: list[dict], window_days: int = WINDOW_DAYS) -> None:
    run_write(
        """
        UNWIND $pairs AS pair
        MATCH (a:Stock {ticker: pair.a})
        MATCH (b:Stock {ticker: pair.b})
        MERGE (a)-[r:CORRELATES_WITH]-(b)
        SET r.coefficient = pair.coefficient, r.window = $window_days
        """,
        {"pairs": pairs, "window_days": window_days},
    )


def main() -> None:
    returns = pd.read_parquet(RETURNS_MATRIX_PATH)
    pairs = compute_correlation_pairs(returns)
    write_correlation_edges(pairs)
    print(
        f"Wrote {len(pairs)} CORRELATES_WITH edges "
        f"(threshold={THRESHOLD}, window={WINDOW_DAYS} days)."
    )


if __name__ == "__main__":
    main()
