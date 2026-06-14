# Neo4j Story Import Guide

이 문서는 현재 `rsc/data` 구조를 Neo4j에 적재하는 방법을 설명한다. 신규 NPC, 신규 퀘스트, 신규 clue/truth ID를 만들지 않고 기존 4명 NPC와 5개 퀘스트만 사용한다.

## 1. 산출물 생성 후 CSV를 적재하는 경로

```bash
python scripts/story_pipeline/run_pipeline.py
```

`run_pipeline.py`는 네 단계를 순서대로 실행한다.

1. `build_integrated_data.py`: `rsc/data/npcs`, `rsc/data/quests`, `rsc/data/world`, `rsc/data/locations`를 읽고 `output/integrated/hazel_story_integrated.json`과 YAML을 만든다.
2. `validate_data.py`: 통합 JSON/YAML이 같은지 확인하고, quest/clue/truth 참조와 forbidden truth 누출을 검사한다.
3. `export_neo4j_import_files.py`: 통합 JSON을 `output/neo4j_import/*.csv`와 `constraints.cypher`로 변환한다.
4. `validate_data.py`: 생성된 CSV 관계가 실제 노드를 가리키는지 다시 검사한다.

Neo4j까지 바로 넣으려면 다음 명령을 쓴다.

```bash
python scripts/story_pipeline/run_pipeline.py --load-neo4j
```

이때 마지막에 `load_neo4j.py`가 추가로 실행된다. 이미 CSV가 생성되어 있다면 다음 명령만 실행해도 된다.

```bash
python scripts/story_pipeline/load_neo4j.py
```

## 2. `load_neo4j.py` 코드 흐름

`scripts/story_pipeline/load_neo4j.py`는 CSV 산출물을 Neo4j에 병합한다.

1. `ROOT`, `OUTPUT_DIR`, `IMPORT_DIR`는 프로젝트 루트와 `output/neo4j_import` 위치를 정한다.
2. `ALLOWED_LABELS`는 적재 가능한 노드 라벨을 `NPC`, `Quest`, `Clue`, `Truth`, `Location`, `Dialogue`로 제한한다.
3. `ALLOWED_RELATIONSHIPS`는 관계 타입을 화이트리스트로 제한한다. CSV에 다른 관계명이 들어오면 적재하지 않는다.
4. `NODE_FILES`는 라벨별 CSV 파일명을 연결한다.
5. `load_dotenv_if_available()`은 `python-dotenv`가 설치되어 있으면 루트 `.env`와 `output/.env`를 읽는다.
6. `parse_props(row)`는 CSV 문자열을 Neo4j 속성으로 바꾼다. 빈 값은 생략하고, `True`/`False`는 boolean으로 변환하고, JSON 문자열은 list/dict로 파싱한다.
7. `read_csv(path)`는 UTF-8 CSV를 `dict` 목록으로 읽는다.
8. `run_constraints(driver, database)`는 `constraints.cypher`의 각 문장을 실행해 ID uniqueness constraint를 만든다.
9. `load_nodes(driver, database)`는 라벨별 CSV를 읽고 `MERGE (n:Label {id: $id}) SET n += $props`로 노드를 만든다. `MERGE`라서 같은 ID는 중복 생성하지 않고 갱신한다.
10. `load_relationships(driver, database)`는 `relationships.csv`를 읽고 시작/끝 라벨과 관계 타입이 허용 목록에 있는지 검사한 뒤 `MATCH`와 `MERGE`로 관계를 만든다.
11. `main()`은 `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`를 읽고 드라이버를 연 뒤 constraint, node, relationship 순서로 적재한다.
12. 적재가 끝나면 `output/reports/neo4j_load_report.md`에 생성 개수를 기록한다.

