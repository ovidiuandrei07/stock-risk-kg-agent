"""Embed each Stock's sector/description text and build a Neo4j vector index.

This powers the "Ground" step for fuzzy questions like "chipmakers" or
"consumer discretionary names" that don't name a ticker directly.
"""
from sentence_transformers import SentenceTransformer

from src.graph.connection import run_write, run_query
from src.graph.schema import create_vector_index

MODEL_NAME = "all-MiniLM-L6-v2"


def _describe(stock: dict) -> str:
    return f"{stock['name']} ({stock['ticker']}), sector: {stock['sector']}"


def build_embeddings() -> None:
    stocks = run_query("MATCH (s:Stock) RETURN s.ticker AS ticker, s.name AS name, s.sector AS sector")
    if not stocks:
        print("No stocks found — run load_graph first.")
        return

    model = SentenceTransformer(MODEL_NAME)
    texts = [_describe(s) for s in stocks]
    embeddings = model.encode(texts, normalize_embeddings=True)

    rows = [
        {"ticker": s["ticker"], "embedding": emb.tolist()}
        for s, emb in zip(stocks, embeddings)
    ]
    run_write(
        """
        UNWIND $rows AS row
        MATCH (s:Stock {ticker: row.ticker})
        SET s.embedding = row.embedding
        """,
        {"rows": rows},
    )
    print(f"Embedded {len(rows)} stocks with {MODEL_NAME}.")


def find_similar_stocks(text: str, top_k: int = 5) -> list[dict]:
    model = SentenceTransformer(MODEL_NAME)
    embedding = model.encode([text], normalize_embeddings=True)[0].tolist()

    return run_query(
        """
        CALL db.index.vector.queryNodes('stock_embedding_index', $top_k, $embedding)
        YIELD node, score
        RETURN node.ticker AS ticker, node.name AS name, node.sector AS sector, score
        """,
        {"top_k": top_k, "embedding": embedding},
    )


def main() -> None:
    create_vector_index()
    build_embeddings()


if __name__ == "__main__":
    main()
