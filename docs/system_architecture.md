# 헤이즐 GraphRAG MVP 전체 구조 문서

이 문서는 현재 저장소에 구현된 MVP 구조를 기준으로, 데이터가 어디에서 시작해 어떤 함수와 서비스를 거쳐 사용자 응답으로 돌아오는지 시각적으로 설명한다. 범위는 현재 동작하는 `Streamlit + Neo4j + 외부 추론 서비스` 구조, importer, Neo4j 그래프 DB, Docker Compose 배포 구조다.

이 문서는 현재 MVP의 짧은 ID 체계를 기준으로 한다. `npc:*`, `quest:*`, `chunk:*` 같은 canonical ID 이관 설계는 이 문서의 대상이 아니다.

## 1. 한눈에 보는 전체 구조

```mermaid
flowchart LR
    User[플레이어 / 운영자 브라우저]
    UI[Streamlit 앱\nsrc/streamlit/test_app.py]
    DB[(Neo4j Graph DB)]
    Infer[외부 추론 서비스\nOpenAI-compatible chat endpoint]
    Source[원천 데이터\nrsc/data]
    Importer[Importer\nsrc/db_control/import_story_source_to_neo4j.py]

    Source -->|Markdown/YAML 읽기| Importer
    Importer -->|MERGE 노드/관계| DB
    User -->|NPC/역할/퀘스트 상태 선택 + 질문| UI
    UI -->|NPC 프로필 조회| DB
    UI -->|허용 KnowledgeChunk 조회| DB
    UI -->|프롬프트 전송| Infer
    Infer -->|스트리밍 응답| UI
    UI -->|NPC 답변 표시| User
```

전체 시스템은 두 개의 큰 흐름으로 나뉜다.

1. 데이터 적재 흐름: `rsc/data`의 Markdown/YAML 원천 데이터를 importer가 읽고 Neo4j 그래프로 변환한다.
2. 런타임 대화 흐름: Streamlit 앱이 사용자의 현재 대화 상태를 기준으로 Neo4j에서 NPC와 지식 chunk를 조회한 뒤, 외부 추론 서비스에 프롬프트를 보내 답변을 스트리밍한다.

## 2. 핵심 파일과 책임

| 파일 | 책임 | 런타임 여부 |
| --- | --- | --- |
| `rsc/data/npcs/*.md` | NPC frontmatter와 `KnowledgeChunk` 원문 정의 | importer 실행 시 사용 |
| `rsc/data/locations/*.md` | 장소 `Location` 정의 | importer 실행 시 사용 |
| `rsc/data/quests/*.yaml` | 퀘스트 `Quest`와 퀘스트-단서-정답 연결 정의 | importer 실행 시 사용 |
| `rsc/data/world/roles.yaml` | 플레이어/NPC 역할 `Role` 정의 | importer 실행 시 사용 |
| `rsc/data/world/events.yaml` | 사건 `Event` 정의 | importer 실행 시 사용 |
| `rsc/data/world/clues.yaml` | 단서 `Clue`와 단서-장소-진실 연결 정의 | importer 실행 시 사용 |
| `rsc/data/world/truths.yaml` | 정답/진실 `Truth`와 공개 조건 정의 | importer 실행 시 사용 |
| `src/db_control/import_story_source_to_neo4j.py` | 원천 데이터를 Neo4j 노드/관계로 적재 | 운영자가 명령으로 실행 |
| `src/streamlit/test_app.py` | 채팅 UI, Neo4j 조회, 프롬프트 생성, 응답 스트리밍 | 사용자가 접속하는 앱 |
| `compose.yaml` | Neo4j, Streamlit, 추론 서비스 컨테이너 정의 | 배포/실행 시 사용 |
| `docs/db_design.md` | 현재 MVP DB 설계 요약 | 참고 문서 |
| `docs/deployment.md` | Windows/Ubuntu 실행 및 배포 절차 | 참고 문서 |

## 3. 배포 토폴로지

```mermaid
flowchart TB
    subgraph Host[Windows 개발 환경 또는 Ubuntu 서버]
        subgraph Compose[Docker Compose 프로젝트]
            Neo4j[neo4j 서비스\n127.0.0.1:7474, 7687\nvolume hazel_neo4j_data:/data]
            Streamlit[streamlit 서비스\n127.0.0.1:8501\nbuild: Dockerfile]
            Inference[추론 서비스\n선택 실행 profile\n127.0.0.1:8000]
        end

        Env[.env / 환경변수]
        SourceTree[저장소 파일\nrsc/data, src, docs]
    end

    Env --> Streamlit
    Env --> Neo4j
    Env --> Inference
    Streamlit -->|bolt://neo4j:7687| Neo4j
    Streamlit -->|HTTP streaming request| Inference
    SourceTree -->|이미지 빌드 컨텍스트| Streamlit
```

