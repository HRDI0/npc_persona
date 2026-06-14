from __future__ import annotations
# pyright: reportAny=false, reportExplicitAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportMissingImports=false, reportUnusedCallResult=false

import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
IMPORT_DIR = OUTPUT_DIR / "neo4j_import"
REPORT_PATH = OUTPUT_DIR / "reports" / "neo4j_load_report.md"

ALLOWED_LABELS = {"NPC", "Quest", "Clue", "Truth", "Location", "Dialogue"}
ALLOWED_RELATIONSHIPS = {
    "INVOLVED_IN",
    "KNOWS_CLUE",
    "DOES_NOT_KNOW_TRUTH",
    "FORBIDDEN_TO_REVEAL",
    "REQUIRES_CLUE",
    "HAS_OPTIONAL_CLUE",
    "REVEALS_TRUTH",
    "TAKES_PLACE_AT",
    "SAID_BY",
    "RELATED_TO_QUEST",
    "ALLOWS_CLUE",
    "FORBIDS_TRUTH",
}
NODE_FILES = {
    "NPC": "nodes_npc.csv",
    "Quest": "nodes_quest.csv",
    "Clue": "nodes_clue.csv",
    "Truth": "nodes_truth.csv",
    "Location": "nodes_location.csv",
    "Dialogue": "nodes_dialogue.csv",
}


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env")
    load_dotenv(OUTPUT_DIR / ".env")


def parse_props(row: dict[str, str]) -> dict[str, Any]:
    props: dict[str, Any] = {}
    for key, value in row.items():
        if key == "id":
            continue
        if value in {"", "None", "null"}:
            continue
        if value in {"True", "False"}:
            props[key] = value == "True"
            continue
        try:
            props[key] = json.loads(value)
        except json.JSONDecodeError:
            props[key] = value
    return props


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def run_constraints(driver: Any, database: str) -> int:
    count = 0
    for statement in (IMPORT_DIR / "constraints.cypher").read_text(encoding="utf-8").split(";"):
        query = statement.strip()
        if query:
            driver.execute_query(query, database_=database)
            count += 1
    return count


def load_nodes(driver: Any, database: str) -> int:
    total = 0
    for label, filename in NODE_FILES.items():
        if label not in ALLOWED_LABELS:
            raise ValueError(f"Disallowed label: {label}")
        rows = read_csv(IMPORT_DIR / filename)
        query = f"MERGE (n:{label} {{id: $id}}) SET n += $props"
        for row_number, row in enumerate(rows, start=2):
            try:
                driver.execute_query(query, id=row["id"], props=parse_props(row), database_=database)
            except Exception as exc:
                raise RuntimeError(f"{filename}:{row_number}: {exc}") from exc
            total += 1
    return total


def load_relationships(driver: Any, database: str) -> int:
    total = 0
    rows = read_csv(IMPORT_DIR / "relationships.csv")
    for row_number, row in enumerate(rows, start=2):
        start_label = row["start_label"]
        end_label = row["end_label"]
        rel_type = row["relationship_type"]
        if start_label not in ALLOWED_LABELS or end_label not in ALLOWED_LABELS or rel_type not in ALLOWED_RELATIONSHIPS:
            raise ValueError(f"relationships.csv:{row_number}: disallowed label/type")
        props = json.loads(row["properties_json"] or "{}")
        query = f"MATCH (a:{start_label} {{id: $start_id}}) MATCH (b:{end_label} {{id: $end_id}}) MERGE (a)-[r:{rel_type}]->(b) SET r += $props"
        try:
            driver.execute_query(query, start_id=row["start_id"], end_id=row["end_id"], props=props, database_=database)
        except Exception as exc:
            raise RuntimeError(f"relationships.csv:{row_number}: {exc}") from exc
        total += 1
    return total


def main() -> None:
    load_dotenv_if_available()
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
        constraint_count = run_constraints(driver, database)
        node_count = load_nodes(driver, database)
        relationship_count = load_relationships(driver, database)
    REPORT_PATH.write_text(
        f"# Neo4j Load Report\n\n- constraints: {constraint_count}\n- nodes: {node_count}\n- relationships: {relationship_count}\n",
        encoding="utf-8",
    )
    print(f"Loaded Neo4j nodes={node_count} relationships={relationship_count}")


if __name__ == "__main__":
    main()
