from __future__ import annotations
# pyright: reportAny=false, reportExplicitAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
INTEGRATED_JSON = OUTPUT_DIR / "integrated" / "hazel_story_integrated.json"
IMPORT_DIR = OUTPUT_DIR / "neo4j_import"

REL_HEADER = ["start_label", "start_id", "relationship_type", "end_label", "end_id", "properties_json"]


def normalize_text(value: Any) -> str:
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return " ".join(str(value).split())


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = {field: normalize_text(row.get(field, "")) for field in fieldnames}
            if not normalized.get("id") and "id" in fieldnames:
                raise ValueError(f"Empty id for {path}")
            writer.writerow(normalized)


def add_relationship(rows: list[dict[str, str]], start_label: str, start_id: str, rel_type: str, end_label: str, end_id: str, props: dict[str, Any] | None = None) -> None:
    if not start_id or not end_id:
        return
    rows.append(
        {
            "start_label": start_label,
            "start_id": start_id,
            "relationship_type": rel_type,
            "end_label": end_label,
            "end_id": end_id,
            "properties_json": json.dumps(props or {}, ensure_ascii=False, sort_keys=True),
        }
    )


def export_csvs(data: dict[str, Any]) -> None:
    npc_rows = [
        {
            "id": npc["id"],
            "name": npc["name"],
            "role": npc["role"],
            "personality_summary": npc["personality_summary"],
            "speech_style": npc["speech_style"],
            "source_file": npc["source_file"],
        }
        for npc in data["npcs"]
    ]
    quest_rows = [
        {
            "id": quest["id"],
            "title": quest["title"],
            "episode_order": quest["episode_order"],
            "summary": quest["summary"],
            "emotional_tone": quest["story_purpose"]["emotional_tone"],
            "source_file": quest["source_file"],
        }
        for quest in data["quests"]
    ]
    clue_rows = [{"id": clue["id"], "title": clue["title"], "text": clue["text"], "is_optional": clue["is_optional"], "source_file": clue["source_file"]} for clue in data["clues"]]
    truth_rows = [{"id": truth["id"], "title": truth["title"], "summary": truth["summary"], "answer_sensitive": truth["answer_sensitive"], "source_file": truth["source_file"]} for truth in data["truths"]]
    location_rows = [{"id": location["id"], "name": location["name"], "summary": location["summary"], "source_file": location["source_file"]} for location in data["locations"]]
    dialogue_rows = [
        {
            "id": dialogue["id"],
            "npc_id": dialogue["npc_id"],
            "quest_id": dialogue["quest_id"],
            "condition": dialogue["condition"],
            "player_text": dialogue["player_text"],
            "npc_text": dialogue["npc_text"],
            "source_file": dialogue["source_file"],
        }
        for dialogue in data["dialogues"]
    ]

    write_csv(IMPORT_DIR / "nodes_npc.csv", ["id", "name", "role", "personality_summary", "speech_style", "source_file"], npc_rows)
    write_csv(IMPORT_DIR / "nodes_quest.csv", ["id", "title", "episode_order", "summary", "emotional_tone", "source_file"], quest_rows)
    write_csv(IMPORT_DIR / "nodes_clue.csv", ["id", "title", "text", "is_optional", "source_file"], clue_rows)
    write_csv(IMPORT_DIR / "nodes_truth.csv", ["id", "title", "summary", "answer_sensitive", "source_file"], truth_rows)
    write_csv(IMPORT_DIR / "nodes_location.csv", ["id", "name", "summary", "source_file"], location_rows)
    write_csv(IMPORT_DIR / "nodes_dialogue.csv", ["id", "npc_id", "quest_id", "condition", "player_text", "npc_text", "source_file"], dialogue_rows)

    relationships: list[dict[str, str]] = []
    for quest in data["quests"]:
        for npc_id in quest["involved_npc_ids"]:
            add_relationship(relationships, "NPC", npc_id, "INVOLVED_IN", "Quest", quest["id"])
        for clue_id in quest["required_clue_ids"]:
            add_relationship(relationships, "Quest", quest["id"], "REQUIRES_CLUE", "Clue", clue_id)
        for clue_id in quest["optional_clue_ids"]:
            add_relationship(relationships, "Quest", quest["id"], "HAS_OPTIONAL_CLUE", "Clue", clue_id)
        for truth_id in quest["answer_truth_ids"]:
            add_relationship(relationships, "Quest", quest["id"], "REVEALS_TRUTH", "Truth", truth_id)
        for location_id in quest["main_location_ids"]:
            add_relationship(relationships, "Quest", quest["id"], "TAKES_PLACE_AT", "Location", location_id)
    for npc in data["npcs"]:
        for clue_id in npc["known_clue_ids"]:
            add_relationship(relationships, "NPC", npc["id"], "KNOWS_CLUE", "Clue", clue_id)
        for truth_id in npc["unknown_truth_ids"]:
            add_relationship(relationships, "NPC", npc["id"], "DOES_NOT_KNOW_TRUTH", "Truth", truth_id)
        for truth_id in npc["forbidden_truth_ids"]:
            add_relationship(relationships, "NPC", npc["id"], "FORBIDDEN_TO_REVEAL", "Truth", truth_id)
    for dialogue in data["dialogues"]:
        add_relationship(relationships, "Dialogue", dialogue["id"], "SAID_BY", "NPC", dialogue["npc_id"])
        add_relationship(relationships, "Dialogue", dialogue["id"], "RELATED_TO_QUEST", "Quest", dialogue["quest_id"])
        for clue_id in dialogue["allowed_clue_ids"]:
            add_relationship(relationships, "Dialogue", dialogue["id"], "ALLOWS_CLUE", "Clue", clue_id)
        for truth_id in dialogue["forbidden_truth_ids"]:
            add_relationship(relationships, "Dialogue", dialogue["id"], "FORBIDS_TRUTH", "Truth", truth_id)

    seen = set()
    unique_relationships = []
    for row in relationships:
        key = tuple(row[field] for field in REL_HEADER)
        if key not in seen:
            seen.add(key)
            unique_relationships.append(row)
    write_csv(IMPORT_DIR / "relationships.csv", REL_HEADER, unique_relationships)