`compose.yaml`의 서비스 책임은 다음과 같다.

| 서비스 | 역할 | 주요 연결 |
| --- | --- | --- |
| `neo4j` | 그래프 DB. 모든 NPC, Quest, KnowledgeChunk, Clue, Truth 등의 최종 저장소 | Streamlit이 Bolt로 조회 |
| `streamlit` | 사용자 UI와 GraphRAG 런타임 로직 | Neo4j 조회, 외부 추론 서비스 호출 |
| `추론 서비스` | OpenAI-compatible HTTP 엔드포인트를 제공하는 응답 생성 서비스 | Streamlit이 HTTP로 호출 |

`streamlit`은 `depends_on.neo4j.condition: service_healthy`를 사용한다. 즉 Compose 기준으로는 Neo4j healthcheck가 통과한 뒤 Streamlit 컨테이너가 시작된다. 단, 데이터 적재는 자동으로 실행되지 않는다. 운영자는 별도 명령으로 importer를 실행해 Neo4j에 원천 데이터를 넣어야 한다.

## 4. 데이터 적재 흐름

### 4.1 전체 import sequence

```mermaid
sequenceDiagram
    autonumber
    actor Operator as 운영자
    participant CLI as python import_story_source_to_neo4j.py
    participant Loader as loader 함수들
    participant Upsert as upsert 함수들
    participant Neo4j as Neo4j
    participant Source as rsc/data

    Operator->>CLI: uv run python ... --source-dir rsc/data
    CLI->>CLI: main()
    CLI->>Neo4j: GraphDatabase.driver(NEO4J_URI, auth)
    CLI->>Upsert: import_story_source(driver, source_dir, reset)
    alt --reset 사용
        Upsert->>Neo4j: MATCH (n) DETACH DELETE n
    end
    Upsert->>Neo4j: create_constraints()
    Upsert->>Loader: load_npcs(source_dir)
    Loader->>Source: rsc/data/npcs/*.md 읽기
    Upsert->>Loader: load_locations(source_dir)
    Loader->>Source: rsc/data/locations/*.md 읽기
    Upsert->>Loader: load_quests(source_dir)
    Loader->>Source: rsc/data/quests/*.yaml 읽기
    Upsert->>Loader: load_world(source_dir)
    Loader->>Source: roles/events/clues/truths YAML 읽기
    Upsert->>Neo4j: Role, Truth, Location, Event, Clue, Quest, NPC, KnowledgeChunk 순서로 MERGE
    CLI-->>Operator: Import complete + 개수 출력
```

### 4.2 importer 함수 호출 구조

```mermaid
flowchart TD
    Main[main]
    Args[argparse\n--source-dir, --reset]
    Driver[GraphDatabase.driver]
    Import[import_story_source]
    Reset[reset_database]
    Constraints[create_constraints]
    LoadNPC[load_npcs]
    LoadLoc[load_locations]
    LoadQuest[load_quests]
    LoadWorld[load_world]
    ParseFM[parse_markdown_with_frontmatter]
    ParseChunks[parse_story_chunks]
    YAML[read_yaml]
    UpRole[upsert_role]
    UpTruth[upsert_truth]
    UpLoc[upsert_location]
    UpEvent[upsert_event]
    UpClue[upsert_clue]
    UpQuest[upsert_quest]
    UpNPC[upsert_npc]
    UpChunk[upsert_knowledge_chunk]

    Main --> Args
    Main --> Driver
    Driver --> Import
    Import -->|reset=True| Reset
    Import --> Constraints
    Import --> LoadNPC
    Import --> LoadLoc
    Import --> LoadQuest
    Import --> LoadWorld
    LoadNPC --> ParseFM
    LoadNPC --> ParseChunks
    LoadLoc --> ParseFM
    LoadQuest --> YAML
    LoadWorld --> YAML
    Import --> UpRole
    Import --> UpTruth
    Import --> UpLoc
    Import --> UpEvent
    Import --> UpClue
    Import --> UpQuest
    Import --> UpNPC
    Import --> UpChunk
```

`main()`의 기본 `--source-dir` 값은 코드상 `rsc/data`다. 따라서 일반 문서와 검증 명령은 이 기본값에 맡기거나, 경로를 명시해야 할 때 `--source-dir rsc/data`를 붙이면 된다.

### 4.3 importer의 적재 순서가 중요한 이유

`import_story_source()`는 다음 순서로 노드와 관계를 만든다.

1. `Role`
2. `Truth`
3. `Location`
4. `Event`
5. `Clue`
6. `Quest`
7. `NPC`
8. `KnowledgeChunk`

