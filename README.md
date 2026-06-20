# persona_chat GraphRAG MVP

헤이즐 마을 NPC 4명과 퀘스트 5개를 Neo4j 그래프로 적재하고, Streamlit에서 현재 역할, 퀘스트 상태, 힌트 레벨에 맞는 `KnowledgeChunk`만 vLLM 프롬프트로 전달하는 GraphRAG MVP입니다.

## 구조

```text
rsc/data/                         원천 데이터
  npcs/*.md                       NPC 프로필과 story chunk
  quests/*.yaml                   퀘스트와 story_expansion
  world/*.yaml                    역할, 사건, 단서, 진실
scripts/story_pipeline/           산출물 생성 파이프라인
src/db_control/import_story_source_to_neo4j.py
src/streamlit/test_app.py
output/reports/                   생성 리포트
output/integrated/                생성 통합 YAML/JSON
output/neo4j_import/              생성 Neo4j CSV/Cypher
docs/presentation/                발표용 HTML deck
```

보강 자료는 별도 `output/expanded` 폴더가 아니라 기존 `rsc/data/quests/*.yaml`의 `story_expansion`에 통합합니다. `output/`은 재생성 가능한 보고서와 Neo4j import 산출물만 둡니다.

## 로컬 산출물 생성

```bash
uv sync --frozen
python scripts/story_pipeline/run_pipeline.py
```

이 명령은 `rsc/data` 원천 자료를 읽어 `output/integrated/`의 YAML/JSON과 `output/neo4j_import/`의 CSV/Cypher 파일을 다시 만듭니다. Neo4j에 바로 병합 적재하려면 같은 파이프라인에 `--load-neo4j`를 붙입니다.

```bash
python scripts/story_pipeline/run_pipeline.py --load-neo4j
```

이미 생성된 CSV를 Neo4j 개발 DB에 병합 적재하려면 다음 명령을 사용합니다.

```bash
python scripts/story_pipeline/load_neo4j.py
```

원천 Markdown/YAML을 그대로 읽어 `NPC`, `Quest`, `Clue`, `Truth`, `Location`, `Event`, `KnowledgeChunk` 그래프로 적재하려면 다음 명령을 사용합니다. 이 경로는 `rsc/data/npcs/*.md`의 frontmatter와 story chunk 본문을 `KnowledgeChunk` 노드로 넣기 때문에, NPC 대화와 지식 조각을 바로 GraphRAG 검색 대상으로 쓰고 싶을 때 적합합니다.

```bash
python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data
```

Neo4j 접속 값은 실제 비밀을 커밋하지 말고 `.env` 또는 시스템 환경변수에 둡니다.

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
NEO4J_DATABASE=neo4j
```

원천 importer는 `--source-dir`, `--reset`, `--dry-run`, `--database`, `--report-path`를 지원합니다. 먼저 DB 접속 없이 원천 검증과 리포트 생성을 확인하려면 다음 명령을 사용합니다.

```bash
python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data --dry-run --database neo4j
```

기본 리포트 경로는 `output/reports/neo4j_story_source_import_report.md`입니다. 자세한 적재 절차와 코드 설명은 `docs/neo4j_story_import_guide.md`에 정리했습니다.

개발 DB 전체 재생성은 명시적으로 승인된 경우에만 실행합니다.

```bash
python scripts/story_pipeline/reset_neo4j_dev.py
```

## Ubuntu Docker 운영

서버에서는 `main`을 가져온 뒤 `.env.example`을 복사하고, 실제 비밀번호와 vLLM 주소를 추적되지 않는 `.env`에만 둡니다.

```bash
git fetch origin
git switch main
git pull --ff-only origin main

cp .env.example .env
nano .env
```

`.env`에서 최소한 다음 값을 서버 환경에 맞게 확인합니다.

```bash
NEO4J_PASSWORD=<your-password>
NEO4J_DATABASE=neo4j
MODEL_NAME=google/gemma-4-E2B-it
CHAT_LOG_PATH=output/reports/streamlit_llm_interactions.jsonl
```

Streamlit은 대화 선택값, 사용자 입력, 모델 출력, 조회 chunk, 최종 프롬프트를 JSONL로 남깁니다. `CHAT_LOG_PATH`를 바꾸지 않으면 기본 경로는 `output/reports/streamlit_llm_interactions.jsonl`입니다.

외부 vLLM 서버를 쓰면 `VLLM_URL`을 해당 서버에서 접근 가능한 주소로 바꿉니다. 같은 Compose 프로젝트에서 GPU vLLM까지 띄우는 서버라면 기본값 `http://vllm:8000/v1/chat/completions`를 그대로 둡니다.

```bash
VLLM_URL=http://<vllm-host>:8000/v1/chat/completions
```

외부 vLLM을 쓰거나 Neo4j와 Streamlit만 먼저 띄울 때는 다음 명령을 사용합니다.

```bash
docker compose --env-file .env build streamlit
docker compose --env-file .env up -d neo4j streamlit
```

같은 Compose 프로젝트에서 GPU vLLM까지 함께 띄우는 서버에서는 다음 명령을 사용합니다.

```bash
docker compose --env-file .env --profile gpu up -d neo4j vllm streamlit
```

원천 데이터 적재는 운영 DB 상태를 확인한 뒤 `--reset` 없이 병합 방식으로 실행합니다.

```bash
docker compose --env-file .env run --rm streamlit uv run --frozen python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data
```

구동 상태는 다음처럼 확인합니다.

```bash
docker compose --env-file .env ps
curl http://127.0.0.1:8501/_stcore/health
docker compose --env-file .env logs -f streamlit
```

기본 `compose.yaml`은 Streamlit, Neo4j, vLLM 포트를 모두 `127.0.0.1`에만 바인딩합니다. 서버 내부에서는 `http://127.0.0.1:8501`로 확인할 수 있지만, 외부 브라우저에서 바로 `http://<server-ip>:8501`로 접속되지는 않습니다.

외부 접속은 reverse proxy 또는 SSH 터널을 권장합니다. 임시 확인은 로컬 PC에서 다음처럼 터널을 열고 브라우저에서 `http://127.0.0.1:8501`로 접속합니다.

```bash
ssh -L 8501:127.0.0.1:8501 <user>@<server-ip>
```

포트를 직접 공개해야 한다면 `compose.yaml`의 Streamlit 포트만 다음처럼 바꾼 뒤 컨테이너를 다시 올리고, 서버 방화벽이나 클라우드 보안 그룹에서 TCP `8501`을 엽니다. Neo4j 포트 `7474`, `7687`은 외부 공개하지 않는 쪽을 권장합니다.

```yaml
ports:
  - "0.0.0.0:8501:8501"
```

```bash
docker compose --env-file .env up -d streamlit
```

## 발표 자료

HTML deck은 `docs/presentation/index.html`입니다. Streamlit 질문 테스트 캡처는 `docs/presentation/assets/` 아래에 있고, Neo4j 적재/조회 근거와 코드 스니펫은 deck 안에서 함께 설명합니다.
