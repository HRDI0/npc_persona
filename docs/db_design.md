# 헤이즐 GraphRAG MVP DB 설계

이 문서는 현재 MVP가 실제로 사용하는 Neo4j 그래프 설계를 기준으로 한다. 지금 단계에서는 짧은 ID를 유지하며, `npc:*`, `quest:*`, `chunk:*` 형식의 canonical ID 이관은 하지 않는다.

## MVP 범위

현재 MVP 목표 데이터 수는 다음과 같다.

```text
NPCs: 4
Locations: 8
Quests: 5
Roles: 4
Events: 5
Clues: 8
Truths: 3
KnowledgeChunks: 26
```

Streamlit 앱은 `NPC` 프로필과 해당 NPC가 `KNOWS`로 연결된 `KnowledgeChunk`만 조회해 vLLM OpenAI-compatible `/v1/chat/completions`에 프롬프트로 전달한다. RDB, embedding index, canonical ID alias 테이블은 이후 확장 단계로 남긴다.

## ID 정책

MVP는 기존 코드와 UI가 사용하는 짧은 ID를 유지한다.

```text
minmin_lady
patrol_leader_rio
mage_lumi
chief_rowan
q_glowing_mushroom
minmin_chronicle_003
```

정규화 단계에서 사용할 canonical ID는 별도 매핑 문서나 alias 데이터로 추가할 수 있지만, 현재 Neo4j 노드의 조회 키는 바꾸지 않는다.

## 소스 파일 매핑

```text
rsc/data/npcs/*.md        -> NPC, KnowledgeChunk
rsc/data/locations/*.md   -> Location
rsc/data/quests/*.yaml    -> Quest
rsc/data/world/roles.yaml -> Role
rsc/data/world/events.yaml -> Event
rsc/data/world/clues.yaml -> Clue
rsc/data/world/truths.yaml -> Truth
```

NPC 문서의 `story-chunk`와 `chunk` fenced block은 모두 `KnowledgeChunk`로 적재된다. chunk 본문은 `KnowledgeChunk.text`가 되고, fenced metadata는 quest, role, hint, clue 연결의 기준이 된다.

## 노드 라벨과 고유 키

| Label | Unique key | 주요 속성 |
| --- | --- | --- |
| `NPC` | `npc_id` | `name`, `role`, `location_id`, `main_quest`, `personality`, `speech_style`, `knowledge_scope`, `restricted_knowledge`, `dialogue_must`, `dialogue_must_not`, `source_path` |
| `Role` | `role_id` | `name`, `description` |
| `Location` | `location_id` | `name`, `mood`, `summary`, `function`, `tags`, `source_path` |
| `Quest` | `quest_id` | `title`, `quest_type`, `summary`, `main_location_id`, `states`, `tags` |
| `Event` | `event_id` | `name`, `summary`, `visible`, `tags` |
| `Clue` | `clue_id` | `name`, `summary`, `hint_level`, `answer_sensitive`, `tags` |
| `Truth` | `truth_id` | `name`, `summary`, `answer_sensitive`, `reveal_quest_states`, `required_clue_ids`, `tags` |
| `KnowledgeChunk` | `chunk_id` | `npc_id`, `phase`, `title`, `knowledge_type`, `quest_id`, `allowed_roles`, `answer_sensitive`, `hint_level`, `tags`, `text`, `text_ref`, `source_path` |

Importer는 위 키에 대해 Neo4j uniqueness constraint를 생성한다.

## 관계 설계