이 순서는 관계 생성 시 placeholder 노드가 생기는 것을 줄이기 위한 구조다. 예를 들어 `KnowledgeChunk`는 `Quest`, `Location`, `Event`, `Clue`를 가리킨다. 이 대상 노드들이 먼저 만들어져 있으면 chunk 관계를 만들 때 속성이 빈 placeholder로 남을 가능성이 낮다.

다만 Cypher에서는 `MERGE`로 대상 노드를 만들기 때문에, 원천 데이터에 존재하지 않는 ID를 chunk가 참조하면 이름이나 요약 속성이 없는 노드가 생길 수 있다. 그래서 검증 쿼리에서 `Clue.name IS NULL`인 placeholder clue를 확인한다.

### 4.4 원천 데이터에서 Neo4j로 변환되는 방식

```mermaid
flowchart LR
    subgraph Source[원천 파일]
        NPCMD[npcs/*.md\nfrontmatter + fenced chunk]
        LOCMD[locations/*.md\nfrontmatter + body]
        QUESTYAML[quests/*.yaml]
        WORLDYAML[world/*.yaml]
    end

    subgraph Parser[파서/로더]
        FM[parse_markdown_with_frontmatter]
        ChunkParser[parse_story_chunks]
        ReadYaml[read_yaml]
    end

    subgraph Graph[Neo4j 노드]
        NPC[NPC]
        KC[KnowledgeChunk]
        LOC[Location]
        Q[Quest]
        Role[Role]
        Event[Event]
        Clue[Clue]
        Truth[Truth]
    end

    NPCMD --> FM --> NPC
    NPCMD --> ChunkParser --> KC
    LOCMD --> FM --> LOC
    QUESTYAML --> ReadYaml --> Q
    WORLDYAML --> ReadYaml --> Role
    WORLDYAML --> ReadYaml --> Event
    WORLDYAML --> ReadYaml --> Clue
    WORLDYAML --> ReadYaml --> Truth
```

NPC Markdown은 두 종류의 데이터를 동시에 제공한다.

| Markdown 영역 | DB 결과 |
| --- | --- |
| YAML frontmatter | `NPC` 노드 속성 |
| `story-chunk` 또는 `chunk` fenced block metadata | `KnowledgeChunk` 속성과 관계 ID 목록 |
| fenced block 뒤의 본문 | `KnowledgeChunk.text` |

`parse_story_chunks()`는 chunk metadata에 다음 필드가 없으면 예외를 발생시킨다.

```text
chunk_id, phase, title, knowledge_type, quest_id,
location_ids, event_ids, clue_ids, allowed_roles,
answer_sensitive, hint_level, tags
```

이 검증은 import 전에 원천 문서의 최소 구조를 강제하는 역할을 한다.

## 5. Neo4j DB 상세 구조

### 5.1 현재 MVP 목표 개수

| Label | Count |
| --- | ---: |
| `NPC` | 4 |
| `Location` | 8 |
| `Quest` | 5 |
| `Role` | 4 |
| `Event` | 5 |
| `Clue` | 8 |
| `Truth` | 3 |
| `KnowledgeChunk` | 26 |

### 5.2 노드 라벨과 고유 키

```mermaid
erDiagram
    NPC {
        string npc_id PK
        string name
        string role
        string location_id
        string main_quest
        list personality
        list speech_style
        list knowledge_scope
        list restricted_knowledge
        list dialogue_must
        list dialogue_must_not
        string source_path
    }

    ROLE {
        string role_id PK
        string name
        string description
    }

    LOCATION {
        string location_id PK
        string name
        string mood
        string summary
        string function
        list tags
        string source_path
    }

    QUEST {
        string quest_id PK
        string title
        string quest_type
        string summary
        string main_location_id
        list states
        list tags
    }

    EVENT {
        string event_id PK
        string name
        string summary
        boolean visible
        list tags
    }

    CLUE {
        string clue_id PK
        string name
        string summary
        int hint_level
        boolean answer_sensitive
        list tags
    }

    TRUTH {
        string truth_id PK
        string name
        string summary
        boolean answer_sensitive
        list reveal_quest_states
        list required_clue_ids
        list tags
    }

    KNOWLEDGE_CHUNK {
        string chunk_id PK
        string npc_id
        string phase
        string title
        string knowledge_type
        string quest_id
        list allowed_roles
        boolean answer_sensitive
        int hint_level
        list tags
        string text
        string text_ref
        string source_path
    }
```

`create_constraints()`는 다음 unique constraint를 생성한다.

| Constraint 대상 | 고유 키 |
| --- | --- |
| `NPC` | `npc_id` |
| `Role` | `role_id` |
| `Location` | `location_id` |
| `Quest` | `quest_id` |
| `Event` | `event_id` |
| `Clue` | `clue_id` |
| `Truth` | `truth_id` |
| `KnowledgeChunk` | `chunk_id` |

이 제약은 importer가 같은 원천 데이터를 여러 번 병합해도 동일 ID의 노드가 중복 생성되지 않게 한다.

