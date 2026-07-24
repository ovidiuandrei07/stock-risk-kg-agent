"""Shared Neo4j driver, built from environment variables in .env."""
import os
from contextlib import contextmanager

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

_driver = None


def get_driver():
    """Lazily builds the driver so importing this module (or anything that imports
    it transitively, e.g. in unit tests) doesn't require NEO4J_* to be set."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
        )
    return _driver


@contextmanager
def session():
    driver = get_driver()
    s = driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j"))
    try:
        yield s
    finally:
        s.close()


def run_query(query: str, parameters: dict | None = None) -> list[dict]:
    with session() as s:
        result = s.run(query, parameters or {})
        return [record.data() for record in result]


def run_write(query: str, parameters: dict | None = None) -> None:
    with session() as s:
        s.run(query, parameters or {})
