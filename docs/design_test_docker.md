# 헤이즐 설계 검증용 분리 Docker 구성

이 문서는 발표용 상세 시각화 문서와 화면 캡처를 Windows Docker Desktop에서 검증하고, 나중에 Ubuntu 운영 서버의 기존 Neo4j/vLLM 컨테이너와 충돌하지 않도록 별도 테스트 스택을 실행하는 방법을 설명한다.

## 목적

운영 서버에는 이미 기존 Neo4j/vLLM 컨테이너가 있을 수 있으므로, 설계 검증용 컨테이너는 `compose.design-test.yaml`로 분리한다. 이 스택은 별도 Compose project name, 별도 host port, 별도 Neo4j volume을 사용한다.

```text
기본 운영/개발 compose.yaml
  streamlit: 127.0.0.1:8501
  neo4j: 127.0.0.1:7474, 127.0.0.1:7687
  vllm: 127.0.0.1:8000

설계 검증 compose.design-test.yaml
  streamlit: 127.0.0.1:18501
  neo4j: 127.0.0.1:17474, 127.0.0.1:17687
  vllm: 127.0.0.1:18000
```

## 모델 다운로드

프로젝트 폴더 아래에 모델을 내려받는다.

```powershell
Copy-Item .env.design-test.example .env.design-test
$env:VLLM_MODEL="google/gemma-4-E4B-it"
$env:LOCAL_MODEL_DIR="./models/google-gemma-4-E4B-it"
$env:VLLM_GPU_MEMORY_UTILIZATION="0.9"
$env:VLLM_MAX_MODEL_LEN="4096"
.\scripts\download_model.ps1
```

접근 권한이 필요한 경우 같은 PowerShell 세션에 `HF_TOKEN`을 먼저 설정한다.

```powershell
$env:HF_TOKEN="hf_..."
.\scripts\download_model.ps1
```

다운로드 결과는 `models/google-gemma-4-E4B-it`에 둔다. `models/`는 git과 Docker build context에서 제외한다.

## Windows Docker Desktop 설계 검증 실행

```powershell
docker compose --env-file .env.design-test -f compose.design-test.yaml config
docker compose --env-file .env.design-test -f compose.design-test.yaml up -d neo4j streamlit
docker compose --env-file .env.design-test -f compose.design-test.yaml run --rm streamlit uv run --frozen python src/db_control/import_story_source_to_neo4j.py --source-dir rsc/data --reset
```

GPU와 로컬 모델 디렉터리가 준비된 경우 vLLM까지 함께 실행한다.

```powershell
docker compose --env-file .env.design-test -f compose.design-test.yaml --profile gpu up -d neo4j vllm streamlit
```

검증 URL은 다음과 같다.

```text
Streamlit: http://localhost:18501
Neo4j Browser: http://localhost:17474
vLLM API: http://localhost:18000/v1/models
```

## Ubuntu 운영 서버 적용 방식

운영 서버에 기존 Neo4j/vLLM 컨테이너가 이미 있으면 `compose.design-test.yaml`를 운영 스택으로 쓰지 않는다. 운영에서는 기존 컨테이너 주소에 맞춰 Streamlit의 `NEO4J_URI`, `VLLM_URL`, `MODEL_NAME=google/gemma-4-E4B-it`만 맞춘다.

분리 검증이 필요할 때만 `compose.design-test.yaml`를 실행한다. host port가 다르기 때문에 기존 Neo4j/vLLM 컨테이너와 동시에 떠 있어도 충돌하지 않는다.
모든 host port는 `127.0.0.1`에 바인딩되어 Windows Docker Desktop 로컬 검증용으로만 열린다.

## 정리

```powershell
docker compose --env-file .env.design-test -f compose.design-test.yaml --profile gpu down
```

Neo4j 검증 데이터를 완전히 삭제하려면 별도 volume을 제거한다.

```powershell
docker volume rm hazel_design_test_hazel_design_test_neo4j_data
```
