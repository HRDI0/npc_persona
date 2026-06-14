# persona_chat GraphRAG MVP 인수인계 보고서

## 1. 이 프로젝트의 목적

이 프로젝트는 게임 NPC가 아무 사실이나 말하는 챗봇이 되지 않도록, 현재 플레이어 상태에서 허용된 지식만 골라 답변하게 만드는 GraphRAG MVP다.

현재 범위는 헤이즐 마을 NPC 4명과 퀘스트 5개다. 핵심 검증 대상은 “NPC별 지식 범위”, “퀘스트 진행 상태”, “힌트 레벨”, “정답 공개 조건”이 실제 대화 응답에 반영되는지다.

전체 흐름은 다음과 같다.

```text
rsc/data 원천 데이터
  -> NPC Markdown story-chunk 파싱
  -> KnowledgeChunk dict 생성
  -> Neo4j 노드/관계 적재
  -> Streamlit에서 현재 상태로 chunk 조회
  -> build_prompt로 허용 지식만 vLLM에 전달
  -> NPC 말투로 응답 생성
```

## 2. 전체 폴더 구조

프로젝트를 이해할 때는 먼저 원천 데이터, 실행 코드, 생성 산출물, 문서, 테스트를 분리해서 보면 된다.

```text
rsc/data/
  사람이 직접 관리하는 원천 데이터

src/
  Neo4j 적재 코드와 Streamlit 런타임 코드

scripts/story_pipeline/
  원천 데이터를 읽어 보고서, 통합 파일, CSV를 재생성하는 자동화 스크립트

output/
  재생성 가능한 보고서와 Neo4j import 산출물

docs/
  운영 문서, DB 설계, 시스템 아키텍처, 발표/인수인계 자료

tests/
  데이터, 산출물, Streamlit, 발표자료 계약 검증
```

가장 중요한 원칙은 `rsc/data`가 원천이고, `output/`은 생성 결과라는 점이다. 스토리나 NPC 지식을 수정해야 하면 `output/`이 아니라 `rsc/data`를 수정해야 한다.

## 3. 원천 데이터 구조

`rsc/data` 안의 주요 파일은 다음 역할을 가진다.

| 위치 | 역할 |
|---|---|
| `rsc/data/npcs/*.md` | NPC 프로필, 말투, 제한 지식, story chunk 본문 |
| `rsc/data/quests/*.yaml` | 퀘스트 기본 정의와 `story_expansion` |
| `rsc/data/world/*.yaml` | 역할, 사건, 단서, 진실 ID 정의 |
| `rsc/data/locations/*.md` | 장소 노드의 설명과 분위기 |

NPC Markdown은 두 부분으로 나뉜다.

```text
YAML frontmatter
  -> NPC 노드 속성

본문의 story-chunk / chunk fence
  -> KnowledgeChunk 노드 후보
```

예를 들어 `rsc/data/npcs/minmin_lady.md`의 frontmatter에는 `npc_id`, `role`, `location_id`, `main_quest`, `personality`, `speech_style`, `knowledge_scope`, `restricted_knowledge`가 들어 있다. 이 값들은 Neo4j `NPC` 노드와 Streamlit prompt의 기본 정보가 된다.

## 4. 데이터 증강에서 추가된 것

데이터 증강은 새 NPC나 새 대형 지역을 추가한 작업이 아니다. 기존 4명 NPC와 5개 퀘스트를 실행 가능한 구조로 바꾼 작업이다.

증강은 두 위치에서 이루어졌다.

```text
rsc/data/quests/*.yaml
  -> story_expansion 추가

rsc/data/npcs/*.md
  -> NPC별 story-chunk / chunk 추가 또는 정리
```

`story_expansion`에 추가된 핵심 요소는 다음과 같다.

| 추가 항목 | 의미 |
|---|---|
| `story_purpose` | 퀘스트가 플레이어에게 어떤 경험과 목표를 주는지 설명 |
| `quest_steps` | 관찰, 힌트, 단서, 추론, 완료 같은 진행 단계 |
| `wrong_hypotheses` | 플레이어가 오해할 수 있는 가설과 반증 단서 |
| `hint_flow` | 힌트 레벨별로 어떤 정보를 공개할지 정의 |
| `answer_reveal_policy` | 정답을 언제, 누가, 어떤 조건에서 말할 수 있는지 정의 |
| `completion` | 퀘스트 완료 조건과 완료 후 반응 |