필수 환경변수는 다음과 같다.

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
NEO4J_DATABASE=neo4j
```

`NEO4J_PASSWORD`가 없으면 적재를 중단한다. 비밀번호는 README나 코드에 직접 쓰지 않는다.

## 3. 원천 `rsc/data`를 바로 적재하는 경로

CSV 산출물이 아니라 Markdown/YAML 원천을 그대로 Neo4j에 넣고 싶으면 다음 명령을 사용한다.

```bash
python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data
```

이 경로는 `KnowledgeChunk`를 만든다는 점이 중요하다. NPC 파일의 YAML frontmatter는 `NPC` 노드가 되고, 각 ```chunk 또는 ```story-chunk 블록은 `KnowledgeChunk` 노드가 된다.

## 4. `import_story_source_to_neo4j.py` 코드 흐름

`src/db_control/import_story_source_to_neo4j.py`는 GraphRAG용 원천 그래프를 만든다.

1. `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`는 환경변수에서 읽고, 없으면 기본 개발값을 사용한다.
2. `FRONTMATTER_RE`는 Markdown 맨 위의 `--- ... ---` YAML frontmatter를 찾는다.
3. `parse_markdown_with_frontmatter(path)`는 NPC/Location Markdown에서 frontmatter와 본문을 분리한다.
4. `parse_story_chunks(markdown_body)`는 ```chunk와 ```story-chunk 코드블록을 찾아 YAML 메타데이터와 본문을 하나의 dict로 합친다.
5. story chunk에는 `chunk_id`, `phase`, `title`, `knowledge_type`, `quest_id`, `location_ids`, `event_ids`, `clue_ids`, `allowed_roles`, `answer_sensitive`, `hint_level`, `tags`가 반드시 있어야 한다.
6. `create_constraints(driver)`는 `npc_id`, `quest_id`, `clue_id`, `truth_id`, `chunk_id` 등에 uniqueness constraint를 만든다.
7. `upsert_role`, `upsert_location`, `upsert_quest`, `upsert_event`, `upsert_clue`, `upsert_truth`는 각 원천 YAML/Markdown 항목을 노드로 병합한다.
8. `upsert_npc(driver, npc)`는 NPC frontmatter를 `NPC` 노드 속성으로 저장하고 `HAS_ROLE`, `LOCATED_AT`, `PARTICIPATES_IN` 관계를 만든다.
9. `upsert_knowledge_chunk(driver, chunk)`는 chunk 본문을 `KnowledgeChunk.text`에 저장하고, 해당 NPC와 `KNOWS` 관계를 만든다.
10. 같은 chunk는 `RELATED_TO`로 Quest에, `MENTIONS`로 Location에, `ABOUT`으로 Event에, `POINTS_TO`로 Clue에 연결된다.
11. `load_npcs(source_dir)`는 `rsc/data/npcs/*.md`를 읽어 NPC 목록과 chunk 목록을 만든다.
12. `load_locations`, `load_quests`, `load_world`는 locations/quests/world 디렉터리를 읽는다.
13. `import_story_source(driver, source_dir, reset=False)`는 constraint를 만든 뒤 Role, Truth, Location, Event, Clue, Quest, NPC, KnowledgeChunk 순서로 적재한다.
14. `--reset`은 전체 노드 삭제 옵션이다. 개발 DB를 명시적으로 초기화할 때만 써야 하며, 일반 적재에서는 사용하지 않는다.

## 5. Neo4j Browser 확인 쿼리

적재 후 다음 쿼리로 결과를 확인한다.

```cypher
MATCH (n) RETURN labels(n) AS labels, count(*) AS count ORDER BY count DESC;
```

노드 라벨별 개수를 확인한다.

```cypher
MATCH (:NPC {npc_id: "mage_lumi"})-[:KNOWS]->(k:KnowledgeChunk)
RETURN k.chunk_id, k.title, k.hint_level, k.answer_sensitive
ORDER BY k.chunk_id;
```

특정 NPC가 아는 지식 조각을 확인한다.

```cypher
MATCH (q:Quest)-[:REQUIRES_CLUE]->(c:Clue)
RETURN q.quest_id, collect(c.clue_id) AS required_clues
ORDER BY q.quest_id;
```

퀘스트가 요구하는 단서가 기존 clue_id만 사용하는지 확인한다.

```cypher
MATCH (k:KnowledgeChunk)-[:POINTS_TO]->(c:Clue)
RETURN k.chunk_id, collect(c.clue_id) AS clues
ORDER BY k.chunk_id;
```

KnowledgeChunk가 어떤 단서와 연결되는지 확인한다.

## 6. 주의사항

- 신규 NPC를 넣지 않는다.
- 신규 지역을 대량으로 만들지 않는다.
- 기존 `quest_id`, `clue_id`, `truth_id`를 바꾸지 않는다.
- reveal 조건 전에는 최종 진실을 대사에 직접 쓰지 않는다.
- `reset_neo4j_dev.py`나 `--reset`은 사용자가 명시적으로 승인한 개발 DB에서만 실행한다.
- 생성 CSV 경로와 원천 `KnowledgeChunk` 경로는 목적이 다르므로, 둘 중 하나를 기준 경로로 정해 운영한다.
