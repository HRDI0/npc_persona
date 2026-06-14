import importlib.util
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast, final

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "rsc" / "data"


class StoryImporter(Protocol):
    def build_import_plan(self, source_dir: Path) -> object: ...

    def validate_import_plan(self, plan: object) -> list[str]: ...

    def source_counts(self, plan: object) -> dict[str, int]: ...

    def relationship_counts(self, plan: object) -> dict[str, int]: ...

    def dry_run_import(self, source_dir: Path, database: str | None = None, report_path: Path | None = None) -> object: ...

    def import_story_source(
        self,
        driver: object,
        source_dir: Path,
        reset: bool = False,
        database: str | None = None,
        report_path: Path | None = None,
    ) -> object: ...

    def load_npcs(
        self,
        source_dir: Path,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]: ...

    def load_quests(self, source_dir: Path) -> list[dict[str, object]]: ...

    def load_world(self, source_dir: Path) -> dict[str, list[dict[str, object]]]: ...

    def load_locations(self, source_dir: Path) -> list[dict[str, object]]: ...


class StorySourceClassifier(Protocol):
    def build_report(
        self,
        source_dir: Path,
        raw_paths: list[Path],
    ) -> dict[str, object]: ...

    def write_report(
        self,
        report: dict[str, object],
        output_path: Path,
        *,
        overwrite: bool = False,
    ) -> None: ...


