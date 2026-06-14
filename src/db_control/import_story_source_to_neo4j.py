import argparse
from collections import Counter
from dataclasses import dataclass
import os
import re
from pathlib import Path
from typing import Any

import yaml


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "admin2026")
DEFAULT_REPORT_PATH = Path("output/reports/neo4j_story_source_import_report.md")

EXPECTED_NPC_IDS = {"chief_rowan", "mage_lumi", "minmin_lady", "patrol_leader_rio"}
EXPECTED_QUEST_IDS = {"q_changed_signpost", "q_glowing_mushroom", "q_jelly_color", "q_main_spore_night", "q_pig_escape"}
EXPECTED_CHUNK_COUNTS = {
    "chief_rowan": 7,
    "mage_lumi": 5,
    "minmin_lady": 8,
    "patrol_leader_rio": 6,
}


@dataclass(frozen=True)
class ImportPlan:
    npcs: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    locations: list[dict[str, Any]]
    quests: list[dict[str, Any]]
    world: dict[str, list[dict[str, Any]]]


@dataclass(frozen=True)
class ImportSummary:
    mode: str
    reset: bool
    database: str | None
    source_counts: dict[str, int]
    relationship_counts: dict[str, int]
    loaded_counts: dict[str, int]
    validation_errors: list[str]


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
STORY_CHUNK_RE = re.compile(
    r"```(?:story-chunk|chunk)(?:\s+[^\n`]*)?\n(.*?)\n```\n(.*?)(?=\n```(?:story-chunk|chunk)|\n---|\n### |\n## |\n# |\Z)",
    re.DOTALL,
)


# -----------------------------
# Basic file parsers
# -----------------------------

def read_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_markdown_with_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)

    if not match:
        raise ValueError(f"Missing YAML frontmatter: {path}")

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        raise ValueError(
            f"\nYAML frontmatter parse error in file: {path}\n"
            f"원인 후보: YAML frontmatter 안에서 '* 항목'을 사용했습니다.\n"
            f"YAML 리스트는 '* 항목'이 아니라 '- 항목' 형식이어야 합니다.\n\n"
            f"{e}\n\n"
            f"--- frontmatter ---\n"
            f"{match.group(1)}\n"
            f"-------------------"
        ) from e

    body = text[match.end():]
    return frontmatter, body

def parse_story_chunks(markdown_body: str) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    pattern = re.compile(
        r"```(?:story-chunk|chunk)[^\n]*\n(.*?)\n```\n(.*?)(?=\n```(?:story-chunk|chunk)|\n### |\n## |\n# |\Z)",
        re.DOTALL,
    )

    for index, match in enumerate(pattern.finditer(markdown_body), start=1):
        metadata_text = match.group(1).strip()
        chunk_text = match.group(2).strip()

        try:
            metadata = yaml.safe_load(metadata_text) or {}
        except yaml.YAMLError as e:
            raise ValueError(
                f"\nYAML parse error in story-chunk #{index}\n"
                f"metadata:\n{metadata_text}\n"
            ) from e

        if not isinstance(metadata, dict):
            raise ValueError(
                f"\nstory-chunk #{index} metadata must be YAML mapping.\n"
                f"metadata:\n{metadata_text}\n"
            )

        required_fields = [
            "chunk_id",
            "phase",
            "title",
            "knowledge_type",
            "quest_id",
            "location_ids",
            "event_ids",
            "clue_ids",
            "allowed_roles",
            "answer_sensitive",
            "hint_level",
            "tags",
        ]

        missing = [field for field in required_fields if field not in metadata]
        if missing:
            raise ValueError(
                f"\nMissing required fields in story-chunk #{index}: {missing}\n"
                f"metadata:\n{metadata_text}\n"
            )

        metadata["text"] = chunk_text
        chunks.append(metadata)

    return chunks


def build_import_plan(source_dir: Path) -> ImportPlan:
    npcs, chunks = load_npcs(source_dir)
    return ImportPlan(
        npcs=npcs,
        chunks=chunks,
        locations=load_locations(source_dir),
        quests=load_quests(source_dir),
        world=load_world(source_dir),
    )