### 5.3 관계 전체 지도

```mermaid
flowchart TB
    NPC[NPC]
    Role[Role]
    Location[Location]
    Quest[Quest]
    Event[Event]
    Clue[Clue]
    Truth[Truth]
    Chunk[KnowledgeChunk]

    NPC -->|HAS_ROLE| Role
    NPC -->|LOCATED_AT| Location
    NPC -->|PARTICIPATES_IN| Quest
    NPC -->|KNOWS| Chunk

    Quest -->|STARTS_AT| Location
    Quest -->|INVOLVES| NPC
    Quest -->|REQUIRES_CLUE| Clue
    Quest -->|HAS_ANSWER| Truth

    Event -->|OCCURRED_AT| Location
    Event -->|CAUSED_BY| Truth

    Clue -->|FOUND_AT| Location
    Clue -->|POINTS_TO| Truth

    Chunk -->|RELATED_TO| Quest
    Chunk -->|MENTIONS| Location
    Chunk -->|ABOUT| Event
    Chunk -->|POINTS_TO| Clue
```

### 5.4 관계별 생성 위치와 의미

| 관계 | 생성 함수 | From -> To | 의미 |
| --- | --- | --- | --- |
| `HAS_ROLE` | `upsert_npc()` | `NPC` -> `Role` | NPC의 역할/직업 |
| `LOCATED_AT` | `upsert_npc()` | `NPC` -> `Location` | NPC 기본 위치 |
| `PARTICIPATES_IN` | `upsert_npc()` | `NPC` -> `Quest` | NPC의 대표 퀘스트 |
| `STARTS_AT` | `upsert_quest()` | `Quest` -> `Location` | 퀘스트 주요 시작 위치 |
| `INVOLVES` | `upsert_quest()` | `Quest` -> `NPC` | 퀘스트 관련 NPC |
| `REQUIRES_CLUE` | `upsert_quest()` | `Quest` -> `Clue` | 퀘스트 풀이에 필요한 단서 |
| `HAS_ANSWER` | `upsert_quest()` | `Quest` -> `Truth` | 퀘스트 정답으로 이어지는 진실 |
| `OCCURRED_AT` | `upsert_event()` | `Event` -> `Location` | 사건 발생 위치 |
| `CAUSED_BY` | `upsert_event()` | `Event` -> `Truth` | 사건의 원인 |
| `FOUND_AT` | `upsert_clue()` | `Clue` -> `Location` | 단서가 발견되는 위치 |
| `POINTS_TO` | `upsert_clue()` | `Clue` -> `Truth` | 단서가 가리키는 진실 |
| `KNOWS` | `upsert_knowledge_chunk()` | `NPC` -> `KnowledgeChunk` | NPC가 말할 수 있는 지식 단위 |
| `RELATED_TO` | `upsert_knowledge_chunk()` | `KnowledgeChunk` -> `Quest` | chunk가 속한 퀘스트 |
| `MENTIONS` | `upsert_knowledge_chunk()` | `KnowledgeChunk` -> `Location` | chunk가 언급하는 장소 |
| `ABOUT` | `upsert_knowledge_chunk()` | `KnowledgeChunk` -> `Event` | chunk가 다루는 사건 |
| `POINTS_TO` | `upsert_knowledge_chunk()` | `KnowledgeChunk` -> `Clue` | chunk가 제공하는 단서 |

`POINTS_TO`는 두 곳에서 쓰인다. `Clue -> Truth`에서는 단서가 어떤 진실을 가리키는지 뜻하고, `KnowledgeChunk -> Clue`에서는 NPC 지식이 어떤 단서를 제공하는지 뜻한다. 같은 관계명이지만 시작/도착 라벨 조합이 다르므로 의미가 구분된다.

### 5.5 NPC별 KnowledgeChunk 분포

```mermaid
pie showData
    title NPC별 KnowledgeChunk 수
    "chief_rowan" : 7
    "mage_lumi" : 5
    "minmin_lady" : 8
    "patrol_leader_rio" : 6
```

이 분포는 런타임에서 특정 NPC를 선택했을 때 조회 가능한 후보 지식의 상한을 결정한다. Streamlit 앱은 매 질문마다 해당 NPC에서 시작하는 `KNOWS` 관계만 따라간다. 다른 NPC의 chunk는 같은 퀘스트에 연결되어 있더라도 조회 시작점이 다르기 때문에 기본적으로 섞이지 않는다.

## 6. Streamlit 런타임 흐름

### 6.1 사용자 요청부터 답변까지

