from __future__ import annotations
# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnusedCallResult=false

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "output" / ".env")


def main() -> None:
    load_dotenv_if_available()
    if os.getenv("ALLOW_NEO4J_RESET") != "true":
        raise SystemExit("Refusing reset. Set ALLOW_NEO4J_RESET=true only for a development database.")
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise SystemExit("neo4j package is required. Run uv sync --frozen from the project root") from exc
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    if not password:
        raise SystemExit("NEO4J_PASSWORD is required")
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.execute_query("MATCH (n) DETACH DELETE n", database_=database)
    print("Development Neo4j database reset")


if __name__ == "__main__":
    main()
