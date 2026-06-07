import argparse
import os
import re
from pathlib import Path
from typing import Any

import yaml
from neo4j import GraphDatabase


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "admin2026")


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
STORY_CHUNK_RE = re.compile(
    r"```story-chunk(?:\s+[^\n`]*)?\n(.*?)\n```\n(.*?)(?=\n---|\n### |\n## |\n# |\Z)",
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
        r"```story-chunk[^\n]*\n(.*?)\n```\n(.*?)(?=\n### |\n## |\n# |\Z)",
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
    UNWIND $location_ids AS location_id
      MERGE (loc:Location {location_id: location_id})
      MERGE (e)-[:OCCURRED_AT]->(loc)

    WITH e
    UNWIND $truth_ids AS truth_id
      MERGE (t:Truth {truth_id: truth_id})
      MERGE (e)-[:CAUSED_BY]->(t)
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
    UNWIND $location_ids AS location_id
      MERGE (loc:Location {location_id: location_id})
      MERGE (c)-[:FOUND_AT]->(loc)

    WITH c
    UNWIND $truth_ids AS truth_id
      MERGE (t:Truth {truth_id: truth_id})
      MERGE (c)-[:POINTS_TO]->(t)
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
    MATCH (n:NPC {npc_id: $npc_id})

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

    MERGE (n)-[:KNOWS]->(k)

    WITH k
    FOREACH (_ IN CASE WHEN $quest_id IS NULL THEN [] ELSE [1] END |
      MERGE (q:Quest {quest_id: $quest_id})
      MERGE (k)-[:RELATED_TO]->(q)
    )

    WITH k
    UNWIND $location_ids AS location_id
      MERGE (loc:Location {location_id: location_id})
      MERGE (k)-[:MENTIONS]->(loc)

    WITH k
    UNWIND $event_ids AS event_id
      MERGE (e:Event {event_id: event_id})
      MERGE (k)-[:ABOUT]->(e)

    WITH k
    UNWIND $clue_ids AS clue_id
      MERGE (c:Clue {clue_id: clue_id})
      MERGE (k)-[:POINTS_TO]->(c)
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

def import_story_source(driver, source_dir: Path, reset: bool = False) -> None:
    if reset:
        reset_database(driver)

    create_constraints(driver)

    npcs, chunks = load_npcs(source_dir)
    locations = load_locations(source_dir)
    quests = load_quests(source_dir)
    world = load_world(source_dir)

    # 먼저 기본 엔티티
    for role in world["roles"]:
        upsert_role(driver, role)

    for truth in world["truths"]:
        upsert_truth(driver, truth)

    for location in locations:
        upsert_location(driver, location)

    for event in world["events"]:
        upsert_event(driver, event)

    for clue in world["clues"]:
        upsert_clue(driver, clue)

    for quest in quests:
        upsert_quest(driver, quest)

    for npc in npcs:
        upsert_npc(driver, npc)

    for chunk in chunks:
        upsert_knowledge_chunk(driver, chunk)

    print("Import complete.")
    print(f"- NPCs: {len(npcs)}")
    print(f"- Locations: {len(locations)}")
    print(f"- Quests: {len(quests)}")
    print(f"- Roles: {len(world['roles'])}")
    print(f"- Events: {len(world['events'])}")
    print(f"- Clues: {len(world['clues'])}")
    print(f"- Truths: {len(world['truths'])}")
    print(f"- KnowledgeChunks: {len(chunks)}")


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
    args = parser.parse_args()

    source_dir = Path(args.source_dir)

    with GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    ) as driver:
        import_story_source(driver, source_dir, reset=args.reset)


if __name__ == "__main__":
    main()