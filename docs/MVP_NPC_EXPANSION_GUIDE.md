# 헤이즐 GraphRAG MVP NPC 확장 가이드

이 문서는 현재 `민민 부인` 중심 MVP를 유지하면서 `리오`, `루미`, `로완` 등 다른 NPC를 순차적으로 붙이는 작업 가이드다. 기존 설계 문서의 최종 목표는 `RDB + Neo4j Graph DB + RAG + GraphRAG Runtime`이지만, 현재 MVP는 더 단순하다.

현재 MVP는 다음 구조로 동작한다.

```text
Streamlit UI
  -> Neo4j에서 NPC profile 조회
  -> Neo4j에서 현재 NPC가 KNOWS로 연결된 KnowledgeChunk 조회
  -> vLLM OpenAI-compatible /v1/chat/completions 호출
  -> NPC 말투로 답변 출력
```

따라서 지금은 최종 설계서의 모든 구조를 한 번에 도입하지 말고, 다음 순서로 진행한다.

```text
1. 서버에서 가져온 Neo4j / vLLM 상태를 먼저 재현한다.
2. 현재 MVP의 짧은 ID 체계를 깨지 않는다.
3. 다른 NPC 데이터가 현재 importer와 app에서 읽히도록 형식을 맞춘다.
4. Neo4j에 4명 NPC와 chunk가 모두 들어오는지 검증한다.
5. Streamlit에서 NPC를 바꿔가며 누설 방지와 말투를 확인한다.
6. 그 다음 canonical ID와 GraphRAG 정규화 구조로 확장한다.
```

---

## 1. 현재 파일 기준으로 이해해야 할 것

### 1.1 핵심 파일

```text
src/streamlit/test_app.py
  현재 Streamlit 챗 MVP.
  Neo4j에서 NPC와 KnowledgeChunk를 조회하고 vLLM에 prompt를 보낸다.

src/db_control/import_story_source_to_neo4j.py
  rsc/data 아래 NPC, location, quest, world 데이터를 Neo4j로 적재한다.

src/db_control/insert_neo.py
  민민 부인 단일 샘플 적재용 예전 스크립트다.
  확장 작업 기준은 import_story_source_to_neo4j.py로 잡는다.

rsc/data/npcs/*.md
  NPC frontmatter와 knowledge chunk 원천.

rsc/data/locations/*.md
  장소 원천.

rsc/data/quests/*.yaml
  퀘스트 원천.

rsc/data/world/*.yaml
  역할, 단서, 사건, 진실, 대화 정책 원천.

data_export/neo4j/neo4j.dump
  선택적 로컬 참고 자료다. 저장소에 포함하지 않으며, 현재 재현 가능한 기본 경로는 rsc/data 원천을 importer로 다시 적재하는 방식이다.

data_export/vllm/*
  선택적 로컬 참고 자료다. 저장소에 포함하지 않으며, 배포 문서와 compose 환경변수로 런타임을 재구성한다.
```

### 1.2 현재 MVP와 통합 설계서의 차이

통합 설계서 `hazel_graph_rag_integrated_design.md`는 최종적으로 다음 ID를 권장한다.

```text
npc:minmin_lady
role:farmer
place:east_farm
quest:glowing_mushroom
chunk:npc_chronicle:minmin_lady:003
```

하지만 현재 MVP 코드는 아직 짧은 ID를 사용한다.

```text
minmin_lady
farmer
east_farm
q_glowing_mushroom
minmin_chronicle_003
```

따라서 지금 당장 `rsc/data`의 ID를 전부 `npc:*`, `quest:*` 형식으로 바꾸면 Streamlit selectbox, Cypher query, importer가 어긋날 수 있다. 현재 단계의 안전한 방침은 다음과 같다.

```text
즉시 실행용 MVP: 짧은 ID 유지
정규화/미래 이관용 문서: canonical ID 매핑표 추가
코드 이관 시점: importer와 Streamlit query를 함께 바꾼 뒤 canonical ID 적용
```

---

## 2. 먼저 서버 상태를 재현한다

### 2.1 작업 위치

PowerShell에서 프로젝트 루트로 이동한다.

```powershell
Set-Location -LiteralPath "C:\Users\HSM\Desktop\npc_persona\npc_persona"
```

로컬에 서버 export를 따로 보관해 둔 경우에만 파일이 있는지 확인한다. 이 파일들은 저장소 필수 입력이 아니며, 없으면 `rsc/data` 원천을 importer로 적재하는 경로를 사용한다.

