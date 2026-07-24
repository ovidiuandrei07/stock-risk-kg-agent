"""Load Stock, Sector, and PricePoint nodes (+ BELONGS_TO / HAS_PRICE edges) into Neo4j.

Reads data/processed/prices_long.parquet (from src.ingest.clean_returns) and
data/raw/stock_metadata.csv (from src.ingest.fetch_investing).
"""
import pandas as pd

from src.graph.connection import run_write
from src.ingest.clean_returns import PRICES_LONG_PATH
from src.ingest.fetch_investing import load_metadata

BATCH_SIZE = 500


def load_stocks_and_sectors(metadata: pd.DataFrame) -> None:
    rows = metadata.to_dict("records")
    run_write(
        """
        UNWIND $rows AS row
        MERGE (sec:Sector {name: row.sector})
        MERGE (s:Stock {ticker: row.ticker})
        SET s.name = row.name, s.listed_exchange = row.listed_exchange, s.sector = row.sector
        MERGE (s)-[:BELONGS_TO]->(sec)
        """,
        {"rows": rows},
    )
    print(f"Loaded {len(rows)} stocks / sectors.")


def load_price_points(prices_long: pd.DataFrame) -> None:
    total = 0
    for ticker, group in prices_long.groupby("ticker"):
        rows = [
            {
                "date": row.date.strftime("%Y-%m-%d"),
                "close": float(row.close),
                "volume": None if pd.isna(row.volume) else float(row.volume),
            }
            for row in group.itertuples()
        ]
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            run_write(
                """
                MATCH (s:Stock {ticker: $ticker})
                UNWIND $rows AS row
                MERGE (s)-[:HAS_PRICE]->(p:PricePoint {date: date(row.date)})
                SET p.close = row.close, p.volume = row.volume
                """,
                {"ticker": ticker, "rows": batch},
            )
        total += len(rows)
        print(f"  {ticker}: {len(rows)} price points")
    print(f"Loaded {total} price points total.")


def main() -> None:
    metadata = load_metadata()
    load_stocks_and_sectors(metadata)

    prices_long = pd.read_parquet(PRICES_LONG_PATH)
    load_price_points(prices_long)


if __name__ == "__main__":
    main()
