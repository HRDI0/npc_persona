# 헤이즐 마을 원천 문서 자동 분류 기준

현재 importer는 root raw markdown 파일을 자동으로 가져오지 않는다.

현재 Neo4j importer의 계약은 이미 정리된 구조화 파일을 읽는 방식이다. `rsc/data/hazel_village_map_stories.md`, `rsc/data/hazel_village_npc_chronicles.md`, `rsc/data/hazel_village_npc_chronicles_plain.md`처럼 `rsc/data` 루트에 있는 raw Markdown은 importer 입력이 아니라 작성/검토용 원천 문서다.

## 현재 importer 계약

현재 적재 경로는 다음과 같이 고정되어 있다.

```text
rsc/data/npcs/*.md        -> NPC, KnowledgeChunk
rsc/data/locations/*.md   -> Location
rsc/data/quests/*.yaml    -> Quest
rsc/data/world/roles.yaml -> Role
rsc/data/world/events.yaml -> Event
rsc/data/world/clues.yaml -> Clue
rsc/data/world/truths.yaml -> Truth
```

NPC와 location Markdown은 반드시 YAML frontmatter를 가져야 한다. NPC 문서 안의 `story-chunk metadata`는 fenced block 안에 들어가며, importer는 그 metadata와 바로 뒤 본문을 `KnowledgeChunk`로 적재한다. Quest와 world 항목은 YAML 파일에 이미 나뉘어 있어야 한다.

따라서 raw 문서에 내용을 추가해도 곧바로 `location`, `world`, `npcs`, `quests`로 적재되지는 않는다. 새 classifier는 raw 문서를 먼저 읽고 어떤 부분이 어느 도메인에 가까운지 보여 주는 비파괴 review-only 보고서를 만든다. 이 보고서는 사람이 검토한 뒤 구조화 파일로 옮기는 기준이며, Neo4j에 직접 import하지 않는다.

## 비파괴 review-only 흐름

권장 흐름은 다음과 같다.

1. raw Markdown에 세계관, 장소, NPC, 퀘스트 아이디어를 작성한다.
2. `scripts/story_pipeline/classify_story_sources.py`로 `output/reports/story_source_classification_review.json` review-only 보고서를 만든다.
3. 보고서에서 `location`, `world`, `npcs`, `quests` 분류와 section 제목을 확인한다.
4. 사람이 검토한 뒤 필요한 항목만 `rsc/data/locations`, `rsc/data/npcs`, `rsc/data/quests`, `rsc/data/world` 파일로 옮긴다.
5. 기존 importer를 실행해 Neo4j에 적재한다.

classifier는 기본적으로 구조화 폴더를 덮어쓰지 않는다. 기존 review JSON도 실수로 덮어쓰지 않도록 overwrite 옵션이 있을 때만 다시 쓴다.

## 도메인 분류 기준

### location

`location`은 물리적 장소, 맵, 건물, 길, 지역을 설명하는 section이다. 다음 신호가 강하면 location으로 분류한다.

- 제목이 `# 헤이즐 광장`, `# 동쪽 농장`, `# 속삭임 숲 입구`처럼 장소명이다.
- 본문에 `장소 개요`, `맵 분위기`, `자주 언급되는 이야기`가 있다.
- 기능, 분위기, 주변 장소, 주민 이동, 발견 가능한 단서가 중심이다.
- NPC가 등장하더라도 장소의 사용 방식이나 분위기를 설명하기 위한 언급이다.

작성 예시는 다음과 같다.

```markdown
# 헤이즐 광장

## 장소 개요
마을 중심이자 소문이 모이는 장소다.

## 맵 분위기
밝고 안전하며 초보자가 안심하는 분위기다.

## 자주 언급되는 이야기
- 안내판이 있다.
- 로완은 광장의 평온함을 마을 상태의 기준으로 본다.
```

구조화 파일로 옮길 때는 `rsc/data/locations/*.md`에 YAML frontmatter를 붙인다.

```yaml
---
location_id: hazel_square
name: 헤이즐 광장
mood: 밝고 안전함
function: 마을의 중심, 소문과 시작점
---
```

### npcs

`npcs`는 이름과 의도, 말투, 지식 범위가 있는 인물을 설명하는 section이다. 다음 신호가 강하면 npcs로 분류한다.

- 제목이 `# 민민 부인`, `# 순찰대장 리오`, `# 마도사 루미`, `# 헤이즐 촌장 로완`처럼 인물명이다.
- 본문에 `인물 개요`, `연대기`, `말투 예시`, `현재의 ...`가 있다.
- 성격, 말투, 동기, 아는 것과 모르는 것, 관련 퀘스트가 중심이다.
- `story-chunk metadata` 또는 RAG chunk 설명이 있다.

구조화 NPC Markdown에는 YAML frontmatter와 `story-chunk` fenced block을 둔다.

```markdown
---
npc_id: minmin_lady
name: 민민 부인
role: farmer
location_id: east_farm
main_quest: q_glowing_mushroom
personality:
- 다정함
speech_style:
- 농사와 밥 비유를 자주 사용한다.
knowledge_scope:
- farm_observation
restricted_knowledge:
- final_truth
dialogue_rules:
  must:
  - 직접 본 것만 말한다.
  must_not:
  - 최종 원인을 말하지 않는다.
---

```story-chunk
chunk_id: minmin_chronicle_003
phase: mushroom_change
title: 민민 부인이 본 몽실버섯의 변화
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
  - 민민 부인
  - 몽실버섯
```

민민 부인이 직접 본 변화만 적는다.
```