def write_cypher_files() -> None:
    constraints = """CREATE CONSTRAINT npc_id_unique IF NOT EXISTS FOR (n:NPC) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT quest_id_unique IF NOT EXISTS FOR (n:Quest) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT clue_id_unique IF NOT EXISTS FOR (n:Clue) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT truth_id_unique IF NOT EXISTS FOR (n:Truth) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT location_id_unique IF NOT EXISTS FOR (n:Location) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT dialogue_id_unique IF NOT EXISTS FOR (n:Dialogue) REQUIRE n.id IS UNIQUE;
"""
    (IMPORT_DIR / "constraints.cypher").write_text(constraints, encoding="utf-8")
    load_csv = """// Copy CSV files to Neo4j import directory before running.
// Python Driver import is the default automation path.

LOAD CSV WITH HEADERS FROM 'file:///nodes_npc.csv' AS row
MERGE (n:NPC {id: row.id})
SET n.name = row.name, n.role = row.role, n.personality_summary = row.personality_summary, n.speech_style = row.speech_style, n.source_file = row.source_file;

LOAD CSV WITH HEADERS FROM 'file:///nodes_quest.csv' AS row
MERGE (n:Quest {id: row.id})
SET n.title = row.title, n.episode_order = toInteger(row.episode_order), n.summary = row.summary, n.emotional_tone = row.emotional_tone, n.source_file = row.source_file;

// Repeat the same pattern for Clue, Truth, Location, Dialogue, then load relationships.csv with whitelisted relationship types.
"""
    (IMPORT_DIR / "load_with_cypher.cypher").write_text(load_csv, encoding="utf-8")
    graph_schema = """# Hazel Village Neo4j Import Graph Schema

## Nodes

- NPC: id, name, role, personality_summary, speech_style, source_file
- Quest: id, title, episode_order, summary, emotional_tone, source_file
- Clue: id, title, text, is_optional, source_file
- Truth: id, title, summary, answer_sensitive, source_file
- Location: id, name, summary, source_file
- Dialogue: id, npc_id, quest_id, condition, player_text, npc_text, source_file

## Relationships

- NPC -[:INVOLVED_IN]-> Quest
- NPC -[:KNOWS_CLUE]-> Clue
- NPC -[:DOES_NOT_KNOW_TRUTH]-> Truth
- NPC -[:FORBIDDEN_TO_REVEAL]-> Truth
- Quest -[:REQUIRES_CLUE]-> Clue
- Quest -[:HAS_OPTIONAL_CLUE]-> Clue
- Quest -[:REVEALS_TRUTH]-> Truth
- Quest -[:TAKES_PLACE_AT]-> Location
- Dialogue -[:SAID_BY]-> NPC
- Dialogue -[:RELATED_TO_QUEST]-> Quest
- Dialogue -[:ALLOWS_CLUE]-> Clue
- Dialogue -[:FORBIDS_TRUTH]-> Truth
"""
    (IMPORT_DIR / "graph_schema.md").write_text(graph_schema, encoding="utf-8")


def main() -> None:
    data = json.loads(INTEGRATED_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Integrated JSON must be an object")
    export_csvs(data)
    write_cypher_files()
    print("Neo4j import files exported")


if __name__ == "__main__":
    main()