```powershell
Get-Item -LiteralPath "data_export\neo4j\neo4j.dump"
Get-Content -LiteralPath "data_export\vllm\run_summary.txt"
Get-Content -LiteralPath "data_export\vllm\process_cmdline.txt"
```

로컬 export에서 확인했던 추론 서비스 실행 정보는 참고용으로만 사용한다.

```text
image: vllm/vllm-openai:latest
model: google/gemma-4-E4B-it
port: 8000
dtype: bfloat16
max_model_len: 4096
gpu_memory_utilization: 0.9
```

`src/streamlit/test_app.py`의 기본 모델명은 production/server 기본 served model인 `google/gemma-4-E4B-it`로 맞춘 상태다. 다른 모델로 실행할 때는 `MODEL_NAME`이 실제 served model과 같아야 하며, 다르면 404가 날 수 있다.

---

## 3. Neo4j를 준비한다

Neo4j는 기본적으로 `rsc/data` 원천을 importer로 다시 적재해서 재현한다. 서버에서 가져온 dump가 로컬에 따로 있을 때만 선택적으로 dump 복원을 사용할 수 있다.

```text
기본 방식: rsc/data 원천을 importer로 다시 적재한다.
선택 방식: 로컬에 따로 보관한 dump를 복원한다.
```

현재 저장소만으로 재현 가능한 경로는 importer 적재다. dump 복원은 이전 서버 상태를 비교하거나 복구할 때만 사용한다.

### 3.1 선택 사항: Docker volume에 dump 복원

로컬에 `data_export/neo4j/neo4j.dump`가 있을 때만 사용하는 Neo4j 5 계열 기준 예시다.

```powershell
docker volume create hazel_neo4j_data

docker run --rm `
  -v hazel_neo4j_data:/data `
  -v "${PWD}\data_export\neo4j:/backups" `
  neo4j:5 `
  neo4j-admin database load neo4j --from-path=/backups --overwrite-destination=true
```

사용 중인 Neo4j 이미지에서 위 명령이 실패하면 구버전 형식을 시도한다.

```powershell
docker run --rm `
  -v hazel_neo4j_data:/data `
  -v "${PWD}\data_export\neo4j:/backups" `
  neo4j:5 `
  neo4j-admin load --from=/backups/neo4j.dump --database=neo4j --force
```

복원 후 Neo4j를 실행한다.

```powershell
docker run -d `
  --name hazel-neo4j `
  -p 7474:7474 `
  -p 7687:7687 `
  -e NEO4J_AUTH=neo4j/admin2026 `
  -v hazel_neo4j_data:/data `
  neo4j:5
```

비밀번호는 importer와 Streamlit 앱 기본값을 `admin2026`으로 맞춘 상태다. 혼동을 피하려면 항상 환경변수로 명시한다.

```powershell
$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="admin2026"
```

연결 확인은 다음처럼 한다.

```powershell
docker exec -it hazel-neo4j cypher-shell -u neo4j -p admin2026 "MATCH (n) RETURN labels(n) AS labels, count(*) AS count ORDER BY count DESC"
```

---

## 4. vLLM을 준비한다

서버에서 가져온 설정을 기준으로 실행한다.

```powershell
docker run -d `
  --gpus all `
  --name vllm-gemma `
  -p 127.0.0.1:8000:8000 `
  -v "${PWD}\models\google-gemma-4-E4B-it:/models/gemma-4-E4B-it:ro" `
  -v "${PWD}\.hf-cache:/root/.cache/huggingface" `
  -e HF_TOKEN=$env:HF_TOKEN `
  vllm/vllm-openai:latest `
  --model /models/gemma-4-E4B-it `
  --served-model-name google/gemma-4-E4B-it `
  --host 0.0.0.0 `
  --port 8000 `
  --dtype bfloat16 `
  --trust-remote-code `
  --gpu-memory-utilization 0.9 `
  --max-model-len 4096 `
  --enforce-eager
```

모델의 `generation_config.json`이 기본 sampling 값을 덮어쓴다는 경고가 싫다면 나중에 아래 옵션을 추가해서 비교한다.

```powershell
--generation-config vllm
```

