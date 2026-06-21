# 헤이즐 MVP 배포 가이드

현재 로컬 작업 환경은 Windows이고, 실제 서버 환경은 Ubuntu로 가정한다. 서버에서는 배포 대상 브랜치인 `main`을 명시적으로 가져온다.

## Windows 로컬 실행

PowerShell에서 환경변수를 명시한다.

```powershell
$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="admin2026"
$env:NEO4J_DATABASE="neo4j"
$env:VLLM_URL="http://localhost:8000/v1/chat/completions"
$env:MODEL_NAME="google/gemma-4-E4B-it"
$env:CHAT_LOG_PATH="output/reports/streamlit_llm_interactions.jsonl"
$env:RETRIEVAL_LOG_PATH="output/reports/streamlit_retrieval_events.jsonl"
$env:PROMPT_LOG_PATH="output/reports/streamlit_prompt_events.jsonl"
$env:MEMORY_LOG_PATH="output/reports/streamlit_memory_events.jsonl"
$env:ADMIN_LOG_PATH="output/reports/streamlit_admin_events.jsonl"
$env:NEO4J_IMPORT_LOG_PATH="output/reports/streamlit_neo4j_import_events.jsonl"
```

Streamlit 런타임 로그는 기능별 JSONL 파일로 나뉜다. `CHAT_LOG_PATH`는 대화 입출력, `RETRIEVAL_LOG_PATH`는 조회 chunk, `PROMPT_LOG_PATH`는 최종 프롬프트, `MEMORY_LOG_PATH`는 메모리 이벤트, `ADMIN_LOG_PATH`는 관리자 동작, `NEO4J_IMPORT_LOG_PATH`는 관리자 Neo4j import 이벤트를 기록한다. 각 JSONL record에는 `timestamp_ms`가 포함된다.

Neo4j가 떠 있는 상태에서 원천 데이터를 병합 적재한다.

```powershell
uv run python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data
```

Streamlit 앱을 실행한다.

```powershell
uv run streamlit run src/streamlit/test_app.py
```

`--reset`은 현재 Neo4j DB의 모든 노드를 삭제한다. 분리된 개발 DB를 재생성할 때만 명시적으로 붙인다.

## Ubuntu 서버 배포

서버에서는 `main`을 명시적으로 가져온다.

```bash
git fetch origin
git switch main
git pull --ff-only origin main
```

환경 파일을 만든다.

```bash
cp .env.example .env
```

필요하면 `.env`의 `NEO4J_DATABASE`, `HF_TOKEN`, `HF_CACHE_DIR`, `VLLM_URL`, `MODEL_NAME`과 로그 경로를 서버 환경에 맞게 수정한다. 지원되는 Streamlit 로그 경로는 `CHAT_LOG_PATH`, `RETRIEVAL_LOG_PATH`, `PROMPT_LOG_PATH`, `MEMORY_LOG_PATH`, `ADMIN_LOG_PATH`, `NEO4J_IMPORT_LOG_PATH`다. 실제 토큰과 비밀번호는 추적되지 않는 `.env`에만 둔다. 로그 경로를 비워 두면 Streamlit은 `output/reports/` 아래 기본 JSONL 파일을 사용하고, 각 record에 `timestamp_ms`를 남긴다. 외부 vLLM 서버를 쓰는 경우에는 `VLLM_URL`을 해당 서버에서 접근 가능한 주소로 바꾼다. vLLM을 같은 Compose 프로젝트에서 띄우면 기본값 `http://vllm:8000/v1/chat/completions`를 그대로 사용할 수 있다.

Streamlit 이미지를 빌드하고 Neo4j와 앱을 실행한다. 실제 서버 실행은 복사해 둔 `.env`를 사용한다.

```bash
docker compose --env-file .env build streamlit
docker compose --env-file .env up -d neo4j streamlit
```

환경 파일을 명시하지 않는 기본 형태는 `docker compose up -d neo4j streamlit`이다. 서버에서는 값이 고정된 `.env`를 명시하는 쪽을 권장한다.