def source_counts(plan: ImportPlan) -> dict[str, int]:
    return {
        "NPC": len(plan.npcs),
        "Location": len(plan.locations),
        "Quest": len(plan.quests),
        "Role": len(plan.world["roles"]),
        "Event": len(plan.world["events"]),
        "Clue": len(plan.world["clues"]),
        "Truth": len(plan.world["truths"]),
        "KnowledgeChunk": len(plan.chunks),
    }


def relationship_counts(plan: ImportPlan) -> dict[str, int]:
    return {
        "NPC_HAS_ROLE": len(plan.npcs),
        "NPC_LOCATED_AT": len(plan.npcs),
        "NPC_PARTICIPATES_IN": sum(1 for npc in plan.npcs if npc.get("main_quest") is not None),
        "QUEST_STARTS_AT": sum(1 for quest in plan.quests if quest.get("main_location_id") is not None),
        "QUEST_INVOLVES": sum(len(quest.get("involved_npc_ids", [])) for quest in plan.quests),
        "QUEST_REQUIRES_CLUE": sum(len(quest.get("required_clue_ids", [])) for quest in plan.quests),
        "QUEST_HAS_ANSWER": sum(len(quest.get("answer_truth_ids", [])) for quest in plan.quests),
        "EVENT_OCCURRED_AT": sum(len(event.get("location_ids", [])) for event in plan.world["events"]),
        "EVENT_CAUSED_BY": sum(len(event.get("truth_ids", [])) for event in plan.world["events"]),
        "CLUE_FOUND_AT": sum(len(clue.get("location_ids", [])) for clue in plan.world["clues"]),
        "CLUE_POINTS_TO": sum(len(clue.get("truth_ids", [])) for clue in plan.world["clues"]),
        "NPC_KNOWS_CHUNK": len(plan.chunks),
        "CHUNK_RELATED_TO": sum(1 for chunk in plan.chunks if chunk.get("quest_id") is not None),
        "CHUNK_MENTIONS": sum(len(chunk.get("location_ids", [])) for chunk in plan.chunks),
        "CHUNK_ABOUT": sum(len(chunk.get("event_ids", [])) for chunk in plan.chunks),
        "CHUNK_POINTS_TO": sum(len(chunk.get("clue_ids", [])) for chunk in plan.chunks),
    }


def duplicate_ids(items: list[dict[str, Any]], key: str) -> list[str]:
    counts = Counter(str(item[key]) for item in items if key in item)
    return sorted(item_id for item_id, count in counts.items() if count > 1)