| Relationship | From -> To | 의미 |
| --- | --- | --- |
| `HAS_ROLE` | `NPC` -> `Role` | NPC의 직업/역할 |
| `LOCATED_AT` | `NPC` -> `Location` | NPC 기본 위치 |
| `PARTICIPATES_IN` | `NPC` -> `Quest` | NPC의 대표 퀘스트 참여 |
| `STARTS_AT` | `Quest` -> `Location` | 퀘스트 주요 시작 위치 |
| `INVOLVES` | `Quest` -> `NPC` | 퀘스트 관련 NPC |
| `REQUIRES_CLUE` | `Quest` -> `Clue` | 퀘스트 풀이에 필요한 단서 |
| `HAS_ANSWER` | `Quest` -> `Truth` | 퀘스트 정답 진실 |
| `OCCURRED_AT` | `Event` -> `Location` | 사건 발생 위치 |
| `CAUSED_BY` | `Event` -> `Truth` | 사건 원인 |
| `FOUND_AT` | `Clue` -> `Location` | 단서를 찾는 장소 |
| `POINTS_TO` | `Clue` -> `Truth` | 단서가 가리키는 진실 |
| `KNOWS` | `NPC` -> `KnowledgeChunk` | NPC가 말할 수 있는 근거 지식 |
| `RELATED_TO` | `KnowledgeChunk` -> `Quest` | chunk 관련 퀘스트 |
| `MENTIONS` | `KnowledgeChunk` -> `Location` | chunk에서 언급한 장소 |
| `ABOUT` | `KnowledgeChunk` -> `Event` | chunk에서 다루는 사건 |
| `POINTS_TO` | `KnowledgeChunk` -> `Clue` | chunk가 제공하는 단서 |

`POINTS_TO`는 `Clue -> Truth`와 `KnowledgeChunk -> Clue`에서 모두 사용된다. 현재 MVP에서는 라벨 조합으로 의미가 구분된다.

## Streamlit 조회 계약

NPC 프로필은 `NPC.npc_id`로 조회한다. 말할 수 있는 chunk는 다음 조건을 통과해야 한다.

```cypher
MATCH (:NPC {npc_id: $npc_id})-[:KNOWS]->(k:KnowledgeChunk)
WHERE
  ($quest_id IS NULL OR k.quest_id = $quest_id OR k.quest_id IS NULL)
  AND $player_role IN k.allowed_roles
  AND k.hint_level <= $allowed_hint_level
  AND (k.answer_sensitive = false OR $quest_state IN ["ready_to_answer", "solved"])
RETURN k
ORDER BY k.hint_level ASC, k.chunk_id ASC
```

이 조건 때문에 모든 chunk는 먼저 `hint_level` 상한을 통과해야 하고, `answer_sensitive=true`인 최종 정답 chunk는 `ready_to_answer` 또는 `solved` 상태에서만 열린다. 중간 가설로 말해도 되는 루미의 마나 분석 chunk는 `answer_sensitive=false`, `hint_level=2`로 둔다.

## Importer 운영 방식

운영 DB에 원천 데이터를 반영할 때는 기본적으로 병합 적재를 사용한다.

```bash
uv run python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data
```

`--reset`은 모든 노드를 삭제한 뒤 다시 적재하므로 분리된 개발 DB 재생성 또는 명시적으로 승인된 DB 재구성에만 사용한다.

```bash
uv run python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data --reset
```

## 검증 쿼리

NPC별 chunk 수는 다음 결과가 나와야 한다.

```cypher
MATCH (n:NPC)
OPTIONAL MATCH (n)-[:KNOWS]->(k:KnowledgeChunk)
RETURN n.npc_id AS npc, n.name AS name, count(k) AS chunks
ORDER BY npc;
```

```text
chief_rowan        6
mage_lumi          4
minmin_lady        7
patrol_leader_rio  5
```

chunk에서만 언급되고 `world/clues.yaml`에 없는 placeholder clue는 없어야 한다.

```cypher
MATCH (c:Clue)
WHERE c.name IS NULL
RETURN c.clue_id AS placeholder_clue
ORDER BY placeholder_clue;
```

퀘스트 연결 검증은 다음 쿼리로 한다.

```cypher
MATCH (q:Quest)
OPTIONAL MATCH (q)-[:INVOLVES]->(n:NPC)
OPTIONAL MATCH (q)-[:REQUIRES_CLUE]->(c:Clue)
OPTIONAL MATCH (q)-[:HAS_ANSWER]->(t:Truth)
RETURN q.quest_id AS quest,
       collect(DISTINCT n.npc_id) AS npcs,
       collect(DISTINCT c.clue_id) AS clues,
       collect(DISTINCT t.truth_id) AS truths
ORDER BY quest;
```

## 이후 확장 방향

다음 단계에서는 canonical ID alias를 별도 계층으로 추가할 수 있다. 순서는 `legacy_id`와 `canonical_id`를 함께 저장하고, Streamlit과 importer가 두 ID를 모두 읽게 만든 뒤, 마지막에 UI와 원천 데이터를 canonical ID 중심으로 옮기는 방식이 안전하다.