예시로 `q_glowing_mushroom`은 단순히 “버섯이 빛난다”가 아니라 다음 조사 흐름을 갖게 됐다.

```text
observe_light
  숲 입구에서 평소보다 밝은 버섯 확인

compare_moon
  달이 밝은 밤의 차이 확인

ask_lumi
  루미에게 포자와 마나 반응 가능성 질문

report_rowan
  로완에게 관찰과 가설을 함께 보고
```

또한 오답 가설도 추가됐다.

```text
whm_bad_weather
  날씨 때문에 버섯이 밝아졌다
```

이런 오답 가설은 플레이어가 너무 빨리 결론을 내리지 않게 하고, NPC가 단서 기반으로만 안내하게 만드는 장치다.

## 5. 민민 부인 데이터를 기준으로 본 전체 흐름

민민 부인 데이터는 프로젝트 구조를 이해하기 좋은 대표 예시다.

민민 부인의 기본 정보는 다음과 같다.

```yaml
npc_id: minmin_lady
name: 민민 부인
role: farmer
location_id: east_farm
main_quest: q_glowing_mushroom
```

민민 부인은 총 7개의 KnowledgeChunk 후보를 가진다.

| chunk | 내용 | 공개 조건 |
|---|---|---|
| `minmin_chronicle_001` | 어린 시절과 생활 감각 | farmer, lord / hint 0 |
| `minmin_chronicle_002` | 동쪽 농장 주인이 된 시기 | farmer, lord / hint 0 |
| `minmin_chronicle_003` | 몽실버섯의 변화 | farmer, lord / hint 1 |
| `minmin_chronicle_004` | 말랑돼지 탈출 | farmer, lord / hint 1 |
| `minmin_chronicle_005` | 방울젤리 색 변화 | farmer, lord / hint 1 |
| `minmin_chronicle_006` | 표지판 사건 소문 | farmer, lord / hint 1 |
| `minmin_chronicle_007` | 현재 농장 피해와 도움 요청 | farmer, lord / hint 1 |

중요한 점은 민민 부인의 chunk들이 대부분 생활 관찰이라는 점이다. 민민은 마법 원리나 최종 진실을 말하지 않는다. 그래서 `answer_sensitive: false`인 관찰 정보는 줄 수 있지만, 최종 원인은 알지 못하는 NPC로 동작한다.

## 6. Markdown chunk가 dict로 바뀌는 과정

예를 들어 `minmin_chronicle_003`은 원천 Markdown에서 다음과 같은 의미를 가진다.

```yaml
chunk_id: minmin_chronicle_003
title: 민민 부인이 본 몽실버섯의 변화
quest_id: q_glowing_mushroom
clue_ids:
  - clue_bright_mushroom
  - clue_moonlit_night
allowed_roles:
  - farmer
  - lord
answer_sensitive: false
hint_level: 1
```

fence 뒤의 본문은 실제 NPC가 말할 수 있는 근거 문장이다.

```text
몽실버섯이 밤에 빛나고, 달이 밝은 날에는 더 눈에 띄며,
그 주변에 희미한 가루 같은 것이 남는다는 정도다.
```

Importer는 이 블록을 읽어 다음 형태의 dict로 바꾼다.

```python
{
  "chunk_id": "minmin_chronicle_003",
  "npc_id": "minmin_lady",
  "quest_id": "q_glowing_mushroom",
  "allowed_roles": ["farmer", "lord"],
  "answer_sensitive": False,
  "hint_level": 1,
  "text_ref": "rsc/data/npcs/minmin_lady.md#minmin_chronicle_003",
  "text": "몽실버섯이 밤에 빛나고..."
}
```

이 중간 dict가 Neo4j 적재의 입력이 된다.

## 7. Neo4j 적재 기준

Neo4j 데이터 구조만 따로 시각적으로 보고 싶다면 `docs/NEO4J_GRAPH_STRUCTURE_VISUAL_GUIDE.md`를 먼저 보면 된다. 이 문서는 전체 노드/관계 구조, 민민 부인 기준 적재 그래프, 확인용 Cypher 쿼리를 별도 Mermaid 구조도로 정리한다.

Neo4j 적재 기준은 크게 네 가지다.

