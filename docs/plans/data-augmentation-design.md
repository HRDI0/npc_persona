# 데이터 증강 설계

## 1. 목표

현재 데이터 증강은 헤이즐 마을 GraphRAG MVP의 기존 구조를 유지하면서 실제 대화에 사용할 수 있는 지식 밀도를 늘리는 작업이다. NPC 수와 퀘스트 수는 고정하고, 각 NPC가 자기 권한과 지식 범위 안에서만 말하도록 `allowed_roles`, `hint_level`, `answer_sensitive`, `answer_reveal_policy`를 함께 관리한다.

## 2. 고정 범위

| 항목 | 유지 기준 |
|---|---|
| NPC | 기존 4명만 사용: `minmin_lady`, `patrol_leader_rio`, `mage_lumi`, `chief_rowan` |
| 퀘스트 | 기존 5개만 사용: `q_glowing_mushroom`, `q_pig_escape`, `q_jelly_color`, `q_changed_signpost`, `q_main_spore_night` |
| 신규 대형 구조 | 신규 NPC, 신규 퀘스트, 대량 지역/오브젝트/생물 디렉터리, JSONL 평가셋, vector DB 확장 금지 |
| 원천 위치 | 사람이 수정하는 원천은 `rsc/data`이며, `output/`은 생성 산출물로 유지 |

데이터량은 늘릴 수 있다. 다만 늘어나는 데이터는 기존 NPC 또는 기존 퀘스트에 귀속되어야 하며, 새 NPC나 새 퀘스트를 만들기 위한 우회 수단으로 사용하면 안 된다.

## 3. 파일별 역할

| 위치 | 증강 가능 내용 | 금지 내용 |
|---|---|---|
| `rsc/data/npcs/*.md` | 개인사, 말투, 직접 관찰, 제한된 지식, NPC별 `KnowledgeChunk` | 전체 스토리, 퀘스트 전개 전체, NPC가 모르는 최종 진실 |
| `rsc/data/quests/*.yaml` | `story_expansion`, 진행 단계, 오답 가설, 힌트 흐름, 공개 정책 | NPC 개인사, 새 퀘스트 ID, reveal 전 최종 truth 공개 |
| `rsc/data/world/*.yaml` | 기존 clue/truth/event/role 정책 설명 보강 | 세계관 대형 확장, 새 대형 사건, 반전/악역 추가 |

## 4. NPC 권한 설계

| NPC | 허용 지식 | 금지 지식 | 안전한 hint 단계 |
|---|---|---|---|
| 민민 부인 | 농장 생활, 냄새, 가축 움직임, 직접 본 숲 입구 변화, 주민 소문 | 마나 원리, 촌장 기밀, 최종 원인, 확정 범인 | `hint_level: 0-1`, `answer_sensitive: false` |
| 순찰대장 리오 | 발자국, 울타리, 표지판, 뿌리 자국, 방향성, 안전 수칙 | 마법 원리, 최종 원인, 로완의 종합 판단 | `hint_level: 0-2`, `answer_sensitive: false` |
| 마도사 루미 | 포자 후보, 마나 반응 가능성, 방울젤리 변화, 실험 가설 | 촌장 비공개 판단, 최종 truth 단정, 표지판 확정 범인 | `hint_level: 0-2`, `answer_sensitive: false` |
| 헤이즐 촌장 로완 | 보고 종합, 기록 비교, 단서 충분 시 최종 추론 검토 | 단서 부족 상태에서 결론 공개 | 일반 보고는 `hint_level: 2`, 최종 종합은 `hint_level: 3`, `answer_sensitive: true` |

## 5. 이번 증강 방식

이번 증강은 다음 두 축으로 제한한다.

1. 기존 NPC 4명에게 각각 1개씩 `KnowledgeChunk`를 추가한다.
2. 기존 퀘스트 5개의 `story_expansion`에 `access_control_notes`를 추가해 역할, 힌트 단계, 공개 금지 기준을 문서화한다.

새로 추가하는 chunk는 모두 기존 NPC와 기존 퀘스트에 연결한다. 새 NPC ID와 새 퀘스트 ID는 만들지 않는다. 새 clue/truth ID도 기본적으로 만들지 않고, 기존 clue/truth 관계를 더 촘촘하게 설명한다.

## 6. MapleStory 참고 원칙

MapleStory Wiki와 공식 자료는 구조와 분위기 참고로만 사용한다.

허용되는 참고 방식은 다음과 같다.

- 초보 마을처럼 따뜻하고 읽기 쉬운 분위기
- 작은 심부름, 이웃 걱정, 생활형 문제
- `Available`, `In Progress`, `Completed`처럼 명확한 퀘스트 상태 감각
- 버섯, 돼지, 젤리형 생물처럼 아기자기한 소재를 일반 명사 수준에서만 활용

금지되는 참고 방식은 다음과 같다.

- Henesys, Victoria Island, Maple World 같은 고유 지역 수입
- Maya, Camila, Chief Stan 등 MapleStory NPC 수입
- Orange Mushroom, Ribbon Pig 등 고유 몬스터명 수입
- 원문 대사, 퀘스트 문장, 고유 사건, 대형 세계관 conflict 복제

## 7. 최종 보고서 요구사항

실제 증강이 끝나면 `docs/DATA_AUGMENTATION_REPORT.md`를 작성한다. 이 보고서는 사용자가 어떤 데이터가 실제로 추가되었는지 확인할 수 있어야 한다.

보고서에는 반드시 다음 항목을 포함한다.

| 항목 | 내용 |
|---|---|
| 추가 파일/수정 파일 | 실제 변경된 `rsc/data` 파일 경로 |
| 추가 chunk 목록 | `chunk_id`, NPC, quest, clue, `allowed_roles`, `hint_level`, `answer_sensitive` |
| 퀘스트 보강 목록 | 각 quest의 `access_control_notes` 추가 내용 |
| 권한 검증 | NPC별 새로 말할 수 있는 정보와 여전히 말하면 안 되는 정보 |
| 테스트 결과 | story source, output pipeline, 전체 테스트 결과 |

## 8. 검증 기준

증강 후 다음 조건을 만족해야 한다.

- NPC 수는 4명이다.
- 퀘스트 수는 5개다.
- 새 NPC ID와 새 퀘스트 ID가 없다.
- 새 chunk는 필수 metadata를 모두 가진다.
- `answer_sensitive: true` chunk는 `hint_level: 3`을 유지한다.
- 민민, 리오, 루미의 대화 예시는 forbidden truth ID나 truth 이름을 직접 말하지 않는다.
- `python -m unittest tests.test_story_source_contract -v`가 통과한다.
- `python -m unittest tests.test_output_pipeline_contract -v`가 통과한다.
- 가능하면 `python -m unittest discover -v`까지 통과한다.
