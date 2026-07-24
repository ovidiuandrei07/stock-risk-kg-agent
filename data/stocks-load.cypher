// Reference load script for Neo4j Browser / Desktop, mirroring what
// src/graph/load_graph.py does via the driver. Useful if you want to poke at the
// schema without setting up the Python environment first.
//
// Prerequisites:
//   - stock_metadata.csv and prices_<TICKER>.csv copied into Neo4j's import/ folder
//     (Neo4j Desktop: right-click the DB -> Open Folder -> Import)
//   - LOAD CSV with periodic commit is deprecated in Neo4j 5 in favor of
//     `:auto USING PERIODIC COMMIT` / `CALL { ... } IN TRANSACTIONS`, used below.

// --- 1. Constraints (same as src/graph/schema.py) ---------------------------
CREATE CONSTRAINT stock_ticker IF NOT EXISTS FOR (s:Stock) REQUIRE s.ticker IS UNIQUE;
CREATE CONSTRAINT sector_name  IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT source_url   IF NOT EXISTS FOR (s:Source) REQUIRE s.url IS UNIQUE;
CREATE CONSTRAINT author_name  IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE;
CREATE INDEX price_point_date  IF NOT EXISTS FOR (p:PricePoint) ON (p.date);
CREATE INDEX risk_score_level  IF NOT EXISTS FOR (r:RiskScore) ON (r.level);

// --- 2. Stocks + Sectors, from stock_metadata.csv ----------------------------
// columns: ticker,name,sector,listed_exchange
LOAD CSV WITH HEADERS FROM 'file:///stock_metadata.csv' AS row
CALL {
  WITH row
  MERGE (sec:Sector {name: row.sector})
  MERGE (s:Stock {ticker: toUpper(row.ticker)})
  SET s.name = row.name, s.listed_exchange = row.listed_exchange, s.sector = row.sector
  MERGE (s)-[:BELONGS_TO]->(sec)
} IN TRANSACTIONS OF 500 ROWS;

// --- 3. Price history for one ticker, from prices_<TICKER>.csv --------------
// Repeat this block once per ticker (or drive it from Python — see load_graph.py
// for the version that loops over every file automatically).
// columns: Date,Price,Open,High,Low,Vol.,Change %
:param ticker => 'AAPL';

LOAD CSV WITH HEADERS FROM 'file:///prices_AAPL.csv' AS row
CALL {
  WITH row
  MATCH (s:Stock {ticker: $ticker})
  MERGE (s)-[:HAS_PRICE]->(p:PricePoint {date: date(datetime({epochMillis: apoc.date.parse(row.Date, 'ms', 'MMM d, yyyy')}))})
  SET p.close = toFloat(replace(row.Price, ',', ''))
} IN TRANSACTIONS OF 500 ROWS;

// --- 4. Sanity check ----------------------------------------------------------
MATCH (s:Stock)
OPTIONAL MATCH (s)-[:HAS_PRICE]->(p:PricePoint)
RETURN s.ticker AS ticker, s.sector AS sector, count(p) AS price_points
ORDER BY ticker;