```mermaid
sequenceDiagram
    autonumber
    actor User as 사용자
    participant UI as Streamlit UI
    participant State as st.session_state
    participant Neo4j as Neo4j
    participant Prompt as build_prompt()
    participant Infer as 외부 추론 서비스

    User->>UI: 브라우저 접속
    UI->>State: 기본 npc_id/player_role/quest_id/quest_state/hint_level 초기화
    User->>UI: 사이드바에서 현재 대화 상태 선택
    User->>UI: 채팅 입력
    UI->>State: user message append
    UI->>Neo4j: get_npc_profile(npc_id)
    Neo4j-->>UI: NPC 프로필 속성
    UI->>Neo4j: get_allowed_chunks(npc_id, role, quest, state, hint)
    Neo4j-->>UI: 허용된 KnowledgeChunk 목록
    UI->>Prompt: build_prompt(npc, chunks, user_message, state)
    Prompt-->>UI: 최종 프롬프트 문자열
    UI->>Infer: 응답 스트리밍 함수(prompt)
    Infer-->>UI: token/text stream
    UI->>State: assistant response append
    UI-->>User: NPC 답변 표시
```

### 6.2 Streamlit 파일 내부 실행 순서

```mermaid
flowchart TD
    Start[파일 로드]
    Config[환경변수에서 Neo4j/추론 URL 읽기]
    Page[st.set_page_config + title]
    InitState[st.session_state 기본값 초기화]
    Sidebar[사이드바 selectbox/slider 렌더]
    History[기존 messages 렌더]
    Input[st.chat_input 대기]
    AppendUser[사용자 메시지 저장/렌더]
    Profile[get_npc_profile]
    Chunks[get_allowed_chunks]
    Prompt[build_prompt]
    Debug[Debug expander에 chunks/prompt 표시]
    Stream[응답 스트리밍 함수]
    AppendAssistant[응답 저장]
    Error[예외 발생 시 오류 메시지 저장/표시]

    Start --> Config --> Page --> InitState --> Sidebar --> History --> Input
    Input --> AppendUser --> Profile --> Chunks --> Prompt --> Debug --> Stream --> AppendAssistant
    Profile -.예외.-> Error
    Chunks -.예외.-> Error
    Stream -.예외 문자열 yield.-> AppendAssistant
```

Streamlit은 스크립트 재실행 방식으로 동작한다. 사용자가 selectbox를 바꾸거나 채팅을 입력하면 파일이 다시 실행되고, `st.session_state`에 저장된 값으로 이전 대화와 현재 선택 상태를 복원한다.

### 6.3 세션 상태 구조

| `st.session_state` 키 | 기본값 | 의미 |
| --- | --- | --- |
| `messages` | `[]` | 화면에 렌더링할 대화 기록 |
| `npc_id` | `minmin_lady` | 현재 대화할 NPC ID |
| `player_role` | `farmer` | 플레이어 역할 |
| `quest_id` | `q_glowing_mushroom` | 현재 퀘스트 |
| `quest_state` | `in_progress` | 현재 퀘스트 진행 상태 |
| `allowed_hint_level` | `1` | 조회 허용 힌트 레벨 |

이 값들은 `get_allowed_chunks()`의 파라미터로 들어가고, 최종 프롬프트의 `[현재 대화 상태]`에도 포함된다.

## 7. Streamlit에서 Neo4j를 조회하는 방식

### 7.1 Driver 생성

```mermaid
flowchart LR
    Env[환경변수\nNEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]
    Cache[st.cache_resource]
    Driver[get_neo4j_driver]
    Neo4j[(Neo4j)]

    Env --> Driver
    Cache --> Driver
    Driver -->|GraphDatabase.driver| Neo4j
```

`get_neo4j_driver()`는 `@st.cache_resource`가 붙어 있다. Streamlit이 스크립트를 재실행해도 같은 설정의 Neo4j driver를 재사용하기 위한 구조다.

### 7.2 NPC 프로필 조회

`get_npc_profile(npc_id)`는 다음 순서로 동작한다.

1. `MATCH (n:NPC {npc_id: $npc_id})`로 NPC를 찾는다.
2. 말투/성격/지식 범위/금지 지식/대화 규칙에 필요한 속성만 반환한다.
3. 결과가 없으면 `ValueError("NPC not found: ...")`를 발생시킨다.
4. 호출부의 `try/except`가 이 예외를 잡아 Streamlit 채팅에 오류 메시지를 표시한다.

조회되는 속성은 다음과 같다.

```text
npc_id, name, role,
personality, speech_style,
knowledge_scope, restricted_knowledge,
dialogue_must, dialogue_must_not
```

### 7.3 KnowledgeChunk 조회

