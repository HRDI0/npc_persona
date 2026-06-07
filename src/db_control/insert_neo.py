import os
from neo4j import GraphDatabase


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "admin2026")


def create_constraints(driver):
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
        CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
        FOR (k:KnowledgeChunk)
        REQUIRE k.chunk_id IS UNIQUE
        """
    ]

    for query in queries:
        driver.execute_query(query)


def upsert_npc(driver, npc):
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
      n.restricted_knowledge = $restricted_knowledge

    MERGE (r:Role {role_id: $role})
    MERGE (n)-[:HAS_ROLE]->(r)

    MERGE (loc:Location {location_id: $location_id})
    MERGE (n)-[:LOCATED_AT]->(loc)

    MERGE (q:Quest {quest_id: $main_quest})
    MERGE (n)-[:PARTICIPATES_IN]->(q)
    """

    driver.execute_query(
        query,
        npc_id=npc["npc_id"],
        name=npc["name"],
        role=npc["role"],
        location_id=npc["location_id"],
        main_quest=npc["main_quest"],
        personality=npc["personality"],
        speech_style=npc["speech_style"],
        knowledge_scope=npc["knowledge_scope"],
        restricted_knowledge=npc["restricted_knowledge"],
    )


def upsert_chunk(driver, chunk):
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
      k.text_ref = $text_ref

    MERGE (n)-[:KNOWS]->(k)

    WITH k

    MERGE (q:Quest {quest_id: $quest_id})
    MERGE (k)-[:RELATED_TO]->(q)

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
        phase=chunk["phase"],
        title=chunk["title"],
        knowledge_type=chunk["knowledge_type"],
        quest_id=chunk["quest_id"],
        location_ids=chunk["location_ids"],
        event_ids=chunk["event_ids"],
        clue_ids=chunk["clue_ids"],
        allowed_roles=chunk["allowed_roles"],
        answer_sensitive=chunk["answer_sensitive"],
        hint_level=chunk["hint_level"],
        tags=chunk["tags"],
        text=chunk["text"],
        text_ref=f"knowledge_chunks.jsonl#{chunk['chunk_id']}",
    )


if __name__ == "__main__":
    npc = {
        "npc_id": "minmin_lady",
        "name": "민민 부인",
        "role": "farmer",
        "location_id": "east_farm",
        "main_quest": "q_glowing_mushroom",
        "personality": ["다정함", "잔소리가 많음", "생활감 있음"],
        "speech_style": [
            '문장 끝에 "~란다", "~하렴", "~지 뭐니"를 자주 사용한다.',
            "농사, 밥, 장보기, 날씨 같은 생활 비유를 자주 사용한다."
        ],
        "knowledge_scope": [
            "farm_life",
            "farm_observation",
            "village_rumor",
            "creature_habit",
            "crop_condition"
        ],
        "restricted_knowledge": [
            "moonlight_spring_mana_principle",
            "chief_confidential_report",
            "magic_spore_analysis",
            "final_truth"
        ]
    }

    chunk = {
        "chunk_id": "minmin_chronicle_003",
        "npc_id": "minmin_lady",
        "phase": "mushroom_change",
        "title": "민민 부인이 본 몽실버섯의 변화",
        "knowledge_type": "farm_observation",
        "quest_id": "q_glowing_mushroom",
        "location_ids": ["whispering_forest_entrance"],
        "event_ids": ["event_glowing_mushroom"],
        "clue_ids": [
            "clue_mushroom_glows_at_night",
            "clue_brighter_under_moonlight"
        ],
        "allowed_roles": ["farmer", "lord"],
        "answer_sensitive": False,
        "hint_level": 1,
        "tags": [
            "민민 부인",
            "몽실버섯",
            "밤",
            "달빛",
            "속삭임 숲 입구",
            "생활 관찰"
        ],
        "text": (
            "어느 밝은 달밤, 민민 부인은 농장 일을 마치고 속삭임 숲 입구를 지나가다가 "
            "몽실버섯이 평소보다 훨씬 강하게 빛나는 모습을 보았다. "
            "그녀는 그 현상이 낮에는 보이지 않고 밤에만 나타난다는 점을 기억했다. "
            "특히 달이 밝은 밤일수록 몽실버섯의 빛이 강해지는 것 같다고 느꼈다. "
            "하지만 민민 부인은 그 원리를 알지 못한다."
        )
    }

    with GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    ) as driver:
        create_constraints(driver)
        upsert_npc(driver, npc)
        upsert_chunk(driver, chunk)

    print("Imported minmin_lady example into Neo4j.")