| 기준 | 설명 |
|---|---|
| 고유 ID | `npc_id`, `chunk_id`, `quest_id`, `clue_id` 같은 ID가 `MERGE` 기준이다. |
| 출처 보존 | `source_path`, `text_ref`로 원천 파일과 chunk 위치를 추적한다. |
| 관계 생성 | `quest_id`, `location_ids`, `event_ids`, `clue_ids`를 관계로 풀어낸다. |
| 공개 정책 | `allowed_roles`, `hint_level`, `answer_sensitive`를 런타임 필터용 속성으로 저장한다. |

민민 부인 기준 그래프 구조는 다음처럼 이해하면 된다.

```text
(:NPC {npc_id: "minmin_lady"})
  -[:HAS_ROLE]-> (:Role {role_id: "farmer"})
  -[:LOCATED_AT]-> (:Location {location_id: "east_farm"})
  -[:KNOWS]-> (:KnowledgeChunk {chunk_id: "minmin_chronicle_003"})

(:KnowledgeChunk {chunk_id: "minmin_chronicle_003"})
  -[:RELATED_TO]-> (:Quest {quest_id: "q_glowing_mushroom"})
  -[:POINTS_TO]-> (:Clue {clue_id: "clue_bright_mushroom"})
```

핵심 관계는 `NPC-[:KNOWS]->KnowledgeChunk`다. NPC가 KNOWS로 연결되지 않은 지식은 기본적으로 그 NPC의 대화 근거가 아니다.

## 8. Streamlit 런타임 조회 기준

Streamlit은 전체 Neo4j DB를 모델에 넘기지 않는다. 현재 선택된 상태를 Cypher 파라미터로 바꿔 허용된 chunk만 조회한다.

```cypher
MATCH (:NPC {npc_id: $npc_id})-[:KNOWS]->(k:KnowledgeChunk)
WHERE
  ($quest_id IS NULL OR k.quest_id = $quest_id OR k.quest_id IS NULL)
  AND $player_role IN k.allowed_roles
  AND k.hint_level <= $allowed_hint_level
  AND (k.answer_sensitive = false OR $quest_state IN ["ready_to_answer", "solved"])
RETURN k.chunk_id, k.title, k.text
ORDER BY k.hint_level ASC, k.chunk_id ASC
```

이 조건은 네 개의 문처럼 동작한다.

```text
1. NPC Gate
   선택한 NPC가 KNOWS로 연결된 chunk인가?

2. Role Gate
   현재 player_role이 allowed_roles에 포함되는가?

3. Hint Gate
   chunk의 hint_level이 현재 allowed_hint_level 이하인가?

4. State Gate
   answer_sensitive 정보라면 quest_state가 ready_to_answer 또는 solved인가?
```

민민 부인, farmer, `q_glowing_mushroom`, `in_progress`, hint level 1 상태에서는 민민이 직접 본 관찰 정보만 프롬프트에 들어간다. 그래서 플레이어가 정답을 요구해도 민민은 최종 원인을 말하지 않고 관찰과 힌트 중심으로 답한다.

## 9. Streamlit 캡처 자료의 의미

발표/인수인계 자료에는 실제 Docker Neo4j와 Streamlit 캡처를 사용했다.

| 파일 | 의미 |
|---|---|
| `assets/neo4j-live-overview.png` | 실제 Docker Neo4j label count와 핵심 관계 구조를 확인한다. |
| `assets/neo4j-live-minmin.png` | 민민 부인이 8개 KnowledgeChunk를 `KNOWS`로 가진다는 점을 확인한다. |
| `assets/streamlit-minmin-query.png` | 민민 부인 기준 질의에서 정답 요구를 관찰/힌트로 제한하는지 확인한다. |
| `assets/streamlit-rio-query.png` | 리오 기준 질의에서 순찰 기록과 물리 증거 중심으로 답하는지 확인한다. |
| `assets/streamlit-lumi-query.png` | 루미 기준 질의에서 마나 분석을 가능성 수준으로 제한하는지 확인한다. |
| `assets/streamlit-rowan-query.png` | 로완, lord, ready_to_answer 상태에서 answer_sensitive 근거가 열리는지 확인한다. |

캡처 페이지에는 이미지를 여러 장 축소 배치하지 않고, 페이지당 하나의 근거 이미지만 배치했다. 각 이미지는 Docker 접근 정보, NPC, role, quest, state, hint level을 함께 설명한다.

