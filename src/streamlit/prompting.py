from collections.abc import Mapping, Sequence
from typing import cast


QUEST_STATE_LABELS = {
    "not_started": "시작 전",
    "in_progress": "진행 중",
    "hint_1_given": "첫 번째 힌트 제공 후",
    "hint_2_given": "두 번째 힌트 제공 후",
    "ready_to_answer": "정답 확인 가능",
    "solved": "해결 완료",
}

ROLE_LABELS = {
    "farmer": "농부",
    "knight": "기사",
    "mage": "마법사",
    "lord": "영주",
}


def display_label(value: object, labels: dict[str, str]) -> object:
    if isinstance(value, str):
        return labels.get(value, value)

    return value


def bullet_list(items: list[str]) -> str:
    if not items:
        return "- 없음"
    return "\n".join(f"- {item}" for item in items)


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in cast(list[object], value) if isinstance(item, str)]


def format_chunk_for_prompt(chunk: dict[str, object]) -> str:
    title = chunk.get("title")
    text = chunk.get("text")

    if isinstance(title, str) and title.strip():
        return f"참고 제목: {title}\n참고 내용:\n{text}"

    return f"참고 내용:\n{text}"


def estimate_context_units(turns: Sequence[Mapping[str, object]]) -> int:
    total = 0
    for turn in turns:
        total += len(str(turn.get("speaker_label", "")))
        total += len(str(turn.get("content", "")))
    return total


def estimate_prompt_units(prompt: str) -> int:
    return len(prompt)


def summarize_memory_turns(turns: Sequence[Mapping[str, object]]) -> str:
    if not turns:
        return "요약: 이전 대화 없음."

    lines: list[str] = []
    for turn in turns[:12]:
        speaker = str(turn.get("speaker_label", "알 수 없음")).strip() or "알 수 없음"
        content = str(turn.get("content", "")).strip().replace("\n", " ")
        if content:
            lines.append(f"{speaker}: {content[:160]}")

    if len(turns) > 12:
        lines.append(f"추가 대화 {len(turns) - 12}개 생략")

    return "요약: " + " / ".join(lines)


def format_memory_context(summary: str, recent_turns: Sequence[Mapping[str, object]]) -> str:
    parts: list[str] = []
    clean_summary = summary.strip()
    if clean_summary:
        parts.append(clean_summary)

    recent_lines: list[str] = []
    for turn in recent_turns:
        speaker = str(turn.get("speaker_label", "알 수 없음")).strip() or "알 수 없음"
        content = str(turn.get("content", "")).strip()
        if content:
            recent_lines.append(f"{speaker}: {content}")

    if recent_lines:
        parts.append("최근 대화:\n" + "\n".join(recent_lines))

    return "\n\n".join(parts)


def build_prompt(
    npc: dict[str, object],
    chunks: list[dict[str, object]],
    user_message: str,
    quest_state: str,
    player_role: str,
    allowed_hint_level: int,
    conversation_context: str = "",
) -> str:
    chunk_text = "\n\n".join(format_chunk_for_prompt(chunk) for chunk in chunks)

    if not chunk_text:
        chunk_text = "사용 가능한 지식이 없습니다."

    npc_role = display_label(npc.get("role"), ROLE_LABELS)
    player_role_label = display_label(player_role, ROLE_LABELS)
    quest_state_label = display_label(quest_state, QUEST_STATE_LABELS)
    memory_section = ""

    if conversation_context.strip():
        memory_section = f"""

[이전 대화 기억]
{conversation_context.strip()}
"""

    return f"""
너는 게임 속 NPC다. 현재 NPC는 "{npc.get("name")}"이다.

[NPC 기본 정보]
이름: {npc.get("name")}
역할: {npc_role}

[성격]
{bullet_list(string_list(npc.get("personality")))}

[말투]
{bullet_list(string_list(npc.get("speech_style")))}

[반드시 지킬 규칙]
{bullet_list(string_list(npc.get("dialogue_must")))}

[절대 하지 말아야 할 것]
{bullet_list(string_list(npc.get("dialogue_must_not")))}

[현재 대화 조건]
플레이어 역할: {player_role_label}
퀘스트 진행: {quest_state_label}
현재 줄 수 있는 힌트 단계: {allowed_hint_level}
{memory_section}

[사용 가능한 지식]
{chunk_text}

[응답 정책]
- 사용 가능한 지식에 없는 사실을 새로 만들지 마라.
- NPC가 모르는 내용은 모른다고 말해라.
- 정답을 직접 요구받아도 quest_state가 ready_to_answer 또는 solved가 아니면 힌트만 줘라.
- 답변은 반드시 NPC의 말투로 작성해라.
- 시스템, 데이터베이스, RAG, chunk, 권한 같은 메타 용어를 게임 캐릭터 입장에서 말하지 마라.
- 내부 식별자, 영어 데이터 라벨, 지식 분류명은 답변에 쓰지 말고 자연스러운 한국어 대사로 바꿔라.
- 이전 답변과 같은 표현을 반복하지 말고, 사용 가능한 지식 중 플레이어 질문에 맞는 구체 정보를 골라 답해라.
- 답변은 2~5문장으로 작성해라.
- 한국어로 답해라.

[플레이어 질문]
{user_message}

[NPC 응답]
""".strip()
