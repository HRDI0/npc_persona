# 문서 지도

이 디렉터리는 헤이즐 GraphRAG MVP의 설계, 운영, 발표, 확장 문서를 모아 둔다. 문서를 줄여서 맥락을 잃기보다, 이 지도를 기준으로 어느 문서가 기준인지 빠르게 찾는 방식을 권장한다.

## 목적별 기준 문서

| 목적 | 기준 문서 | 읽는 때 |
| --- | --- | --- |
| 온보딩과 인수인계 | [PROJECT_HANDOFF_REPORT.md](PROJECT_HANDOFF_REPORT.md) | 저장소 구조, 원천 데이터 원칙, 다음 작업 맥락을 빠르게 파악할 때 |
| 전체 아키텍처 | [system_architecture.md](system_architecture.md) | Streamlit, Neo4j, importer, Docker Compose 흐름을 깊게 이해할 때 |
| DB 스키마와 검증 쿼리 | [db_design.md](db_design.md) | 현재 Neo4j label, 관계, KnowledgeChunk 조회 조건을 확인할 때 |
| 배포와 운영 실행 | [deployment.md](deployment.md) | Windows 개발 환경, Ubuntu 서버, Compose 실행 절차를 볼 때 |
| 설계 테스트 Docker | [design_test_docker.md](design_test_docker.md) | 발표나 검증용 분리 Docker 스택을 띄울 때 |
| Neo4j 원천 import | [neo4j_story_import_guide.md](neo4j_story_import_guide.md) | `rsc/data`를 Neo4j 그래프로 적재하는 세부 절차가 필요할 때 |
| 그래프 구조 시각 설명 | [NEO4J_GRAPH_STRUCTURE_VISUAL_GUIDE.md](NEO4J_GRAPH_STRUCTURE_VISUAL_GUIDE.md) | Neo4j 구조를 그림 중심으로 설명하거나 리뷰할 때 |
| 스토리 원천 분류 | [story_source_classification.md](story_source_classification.md) | 원천 자료를 NPC, 퀘스트, 세계관 데이터로 나누는 기준을 볼 때 |
| 데이터 증강 결과 | [DATA_AUGMENTATION_REPORT.md](DATA_AUGMENTATION_REPORT.md) | KnowledgeChunk 26개로 늘어난 내역과 검증 기준을 확인할 때 |
| 발표 deck | [presentation/index.html](presentation/index.html) | 발표용 HTML deck 근거와 실제 캡처 흐름을 맞출 때 |
| NPC 확장 가이드 | [MVP_NPC_EXPANSION_GUIDE.md](MVP_NPC_EXPANSION_GUIDE.md) | 새 NPC와 chunk를 추가하거나 legacy 설계 맥락을 확인할 때 |
| 학습 커리큘럼 | [.study/README.md](.study/README.md) | 현재 MVP부터 운영 practice extension까지 순서대로 공부할 때 |
| 계획 문서 | [plans/](plans/) | 아직 구현 전이거나 설계 중인 작업의 의도와 범위를 확인할 때 |

## 깊은 문서를 유지하는 기준

`system_architecture.md`, `MVP_NPC_EXPANSION_GUIDE.md`, 각종 report 문서는 짧게 압축하지 않는다. 이 문서들은 문제 발생 시 원인 추적에 필요한 상세 맥락, 예시, 검증 기준을 담고 있다. 중복된 길 안내만 이 문서 지도로 모으고, 깊은 설명은 원래 문서에 남긴다.

## 문서 중복 정리 기준

전체 명령 블록을 모든 문서에 반복해서 복사하지 않는다. 운영 명령은 [deployment.md](deployment.md), 원천 import 명령은 [neo4j_story_import_guide.md](neo4j_story_import_guide.md)와 [db_design.md](db_design.md)를 우선 기준으로 삼는다. 다른 문서에서는 필요한 맥락만 짧게 설명하고 기준 문서로 연결한다.

## 비공개 작업 노트 기준

개인 작업 노트는 공개 문서 지도에서 제외한다. Affine용 주간 기록은 개인 고민과 확인 과정을 남기는 공간이므로, 이 공개 문서 지도에서는 직접 연결하지 않는다.