```mermaid
flowchart TD
    Params[입력 파라미터\nnpc_id, player_role, quest_id, quest_state, allowed_hint_level]
    MatchNPC[MATCH NPC - KNOWS - KnowledgeChunk]
    QuestFilter[quest_id 필터\n같은 퀘스트 또는 quest_id 없음]
    RoleFilter[역할 필터\nplayer_role IN allowed_roles]
    HintFilter[힌트 상한 필터\nhint_level <= allowed_hint_level]
    SensitiveFilter[정답성 필터\n비민감 or 상태 허용]
    Sort[hint_level, chunk_id 정렬]
    Limit[LIMIT 5]
    Result[chunk_id/title/type/quest/hint/sensitive/text 반환]

    Params --> MatchNPC --> QuestFilter --> RoleFilter --> HintFilter --> SensitiveFilter --> Sort --> Limit --> Result
```

현재 Cypher 조건은 다음 개념을 구현한다.

| 조건 | 의미 |
| --- | --- |
| `(:NPC {npc_id})-[:KNOWS]->(k)` | 선택한 NPC가 알고 있는 chunk만 후보가 된다 |
| `quest_id` 일치 또는 `k.quest_id IS NULL` | 현재 퀘스트와 관련 있거나 범용 지식인 chunk만 허용한다 |
| `player_role IN k.allowed_roles` | 현재 플레이어 역할에게 말할 수 있는 chunk만 허용한다 |
| `k.hint_level <= allowed_hint_level` | 허용 힌트 레벨 이하의 지식만 통과한다 |
| `k.answer_sensitive = false` | 민감하지 않은 지식은 기본 허용한다 |
| `quest_state IN [ready_to_answer, solved]` | 정답 공개 가능한 상태면 민감 지식도 허용한다 |
| `ORDER BY hint_level, chunk_id LIMIT 5` | 낮은 힌트부터 안정적 순서로 최대 5개만 전달한다 |

이 조회는 MVP의 핵심 GraphRAG 단계다. embedding 검색은 없지만, 그래프 관계와 속성 조건으로 “현재 NPC가 현재 상황에서 말할 수 있는 지식”만 좁힌다.

## 8. 프롬프트 생성과 응답 처리

### 8.1 프롬프트 조립 구조

```mermaid
flowchart TB
    NPCProfile[NPC 프로필]
    Chunks[허용 KnowledgeChunk 목록]
    UserMsg[플레이어 질문]
    DialogState[quest_id / quest_state / player_role / hint_level]
    Prompt[build_prompt 결과]

    NPCProfile --> Prompt
    Chunks --> Prompt
    UserMsg --> Prompt
    DialogState --> Prompt
```

`build_prompt()`는 다음 블록을 하나의 문자열로 합친다.

| 프롬프트 블록 | 입력 데이터 | 목적 |
| --- | --- | --- |
| NPC 기본 정보 | `npc_id`, `name`, `role` | 응답 화자 고정 |
| 성격 | `personality` | 캐릭터 성격 반영 |
| 말투 | `speech_style` | 캐릭터 말투 반영 |
| 알고 있는 지식 범위 | `knowledge_scope` | 답변 가능 범위 제한 |
| 모르는 지식/금지 지식 | `restricted_knowledge` | 누설 방지 |
| 반드시 지킬 규칙 | `dialogue_must` | 대화 정책 적용 |
| 절대 하지 말아야 할 것 | `dialogue_must_not` | 금지 행동 적용 |
| 현재 대화 상태 | session state 값 | 퀘스트 진행 상태 반영 |
| 사용 가능한 지식 | 조회된 chunk text | 답변 근거 제공 |
| 응답 정책 | 고정 규칙 | 환각/메타 발화/정답 누설 제한 |
| 플레이어 질문 | 사용자가 입력한 문장 | 실제 응답 대상 |

`string_list()`는 Neo4j에서 돌아온 속성이 list가 아닐 때 빈 list로 바꾼다. `bullet_list()`는 빈 list를 `- 없음`으로 표현한다. 이 두 함수는 프롬프트의 리스트 블록이 깨지지 않게 만드는 보조 함수다.

### 8.2 응답 스트리밍 처리

```mermaid
sequenceDiagram
    autonumber
    participant UI as Streamlit chat handler
    participant Stream as 응답 스트리밍 함수
    participant HTTP as requests.post(..., stream=True)
    participant Endpoint as 외부 추론 엔드포인트

    UI->>Stream: prompt 전달
    Stream->>HTTP: POST 요청 생성
    HTTP->>Endpoint: JSON payload 전송
    Endpoint-->>HTTP: data: ... 라인 스트림
    loop 각 라인
        HTTP-->>Stream: response.iter_lines()
        Stream->>Stream: data: prefix 확인
        Stream->>Stream: [DONE]이면 종료
        Stream-->>UI: content 조각 yield
    end
    UI->>UI: st.write_stream으로 화면에 누적 표시
```

응답 처리의 핵심은 `stream=True`다. 전체 응답이 끝날 때까지 기다린 뒤 한 번에 보여주는 방식이 아니라, 들어오는 조각을 `yield`하고 `st.write_stream()`이 이를 화면에 누적한다.

