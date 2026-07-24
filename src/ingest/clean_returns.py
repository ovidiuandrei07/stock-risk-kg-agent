"""Clean raw price history and derive a daily-returns matrix.

Writes:
    data/processed/prices_long.parquet   (date, ticker, close, volume)
    data/processed/returns_matrix.parquet (date index, one column per ticker)
"""
from pathlib import Path

import pandas as pd

from src.ingest.fetch_investing import DATA_DIR, load_all_prices

PROCESSED_DIR = DATA_DIR / "processed"
PRICES_LONG_PATH = PROCESSED_DIR / "prices_long.parquet"
RETURNS_MATRIX_PATH = PROCESSED_DIR / "returns_matrix.parquet"


def clean_prices(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop_duplicates(subset=["ticker", "date"]).sort_values(["ticker", "date"])
    df = df.dropna(subset=["close"])
    return df.reset_index(drop=True)


def compute_returns_matrix(prices_long: pd.DataFrame) -> pd.DataFrame:
    wide = prices_long.pivot(index="date", columns="ticker", values="close").sort_index()
    returns = wide.pct_change().dropna(how="all")
    return returns


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw = load_all_prices()
    prices_long = clean_prices(raw)
    prices_long.to_parquet(PRICES_LONG_PATH, index=False)

    returns_matrix = compute_returns_matrix(prices_long)
    returns_matrix.to_parquet(RETURNS_MATRIX_PATH)

    print(f"Wrote {len(prices_long)} cleaned price rows -> {PRICES_LONG_PATH}")
    print(
        f"Wrote returns matrix {returns_matrix.shape[0]} days x "
        f"{returns_matrix.shape[1]} tickers -> {RETURNS_MATRIX_PATH}"
    )


if __name__ == "__main__":
    main()