def validate_import_plan(plan: ImportPlan) -> list[str]:
    errors: list[str] = []
    npc_ids = {str(npc["npc_id"]) for npc in plan.npcs}
    quest_ids = {str(quest["quest_id"]) for quest in plan.quests}
    location_ids = {str(location["location_id"]) for location in plan.locations}
    role_ids = {str(role["role_id"]) for role in plan.world["roles"]}
    event_ids = {str(event["event_id"]) for event in plan.world["events"]}
    clue_ids = {str(clue["clue_id"]) for clue in plan.world["clues"]}
    truth_ids = {str(truth["truth_id"]) for truth in plan.world["truths"]}

    if npc_ids != EXPECTED_NPC_IDS:
        errors.append(f"NPC IDs changed: expected {sorted(EXPECTED_NPC_IDS)}, got {sorted(npc_ids)}")
    if quest_ids != EXPECTED_QUEST_IDS:
        errors.append(f"Quest IDs changed: expected {sorted(EXPECTED_QUEST_IDS)}, got {sorted(quest_ids)}")

    chunk_counts = dict(Counter(str(chunk["npc_id"]) for chunk in plan.chunks))
    if len(plan.chunks) != sum(EXPECTED_CHUNK_COUNTS.values()):
        errors.append(f"KnowledgeChunk count changed: expected 26, got {len(plan.chunks)}")
    if chunk_counts != EXPECTED_CHUNK_COUNTS:
        errors.append(f"KnowledgeChunk distribution changed: expected {EXPECTED_CHUNK_COUNTS}, got {chunk_counts}")

    for label, items, key in [
        ("NPC", plan.npcs, "npc_id"),
        ("Location", plan.locations, "location_id"),
        ("Quest", plan.quests, "quest_id"),
        ("Role", plan.world["roles"], "role_id"),
        ("Event", plan.world["events"], "event_id"),
        ("Clue", plan.world["clues"], "clue_id"),
        ("Truth", plan.world["truths"], "truth_id"),
        ("KnowledgeChunk", plan.chunks, "chunk_id"),
    ]:
        duplicates = duplicate_ids(items, key)
        if duplicates:
            errors.append(f"Duplicate {label} IDs: {duplicates}")

    for npc in plan.npcs:
        npc_id = str(npc["npc_id"])
        if str(npc.get("role", "")) not in role_ids:
            errors.append(f"NPC {npc_id} references missing role: {npc.get('role')}")
        if str(npc.get("location_id", "")) not in location_ids:
            errors.append(f"NPC {npc_id} references missing location: {npc.get('location_id')}")
        main_quest = npc.get("main_quest")
        if main_quest is not None and str(main_quest) not in quest_ids:
            errors.append(f"NPC {npc_id} references missing main_quest: {main_quest}")

    for quest in plan.quests:
        quest_id = str(quest["quest_id"])
        main_location = quest.get("main_location_id")
        if main_location is not None and str(main_location) not in location_ids:
            errors.append(f"Quest {quest_id} references missing main_location_id: {main_location}")
        for npc_id in quest.get("involved_npc_ids", []):
            if str(npc_id) not in npc_ids:
                errors.append(f"Quest {quest_id} references missing NPC: {npc_id}")
        for clue_id in quest.get("required_clue_ids", []):
            if str(clue_id) not in clue_ids:
                errors.append(f"Quest {quest_id} references missing clue: {clue_id}")
        for truth_id in quest.get("answer_truth_ids", []):
            if str(truth_id) not in truth_ids:
                errors.append(f"Quest {quest_id} references missing truth: {truth_id}")

    for event in plan.world["events"]:
        event_id = str(event["event_id"])
        for location_id in event.get("location_ids", []):
            if str(location_id) not in location_ids:
                errors.append(f"Event {event_id} references missing location: {location_id}")
        for truth_id in event.get("truth_ids", []):
            if str(truth_id) not in truth_ids:
                errors.append(f"Event {event_id} references missing truth: {truth_id}")

    for clue in plan.world["clues"]:
        clue_id = str(clue["clue_id"])
        for location_id in clue.get("location_ids", []):
            if str(location_id) not in location_ids:
                errors.append(f"Clue {clue_id} references missing location: {location_id}")
        for truth_id in clue.get("truth_ids", []):
            if str(truth_id) not in truth_ids:
                errors.append(f"Clue {clue_id} references missing truth: {truth_id}")

    for chunk in plan.chunks:
        chunk_id = str(chunk["chunk_id"])
        if str(chunk["npc_id"]) not in npc_ids:
            errors.append(f"Chunk {chunk_id} references missing NPC: {chunk['npc_id']}")
        quest_id = chunk.get("quest_id")
        if quest_id is not None and str(quest_id) not in quest_ids:
            errors.append(f"Chunk {chunk_id} references missing quest: {quest_id}")
        for location_id in chunk.get("location_ids", []):
            if str(location_id) not in location_ids:
                errors.append(f"Chunk {chunk_id} references missing location: {location_id}")
        for event_id in chunk.get("event_ids", []):
            if str(event_id) not in event_ids:
                errors.append(f"Chunk {chunk_id} references missing event: {event_id}")
        for clue_id in chunk.get("clue_ids", []):
            if str(clue_id) not in clue_ids:
                errors.append(f"Chunk {chunk_id} references missing clue: {clue_id}")
        if chunk.get("answer_sensitive") is True and chunk.get("hint_level") != 3:
            errors.append(f"Chunk {chunk_id} is answer_sensitive but hint_level is not 3")

    return errors


def raise_for_validation_errors(errors: list[str]) -> None:
    if errors:
        raise ValueError("Invalid story source import plan:\n" + "\n".join(f"- {error}" for error in errors))