예외가 발생하면 응답 스트리밍 함수는 예외를 다시 던지지 않고 오류 문자열을 yield한다. 반면 Neo4j 조회나 prompt 생성 단계에서 발생한 예외는 chat handler의 `try/except`가 잡아서 `오류 발생: ...` 형태로 화면에 표시한다.

## 9. 런타임 데이터 이동 상세

```mermaid
flowchart LR
    A[사용자 입력 문장]
    B[st.session_state.messages에 user 저장]
    C[get_npc_profile]
    D[NPC 프로필 dict]
    E[get_allowed_chunks]
    F[KnowledgeChunk dict list]
    G[build_prompt]
    H[프롬프트 문자열]
    I[HTTP streaming request]
    J[응답 조각 stream]
    K[st.write_stream 출력]
    L[st.session_state.messages에 assistant 저장]

    A --> B --> C --> D --> G
    B --> E --> F --> G
    G --> H --> I --> J --> K --> L
```

데이터 타입 관점에서 보면 다음과 같다.

| 단계 | 입력 | 출력 |
| --- | --- | --- |
| 채팅 입력 | 문자열 | `{"role": "user", "content": ...}` |
| NPC 조회 | `npc_id: str` | `dict[str, object]` |
| chunk 조회 | `npc_id`, `role`, `quest`, `state`, `hint` | `list[dict[str, object]]` |
| 프롬프트 생성 | NPC dict, chunk list, 사용자 질문, 상태값 | `str` |
| 추론 요청 | prompt 문자열 | 스트리밍 text 조각 |
| 화면 출력 | text 조각 | 누적된 assistant response |
| 히스토리 저장 | assistant response | `messages`에 append |

## 10. Importer와 Streamlit의 DB 사용 차이

| 구분 | Importer | Streamlit |
| --- | --- | --- |
| 목적 | 원천 데이터를 그래프 DB로 변환 | 그래프 DB에서 현재 대화에 필요한 데이터 조회 |
| 실행 주체 | 운영자/배포 스크립트 | 사용자 브라우저 요청에 따른 앱 실행 |
| DB 작업 | `MERGE`, `SET`, 관계 생성, constraint 생성 | `MATCH`, `RETURN` 조회 |
| 주요 함수 | `import_story_source()`, `upsert_*()` | `get_npc_profile()`, `get_allowed_chunks()` |
| 실패 방식 | 예외 발생 시 import 중단 | 화면에 오류 메시지 표시 또는 오류 문자열 출력 |
| 데이터 방향 | 파일 -> Neo4j | Neo4j -> 프롬프트 -> 사용자 화면 |

## 11. 운영 시나리오별 흐름

### 11.1 최초 데이터 구축

```mermaid
flowchart TD
    Pull[git pull / 코드 확보]
    Env[.env 준비]
    UpDB[docker compose up -d neo4j]
    Import[import_story_source_to_neo4j.py --source-dir rsc/data]
    CheckCounts[개수 검증 쿼리]
    UpApp[docker compose up -d streamlit]
    Health[Streamlit health 확인]

    Pull --> Env --> UpDB --> Import --> CheckCounts --> UpApp --> Health
```

운영 DB는 기본적으로 `--reset` 없이 병합 적재한다. `--reset`은 모든 노드를 삭제하므로 분리된 개발 DB나 검증용 DB 재생성에만 사용한다.

### 11.2 일반 사용자 대화

```mermaid
flowchart TD
    Open[브라우저로 Streamlit 접속]
    Select[사이드바 상태 선택]
    Ask[질문 입력]
    Retrieve[Neo4j에서 NPC + chunk 조회]
    Compose[프롬프트 생성]
    Stream[외부 추론 응답 스트리밍]
    Save[대화 히스토리 저장]

    Open --> Select --> Ask --> Retrieve --> Compose --> Stream --> Save
```

### 11.3 원천 데이터 수정 후 반영

```mermaid
flowchart TD
    EditData[rsc/data 수정]
    RunTests[loader/contract 테스트 실행]
    ImportNoReset[importer 실행]
    Verify[Neo4j 검증 쿼리]
    AppCheck[Streamlit에서 NPC별 확인]

    EditData --> RunTests --> ImportNoReset --> Verify --> AppCheck
```

원천 데이터 수정이 `chunk_id`, `quest_id`, `clue_id` 같은 고유 ID를 바꾸는 경우에는 기존 노드와 관계가 남을 수 있다. 이때는 개발 환경에서 `--reset`으로 재생성하고, 운영 환경에서는 삭제/마이그레이션 계획을 별도로 세우는 편이 안전하다.

## 12. 에러 흐름