외부 vLLM을 이미 준비했거나 `.env`의 `VLLM_URL`을 외부 vLLM으로 바꾼 경우에는 위 명령을 사용한다. 같은 Compose 프로젝트에서 vLLM까지 함께 실행하려면 GPU 서버에서 다음 명령을 사용한다.
기본 Compose host port는 `127.0.0.1`에만 바인딩한다. 외부 공개가 필요하면 방화벽과 reverse proxy 또는 SSH 터널을 별도로 둔다.

```bash
docker compose --env-file .env --profile gpu up -d neo4j vllm streamlit
```

환경 파일을 명시하지 않는 기본 형태는 `docker compose --profile gpu up -d neo4j vllm streamlit`이다. 서버에서는 값이 고정된 `.env`를 명시하는 쪽을 권장한다.

원천 데이터를 Neo4j에 병합 적재한다. 운영 DB에서는 기본적으로 `--reset`을 붙이지 않는다.

```bash
docker compose --env-file .env run --rm streamlit uv run --frozen python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data
```

`--reset`은 분리된 개발 DB나 발표 검증용 `compose.design-test.yaml` 스택에서만 사용한다.

이미 Neo4j와 Streamlit을 띄운 뒤 GPU가 있는 서버에서 vLLM만 추가로 띄우려면 다음을 사용한다.

```bash
docker compose --env-file .env --profile gpu up -d vllm
```

vLLM 설정은 서버에서 확인된 값에 맞춰져 있다.

```text
image: vllm/vllm-openai:latest
model: google/gemma-4-E4B-it
port: 8000
dtype: bfloat16
max_model_len: 4096
gpu_memory_utilization: 0.9
```

vLLM 컨테이너는 Compose에서 OpenAI 호환 API를 제공하는 용도다. GPU 메모리와 모델 권한은 서버 환경에 따라 달라지므로, 외부 vLLM을 이미 운영 중이면 `VLLM_URL`만 그 주소로 맞추고 Streamlit/Neo4j 스택과 분리해도 된다.

## 검증 명령

Compose 파일을 검증한다.

```bash
docker compose config
```

앱 컨테이너 로그를 확인한다.

```bash
docker compose logs -f streamlit
```

Neo4j chunk 적재 상태를 확인한다.

```bash
docker compose exec neo4j cypher-shell -u neo4j -p admin2026 "MATCH (n:NPC) OPTIONAL MATCH (n)-[:KNOWS]->(k:KnowledgeChunk) RETURN n.npc_id AS npc, n.name AS name, count(k) AS chunks ORDER BY npc"
```

placeholder clue가 없어야 한다.

```bash
docker compose exec neo4j cypher-shell -u neo4j -p admin2026 "MATCH (c:Clue) WHERE c.name IS NULL RETURN c.clue_id AS placeholder_clue ORDER BY placeholder_clue"
```

Streamlit은 기본적으로 서버 내부 또는 SSH 터널에서 `http://localhost:8501`로 확인한다. multipage 앱의 관리자 화면은 `http://localhost:8501/admin`에서 접근하며, Memory Admin, Quest Admin, Concept Story Admin을 포함한다. vLLM을 외부 서버에서 쓸 경우 `.env`의 `VLLM_URL`과 `MODEL_NAME=google/gemma-4-E4B-it`를 맞춘 뒤 `docker compose --env-file .env up -d streamlit`을 다시 실행한다.

## 산출물 재생성

보강 자료는 기존 `rsc/data/quests/*.yaml`의 `story_expansion`에 통합되어 있다. 서버에서 발표/검증 산출물을 다시 만들 때는 output-local 스크립트가 아니라 프로젝트 레벨 파이프라인을 실행한다.

```bash
uv sync --frozen
python scripts/story_pipeline/run_pipeline.py
```

생성 결과는 `output/reports/`, `output/integrated/`, `output/neo4j_import/` 아래에만 둔다. `output/expanded`, `output/scripts`, `output/requirements.txt`, `output/.env.example`은 운영 구조에서 사용하지 않는다.
