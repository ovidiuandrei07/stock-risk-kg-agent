"""Attach :Source / :Author provenance to :RiskScore nodes.

This is what makes the agent's "Audit" step possible: every risk claim can be
traced back to *what data* produced it and *what code/version* computed it.
"""
from src.graph.connection import run_query, run_write


def attach_risk_score_provenance(
    score_ids: list[str],
    source: dict,
    author: dict,
    confidence: float = 1.0,
) -> None:
    """
    source: {"url": ..., "name": ...}
    author: {"name": ...}
    """
    run_write(
        """
        UNWIND $score_ids AS score_id
        MATCH (r:RiskScore {score_id: score_id})
        MERGE (src:Source {url: $source.url})
        SET src.name = $source.name
        MERGE (auth:Author {name: $author.name})
        MERGE (r)-[d:DERIVED_FROM]->(src)
        SET d.confidence = $confidence, d.recorded_at = datetime()
        MERGE (r)-[:COMPUTED_BY]->(auth)
        """,
        {
            "score_ids": score_ids,
            "source": source,
            "author": author,
            "confidence": confidence,
        },
    )


def get_provenance(score_id: str) -> dict | None:
    """Fetch the audit trail for a single RiskScore node, for the agent's Audit step."""
    results = run_query(
        """
        MATCH (r:RiskScore {score_id: $score_id})
        OPTIONAL MATCH (r)-[d:DERIVED_FROM]->(src:Source)
        OPTIONAL MATCH (r)-[:COMPUTED_BY]->(auth:Author)
        RETURN r.value AS value, r.level AS level, r.computed_at AS computed_at,
               src.name AS source_name, src.url AS source_url, d.confidence AS confidence,
               auth.name AS author
        """,
        {"score_id": score_id},
    )
    return results[0] if results else None
