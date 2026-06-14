from __future__ import annotations
# pyright: reportAny=false, reportExplicitAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false

import csv
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
INTEGRATED_DIR = OUTPUT_DIR / "integrated"
IMPORT_DIR = OUTPUT_DIR / "neo4j_import"
REPORT_PATH = OUTPUT_DIR / "reports" / "integration_report.md"

NODE_FILES = {
    "NPC": "nodes_npc.csv",
    "Quest": "nodes_quest.csv",
    "Clue": "nodes_clue.csv",
    "Truth": "nodes_truth.csv",
    "Location": "nodes_location.csv",
    "Dialogue": "nodes_dialogue.csv",
}
REQUIRED_REL_COLUMNS = ["start_label", "start_id", "relationship_type", "end_label", "end_id", "properties_json"]


def load_integrated() -> dict[str, Any]:
    json_data = json.loads((INTEGRATED_DIR / "hazel_story_integrated.json").read_text(encoding="utf-8"))
    yaml_data = yaml.safe_load((INTEGRATED_DIR / "hazel_story_integrated.yaml").read_text(encoding="utf-8"))
    if json_data != yaml_data:
        raise ValueError("Integrated JSON and YAML differ")
    if not isinstance(json_data, dict):
        raise ValueError("Integrated data must be mapping")
    return json_data


def validate_ids(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    clue_ids = {clue["id"] for clue in data["clues"]}
    truth_ids = {truth["id"] for truth in data["truths"]}
    npc_ids = {npc["id"] for npc in data["npcs"]}
    quest_ids = {quest["id"] for quest in data["quests"]}
    for quest in data["quests"]:
        for field, valid_ids in [("required_clue_ids", clue_ids), ("optional_clue_ids", clue_ids), ("answer_truth_ids", truth_ids)]:
            missing = sorted(set(quest[field]) - valid_ids)
            if missing:
                errors.append(f"{quest['id']} missing {field}: {missing}")
    for dialogue in data["dialogues"]:
        if dialogue["npc_id"] not in npc_ids:
            errors.append(f"{dialogue['id']} unknown npc_id")
        if dialogue["quest_id"] not in quest_ids:
            errors.append(f"{dialogue['id']} unknown quest_id")
    return errors


def validate_forbidden_truths(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    truth_titles = {truth["id"]: truth["title"] for truth in data["truths"]}
    forbidden = {npc["id"]: set(npc["forbidden_truth_ids"]) for npc in data["npcs"]}
    for dialogue in data["dialogues"]:
        npc_text = dialogue["npc_text"]
        for truth_id in forbidden[dialogue["npc_id"]]:
            if truth_id in npc_text or truth_titles[truth_id] in npc_text:
                errors.append(f"{dialogue['id']} leaks {truth_id}")
    return errors


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_csvs() -> list[str]:
    errors: list[str] = []
    if not (IMPORT_DIR / "relationships.csv").exists():
        return errors
    node_ids: dict[str, set[str]] = {}
    for label, filename in NODE_FILES.items():
        path = IMPORT_DIR / filename
        rows = read_csv(path)
        ids = [row.get("id", "") for row in rows]
        if "" in ids:
            errors.append(f"{filename} has empty id")
        if len(ids) != len(set(ids)):
            errors.append(f"{filename} has duplicate id")
        node_ids[label] = set(ids)
    rel_rows = read_csv(IMPORT_DIR / "relationships.csv")
    if rel_rows and set(REQUIRED_REL_COLUMNS) - set(rel_rows[0]):
        errors.append("relationships.csv missing required columns")
    for index, row in enumerate(rel_rows, start=2):
        if row["start_id"] not in node_ids.get(row["start_label"], set()):
            errors.append(f"relationships.csv:{index} missing start node")
        if row["end_id"] not in node_ids.get(row["end_label"], set()):
            errors.append(f"relationships.csv:{index} missing end node")
        json.loads(row["properties_json"])
    return errors


def write_report(errors: list[str]) -> None:
    status = "PASS" if not errors else "FAIL"
    lines = ["# Integration Report", "", f"## Validation {status}", ""]
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("- YAML/JSON parsing passed.")
        lines.append("- Quest clue/truth references passed.")
        lines.append("- Dialogue forbidden truth leakage check passed.")
        lines.append("- CSV relationship references passed when CSV files are present.")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    data = load_integrated()
    errors = validate_ids(data) + validate_forbidden_truths(data) + validate_csvs()
    write_report(errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Validation PASS")


if __name__ == "__main__":
    main()