## 10. 운영 서버 적용 방법

운영 서버 적용은 다음 순서로 진행한다.

```bash
git pull --ff-only origin main
cp .env.example .env
docker compose --env-file .env build streamlit
docker compose --env-file .env up -d neo4j streamlit
docker compose --env-file .env run --rm streamlit uv run --frozen python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data
```

운영에서 중요한 원칙은 다음과 같다.

```text
1. 실제 secret은 .env에만 둔다.
2. .env.example은 템플릿이다.
3. 운영 DB에는 기본적으로 --reset을 붙이지 않는다.
4. 원천 데이터는 --source-dir rsc/data 기준으로 병합 적재한다.
5. vLLM 주소와 모델명은 환경변수로 맞춘다.
```

운영 반영 후에는 다음을 확인해야 한다.

| 확인 항목 | 기대값 |
|---|---|
| NPC 수 | 4 |
| Quest 수 | 5 |
| KnowledgeChunk 수 | 26 |
| 핵심 관계 | `NPC-[:KNOWS]->KnowledgeChunk` |
| Streamlit 접속 | 서버의 8501 또는 설정된 포트 |
| vLLM endpoint | `/v1/chat/completions` streaming 응답 |

## 11. 새 발표자료의 구성

새 상세 설계 문서는 `docs/presentation/index.html`에 있다. 단순 PPT 스타일이 아니라 프로젝트 전체를 설명하는 시각화 문서로 다시 작성했다.

중점적으로 보강한 내용은 다음과 같다.

- 전체 프로젝트 구조를 root 수준에서 설명
- `rsc/data` 내부 원천 데이터 구조 설명
- 데이터 증강에서 실제로 추가된 항목 설명
- `q_glowing_mushroom`, `q_main_spore_night` 실제 증강 예시 설명
- 민민 부인 데이터를 기준으로 frontmatter, chunk 분포, dict 변환, 적재 기준, 그래프 구조, 런타임 trace 설명
- Neo4j 적재 구조를 이미지와 DOM 구조도로 설명
- 실제 Docker 캡처를 evidence slide로 사용
- 운영 서버 적용 명령과 검증 항목 설명

모든 슬라이드에는 상세 설명 문단이 포함되어 있고, 지시문체 표현은 제거했다.

## 12. 검증 결과

완료 후 다음 검증을 진행했다.

```text
python -m unittest tests.test_presentation_artifact -v
  -> 11 OK

python -m unittest discover -v
  -> 42 OK
```

LSP diagnostics도 다음 파일에서 clean 상태를 확인했다.

- `docs/presentation/index.html`
- `docs/presentation/styles.css`
- `docs/presentation/deck.js`
- `tests/test_presentation_artifact.py`

브라우저 렌더링 검증으로 다음 캡처를 생성했다.

- `output/playwright/handoff-visualization-title.png`
- `output/playwright/handoff-minmin-graph.png`
- `output/playwright/handoff-neo4j-evidence.png`

Visual QA 결과도 최종 PASS를 받았다. 특히 민민 부인 그래프 구조 slide는 처음에 관계선과 라벨 혼잡 문제가 있었고, 이후 connector line과 라벨 위치를 수정해 재검토 PASS를 받았다.

## 13. 이어받을 때 가장 먼저 볼 파일

처음 이어받는 사람은 다음 순서로 보면 된다.

```text
1. docs/PROJECT_HANDOFF_REPORT.md
   이 보고서. 전체 이해용.

2. docs/presentation/index.html
   시각화 중심 인수인계 자료.

3. docs/NEO4J_GRAPH_STRUCTURE_VISUAL_GUIDE.md
   Neo4j 데이터 구조 전용 시각화 문서.

4. rsc/data/npcs/minmin_lady.md
   NPC 원천 데이터와 chunk 구조 예시.

5. rsc/data/quests/q_glowing_mushroom.yaml
   quest story_expansion 예시.

6. src/db_control/import_story_source_to_neo4j.py
   원천 데이터를 Neo4j에 넣는 코드.

7. src/streamlit/test_app.py
   런타임 조회와 prompt 생성 코드.
```

이 순서로 보면 전체 구조에서 세부 프로세스까지 자연스럽게 이어진다.
