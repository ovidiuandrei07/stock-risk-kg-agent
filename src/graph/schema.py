"""Node labels, relationship types, and the constraints/indexes that back them.

Run `python -m src.graph.schema` once against a fresh database before loading data.
"""
from src.graph.connection import run_write

# Labels
STOCK = "Stock"
PRICE_POINT = "PricePoint"
RISK_SCORE = "RiskScore"
SECTOR = "Sector"
SOURCE = "Source"
AUTHOR = "Author"

# Relationship types
HAS_PRICE = "HAS_PRICE"
BELONGS_TO = "BELONGS_TO"
HAS_RISK = "HAS_RISK"
CORRELATES_WITH = "CORRELATES_WITH"
DERIVED_FROM = "DERIVED_FROM"
COMPUTED_BY = "COMPUTED_BY"

# Risk levels, in ascending order
RISK_LEVELS = ("scazut", "mediu", "ridicat")

VECTOR_INDEX_NAME = "stock_embedding_index"
VECTOR_DIMENSIONS = 384  # all-MiniLM-L6-v2

CONSTRAINTS = [
    f"CREATE CONSTRAINT stock_ticker IF NOT EXISTS FOR (s:{STOCK}) REQUIRE s.ticker IS UNIQUE",
    f"CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (s:{SECTOR}) REQUIRE s.name IS UNIQUE",
    f"CREATE CONSTRAINT source_url IF NOT EXISTS FOR (s:{SOURCE}) REQUIRE s.url IS UNIQUE",
    f"CREATE CONSTRAINT author_name IF NOT EXISTS FOR (a:{AUTHOR}) REQUIRE a.name IS UNIQUE",
]

INDEXES = [
    f"CREATE INDEX price_point_date IF NOT EXISTS FOR (p:{PRICE_POINT}) ON (p.date)",
    f"CREATE INDEX risk_score_level IF NOT EXISTS FOR (r:{RISK_SCORE}) ON (r.level)",
]


def create_schema() -> None:
    for statement in CONSTRAINTS + INDEXES:
        run_write(statement)
    print(f"Applied {len(CONSTRAINTS)} constraints and {len(INDEXES)} indexes.")


def create_vector_index() -> None:
    run_write(
        f"""
        CREATE VECTOR INDEX {VECTOR_INDEX_NAME} IF NOT EXISTS
        FOR (s:{STOCK}) ON (s.embedding)
        OPTIONS {{indexConfig: {{
            `vector.dimensions`: {VECTOR_DIMENSIONS},
            `vector.similarity_function`: 'cosine'
        }}}}
        """
    )
    print(f"Vector index '{VECTOR_INDEX_NAME}' ensured ({VECTOR_DIMENSIONS} dims).")


if __name__ == "__main__":
    create_schema()
    create_vector_index()
