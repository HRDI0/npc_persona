import csv
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import cast

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
PIPELINE_SCRIPTS = ROOT / "scripts" / "story_pipeline"


class OutputPipelineContractTest(unittest.TestCase):
    def test_requested_output_tree_exists(self):
        required_paths = [
            OUTPUT / "README.md",
            OUTPUT / "reports" / "source_inventory.md",
            OUTPUT / "reports" / "reference_research.md",
            OUTPUT / "reports" / "expansion_summary.md",
            OUTPUT / "reports" / "integration_report.md",
            OUTPUT / "reports" / "neo4j_load_report.md",
            OUTPUT / "reports" / "quest_line_overview.md",
            OUTPUT / "reports" / "dialogue_samples.md",
            OUTPUT / "integrated" / "hazel_story_integrated.yaml",
            OUTPUT / "integrated" / "hazel_story_integrated.json",
            OUTPUT / "integrated" / "npc_profiles.yaml",
            OUTPUT / "integrated" / "quest_lines.yaml",
            OUTPUT / "integrated" / "dialogue_policies_integrated.yaml",
            OUTPUT / "neo4j_import" / "nodes_npc.csv",
            OUTPUT / "neo4j_import" / "nodes_quest.csv",
            OUTPUT / "neo4j_import" / "nodes_clue.csv",
            OUTPUT / "neo4j_import" / "nodes_truth.csv",
            OUTPUT / "neo4j_import" / "nodes_location.csv",
            OUTPUT / "neo4j_import" / "nodes_dialogue.csv",
            OUTPUT / "neo4j_import" / "relationships.csv",
            OUTPUT / "neo4j_import" / "constraints.cypher",
            OUTPUT / "neo4j_import" / "load_with_cypher.cypher",
            OUTPUT / "neo4j_import" / "graph_schema.md",
            PIPELINE_SCRIPTS / "build_integrated_data.py",
            PIPELINE_SCRIPTS / "export_neo4j_import_files.py",
            PIPELINE_SCRIPTS / "load_neo4j.py",
            PIPELINE_SCRIPTS / "validate_data.py",
            PIPELINE_SCRIPTS / "reset_neo4j_dev.py",
            PIPELINE_SCRIPTS / "run_pipeline.py",
        ]

        missing = [str(path.relative_to(ROOT)) for path in required_paths if not path.exists()]
        self.assertEqual([], missing)
        self.assertFalse((OUTPUT / "expanded").exists(), "expanded story material must live under rsc/data, not output/expanded")
        self.assertFalse((OUTPUT / "scripts").exists(), "pipeline scripts must live under scripts/story_pipeline")
        self.assertFalse((OUTPUT / "requirements.txt").exists(), "dependencies must be project-level, not output-local")
        self.assertFalse((OUTPUT / ".env.example").exists(), "env examples must be project-level, not output-local")

    def test_integrated_story_is_parseable_and_scoped(self):
        data = json.loads((OUTPUT / "integrated" / "hazel_story_integrated.json").read_text(encoding="utf-8"))
        yaml_data = yaml.safe_load((OUTPUT / "integrated" / "hazel_story_integrated.yaml").read_text(encoding="utf-8"))
        self.assertEqual(data, yaml_data)

        self.assertEqual(
            {"minmin_lady", "patrol_leader_rio", "mage_lumi", "chief_rowan"},
            {npc["id"] for npc in data["npcs"]},
        )
        self.assertEqual(5, len(data["quests"]))
        self.assertGreaterEqual(len(data["dialogues"]), 40)
        self.assertEqual([], data.get("new_major_regions", []))
        self.assertEqual([], data.get("new_npcs", []))

        for npc in data["npcs"]:
            self.assertIn("known_clue_ids", npc)
            self.assertIn("unknown_truth_ids", npc)
            self.assertIn("forbidden_truth_ids", npc)

        dialogue_lengths_by_npc: dict[str, list[int]] = {}
        for dialogue in data["dialogues"]:
            npc_id = str(dialogue["npc_id"])
            dialogue_lengths_by_npc.setdefault(npc_id, []).append(len(str(dialogue["npc_text"])))
        sparse_dialogue_npcs = [
            npc_id
            for npc_id, lengths in sorted(dialogue_lengths_by_npc.items())
            if sum(lengths) / len(lengths) < 55
        ]
        self.assertEqual([], sparse_dialogue_npcs)

        for quest in data["quests"]:
            self.assertIn("required_clue_ids", quest)
            self.assertIn("optional_clue_ids", quest)
            self.assertIn("answer_truth_ids", quest)
            self.assertGreaterEqual(len(quest["quest_steps"]), 4)
            self.assertLessEqual(len(quest["quest_steps"]), 6)
            self.assertLessEqual(len(quest["wrong_hypotheses"]), 2)

    def test_integrated_story_uses_canonical_rsc_data_sources(self):
        data = cast(
            dict[str, object],
            json.loads((OUTPUT / "integrated" / "hazel_story_integrated.json").read_text(encoding="utf-8")),
        )

        source_files: list[str] = []
        for collection_name in ["npcs", "quests", "dialogues", "clues", "truths", "locations"]:
            for row in cast(list[dict[str, object]], data[collection_name]):
                source_files.append(str(row.get("source_file", "")))

        self.assertTrue(source_files)
        self.assertFalse([path for path in source_files if path.startswith("output/expanded")])
        self.assertTrue(all(path.startswith("rsc/data/") for path in source_files), source_files)

        for quest_path in sorted((ROOT / "rsc" / "data" / "quests").glob("*.yaml")):
            quest = yaml.safe_load(quest_path.read_text(encoding="utf-8"))
            self.assertIn("story_expansion", quest, quest_path.name)
            expansion = quest["story_expansion"]
            self.assertGreaterEqual(len(expansion["quest_steps"]), 4, quest_path.name)
            self.assertLessEqual(len(expansion["wrong_hypotheses"]), 2, quest_path.name)

    def test_quest_clues_and_reveal_policy_are_semantically_consistent(self):
        data = cast(
            dict[str, object],
            json.loads((OUTPUT / "integrated" / "hazel_story_integrated.json").read_text(encoding="utf-8")),
        )
        forbidden_by_npc = {
            str(npc["id"]): set(cast(list[str], npc["forbidden_truth_ids"]))
            for npc in cast(list[dict[str, object]], data["npcs"])
        }

        overlaps: dict[str, set[str]] = {}
        reveal_conflicts: dict[str, set[str]] = {}
        for quest in cast(list[dict[str, object]], data["quests"]):
            required = set(cast(list[str], quest["required_clue_ids"]))
            optional = set(cast(list[str], quest["optional_clue_ids"]))
            overlap = required & optional
            if overlap:
                overlaps[str(quest["id"])] = overlap

            reveal_policy = cast(dict[str, object], quest["answer_reveal_policy"])
            answer_truths = set(cast(list[str], quest["answer_truth_ids"]))
            for npc_id in cast(list[str], reveal_policy["npc_allowed_to_reveal"]):
                conflict = answer_truths & forbidden_by_npc[npc_id]
                if conflict:
                    reveal_conflicts[npc_id] = conflict

        self.assertEqual({}, overlaps)
        self.assertEqual({}, reveal_conflicts)

    def test_neo4j_csv_relationships_reference_existing_nodes(self):
        import_dir = OUTPUT / "neo4j_import"
        node_files = {
            "NPC": "nodes_npc.csv",
            "Quest": "nodes_quest.csv",
            "Clue": "nodes_clue.csv",
            "Truth": "nodes_truth.csv",
            "Location": "nodes_location.csv",
            "Dialogue": "nodes_dialogue.csv",
        }
        node_ids: dict[str, set[str]] = {}
        for label, filename in node_files.items():
            with (import_dir / filename).open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertGreater(len(rows), 0, filename)
            ids = {row["id"] for row in rows}
            self.assertNotIn("", ids, filename)
            self.assertEqual(len(rows), len(ids), filename)
            node_ids[label] = ids

        allowed_relationships = {
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
        with (import_dir / "relationships.csv").open("r", encoding="utf-8", newline="") as handle:
            relationships = list(csv.DictReader(handle))
        self.assertGreater(len(relationships), 0)
        for row in relationships:
            self.assertIn(row["relationship_type"], allowed_relationships)
            self.assertIn(row["start_id"], node_ids[row["start_label"]])
            self.assertIn(row["end_id"], node_ids[row["end_label"]])
            json.loads(row["properties_json"])

    def test_reference_research_uses_web_sources_without_copying_story_text(self):
        text = (OUTPUT / "reports" / "reference_research.md").read_text(encoding="utf-8")
        for required in [
            "MapleStory",
            "Grand Athenaeum",
            "Dimensional Library",
            "Yarn Spinner",
            "Neo4j",
            "Three Clue Rule",
            "2026-06-14",
        ]:
            self.assertIn(required, text)
        self.assertIn("원문 대사나 고유 스토리 문장은 복사하지 않음", text)

    def test_readme_explains_neo4j_loading_paths(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for required in [
            "python scripts/story_pipeline/run_pipeline.py",
            "python scripts/story_pipeline/run_pipeline.py --load-neo4j",
            "python scripts/story_pipeline/load_neo4j.py",
            "python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data",
            "NEO4J_URI",
            "NEO4J_USER",
            "NEO4J_PASSWORD",
            "NEO4J_DATABASE",
            "KnowledgeChunk",
            "reset_neo4j_dev.py",
        ]:
            self.assertIn(required, text)

    def test_pipeline_cli_runs_and_validates_generated_outputs(self):
        result = subprocess.run(
            [sys.executable, "scripts/story_pipeline/run_pipeline.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn("Pipeline complete", result.stdout)
        report = (OUTPUT / "reports" / "integration_report.md").read_text(encoding="utf-8")
        self.assertIn("Validation PASS", report)

    def test_dialogues_do_not_directly_reveal_forbidden_truth_ids(self):
        data = cast(
            dict[str, object],
            json.loads((OUTPUT / "integrated" / "hazel_story_integrated.json").read_text(encoding="utf-8")),
        )
        truths = {str(truth["id"]): str(truth["title"]) for truth in cast(list[dict[str, object]], data["truths"])}
        forbidden_by_npc = {
            str(npc["id"]): set(cast(list[str], npc["forbidden_truth_ids"]))
            for npc in cast(list[dict[str, object]], data["npcs"])
        }
        leaks: list[str] = []
        for dialogue in cast(list[dict[str, object]], data["dialogues"]):
            npc_id = str(dialogue["npc_id"])
            npc_text = str(dialogue["npc_text"])
            for truth_id in forbidden_by_npc[npc_id]:
                if truth_id in npc_text or truths[truth_id] in npc_text:
                    leaks.append(str(dialogue["id"]))
        self.assertEqual([], leaks)


if __name__ == "__main__":
    unittest.main()