class DriverWithDatabase:
    def __init__(self, driver: Any, database: str | None) -> None:
        self.driver = driver
        self.database = database

    def execute_query(self, query: str, **kwargs: Any) -> Any:
        if self.database and "database_" not in kwargs:
            kwargs["database_"] = self.database
        return self.driver.execute_query(query, **kwargs)


def write_import_report(path: Path, summary: ImportSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Neo4j Story Source Import Report",
        "",
        f"- mode: {summary.mode}",
        f"- reset: {str(summary.reset).lower()}",
        f"- database: {summary.database or 'driver default'}",
        f"- validation: {'PASS' if not summary.validation_errors else 'FAIL'}",
        "",
        "## Source Counts",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in summary.source_counts.items())
    lines.extend(["", "## Relationship Counts", ""])
    lines.extend(f"- {key}: {value}" for key, value in summary.relationship_counts.items())
    if summary.loaded_counts:
        lines.extend(["", "## Loaded Counts", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary.loaded_counts.items())
    if summary.validation_errors:
        lines.extend(["", "## Validation Errors", ""])
        lines.extend(f"- {error}" for error in summary.validation_errors)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# -----------------------------
# Neo4j setup
# -----------------------------

def reset_database(driver) -> None:
    driver.execute_query("MATCH (n) DETACH DELETE n")


def create_constraints(driver) -> None:
    queries = [
        """
        CREATE CONSTRAINT npc_id_unique IF NOT EXISTS
        FOR (n:NPC)
        REQUIRE n.npc_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT role_id_unique IF NOT EXISTS
        FOR (r:Role)
        REQUIRE r.role_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT location_id_unique IF NOT EXISTS
        FOR (l:Location)
        REQUIRE l.location_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT quest_id_unique IF NOT EXISTS
        FOR (q:Quest)
        REQUIRE q.quest_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT event_id_unique IF NOT EXISTS
        FOR (e:Event)
        REQUIRE e.event_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT clue_id_unique IF NOT EXISTS
        FOR (c:Clue)
        REQUIRE c.clue_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT truth_id_unique IF NOT EXISTS
        FOR (t:Truth)
        REQUIRE t.truth_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
        FOR (k:KnowledgeChunk)
        REQUIRE k.chunk_id IS UNIQUE
        """,
    ]

    for query in queries:
        driver.execute_query(query)


# -----------------------------
# Upsert source entities
# -----------------------------

def upsert_role(driver, role: dict[str, Any]) -> None:
    query = """
    MERGE (r:Role {role_id: $role_id})
    SET
      r.name = $name,
      r.description = $description
    """
    driver.execute_query(
        query,
        role_id=role["role_id"],
        name=role.get("name", role["role_id"]),
        description=role.get("description", ""),
    )


def upsert_location(driver, location: dict[str, Any]) -> None:
    query = """
    MERGE (l:Location {location_id: $location_id})
    SET
      l.name = $name,
      l.mood = $mood,
      l.summary = $summary,
      l.function = $function,
      l.tags = $tags,
      l.source_path = $source_path
    """
    driver.execute_query(
        query,
        location_id=location["location_id"],
        name=location.get("name", location["location_id"]),
        mood=location.get("mood", ""),
        summary=location.get("summary", ""),
        function=location.get("function", ""),
        tags=location.get("tags", []),
        source_path=location.get("source_path", ""),
    )


def upsert_npc(driver, npc: dict[str, Any]) -> None:
    query = """
    MERGE (n:NPC {npc_id: $npc_id})
    SET
      n.name = $name,
      n.role = $role,
      n.location_id = $location_id,
      n.main_quest = $main_quest,
      n.personality = $personality,
      n.speech_style = $speech_style,
      n.knowledge_scope = $knowledge_scope,
      n.restricted_knowledge = $restricted_knowledge,
      n.dialogue_must = $dialogue_must,
      n.dialogue_must_not = $dialogue_must_not,
      n.source_path = $source_path

    WITH n
    OPTIONAL MATCH (n)-[old_role:HAS_ROLE]->(:Role)
    DELETE old_role

    WITH n
    OPTIONAL MATCH (n)-[old_location:LOCATED_AT]->(:Location)
    DELETE old_location

    WITH n
    OPTIONAL MATCH (n)-[old_quest:PARTICIPATES_IN]->(:Quest)
    DELETE old_quest

    WITH n
    MERGE (r:Role {role_id: $role})
    MERGE (n)-[:HAS_ROLE]->(r)

    MERGE (loc:Location {location_id: $location_id})
    MERGE (n)-[:LOCATED_AT]->(loc)

    WITH n
    FOREACH (_ IN CASE WHEN $main_quest IS NULL THEN [] ELSE [1] END |
      MERGE (q:Quest {quest_id: $main_quest})
      MERGE (n)-[:PARTICIPATES_IN]->(q)
    )
    """

    dialogue_rules = npc.get("dialogue_rules", {}) or {}

    driver.execute_query(
        query,
        npc_id=npc["npc_id"],
        name=npc.get("name", npc["npc_id"]),
        role=npc.get("role", ""),
        location_id=npc.get("location_id", ""),
        main_quest=npc.get("main_quest"),
        personality=npc.get("personality", []),
        speech_style=npc.get("speech_style", []),
        knowledge_scope=npc.get("knowledge_scope", []),
        restricted_knowledge=npc.get("restricted_knowledge", []),
        dialogue_must=dialogue_rules.get("must", []),
        dialogue_must_not=dialogue_rules.get("must_not", []),
        source_path=npc.get("source_path", ""),
    )


def upsert_quest(driver, quest: dict[str, Any]) -> None:
    query = """
    MERGE (q:Quest {quest_id: $quest_id})
    SET
      q.title = $title,
      q.quest_type = $quest_type,
      q.summary = $summary,
      q.main_location_id = $main_location_id,
      q.states = $states,
      q.tags = $tags

    WITH q
    OPTIONAL MATCH (q)-[old_start:STARTS_AT]->(:Location)
    DELETE old_start

    WITH q
    FOREACH (_ IN CASE WHEN $main_location_id IS NULL THEN [] ELSE [1] END |
      MERGE (loc:Location {location_id: $main_location_id})
      MERGE (q)-[:STARTS_AT]->(loc)
    )
    """

    driver.execute_query(
        query,
        quest_id=quest["quest_id"],
        title=quest.get("title", quest["quest_id"]),
        quest_type=quest.get("quest_type", "dialogue"),
        summary=quest.get("summary", ""),
        main_location_id=quest.get("main_location_id"),
        states=quest.get("states", []),
        tags=quest.get("tags", []),
    )

    driver.execute_query(
        """
        MATCH (q:Quest {quest_id: $quest_id})
        OPTIONAL MATCH (q)-[r:INVOLVES]->(:NPC)
        DELETE r
        """,
        quest_id=quest["quest_id"],
    )

    for npc_id in quest.get("involved_npc_ids", []):
        driver.execute_query(
            """
            MATCH (q:Quest {quest_id: $quest_id})
            MERGE (n:NPC {npc_id: $npc_id})
            MERGE (q)-[:INVOLVES]->(n)
            """,
            quest_id=quest["quest_id"],
            npc_id=npc_id,
        )

    driver.execute_query(
        """
        MATCH (q:Quest {quest_id: $quest_id})
        OPTIONAL MATCH (q)-[r:REQUIRES_CLUE]->(:Clue)
        DELETE r
        """,
        quest_id=quest["quest_id"],
    )

    for clue_id in quest.get("required_clue_ids", []):
        driver.execute_query(
            """
            MATCH (q:Quest {quest_id: $quest_id})
            MERGE (c:Clue {clue_id: $clue_id})
            MERGE (q)-[:REQUIRES_CLUE]->(c)
            """,
            quest_id=quest["quest_id"],
            clue_id=clue_id,
        )

    driver.execute_query(
        """
        MATCH (q:Quest {quest_id: $quest_id})
        OPTIONAL MATCH (q)-[r:HAS_ANSWER]->(:Truth)
        DELETE r
        """,
        quest_id=quest["quest_id"],
    )

    for truth_id in quest.get("answer_truth_ids", []):
        driver.execute_query(
            """
            MATCH (q:Quest {quest_id: $quest_id})
            MERGE (t:Truth {truth_id: $truth_id})
            MERGE (q)-[:HAS_ANSWER]->(t)
            """,
            quest_id=quest["quest_id"],
            truth_id=truth_id,
        )


def upsert_event(driver, event: dict[str, Any]) -> None:
    query = """
    MERGE (e:Event {event_id: $event_id})
    SET
      e.name = $name,
      e.summary = $summary,
      e.visible = $visible,
      e.tags = $tags

    WITH e
    OPTIONAL MATCH (e)-[old_location:OCCURRED_AT]->(:Location)
    DELETE old_location

    WITH e
    OPTIONAL MATCH (e)-[old_truth:CAUSED_BY]->(:Truth)
    DELETE old_truth

    WITH e
    FOREACH (location_id IN $location_ids |
      MERGE (loc:Location {location_id: location_id})
      MERGE (e)-[:OCCURRED_AT]->(loc)
    )

    WITH e
    FOREACH (truth_id IN $truth_ids |
      MERGE (t:Truth {truth_id: truth_id})
      MERGE (e)-[:CAUSED_BY]->(t)
    )
    """

    driver.execute_query(
        query,
        event_id=event["event_id"],
        name=event.get("name", event["event_id"]),
        summary=event.get("summary", ""),
        visible=event.get("visible", True),
        tags=event.get("tags", []),
        location_ids=event.get("location_ids", []),
        truth_ids=event.get("truth_ids", []),
    )


def upsert_clue(driver, clue: dict[str, Any]) -> None:
    query = """
    MERGE (c:Clue {clue_id: $clue_id})
    SET
      c.name = $name,
      c.summary = $summary,
      c.hint_level = $hint_level,
      c.answer_sensitive = $answer_sensitive,
      c.tags = $tags

    WITH c
    OPTIONAL MATCH (c)-[old_location:FOUND_AT]->(:Location)
    DELETE old_location

    WITH c
    OPTIONAL MATCH (c)-[old_truth:POINTS_TO]->(:Truth)
    DELETE old_truth

    WITH c
    FOREACH (location_id IN $location_ids |
      MERGE (loc:Location {location_id: location_id})
      MERGE (c)-[:FOUND_AT]->(loc)
    )

    WITH c
    FOREACH (truth_id IN $truth_ids |
      MERGE (t:Truth {truth_id: truth_id})
      MERGE (c)-[:POINTS_TO]->(t)
    )
    """

    driver.execute_query(
        query,
        clue_id=clue["clue_id"],
        name=clue.get("name", clue["clue_id"]),
        summary=clue.get("summary", ""),
        hint_level=clue.get("hint_level", 0),
        answer_sensitive=clue.get("answer_sensitive", False),
        tags=clue.get("tags", []),
        location_ids=clue.get("location_ids", []),
        truth_ids=clue.get("truth_ids", []),
    )


def upsert_truth(driver, truth: dict[str, Any]) -> None:
    reveal_conditions = truth.get("reveal_conditions", {}) or {}

    query = """
    MERGE (t:Truth {truth_id: $truth_id})
    SET
      t.name = $name,
      t.summary = $summary,
      t.answer_sensitive = $answer_sensitive,
      t.reveal_quest_states = $reveal_quest_states,
      t.required_clue_ids = $required_clue_ids,
      t.tags = $tags
    """

    driver.execute_query(
        query,
        truth_id=truth["truth_id"],
        name=truth.get("name", truth["truth_id"]),
        summary=truth.get("summary", ""),
        answer_sensitive=truth.get("answer_sensitive", True),
        reveal_quest_states=reveal_conditions.get("quest_states", []),
        required_clue_ids=reveal_conditions.get("required_clue_ids", []),
        tags=truth.get("tags", []),
    )


def upsert_knowledge_chunk(driver, chunk: dict[str, Any]) -> None:
    query = """
    MERGE (k:KnowledgeChunk {chunk_id: $chunk_id})
    SET
      k.npc_id = $npc_id,
      k.phase = $phase,
      k.title = $title,
      k.knowledge_type = $knowledge_type,
      k.quest_id = $quest_id,
      k.allowed_roles = $allowed_roles,
      k.answer_sensitive = $answer_sensitive,
      k.hint_level = $hint_level,
      k.tags = $tags,
      k.text = $text,
      k.text_ref = $text_ref,
      k.source_path = $source_path

    WITH k
    OPTIONAL MATCH (:NPC)-[old_knows:KNOWS]->(k)
    DELETE old_knows

    WITH k
    OPTIONAL MATCH (k)-[old_related:RELATED_TO]->(:Quest)
    DELETE old_related

    WITH k
    OPTIONAL MATCH (k)-[old_location:MENTIONS]->(:Location)
    DELETE old_location

    WITH k
    OPTIONAL MATCH (k)-[old_event:ABOUT]->(:Event)
    DELETE old_event

    WITH k
    OPTIONAL MATCH (k)-[old_clue:POINTS_TO]->(:Clue)
    DELETE old_clue

    WITH k
    MATCH (n:NPC {npc_id: $npc_id})
    MERGE (n)-[:KNOWS]->(k)

    WITH k
    FOREACH (_ IN CASE WHEN $quest_id IS NULL THEN [] ELSE [1] END |
      MERGE (q:Quest {quest_id: $quest_id})
      MERGE (k)-[:RELATED_TO]->(q)
    )

    WITH k
    FOREACH (location_id IN $location_ids |
      MERGE (loc:Location {location_id: location_id})
      MERGE (k)-[:MENTIONS]->(loc)
    )

    WITH k
    FOREACH (event_id IN $event_ids |
      MERGE (e:Event {event_id: event_id})
      MERGE (k)-[:ABOUT]->(e)
    )

    WITH k
    FOREACH (clue_id IN $clue_ids |
      MERGE (c:Clue {clue_id: clue_id})
      MERGE (k)-[:POINTS_TO]->(c)
    )
    """

    driver.execute_query(
        query,
        npc_id=chunk["npc_id"],
        chunk_id=chunk["chunk_id"],
        phase=chunk.get("phase", ""),
        title=chunk.get("title", chunk["chunk_id"]),
        knowledge_type=chunk.get("knowledge_type", ""),
        quest_id=chunk.get("quest_id"),
        location_ids=chunk.get("location_ids", []),
        event_ids=chunk.get("event_ids", []),
        clue_ids=chunk.get("clue_ids", []),
        allowed_roles=chunk.get("allowed_roles", []),
        answer_sensitive=chunk.get("answer_sensitive", False),
        hint_level=chunk.get("hint_level", 0),
        tags=chunk.get("tags", []),
        text=chunk.get("text", ""),
        text_ref=f"{chunk.get('source_path', '')}#{chunk['chunk_id']}",
        source_path=chunk.get("source_path", ""),
    )


# -----------------------------
# Source loading
# -----------------------------

def load_npcs(source_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    npc_dir = source_dir / "npcs"
    npcs: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []

    for path in sorted(npc_dir.glob("*.md")):
        frontmatter, body = parse_markdown_with_frontmatter(path)

        npc = dict(frontmatter)
        npc["source_path"] = str(path)
        npcs.append(npc)

        parsed_chunks = parse_story_chunks(body)
        for chunk in parsed_chunks:
            chunk["npc_id"] = npc["npc_id"]
            chunk["source_path"] = str(path)
            chunks.append(chunk)

    return npcs, chunks


def load_locations(source_dir: Path) -> list[dict[str, Any]]:
    location_dir = source_dir / "locations"
    locations: list[dict[str, Any]] = []

    for path in sorted(location_dir.glob("*.md")):
        frontmatter, body = parse_markdown_with_frontmatter(path)
        location = dict(frontmatter)
        location["source_path"] = str(path)

        if "summary" not in location:
            # 간단 기본값: 첫 문단을 summary로 사용
            first_paragraph = body.strip().split("\n\n")[0].strip()
            location["summary"] = first_paragraph[:500]

        locations.append(location)

    return locations


def load_quests(source_dir: Path) -> list[dict[str, Any]]:
    quest_dir = source_dir / "quests"
    quests: list[dict[str, Any]] = []

    for path in sorted(quest_dir.glob("*.yaml")):
        data = read_yaml(path)
        if not data:
            continue

        if "quest_id" in data:
            quests.append(data)
        elif "quests" in data:
            quests.extend(data["quests"])

    return quests


def load_world(source_dir: Path) -> dict[str, list[dict[str, Any]]]:
    world_dir = source_dir / "world"

    roles_data = read_yaml(world_dir / "roles.yaml") or {}
    events_data = read_yaml(world_dir / "events.yaml") or {}
    clues_data = read_yaml(world_dir / "clues.yaml") or {}
    truths_data = read_yaml(world_dir / "truths.yaml") or {}

    return {
        "roles": roles_data.get("roles", []),
        "events": events_data.get("events", []),
        "clues": clues_data.get("clues", []),
        "truths": truths_data.get("truths", []),
    }


# -----------------------------
# Main import
# -----------------------------

def import_story_source(
    driver: Any,
    source_dir: Path,
    reset: bool = False,
    database: str | None = None,
    report_path: Path | None = None,
) -> ImportSummary:
    plan = build_import_plan(source_dir)
    validation_errors = validate_import_plan(plan)
    raise_for_validation_errors(validation_errors)
    db_driver = DriverWithDatabase(driver, database)

    if reset:
        reset_database(db_driver)

    create_constraints(db_driver)

    for role in plan.world["roles"]:
        upsert_role(db_driver, role)

    for truth in plan.world["truths"]:
        upsert_truth(db_driver, truth)

    for location in plan.locations:
        upsert_location(db_driver, location)

    for event in plan.world["events"]:
        upsert_event(db_driver, event)

    for clue in plan.world["clues"]:
        upsert_clue(db_driver, clue)

    for quest in plan.quests:
        upsert_quest(db_driver, quest)

    for npc in plan.npcs:
        upsert_npc(db_driver, npc)

    for chunk in plan.chunks:
        upsert_knowledge_chunk(db_driver, chunk)

    counts = source_counts(plan)
    summary = ImportSummary(
        mode="import",
        reset=reset,
        database=database,
        source_counts=counts,
        relationship_counts=relationship_counts(plan),
        loaded_counts=counts,
        validation_errors=validation_errors,
    )

    if report_path is not None:
        write_import_report(report_path, summary)

    print("Import complete.")
    print(f"- NPCs: {counts['NPC']}")
    print(f"- Locations: {counts['Location']}")
    print(f"- Quests: {counts['Quest']}")
    print(f"- Roles: {counts['Role']}")
    print(f"- Events: {counts['Event']}")
    print(f"- Clues: {counts['Clue']}")
    print(f"- Truths: {counts['Truth']}")
    print(f"- KnowledgeChunks: {counts['KnowledgeChunk']}")
    return summary


def dry_run_import(source_dir: Path, database: str | None = None, report_path: Path | None = None) -> ImportSummary:
    plan = build_import_plan(source_dir)
    validation_errors = validate_import_plan(plan)
    summary = ImportSummary(
        mode="dry-run",
        reset=False,
        database=database,
        source_counts=source_counts(plan),
        relationship_counts=relationship_counts(plan),
        loaded_counts={},
        validation_errors=validation_errors,
    )
    if report_path is not None:
        write_import_report(report_path, summary)
    raise_for_validation_errors(validation_errors)
    print("Dry-run validation complete.")
    for label, count in summary.source_counts.items():
        print(f"- {label}: {count}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        default="story-source",
        help="Path to story-source directory",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all Neo4j nodes before import",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize source data without connecting to Neo4j",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("NEO4J_DATABASE"),
        help="Neo4j database name. Defaults to NEO4J_DATABASE or driver default",
    )
    parser.add_argument(
        "--report-path",
        default=str(DEFAULT_REPORT_PATH),
        help="Markdown report path for source import summary",
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    report_path = Path(args.report_path)

    if args.dry_run:
        dry_run_import(source_dir, database=args.database, report_path=report_path)
        return

    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise SystemExit("neo4j package is required for live import. Run `uv sync --frozen` or use `--dry-run`.") from exc

    with GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    ) as driver:
        import_story_source(driver, source_dir, reset=args.reset, database=args.database, report_path=report_path)


if __name__ == "__main__":
    main()