class _GraphDatabaseStub:
    @staticmethod
    def driver(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("Neo4j is not available in story source contract tests")


class FakeNeo4jDriver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute_query(self, query: str, **kwargs: object) -> tuple[list[object], object, list[str]]:
        self.calls.append((query, kwargs))
        return [], object(), []


def install_neo4j_stub() -> None:
    if "neo4j" in sys.modules:
        return

    module = ModuleType("neo4j")
    setattr(module, "GraphDatabase", _GraphDatabaseStub)
    sys.modules["neo4j"] = module


def load_importer_module() -> StoryImporter:
    install_neo4j_stub()
    path = ROOT / "src" / "db_control" / "import_story_source_to_neo4j.py"
    spec = importlib.util.spec_from_file_location("story_importer", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return cast(StoryImporter, cast(object, module))


def load_classifier_module() -> StorySourceClassifier:
    path = ROOT / "scripts" / "story_pipeline" / "classify_story_sources.py"
    assert path.exists(), "scripts/story_pipeline/classify_story_sources.py must provide the raw source classifier"
    spec = importlib.util.spec_from_file_location("story_source_classifier", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return cast(StorySourceClassifier, cast(object, module))


def raw_story_paths() -> list[Path]:
    return [
        SOURCE_DIR / "hazel_village_map_stories.md",
        SOURCE_DIR / "hazel_village_npc_chronicles_plain.md",
    ]


def section_after(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.find(marker)
    if start == -1:
        return ""
    remainder = text[start + len(marker):]
    next_heading = remainder.find("\n## ")
    if next_heading == -1:
        return remainder
    return remainder[:next_heading]


@final
class StorySourceContractTest(unittest.TestCase):
    def test_mvp_story_source_loads_four_npcs_and_twenty_six_chunks(self):
        importer = load_importer_module()
        npcs, chunks = importer.load_npcs(SOURCE_DIR)

        self.assertEqual(4, len(npcs))
        self.assertEqual(26, len(chunks))
        self.assertEqual(
            {
                "chief_rowan": 7,
                "mage_lumi": 5,
                "minmin_lady": 8,
                "patrol_leader_rio": 6,
            },
            dict(Counter(chunk["npc_id"] for chunk in chunks)),
        )

    def test_import_plan_validates_augmented_source_counts_and_relationships(self):
        importer = load_importer_module()
        plan = importer.build_import_plan(SOURCE_DIR)

        self.assertEqual([], importer.validate_import_plan(plan))
        self.assertEqual(
            {
                "NPC": 4,
                "Location": 8,
                "Quest": 5,
                "Role": 4,
                "Event": 5,
                "Clue": 8,
                "Truth": 3,
                "KnowledgeChunk": 26,
            },
            importer.source_counts(plan),
        )
        relationship_counts = importer.relationship_counts(plan)
        self.assertEqual(26, relationship_counts["NPC_KNOWS_CHUNK"])
        self.assertGreater(relationship_counts["CHUNK_POINTS_TO"], 0)
        self.assertGreater(relationship_counts["QUEST_REQUIRES_CLUE"], 0)

    def test_dry_run_writes_report_without_real_neo4j_driver(self):
        importer = load_importer_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "neo4j_story_source_import_report.md"
            summary = importer.dry_run_import(SOURCE_DIR, database="neo4j", report_path=report_path)

            self.assertTrue(report_path.exists())
            text = report_path.read_text(encoding="utf-8")
            self.assertIn("mode: dry-run", text)
            self.assertIn("validation: PASS", text)
            self.assertIn("- KnowledgeChunk: 26", text)
            self.assertIn("- database: neo4j", text)
            self.assertEqual("dry-run", getattr(summary, "mode"))

    def test_source_import_uses_database_and_does_not_reset_by_default(self):
        importer = load_importer_module()
        fake_driver = FakeNeo4jDriver()

        summary = importer.import_story_source(fake_driver, SOURCE_DIR, reset=False, database="neo4j")

        self.assertEqual("import", getattr(summary, "mode"))
        self.assertEqual(26, getattr(summary, "loaded_counts")["KnowledgeChunk"])
        self.assertTrue(fake_driver.calls)
        self.assertFalse(any("DETACH DELETE" in query for query, _ in fake_driver.calls))
        self.assertTrue(all(kwargs.get("database_") == "neo4j" for _, kwargs in fake_driver.calls))
        self.assertTrue(any("OPTIONAL MATCH (k)-[old_clue:POINTS_TO]" in query for query, _ in fake_driver.calls))

    def test_import_plan_validation_rejects_missing_chunk_clue_reference(self):
        importer = load_importer_module()
        plan = importer.build_import_plan(SOURCE_DIR)
        chunks = [dict(chunk) for chunk in getattr(plan, "chunks")]
        chunks[0]["clue_ids"] = ["missing_clue"]
        plan_type = cast(Any, plan).__class__
        bad_plan = plan_type(
            npcs=getattr(plan, "npcs"),
            chunks=chunks,
            locations=getattr(plan, "locations"),
            quests=getattr(plan, "quests"),
            world=getattr(plan, "world"),
        )

        errors = importer.validate_import_plan(bad_plan)

        self.assertTrue(any("missing clue" in error for error in errors))

    def test_existing_entity_id_sets_stay_fixed(self):
        importer = load_importer_module()
        npcs, chunks = importer.load_npcs(SOURCE_DIR)
        locations = importer.load_locations(SOURCE_DIR)
        quests = importer.load_quests(SOURCE_DIR)
        world = importer.load_world(SOURCE_DIR)

        self.assertEqual(
            ["chief_rowan", "mage_lumi", "minmin_lady", "patrol_leader_rio"],
            sorted(str(npc["npc_id"]) for npc in npcs),
        )
        self.assertEqual(
            [
                "chief_rowan.md#rowan_chronicle_001",
                "chief_rowan.md#rowan_chronicle_002",
                "chief_rowan.md#rowan_chronicle_003",
                "chief_rowan.md#rowan_chronicle_004",
                "chief_rowan.md#rowan_chronicle_005",
                "chief_rowan.md#rowan_chronicle_006",
                "chief_rowan.md#rowan_chronicle_007",
                "mage_lumi.md#lumi_chronicle_001",
                "mage_lumi.md#lumi_chronicle_002",
                "mage_lumi.md#lumi_chronicle_003",
                "mage_lumi.md#lumi_chronicle_004",
                "mage_lumi.md#lumi_chronicle_005",
                "minmin_lady.md#minmin_chronicle_001",
                "minmin_lady.md#minmin_chronicle_002",
                "minmin_lady.md#minmin_chronicle_003",
                "minmin_lady.md#minmin_chronicle_004",
                "minmin_lady.md#minmin_chronicle_005",
                "minmin_lady.md#minmin_chronicle_006",
                "minmin_lady.md#minmin_chronicle_007",
                "minmin_lady.md#minmin_chronicle_008",
                "patrol_leader_rio.md#rio_chronicle_001",
                "patrol_leader_rio.md#rio_chronicle_002",
                "patrol_leader_rio.md#rio_chronicle_003",
                "patrol_leader_rio.md#rio_chronicle_004",
                "patrol_leader_rio.md#rio_chronicle_005",
                "patrol_leader_rio.md#rio_chronicle_006",
            ],
            sorted(f"{Path(str(chunk['source_path'])).name}#{chunk['chunk_id']}" for chunk in chunks),
        )
        self.assertEqual(
            ["q_changed_signpost", "q_glowing_mushroom", "q_jelly_color", "q_main_spore_night", "q_pig_escape"],
            sorted(str(quest["quest_id"]) for quest in quests),
        )
        self.assertEqual(
            [
                "clue_bright_mushroom",
                "clue_changed_signpost",
                "clue_glittering_powder",
                "clue_jelly_color_change",
                "clue_mana_reaction",
                "clue_moonlit_night",
                "clue_pig_tracks",
                "clue_root_marks",
            ],
            sorted(str(clue["clue_id"]) for clue in world["clues"]),
        )
        self.assertEqual(
            ["truth_moonwell_mana_cycle", "truth_spore_scent_attraction", "truth_stump_followed_spores"],
            sorted(str(truth["truth_id"]) for truth in world["truths"]),
        )
        self.assertEqual(
            [
                "east_farm",
                "hazel_square",
                "magic_shop",
                "moonlight_spring",
                "pebble_path",
                "soft_field",
                "training_ground",
                "whispering_forest_entrance",
            ],
            sorted(str(location["location_id"]) for location in locations),
        )

    def test_each_existing_npc_markdown_has_dialogue_examples(self):
        missing_or_sparse: list[str] = []
        for path in sorted((SOURCE_DIR / "npcs").glob("*.md")):
            dialogue_section = section_after(path.read_text(encoding="utf-8"), "대화 예시")
            if dialogue_section.count("\n### ") < 5:
                missing_or_sparse.append(path.name)

        self.assertEqual([], missing_or_sparse)

    def test_source_dialogue_examples_do_not_leak_forbidden_truths(self):
        truths_data = cast(
            dict[str, object],
            yaml.safe_load((SOURCE_DIR / "world" / "truths.yaml").read_text(encoding="utf-8")),
        )
        forbidden_terms = [
            str(value)
            for truth in cast(list[dict[str, object]], truths_data["truths"])
            for value in [truth["truth_id"], truth["name"]]
        ]
        leaks: list[str] = []
        for path in sorted((SOURCE_DIR / "npcs").glob("*.md")):
            if path.name == "chief_rowan.md":
                continue
            dialogue_section = section_after(path.read_text(encoding="utf-8"), "대화 예시")
            for term in forbidden_terms:
                if term in dialogue_section:
                    leaks.append(f"{path.name}:{term}")

        self.assertEqual([], leaks)

    def test_every_chunk_clue_id_is_defined_in_world_clues(self):
        importer = load_importer_module()
        _, chunks = importer.load_npcs(SOURCE_DIR)
        world = importer.load_world(SOURCE_DIR)

        defined_clue_ids: set[str] = set()
        for clue in world["clues"]:
            clue_id = clue["clue_id"]
            assert isinstance(clue_id, str)
            defined_clue_ids.add(clue_id)

        used_clue_ids: set[str] = set()
        for chunk in chunks:
            clue_ids_obj = chunk.get("clue_ids", [])
            assert isinstance(clue_ids_obj, list)
            for clue_id in cast(list[object], clue_ids_obj):
                assert isinstance(clue_id, str)
                used_clue_ids.add(clue_id)

        self.assertEqual([], sorted(used_clue_ids - defined_clue_ids))

    def test_yaml_sources_use_importer_contract_keys(self):
        for path in sorted((SOURCE_DIR / "quests").glob("*.yaml")):
            quest = cast(
                dict[str, object],
                yaml.safe_load(path.read_text(encoding="utf-8")),
            )

            self.assertNotIn("involves", quest, path.name)
            self.assertNotIn("required_clues", quest, path.name)
            self.assertNotIn("answer_truth_id", quest, path.name)
            self.assertIn("involved_npc_ids", quest, path.name)
            self.assertIn("required_clue_ids", quest, path.name)
            self.assertIsInstance(quest.get("answer_truth_ids"), list, path.name)

        clues_data = cast(
            dict[str, object],
            yaml.safe_load((SOURCE_DIR / "world" / "clues.yaml").read_text(encoding="utf-8")),
        )
        clues = cast(list[dict[str, object]], clues_data["clues"])
        for clue in clues:
            self.assertNotIn("found_at", clue, clue["clue_id"])
            self.assertNotIn("points_to", clue, clue["clue_id"])
            self.assertIsInstance(clue.get("location_ids"), list, clue["clue_id"])
            self.assertIsInstance(clue.get("truth_ids"), list, clue["clue_id"])

        truths_data = cast(
            dict[str, object],
            yaml.safe_load((SOURCE_DIR / "world" / "truths.yaml").read_text(encoding="utf-8")),
        )
        truths = cast(list[dict[str, object]], truths_data["truths"])
        for truth in truths:
            reveal_conditions = cast(
                dict[str, object],
                truth.get("reveal_conditions", {}),
            )
            self.assertNotIn("quest_state", reveal_conditions, truth["truth_id"])
            self.assertNotIn("required_clues", reveal_conditions, truth["truth_id"])
            self.assertIsInstance(reveal_conditions.get("quest_states"), list, truth["truth_id"])
            self.assertIsInstance(reveal_conditions.get("required_clue_ids"), list, truth["truth_id"])

    def test_current_mvp_keeps_short_ids(self):
        importer = load_importer_module()
        npcs, chunks = importer.load_npcs(SOURCE_DIR)
        quests = importer.load_quests(SOURCE_DIR)
        world = importer.load_world(SOURCE_DIR)

        ids: list[str] = []
        for npc in npcs:
            npc_id = npc["npc_id"]
            assert isinstance(npc_id, str)
            ids.append(npc_id)
        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            assert isinstance(chunk_id, str)
            ids.append(chunk_id)
        for quest in quests:
            quest_id = quest["quest_id"]
            assert isinstance(quest_id, str)
            ids.append(quest_id)
        for clue in world["clues"]:
            clue_id = clue["clue_id"]
            assert isinstance(clue_id, str)
            ids.append(clue_id)
        for truth in world["truths"]:
            truth_id = truth["truth_id"]
            assert isinstance(truth_id, str)
            ids.append(truth_id)

        canonical_ids = sorted(entity_id for entity_id in ids if ":" in entity_id)
        self.assertEqual([], canonical_ids)

    def test_answer_sensitive_chunks_match_mvp_gating_policy(self):
        importer = load_importer_module()
        _, chunks = importer.load_npcs(SOURCE_DIR)
        by_id = {str(chunk["chunk_id"]): chunk for chunk in chunks}

        for chunk in chunks:
            if chunk["answer_sensitive"] is True:
                self.assertEqual(3, chunk["hint_level"], chunk["chunk_id"])

        for chunk_id in ["lumi_chronicle_003", "lumi_chronicle_004"]:
            chunk = by_id[chunk_id]
            self.assertEqual(False, chunk["answer_sensitive"])
            self.assertEqual(2, chunk["hint_level"])

        for chunk_id in ["rowan_chronicle_005", "rowan_chronicle_006", "rowan_chronicle_007"]:
            chunk = by_id[chunk_id]
            self.assertEqual(True, chunk["answer_sensitive"])
            self.assertEqual(3, chunk["hint_level"])

    def test_current_importer_does_not_auto_load_root_raw_markdown_sources(self):
        for path in raw_story_paths():
            self.assertTrue(path.exists(), path)

        importer = load_importer_module()
        npcs, chunks = importer.load_npcs(SOURCE_DIR)
        locations = importer.load_locations(SOURCE_DIR)
        quests = importer.load_quests(SOURCE_DIR)
        world = importer.load_world(SOURCE_DIR)

        raw_source_paths = {str(path) for path in raw_story_paths()}
        imported_source_paths: set[str] = set()
        for item in [*npcs, *chunks, *locations]:
            source_path = item.get("source_path")
            if isinstance(source_path, str):
                imported_source_paths.add(source_path)

        self.assertEqual(set(), imported_source_paths & raw_source_paths)
        self.assertEqual(4, len(npcs))
        self.assertEqual(26, len(chunks))
        self.assertEqual(0, len([quest for quest in quests if quest.get("source_path") in raw_source_paths]))
        self.assertEqual({"roles", "events", "clues", "truths"}, set(world))

    def test_raw_story_classifier_builds_review_only_summary_by_domain(self):
        classifier = load_classifier_module()
        report = classifier.build_report(SOURCE_DIR, raw_story_paths())

        self.assertEqual("review_only", report.get("mode"))
        summary = cast(dict[str, object], report.get("summary"))
        self.assertEqual({"location", "world", "npcs", "quests"}, set(summary))

        sources = cast(list[dict[str, object]], report.get("sources"))
        by_path = {Path(str(source["path"])).name: source for source in sources}
        map_source = by_path["hazel_village_map_stories.md"]
        npc_source = by_path["hazel_village_npc_chronicles_plain.md"]

        map_summary = cast(dict[str, int], map_source["summary"])
        npc_summary = cast(dict[str, int], npc_source["summary"])
        self.assertGreaterEqual(map_summary["location"], 2)
        self.assertGreaterEqual(npc_summary["npcs"], 2)

    def test_raw_story_classifier_refuses_to_overwrite_review_report_by_default(self):
        classifier = load_classifier_module()
        report = classifier.build_report(SOURCE_DIR, raw_story_paths())

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "story_source_classification_review.json"
            classifier.write_report(report, output_path)
            self.assertTrue(output_path.exists())

            with self.assertRaises(FileExistsError):
                classifier.write_report(report, output_path)

            classifier.write_report(report, output_path, overwrite=True)
            self.assertTrue(output_path.exists())

    def test_raw_story_classifier_never_writes_review_report_to_structured_sources(self):
        classifier = load_classifier_module()
        report = classifier.build_report(SOURCE_DIR, raw_story_paths())

        for folder in ["npcs", "locations", "quests", "world"]:
            output_path = SOURCE_DIR / folder / "story_source_classification_review.json"
            with self.assertRaises(ValueError, msg=folder):
                classifier.write_report(report, output_path, overwrite=True)
            self.assertFalse(output_path.exists(), folder)

    def test_story_source_classification_docs_explain_review_contract_in_korean(self):
        path = ROOT / "docs" / "story_source_classification.md"
        self.assertTrue(path.exists(), "docs/story_source_classification.md must document classifier rules")
        text = path.read_text(encoding="utf-8")

        self.assertRegex(text, r"[가-힣]")
        self.assertIn("현재 importer는 root raw markdown 파일을 자동으로 가져오지 않는다", text)
        for term in [
            "location",
            "world",
            "npcs",
            "quests",
            "YAML frontmatter",
            "story-chunk metadata",
            "비파괴",
            "review-only",
        ]:
            self.assertIn(term, text)


if __name__ == "__main__":
    _ = unittest.main()