`story-chunk metadata`의 필수 필드는 `chunk_id`, `phase`, `title`, `knowledge_type`, `quest_id`, `location_ids`, `event_ids`, `clue_ids`, `allowed_roles`, `answer_sensitive`, `hint_level`, `tags`다.

### quests

`quests`는 플레이어 목표, 조사 흐름, 단서 수집, 정답 판정, 보상 또는 상태 전환이 중심인 section이다. 다음 신호가 강하면 quests로 분류한다.

- `퀘스트`, `의뢰`, `목표`, `힌트`, `정답`, `보상`, `단서`가 반복된다.
- 누가 시작하고, 어디서 시작하며, 어떤 NPC와 장소를 거치는지가 드러난다.
- `not_started`, `in_progress`, `ready_to_answer`, `solved` 같은 상태가 있다.
- player-facing objective와 성공 조건이 있다.

구조화 파일 예시는 다음과 같다.

```yaml
quest_id: q_glowing_mushroom
title: 빛나는 몽실버섯
quest_type: investigation
main_location_id: whispering_forest_entrance
involved_npc_ids:
- minmin_lady
- mage_lumi
required_clue_ids:
- clue_bright_mushroom
answer_truth_ids:
- truth_moonwell_mana_cycle
states:
- not_started
- in_progress
- ready_to_answer
- solved
```

### world

`world`는 특정 NPC나 장소 하나보다 넓은 규칙, 역사, 사건 원리, 역할 체계, 지식 유형, 진실, 단서 체계를 설명하는 section이다. 다음 신호가 강하면 world로 분류한다.

- `문서 개요`, `전체 정리`, `캐릭터별 정보 차이`, `맵별 스토리 활용 방향` 같은 종합 section이다.
- 마나, 포자, 달빛 샘터 주기, 마을 규칙, RBAC 역할, knowledge_type 같은 시스템 규칙을 설명한다.
- 여러 NPC가 같은 사건을 어떻게 다르게 아는지 비교한다.
- `roles.yaml`, `events.yaml`, `clues.yaml`, `truths.yaml`로 옮길 수 있는 사실이다.

world 항목은 하나의 Markdown section이 아니라 여러 YAML 파일로 나뉜다.

```yaml
events:
- event_id: event_glowing_mushroom
  name: 몽실버섯 발광 변화
  summary: 몽실버섯이 밤과 밝은 달빛 아래에서 평소보다 강하게 빛난다.
  location_ids:
  - whispering_forest_entrance
  truth_ids:
  - truth_moonwell_mana_cycle
```

## raw Markdown 작성 규칙

자동 분류를 예측 가능하게 만들려면 section 경계를 명확히 해야 한다.

- 큰 단위는 `#` heading으로 시작한다.
- 장소는 `## 장소 개요`, `## 맵 분위기`, `## 자주 언급되는 이야기`를 사용한다.
- 인물은 `## 인물 개요`, `## 어린 시절`, `## 현재의 ...`, `## 말투 예시`를 사용한다.
- 퀘스트는 `## 목표`, `## 시작 조건`, `## 필요 단서`, `## 정답 조건`, `## 완료 상태`를 사용한다.
- 세계관 규칙은 `## 세계 규칙`, `## 지식 유형`, `## 사건 원리`, `## 캐릭터별 정보 차이`처럼 쓴다.
- 한 section에는 하나의 주제만 둔다. 장소 설명 안에 퀘스트 절차를 길게 쓰지 않는다.
- 이름은 구조화 ID로 바꾸기 쉬워야 한다. 예: `헤이즐 광장` -> `hazel_square`, `민민 부인` -> `minmin_lady`.
- prose는 사람이 읽는 설명이고, tag나 ID는 importer가 연결할 구조다. 둘을 섞지 않는다.

## 상세 작성 가이드

장소를 쓸 때는 배경 묘사만 쓰지 말고 게임 내 기능을 함께 적는다. 예를 들어 헤이즐 광장은 예쁜 배경이 아니라 소문이 모이고 초보자가 시작하는 곳이다. 동쪽 농장은 생활감뿐 아니라 이상 징후가 처음 드러나는 곳이다.

NPC를 쓸 때는 모든 사실을 다 아는 인물로 만들지 않는다. 각 NPC는 자신이 직접 본 것, 직업상 알 수 있는 것, 말하면 안 되는 것을 구분해야 한다. 이 구분이 `knowledge_scope`, `restricted_knowledge`, `allowed_roles`, `answer_sensitive`, `hint_level`로 이어진다.

퀘스트를 쓸 때는 “무엇을 하라”보다 “왜 조사해야 하는가”와 “어떤 단서를 통해 다음 단계로 가는가”를 분명히 한다. 정답을 포함하는 문장은 `answer_sensitive: true`와 높은 `hint_level`이 필요한지 검토한다.

world를 쓸 때는 단일 대사보다 재사용 가능한 규칙으로 적는다. 마나 주기, 포자 반응, 역할별 접근 권한, 단서와 진실의 연결은 여러 NPC와 퀘스트에서 재사용되므로 `world/*.yaml` 후보로 본다.

## 검토 체크리스트

- 이 section은 장소인가, 인물인가, 퀘스트인가, 세계 규칙인가?
- 구조화 파일로 옮길 때 필요한 ID를 만들 수 있는가?
- NPC가 말해도 되는 지식과 말하면 안 되는 지식이 분리되어 있는가?
- 정답 유출 가능성이 있는 문장은 `answer_sensitive` 후보로 표시했는가?
- 단서, 사건, 진실이 각각 `clue_id`, `event_id`, `truth_id`로 연결될 수 있는가?
- review-only 보고서를 검토한 뒤에만 구조화 폴더를 수정했는가?
