"""Translate a natural-language question into a read-only Cypher query and run it.

This is the "Query" step of the agent: the LLM never talks to the user directly
about facts, it only proposes Cypher against the schema below, which we then
execute and hand back — the LLM's job is translation, not recall.
"""
import os
import re

from neo4j.exceptions import ClientError
from openai import OpenAI
from dotenv import load_dotenv

from src.graph.connection import run_query

load_dotenv()

LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.1:8b")
# Local model server (Ollama's OpenAI-compatible endpoint by default).
# Point this at LM Studio, llama.cpp, vLLM, etc. by overriding LLM_BASE_URL.
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")

SCHEMA_DESCRIPTION = """
Nodes:
  (:Stock {ticker, name, sector, listed_exchange, embedding})
  (:PricePoint {date, close, volume})
  (:RiskScore {score_id, value, level, computed_at})   // level in ["scazut","mediu","ridicat"]
  (:Sector {name})
  (:Source {url, name})
  (:Author {name})

Relationships:
  (:Stock)-[:HAS_PRICE]->(:PricePoint)
  (:Stock)-[:BELONGS_TO]->(:Sector)
  (:Stock)-[:HAS_RISK]->(:RiskScore)
  (:Stock)-[:CORRELATES_WITH {coefficient, window}]-(:Stock)
  (:RiskScore)-[:DERIVED_FROM]->(:Source)
  (:RiskScore)-[:COMPUTED_BY]->(:Author)
"""

SYSTEM_PROMPT = f"""You translate questions about stock risk into a single read-only \
Cypher query for a Neo4j database with this schema:
{SCHEMA_DESCRIPTION}

Rules:
- Output ONLY the Cypher query, no prose, no markdown fences.
- Never use CREATE, MERGE, SET, DELETE, REMOVE, DROP, or any write/admin clause.
- Use only real Cypher syntax. There is no CURRENT_TIMESTAMP(), NOW() comparison \
against RiskScore for "latest", NULLS FIRST/LAST, or any SQL keyword — Cypher is not SQL.
- A query has exactly ONE final RETURN. Never put a WITH after a RETURN.
- To get the most recent RiskScore per stock, order by computed_at descending and take \
the first element of a collect(), as shown in the examples below — do not invent a \
"latest" function.
- Always LIMIT results to at most 25 rows unless the question asks for a single value.
- Whenever a query returns data from a :RiskScore node (directly or via the "latest"
  pattern below), always include its score_id in the RETURN as `score_id` — the
  caller uses it to look up the audit trail (source/author provenance) for that score.
  Never omit it when a RiskScore is part of the result.

Examples:

Q: Which stocks have the highest risk score right now?
MATCH (s:Stock)-[:HAS_RISK]->(r:RiskScore)
WITH s, r ORDER BY r.computed_at DESC
WITH s, collect(r)[0] AS latest
RETURN s.ticker AS ticker, s.name AS name, latest.value AS risk_score, latest.level AS risk_level, latest.score_id AS score_id
ORDER BY risk_score DESC
LIMIT 25

Q: How risky is AAPL compared to other stocks in its sector?
MATCH (target:Stock {{ticker: "AAPL"}})-[:BELONGS_TO]->(sector:Sector)
MATCH (peer:Stock)-[:BELONGS_TO]->(sector)
MATCH (peer)-[:HAS_RISK]->(r:RiskScore)
WITH peer, r ORDER BY r.computed_at DESC
WITH peer, collect(r)[0] AS latest
RETURN peer.ticker AS ticker, latest.value AS risk_score, latest.level AS risk_level, latest.score_id AS score_id
ORDER BY risk_score DESC
LIMIT 25

Q: Which stocks are highly correlated with NVDA?
MATCH (s:Stock {{ticker: "NVDA"}})-[c:CORRELATES_WITH]-(other:Stock)
RETURN other.ticker AS ticker, other.name AS name, c.coefficient AS coefficient, c.window AS window_days
ORDER BY abs(c.coefficient) DESC
LIMIT 25
"""

_FORBIDDEN = re.compile(
    r"\b(CREATE|MERGE|SET|DELETE|REMOVE|DROP|CALL\s+dbms|CALL\s+apoc\.\w*\.(create|remove))\b",
    re.IGNORECASE,
)


class UnsafeCypherError(ValueError):
    pass


class CypherGenerationError(RuntimeError):
    """Raised when the LLM couldn't produce runnable Cypher within the retry budget."""


def _client() -> OpenAI:
    # Local servers (Ollama, LM Studio) ignore the key but the client requires a non-empty string.
    return OpenAI(api_key=os.environ.get("LLM_API_KEY", "ollama"), base_url=LLM_BASE_URL)


def _extract_cypher(text: str) -> str:
    cypher = text.strip()
    return re.sub(r"^```(cypher)?|```$", "", cypher, flags=re.MULTILINE).strip()


def generate_cypher(question: str) -> str:
    response = _client().chat.completions.create(
        model=LLM_MODEL,
        max_tokens=512,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    return _extract_cypher(response.choices[0].message.content)


def repair_cypher(question: str, broken_cypher: str, error_message: str) -> str:
    """Feed the failing query and the database's own error back to the LLM and
    ask for a corrected one. Small local models get Cypher syntax wrong often
    enough that this single round-trip meaningfully improves the success rate."""
    response = _client().chat.completions.create(
        model=LLM_MODEL,
        max_tokens=512,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": broken_cypher},
            {
                "role": "user",
                "content": (
                    "That query failed against Neo4j with this error:\n"
                    f"{error_message}\n\n"
                    "Output a corrected Cypher query only, no prose, no markdown fences."
                ),
            },
        ],
    )
    return _extract_cypher(response.choices[0].message.content)


def validate_cypher(cypher: str) -> None:
    if _FORBIDDEN.search(cypher):
        raise UnsafeCypherError(f"Generated Cypher contains a write/admin clause, refusing:\n{cypher}")


def ask(question: str, max_attempts: int = 2) -> dict:
    """Generate Cypher for `question` and run it, retrying with the database's
    error message fed back to the LLM up to `max_attempts` times total."""
    cypher = generate_cypher(question)

    last_error = None
    for attempt in range(1, max_attempts + 1):
        validate_cypher(cypher)
        try:
            results = run_query(cypher)
            return {"question": question, "cypher": cypher, "results": results, "attempts": attempt}
        except ClientError as e:
            last_error = e
            if attempt < max_attempts:
                cypher = repair_cypher(question, cypher, str(e))

    raise CypherGenerationError(
        f"Could not produce runnable Cypher for {question!r} after {max_attempts} attempts. "
        f"Last error: {last_error}\nLast Cypher:\n{cypher}"
    )


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "Which stocks have the highest risk score right now?"
    answer = ask(q)
    print(f"Cypher (attempt {answer['attempts']}):\n", answer["cypher"])
    print("\nResults:")
    for row in answer["results"]:
        print(" ", row)
