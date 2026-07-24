# data/raw/

- `stock_metadata.csv` — filled in with a starter set of tickers (edit/extend freely).
  Columns: `ticker,name,sector,listed_exchange`.
- `prices_<TICKER>.csv` — **you provide these.** For each ticker in
  `stock_metadata.csv` (including the market benchmark, `SPY` by default), go to its
  investing.com historical data page, click "Download Data", and save the export
  here as `prices_<TICKER>.csv` (e.g. `prices_AAPL.csv`).

`src/ingest/fetch_investing.py` expects the standard investing.com export columns:
`Date,Price,Open,High,Low,Vol.,Change %`.

No price CSVs are checked in — real market data isn't something to fabricate or
redistribute, and investing.com's terms don't allow scraping it automatically, so
this is a manual, one-time step per ticker.