```mermaid
flowchart TD
    ImportStart[Importer 실행]
    FMError[frontmatter 없음/파싱 실패]
    ChunkError[chunk metadata 필수 필드 누락]
    DBError[Neo4j 연결/쿼리 실패]
    ImportStop[import 중단]

    AppStart[Streamlit 질문 처리]
    NPCMissing[NPC not found]
    QueryError[Neo4j 조회 실패]
    InferError[추론 HTTP/stream 오류]
    UIError[채팅창 오류 표시]
    UIYield[오류 문자열 스트리밍]

    ImportStart --> FMError --> ImportStop
    ImportStart --> ChunkError --> ImportStop
    ImportStart --> DBError --> ImportStop

    AppStart --> NPCMissing --> UIError
    AppStart --> QueryError --> UIError
    AppStart --> InferError --> UIYield
```

Importer는 데이터 품질 문제가 있으면 즉시 예외를 발생시켜 중단한다. 반면 Streamlit 앱은 사용자 화면을 유지해야 하므로 오류를 채팅 메시지나 스트리밍 문자열로 표시한다.

## 13. 검증 지점

### 13.1 파일/파서 단계

| 검증 | 목적 |
| --- | --- |
| NPC 수 4 | 모든 NPC Markdown frontmatter가 읽히는지 확인 |
| KnowledgeChunk 수 26 | 모든 `story-chunk`/`chunk` fenced block이 파싱되는지 확인 |
| clue ID 참조 검증 | placeholder clue 생성 방지 |
| quest/world YAML key 검증 | 관계 생성에 필요한 필드가 importer 계약과 맞는지 확인 |

### 13.2 DB 단계

| 검증 쿼리 | 확인 내용 |
| --- | --- |
| NPC별 `KNOWS` count | NPC별 chunk 분포가 기대값과 맞는지 확인 |
| `Clue.name IS NULL` | chunk 참조만 있고 정의가 없는 clue 탐지 |
| Quest 관계 조회 | `INVOLVES`, `REQUIRES_CLUE`, `HAS_ANSWER` 생성 확인 |

### 13.3 앱 단계

| 검증 | 확인 내용 |
| --- | --- |
| Streamlit health | 앱 프로세스가 떠 있는지 확인 |
| 사이드바 옵션 | 현재 MVP의 NPC/Role/Quest/State 선택 가능 여부 |
| Debug Retrieved Chunks | 현재 상태에서 어떤 chunk가 조회되는지 확인 |
| Debug Prompt | 최종 프롬프트에 NPC/상태/chunk가 올바르게 들어갔는지 확인 |

## 14. 현재 MVP의 의도적 단순화

현재 MVP는 GraphRAG의 전체 최종형이 아니라, 그래프 기반 지식 제한을 먼저 검증하는 단계다.

의도적으로 단순화된 부분은 다음과 같다.

| 영역 | 현재 방식 | 이후 확장 가능성 |
| --- | --- | --- |
| ID | 짧은 ID 직접 사용 | canonical ID alias 계층 추가 |
| 검색 | Neo4j 관계/속성 필터 | embedding 검색과 graph traversal 결합 |
| UI 옵션 | 코드에 하드코딩된 목록 | DB에서 동적 로딩 |
| 대화 상태 | 사이드바 수동 선택 | 게임 서버/세이브 상태 연동 |
| 데이터 적재 | 수동 importer 실행 | 배포 파이프라인/관리자 도구 연동 |
| 오류 처리 | 화면 표시 중심 | 사용자 친화적 오류 분류/재시도 정책 |

이 단순화 덕분에 현재 구조에서는 “NPC가 아는 것만 말하게 하기”, “퀘스트 상태와 힌트 레벨에 따라 공개 범위를 제한하기”, “원천 데이터 변경이 DB와 앱에 어떻게 반영되는지 추적하기”를 빠르게 검증할 수 있다.

## 15. 최종 데이터 흐름 요약

```mermaid
flowchart LR
    D1[작성자\nMarkdown/YAML 작성]
    D2[Importer\n파일 파싱]
    D3[Neo4j\n노드/관계 저장]
    D4[Streamlit\n현재 상태 수집]
    D5[Cypher 조회\nNPC + 허용 chunk]
    D6[Prompt 생성\n캐릭터/상태/근거 조합]
    D7[외부 추론 서비스\n응답 생성]
    D8[Streamlit\n스트리밍 출력 + 히스토리 저장]

    D1 --> D2 --> D3 --> D4 --> D5 --> D6 --> D7 --> D8
```

한 문장으로 정리하면, 현재 MVP는 `rsc/data`의 세계관 원천 데이터를 Neo4j 그래프로 바꾼 뒤, Streamlit이 사용자의 현재 대화 상태를 기준으로 “선택된 NPC가 말할 수 있는 KnowledgeChunk”만 가져와 답변 근거로 쓰는 구조다.
