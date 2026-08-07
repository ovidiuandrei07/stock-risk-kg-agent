"""Orchestrates the Ground -> Query -> Audit pipeline.

Ground:  resolve tickers named in the question, plus vector-similar stocks for
         fuzzy phrases (e.g. "chipmakers"), so the query only touches
         entities that actually exist in the graph.
Query:   translate the (now-grounded) question into Cypher and execute it.
Audit:   attach the Cypher used and the Source/Author provenance of any
         RiskScore rows in the result, so the answer is independently checkable.
"""
import re
import sys

from src.graph.connection import run_query
from src.graph.vector_index import find_similar_stocks
from src.provenance.attach_sources import get_provenance
from src.query.text2cypher import ask as query_graph

TICKER_PATTERN = re.compile(r"\b[A-Z]{1,5}\b")


def ground(question: str, fuzzy_top_k: int = 5) -> dict:
    candidates = sorted(set(TICKER_PATTERN.findall(question)))
    known = []
    if candidates:
        known = run_query(
            "MATCH (s:Stock) WHERE s.ticker IN $candidates RETURN s.ticker AS ticker",
            {"candidates": candidates},
        )
    known_tickers = {row["ticker"] for row in known}

    fuzzy = find_similar_stocks(question, top_k=fuzzy_top_k)
    fuzzy_tickers = {row["ticker"] for row in fuzzy if row["score"] > 0.4}

    return {
        "explicit_tickers": sorted(known_tickers),
        "fuzzy_tickers": sorted(fuzzy_tickers - known_tickers),
        "unresolved_mentions": sorted(set(candidates) - known_tickers),
    }


def audit(results: list[dict]) -> list[dict]:
    trails = []
    for row in results:
        score_id = row.get("score_id")
        if score_id:
            provenance = get_provenance(score_id)
            if provenance:
                trails.append(provenance)
    return trails


def answer(question: str) -> dict:
    grounding = ground(question)
    query_result = query_graph(question)
    audit_trail = audit(query_result["results"])

    return {
        "question": question,
        "grounding": grounding,
        "cypher": query_result["cypher"],
        "results": query_result["results"],
        "audit_trail": audit_trail,
    }


def format_answer(a: dict) -> str:
    lines = [f"Q: {a['question']}", ""]

    g = a["grounding"]
    if g["explicit_tickers"]:
        lines.append(f"Ground (explicit): {', '.join(g['explicit_tickers'])}")
    if g["fuzzy_tickers"]:
        lines.append(f"Ground (similar):  {', '.join(g['fuzzy_tickers'])}")
    if g["unresolved_mentions"]:
        lines.append(f"Ground (unresolved): {', '.join(g['unresolved_mentions'])}")

    lines.append("")
    lines.append("Cypher used:")
    lines.append(a["cypher"])

    lines.append("")
    lines.append("Results:")
    for row in a["results"]:
        lines.append(f"  {row}")

    if a["audit_trail"]:
        lines.append("")
        lines.append("Audit trail (RiskScore provenance):")
        for trail in a["audit_trail"]:
            lines.append(f"  {trail}")

    return "\n".join(lines)


def main() -> None:
    question = " ".join(sys.argv[1:])
    if not question:
        print('Usage: python -m src.agent.risk_agent "How risky is AAPL?"')
        return
    print(format_answer(answer(question)))


if __name__ == "__main__":
    main()