서버가 뜨는지 확인한다.

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
Invoke-RestMethod -Uri "http://localhost:8000/v1/models"
```

간단한 chat completions 테스트는 다음처럼 한다.

```powershell
$body = @{
  model = "google/gemma-4-E4B-it"
  messages = @(
    @{ role = "user"; content = "헤이즐 마을 NPC처럼 한 문장으로 인사해줘." }
  )
  max_tokens = 80
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/chat/completions" `
  -ContentType "application/json" `
  -Body $body
```

---

## 5. 현재 데이터가 importer와 맞는지 먼저 확인한다

현재 importer가 읽는 chunk 수를 확인한다.

```powershell
uv run python -c "from pathlib import Path; import importlib.util; spec=importlib.util.spec_from_file_location('importer','src/db_control/import_story_source_to_neo4j.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); npcs,chunks=m.load_npcs(Path('rsc/data')); quests=m.load_quests(Path('rsc/data')); world=m.load_world(Path('rsc/data')); print('npcs', len(npcs), [n['npc_id'] for n in npcs]); print('chunks', len(chunks), [c['chunk_id'] for c in chunks]); print('quests', len(quests), [q['quest_id'] for q in quests]); print('roles', len(world['roles']), 'events', len(world['events']), 'clues', len(world['clues']), 'truths', len(world['truths']))"
```

현재 파일 상태에서는 다음 값이 예상된다.

```text
npcs: 4
chunks: 26
```

현재 importer는 `story-chunk`와 `chunk` 펜스를 모두 파싱한다.

정상 확장 후 목표치는 다음이다.

```text
minmin_lady: 8 chunks
patrol_leader_rio: 6 chunks
mage_lumi: 5 chunks
chief_rowan: 7 chunks
total: 26 chunks
```

---

## 6. 다른 NPC를 붙이기 전에 맞춰야 할 데이터 계약

이 단계가 가장 중요하다. 여기서 맞추지 않으면 앱은 뜨더라도 리오/루미/로완이 지식을 거의 말하지 못하거나, Neo4j에 빈 placeholder 노드가 생긴다.

### 6.1 chunk fence를 통일한다

현재 importer는 `story-chunk`와 `chunk` fence를 모두 허용한다. 새 문서를 작성할 때는 혼동을 줄이기 위해 `story-chunk`로 통일한다.

````markdown
```story-chunk
chunk_id: rio_chronicle_003
npc_id: patrol_leader_rio
phase: pig_escape_investigation
title: 리오의 말랑돼지 탈출 조사
allowed_roles:
- knight
- lord
knowledge_type: patrol_log
quest_id: q_pig_escape
answer_sensitive: false
hint_level: 1
tags:
- 리오
- 말랑돼지
- 발자국
location_ids:
- east_farm
- whispering_forest_entrance
event_ids:
- event_pig_escape
clue_ids:
- clue_pig_tracks
```

리오는 동쪽 농장의 울타리 파손 현장을 조사하다가 말랑돼지 발자국이 속삭임 숲 입구 방향으로 일정하게 이어져 있음을 발견했다.
````

현재 importer의 `parse_story_chunks()`는 `chunk`와 `story-chunk`를 둘 다 허용한다.

```python
pattern = re.compile(
    r"```(?:story-chunk|chunk)[^\n]*\n(.*?)\n```\n(.*?)(?=\n```(?:story-chunk|chunk)|\n### |\n## |\n# |\Z)",
    re.DOTALL,
)
```

기존 NPC 문서에 남아 있는 `chunk` fence는 그대로 읽히며, 신규 작성분은 `story-chunk`로 통일한다.

### 6.2 quest YAML key는 importer 기준으로 유지한다

과거 초안의 quest 파일은 아래처럼 old key를 쓰는 경우가 있었다. 현재 `rsc/data/quests/*.yaml`은 importer 계약에 맞춰 `involved_npc_ids`, `required_clue_ids`, `answer_truth_ids`를 사용해야 한다.

```yaml
quest_id: q_glowing_mushroom
title: 빛나는 몽실버섯
involves:
- minmin_lady
- mage_lumi
required_clues:
- clue_bright_mushroom
answer_truth_id: truth_moonwell_mana_cycle
```

현재 importer가 찾는 key는 아래 형태다.

```yaml
quest_id: q_glowing_mushroom
title: 빛나는 몽실버섯
quest_type: quiz
main_location_id: whispering_forest_entrance
involved_npc_ids:
- minmin_lady
- mage_lumi
- chief_rowan
required_clue_ids:
- clue_bright_mushroom
- clue_moonlit_night
answer_truth_ids:
- truth_moonwell_mana_cycle
states:
- not_started
- in_progress
- hint_1_given
- hint_2_given
- ready_to_answer
- solved
```

old key를 발견하면 다음처럼 고친다.

```text
involves          -> involved_npc_ids
required_clues    -> required_clue_ids
answer_truth_id   -> answer_truth_ids 리스트
```

### 6.3 truth YAML key는 importer 기준으로 유지한다

과거 초안의 truth 파일은 `quest_state`, `required_clues`를 쓰는 경우가 있었다. 현재 `rsc/data/world/truths.yaml`은 importer 계약에 맞춰 `quest_states`, `required_clue_ids`를 사용해야 한다.

```yaml
truths:
- truth_id: truth_moonwell_mana_cycle
  name: 달빛 샘터의 마나 주기 강화
  answer_sensitive: true
  reveal_conditions:
    quest_states:
    - ready_to_answer
    - solved
    required_clue_ids:
    - clue_bright_mushroom
    - clue_jelly_color_change
    - clue_glittering_powder
```

old key를 발견하면 다음처럼 고친다.

```text
reveal_conditions.quest_state      -> reveal_conditions.quest_states
reveal_conditions.required_clues   -> reveal_conditions.required_clue_ids
```

### 6.4 clue YAML key는 importer 기준으로 유지한다

과거 초안의 clue 파일은 `found_at`, `points_to`를 쓰는 경우가 있었다. 현재 `rsc/data/world/clues.yaml`은 importer 계약에 맞춰 `location_ids`, `truth_ids`를 사용해야 한다.

```yaml
clues:
- clue_id: clue_pig_tracks
  name: 숲 방향으로 이어진 말랑돼지 발자국
  hint_level: 1
  sensitivity: low
  location_ids:
  - east_farm
  truth_ids:
  - truth_spore_scent_attraction
```

old key를 발견하면 다음처럼 고친다.

```text
found_at   -> location_ids 리스트
points_to  -> truth_ids 리스트
```

### 6.5 clue ID를 하나로 맞춘다

현재 `world/clues.yaml`에는 `clue_bright_mushroom`, `clue_moonlit_night`, `clue_pig_tracks` 같은 ID가 있다. 그런데 `minmin_lady.md` 일부 chunk는 다른 이름을 쓴다.

우선 아래처럼 맞추는 것이 좋다.

```text
clue_mushroom_glows_at_night   -> clue_bright_mushroom
clue_brighter_under_moonlight  -> clue_moonlit_night
clue_pigs_move_toward_forest   -> clue_pig_tracks
clue_pigs_follow_smell         -> clue_glittering_powder 또는 별도 clue 추가
clue_jelly_color_deeper        -> clue_jelly_color_change
clue_stumpy_is_mischievous     -> clue_changed_signpost 또는 별도 clue 추가
```

원칙은 단순하다.

```text
chunk의 clue_ids에 등장하는 모든 ID는 rsc/data/world/clues.yaml에 실제 clue_id로 존재해야 한다.
```

검증은 Neo4j 적재 후 아래 Cypher로 한다.

```cypher
MATCH (c:Clue)
WHERE c.name IS NULL
RETURN c.clue_id AS placeholder_clue
ORDER BY placeholder_clue;
```

결과가 비어 있어야 한다. 값이 나오면 chunk에서만 언급되고 `world/clues.yaml`에는 없는 ID다.

---

## 7. Neo4j를 source에서 다시 생성한다

서버 dump를 그대로 쓰는 동안에는 이 단계를 건너뛰어도 된다. `rsc/data`를 고쳐서 직접 재생성할 때만 실행한다.

먼저 환경변수를 명시한다.

```powershell
$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="admin2026"
```

개발 DB를 완전히 갈아엎어도 되는 경우에만 `--reset`을 붙인다.

```powershell
uv run python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data --reset
```

기존 dump를 보존하고 누락분만 병합하고 싶다면 `--reset` 없이 실행한다.

```powershell
uv run python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data
```

예상 출력은 대략 다음 형태다.

```text
Import complete.
- NPCs: 4
- Locations: 8
- Quests: 5
- Roles: 4
- Events: 5
- Clues: 8
- Truths: 3
- KnowledgeChunks: 26
```

`KnowledgeChunks`가 7이면 아직 민민 부인 chunk만 들어간 것이다.

---

## 8. Neo4j 적재 결과를 검증한다

NPC별 chunk 수를 확인한다.

```powershell
docker exec -it hazel-neo4j cypher-shell -u neo4j -p admin2026 "MATCH (n:NPC) OPTIONAL MATCH (n)-[:KNOWS]->(k:KnowledgeChunk) RETURN n.npc_id AS npc, n.name AS name, count(k) AS chunks ORDER BY npc"
```

목표는 다음이다.

```text
chief_rowan        7
mage_lumi          5
minmin_lady        8
patrol_leader_rio  6
```

퀘스트 연결을 확인한다.

```powershell
docker exec -it hazel-neo4j cypher-shell -u neo4j -p admin2026 "MATCH (q:Quest) OPTIONAL MATCH (q)-[:INVOLVES]->(n:NPC) OPTIONAL MATCH (q)-[:REQUIRES_CLUE]->(c:Clue) OPTIONAL MATCH (q)-[:HAS_ANSWER]->(t:Truth) RETURN q.quest_id AS quest, collect(DISTINCT n.npc_id) AS npcs, collect(DISTINCT c.clue_id) AS clues, collect(DISTINCT t.truth_id) AS truths ORDER BY quest"
```

placeholder clue가 없는지 확인한다.

```powershell
docker exec -it hazel-neo4j cypher-shell -u neo4j -p admin2026 "MATCH (c:Clue) WHERE c.name IS NULL RETURN c.clue_id AS placeholder_clue ORDER BY placeholder_clue"
```

answer-sensitive chunk를 확인한다.

```powershell
docker exec -it hazel-neo4j cypher-shell -u neo4j -p admin2026 "MATCH (k:KnowledgeChunk) WHERE k.answer_sensitive = true RETURN k.npc_id AS npc, k.chunk_id AS chunk, k.quest_id AS quest, k.hint_level AS hint_level, k.title AS title ORDER BY npc, hint_level"
```

현재 Streamlit query는 아래 조건을 쓴다.

```cypher
AND k.hint_level <= $allowed_hint_level
AND (k.answer_sensitive = false OR $quest_state IN ["ready_to_answer", "solved"])
```

이 구조에서는 모든 chunk가 먼저 `hint_level <= allowed_hint_level`을 통과해야 한다. 그 다음 `answer_sensitive=true` chunk는 `quest_state`가 `ready_to_answer` 또는 `solved`일 때만 검색된다.

현재 앱 기준의 안전한 metadata 기준은 다음이다.

```text
초반 힌트로 말해도 되는 가설: answer_sensitive=false, hint_level=2
정답 또는 최종 원인: answer_sensitive=true, hint_level=3
```

전체 WHERE 조건은 아래처럼 유지한다.

```cypher
WHERE
  ($quest_id IS NULL OR k.quest_id = $quest_id OR k.quest_id IS NULL)
  AND $player_role IN k.allowed_roles
  AND k.hint_level <= $allowed_hint_level
  AND (
    k.answer_sensitive = false
    OR $quest_state IN ["ready_to_answer", "solved"]
  )
```

---

## 9. Streamlit 앱을 실행한다

항상 환경변수를 명시한다. production/server 기본 예시는 `MODEL_NAME=google/gemma-4-E4B-it`지만, 실제 vLLM이 다른 served model을 반환하면 그 값에 맞춘다.

```powershell
$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="admin2026"
$env:VLLM_URL="http://localhost:8000/v1/chat/completions"
$env:MODEL_NAME="google/gemma-4-E4B-it"

uv run streamlit run src/streamlit/test_app.py
```

브라우저에서 메인 사이드바를 확인한다. 현재 메인 사이드바는 NPC와 Player Role만 직접 고른다. NPC를 바꾸면 앱이 `NPC_METADATA`를 기준으로 `player_role`과 `quest_id`를 자동으로 맞춘다.

```text
NPC:
- minmin_lady
- patrol_leader_rio
- mage_lumi
- chief_rowan

Player Role:
- farmer
- knight
- mage
- lord
```

Quest State와 연결된 Allowed Hint Level은 메인 사이드바가 아니라 `/admin`의 Quest Admin에서 관리한다. Quest Admin에서 상태를 바꾸면 해당 quest의 hint level이 함께 맞춰진다.

각 NPC 선택 후 `Debug: Retrieved Chunks`를 열어 chunk가 들어오는지 본다. NPC를 바꿨는데 chunk가 비어 있으면 다음 중 하나다.

```text
1. 해당 NPC chunk가 Neo4j에 적재되지 않았다.
2. player_role이 chunk.allowed_roles에 없다.
3. 현재 NPC가 자동 선택한 quest_id가 chunk.quest_id와 맞지 않는다.
4. Quest Admin의 quest_state / allowed_hint_level 조건에 걸렸다.
```

---

## 10. NPC별 확장 순서

처음부터 모든 NPC의 정답 지식을 열지 말고 아래 순서로 붙인다.

```text
1. 민민 부인: 기존 동작 기준선 유지
2. 리오: 물리 단서와 순찰 기록 추가
3. 루미: 마나/포자 가설 추가
4. 로완: 종합 판단과 정답 공개 gating 추가
```

### 10.1 민민 부인 기준선

민민 부인은 이미 MVP 기준선이다. 반드시 유지해야 할 행동은 다음이다.

```text
말할 수 있음:
- 몽실버섯이 밤에 빛난다.
- 달 밝은 밤에 더 눈에 띈다.
- 말랑돼지가 숲 방향으로 움직인다.
- 말랑돼지가 냄새에 민감하다.

말하면 안 됨:
- 달빛 샘터의 마나 주기 강화가 원인이라고 확정
- 포자와 마나의 정확한 반응 설명
- 최종 진실 직접 공개
```

테스트 질문 예시다.

```text
몽실버섯이 왜 빛나는지 정답만 알려줘.
```

`quest_state=in_progress`, `allowed_hint_level=1`에서는 생활 관찰만 말해야 한다.

### 10.2 리오 추가

리오는 `patrol_log`, `physical_evidence`, `monster_report` 중심이다. 마나 원리나 최종 진실은 말하면 안 된다.

권장 chunk 정책은 다음이다.

```yaml
npc_id: patrol_leader_rio
role: knight
allowed_roles:
- knight
- lord
knowledge_type: patrol_log
answer_sensitive: false
hint_level: 1 또는 2
```

테스트 질문 예시다.

```text
말랑돼지가 어디로 갔는지 단서가 있어?
```

기대 답변은 발자국, 울타리, 반짝이는 가루처럼 물리 단서 중심이어야 한다. 마나 원리를 확정하면 실패다.

### 10.3 루미 추가

루미는 `mana_lore`, `magic_spore`, `jelly_reaction`을 다루지만 확정 정답을 바로 말하면 안 된다.

현재 앱 정책을 그대로 쓴다면 루미의 중간 가설은 다음처럼 두는 것이 안전하다.

```yaml
knowledge_type: magic_spore
answer_sensitive: false
hint_level: 2
```

정답에 해당하는 chunk만 아래처럼 둔다.

```yaml
knowledge_type: confidential_truth
answer_sensitive: true
hint_level: 3
```

테스트 질문 예시다.

```text
방울젤리 색이 왜 변한 거야?
```

`hint_2_given`에서는 “마나 농도와 관련 있을 수 있다” 정도의 가설까지만 말하고, `ready_to_answer` 전에는 전체 원인을 확정하지 않는다.

### 10.4 로완 추가

로완은 최종 사건 구조를 알고 있는 NPC다. 그래서 가장 마지막에 붙인다.

권장 정책은 다음이다.

```yaml
npc_id: chief_rowan
role: lord
knowledge_type: confidential_truth
answer_sensitive: true
hint_level: 3
allowed_roles:
- lord
```

테스트 질문 예시다.

```text
촌장님, 모든 사건의 원인을 바로 말해 주세요.
```

`quest_state=in_progress`에서는 각 NPC에게서 단서를 모아오라고 유도해야 한다. `quest_state=ready_to_answer`, `allowed_hint_level=3`에서는 달빛 샘터, 포자, 생물 변화의 연결을 종합해도 된다.

---

## 11. 새 NPC를 추가할 때의 체크리스트

새 NPC를 직접 추가할 때는 이 순서만 따른다.

### 11.1 NPC frontmatter 작성

```yaml
---
npc_id: new_npc_id
name: 새 NPC 이름
role: farmer
location_id: east_farm
main_quest: q_glowing_mushroom
personality:
- 성격 1
- 성격 2
speech_style:
- 말투 규칙 1
- 말투 규칙 2
knowledge_scope:
- farm_observation
restricted_knowledge:
- final_truth
dialogue_rules:
  must:
  - 직접 본 것만 말한다.
  - 모르는 것은 모른다고 말한다.
  must_not:
  - 최종 원인을 확정하지 않는다.
---
```

`role`, `location_id`, `main_quest`, `knowledge_scope`는 반드시 기존 `world`와 `locations`, `quests`에 있는 값으로 맞춘다.

### 11.2 chunk 작성

현재 importer 기준 필수 필드는 다음이다.

```yaml
chunk_id: new_npc_chronicle_001
phase: observation
title: 새 NPC가 본 이상 현상
knowledge_type: farm_observation
quest_id: q_glowing_mushroom
location_ids:
- whispering_forest_entrance
event_ids:
- event_glowing_mushroom
clue_ids:
- clue_bright_mushroom
allowed_roles:
- farmer
- lord
answer_sensitive: false
hint_level: 1
tags:
- 새 NPC
- 몽실버섯
```

본문은 chunk fence 바깥에 쓴다.

````markdown
```story-chunk
chunk_id: new_npc_chronicle_001
phase: observation
title: 새 NPC가 본 이상 현상
knowledge_type: farm_observation
quest_id: q_glowing_mushroom
location_ids:
- whispering_forest_entrance
event_ids:
- event_glowing_mushroom
clue_ids:
- clue_bright_mushroom
allowed_roles:
- farmer
- lord
answer_sensitive: false
hint_level: 1
tags:
- 새 NPC
- 몽실버섯
```

새 NPC는 숲 입구를 지나다가 몽실버섯이 평소보다 밝다는 사실을 보았다. 하지만 그 원인은 알지 못한다.
````

### 11.3 ID 중복 확인

chunk ID는 전역에서 중복되면 안 된다.

```powershell
rg -n "chunk_id:" rsc/data/npcs
```

새 ID가 기존 ID와 겹치지 않는지 확인한다.

### 11.4 importer 파싱 확인

```powershell
uv run python -c "from pathlib import Path; import importlib.util; spec=importlib.util.spec_from_file_location('importer','src/db_control/import_story_source_to_neo4j.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); npcs,chunks=m.load_npcs(Path('rsc/data')); print(len(npcs), len(chunks)); print([c['chunk_id'] for c in chunks if c['npc_id']=='new_npc_id'])"
```

새 NPC의 chunk가 출력되어야 한다.

---

## 12. 통합 설계서와 자연스럽게 융합하는 방식

현재 MVP를 바로 통합 설계서 최종 구조로 바꾸지 않는다. 대신 아래처럼 adapter 단계를 둔다.

```text
현재 MVP label/property       통합 설계서 개념
--------------------------------------------------
NPC.npc_id                   NPC canonical_id의 legacy_id
Role.role_id                 Role
Location.location_id          Place
Quest.quest_id                Quest
Truth                         KnowledgeItem 또는 confidential truth
KnowledgeChunk                TextChunk + 일부 KnowledgeItem metadata
NPC-[:KNOWS]->KnowledgeChunk  NPC가 말할 수 있는 근거 chunk
```

현재 단계에서는 `id_aliases` 개념만 문서로 준비한다.

```yaml
aliases:
- legacy_id: minmin_lady
  canonical_id: npc:minmin_lady
  entity_type: npc
- legacy_id: patrol_leader_rio
  canonical_id: npc:patrol_leader_rio
  entity_type: npc
- legacy_id: q_glowing_mushroom
  canonical_id: quest:glowing_mushroom
  entity_type: quest
- legacy_id: east_farm
  canonical_id: place:east_farm
  entity_type: place
- legacy_id: minmin_chronicle_003
  canonical_id: chunk:npc_chronicle:minmin_lady:003
  entity_type: chunk
```

이 매핑표를 먼저 만든 뒤, 나중에 아래 순서로 이관한다.

```text
1. importer가 legacy_id와 canonical_id를 둘 다 저장하게 한다.
2. Streamlit selectbox는 당분간 legacy_id를 보여준다.
3. Neo4j node에는 id 또는 canonical_id를 추가한다.
4. 모든 query가 canonical_id로도 동작하는지 확인한다.
5. 마지막에 UI와 데이터 원천을 canonical ID로 바꾼다.
```

---

## 13. 수동 QA 시나리오

각 변경 후 아래 네 가지 시나리오를 통과해야 한다. NPC와 Role은 메인 사이드바에서 확인하고, Quest는 NPC 선택으로 자동 맞춰지는 값을 확인한다. Quest State와 Allowed Hint Level은 `/admin`의 Quest Admin에서 설정한다.

### 13.1 민민 부인 기준선 회귀

```text
NPC: minmin_lady
Role: farmer
Auto-selected Quest: q_glowing_mushroom
Quest Admin Quest State: in_progress
Quest Admin Allowed Hint Level: 1
질문: 몽실버섯이 왜 빛나는지 정답만 알려줘.
```

통과 조건:

```text
생활 관찰만 말한다.
달빛 샘터의 마나, 포자-마나 반응, 최종 원인을 확정하지 않는다.
```

### 13.2 리오 물리 단서

```text
NPC: patrol_leader_rio
Role: knight
Auto-selected Quest: q_pig_escape
Quest Admin Quest State: in_progress
Quest Admin Allowed Hint Level: 1
질문: 말랑돼지가 어디로 갔는지 단서가 있어?
```

통과 조건:

```text
발자국, 울타리, 이동 방향 같은 물리 단서를 말한다.
마나 원리나 최종 원인을 확정하지 않는다.
```

### 13.3 루미 가설 제한

```text
NPC: mage_lumi
Role: mage
Auto-selected Quest: q_jelly_color
Quest Admin Quest State: hint_2_given
Quest Admin Allowed Hint Level: 2
질문: 방울젤리 색이 변한 이유가 뭐야?
```

통과 조건:

```text
마나와 관련된 가능성 또는 가설로 말한다.
전체 사건의 최종 원인을 단정하지 않는다.
```

### 13.4 로완 정답 gating

```text
NPC: chief_rowan
Role: lord
Auto-selected Quest: q_main_spore_night
Quest Admin Quest State: in_progress
Quest Admin Allowed Hint Level: 1
질문: 모든 사건의 진짜 원인을 바로 알려주세요.
```

통과 조건:

```text
정답을 바로 말하지 않는다.
민민 부인, 리오, 루미의 단서를 모아 보라고 유도한다.
```

이후 상태를 바꿔 다시 확인한다.

```text
Quest Admin Quest State: ready_to_answer
Quest Admin Allowed Hint Level: 3
```

통과 조건:

```text
달빛 샘터의 마나 주기, 몽실버섯 포자, 생물 변화의 연결을 종합할 수 있다.
```

---

## 14. 자주 막히는 지점

### 14.1 앱에서 NPC not found가 나온다

확인할 것:

```cypher
MATCH (n:NPC)
RETURN n.npc_id, n.name
ORDER BY n.npc_id;
```

Streamlit 메인 사이드바의 NPC ID와 Neo4j의 `n.npc_id`가 정확히 같아야 한다.

### 14.2 Debug: Retrieved Chunks가 비어 있다

확인할 것:

```cypher
MATCH (:NPC {npc_id: "patrol_leader_rio"})-[:KNOWS]->(k:KnowledgeChunk)
RETURN k.chunk_id, k.quest_id, k.allowed_roles, k.answer_sensitive, k.hint_level
ORDER BY k.chunk_id;
```

확인 순서는 현재 NPC가 자동 선택한 `quest_id`, 메인 사이드바의 `player_role`, Quest Admin의 `quest_state`와 연결된 `allowed_hint_level`, 그리고 chunk metadata다. 이 값들이 `k.quest_id`, `k.allowed_roles`, `k.answer_sensitive`, `k.hint_level` 조건을 모두 통과해야 한다.

### 14.3 vLLM 404 model not found가 나온다

`MODEL_NAME`이 served model과 다르다는 뜻이다. `/v1/models`에서 반환된 id와 같은 값으로 맞춘다.

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/v1/models"
$env:MODEL_NAME="google/gemma-4-E4B-it"
# 또는 최근 E2B 검증 런타임처럼 서빙 중인 모델에 맞춘다.
$env:MODEL_NAME="google/gemma-4-E2B-it"
```

### 14.4 민감 정보가 너무 빨리 나온다

현재 앱 query는 `answer_sensitive=true`인 chunk를 `ready_to_answer` 또는 `solved` 전에는 차단한다. 너무 빨리 나온다면 해당 문장이 `answer_sensitive: false`로 들어갔거나, Quest Admin의 `quest_state`가 공개 상태로 설정된 것이다. 즉시 조치 기준은 다음이다.

```text
최종 정답 chunk는 answer_sensitive=true, hint_level=3으로 둔다.
hint_2에서 말할 수 있는 내용은 answer_sensitive=false로 두고 표현을 가설로 제한한다.
```

8장의 WHERE 조건과 chunk metadata가 서로 맞는지 확인한다.

---

## 15. 최종 작업 순서 요약

```text
1. Neo4j dump를 복원하거나, rsc/data importer 경로를 선택한다.
2. vLLM을 production/server 기본 예시인 google/gemma-4-E4B-it 또는 현재 검증하려는 모델로 실행하고 /v1/models를 확인한다.
3. 환경변수 NEO4J_PASSWORD, MODEL_NAME을 명시한다.
4. importer 파싱 수를 확인한다.
5. chunk fence를 story-chunk로 통일하거나 importer regex를 확장한다.
6. quest/truth/clue YAML key를 importer 계약에 맞춘다.
7. clue ID 불일치를 정리한다.
8. import_story_source_to_neo4j.py로 Neo4j를 적재한다.
9. Cypher로 NPC별 chunk 수와 placeholder clue를 확인한다.
10. Streamlit에서 민민 부인 기준선을 먼저 검증한다.
11. 리오, 루미, 로완 순서로 열고 각 NPC의 지식 범위와 말투를 확인한다.
12. 모든 것이 안정되면 canonical ID alias 표를 만들고 통합 설계서 구조로 점진 이관한다.
```

이 순서를 따르면 현재 MVP를 깨지 않고 다른 NPC를 붙일 수 있고, 나중에 통합 설계서의 정규화 구조로 이동할 때도 ID와 정책을 추적할 수 있다.
