"""Normalize investing.com "Download Data" CSV exports.

investing.com's terms restrict automated scraping, so this module does not fetch
anything over the network. It expects you to have manually exported one CSV per
ticker (via the site's own "Download Data" button) into data/raw/ as
`prices_<TICKER>.csv`, plus a `data/raw/stock_metadata.csv` with columns
`ticker,name,sector,listed_exchange` that you fill in by hand.

investing.com's export columns are typically:
    Date,Price,Open,High,Low,Vol.,Change %
with Date like "Jul 22, 2026", numbers using "," as a thousands separator, and
Vol. using a K/M/B suffix (e.g. "45.67M").
"""
import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RAW_DIR = DATA_DIR / "raw"
METADATA_PATH = RAW_DIR / "stock_metadata.csv"

_VOL_SUFFIX = {"K": 1e3, "M": 1e6, "B": 1e9}


def _parse_volume(raw: str | float) -> float:
    if pd.isna(raw) or raw == "":
        return float("nan")
    raw = str(raw).strip()
    match = re.match(r"^([\d.,]+)([KMB]?)$", raw)
    if not match:
        return float("nan")
    number, suffix = match.groups()
    value = float(number.replace(",", ""))
    return value * _VOL_SUFFIX.get(suffix, 1)


def _parse_number(raw: str | float) -> float:
    if pd.isna(raw):
        return float("nan")
    return float(str(raw).replace(",", "").replace("%", ""))


def ticker_from_filename(path: Path) -> str:
    stem = path.stem  # "prices_AAPL"
    if not stem.startswith("prices_"):
        raise ValueError(f"Expected 'prices_<TICKER>.csv', got {path.name}")
    return stem.removeprefix("prices_").upper()


def load_price_csv(path: Path) -> pd.DataFrame:
    """Load one investing.com export into a normalized long DataFrame."""
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df["Date"], format="mixed")
    out["close"] = df["Price"].apply(_parse_number)
    out["open"] = df["Open"].apply(_parse_number)
    out["high"] = df["High"].apply(_parse_number)
    out["low"] = df["Low"].apply(_parse_number)
    out["volume"] = df["Vol."].apply(_parse_volume) if "Vol." in df.columns else float("nan")
    out["ticker"] = ticker_from_filename(path)

    return out.sort_values("date").reset_index(drop=True)


def load_all_prices(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    csv_paths = sorted(raw_dir.glob("prices_*.csv"))
    if not csv_paths:
        raise FileNotFoundError(
            f"No prices_*.csv files found in {raw_dir}. Export CSVs from "
            "investing.com's 'Download Data' button and drop them there."
        )
    frames = [load_price_csv(p) for p in csv_paths]
    return pd.concat(frames, ignore_index=True)


def load_metadata(path: Path = METADATA_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Create it with columns: ticker,name,sector,listed_exchange"
        )
    df = pd.read_csv(path)
    df["ticker"] = df["ticker"].str.upper()
    return df


if __name__ == "__main__":
    prices = load_all_prices()
    print(f"Loaded {len(prices)} price rows across {prices['ticker'].nunique()} tickers.")
    print(prices.head())
