# pyright: reportAny=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false
import json
import os
import time
from pathlib import Path

import requests
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from neo4j import GraphDatabase

from src.streamlit.prompting import (
    build_prompt,
    estimate_prompt_units,
    format_memory_context,
    summarize_memory_turns,
)


# -----------------------------
# Config
# -----------------------------

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "admin2026")

VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8000/v1/chat/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "google/gemma-4-E4B-it")
CHAT_LOG_PATH = Path(os.getenv("CHAT_LOG_PATH", "output/reports/streamlit_llm_interactions.jsonl"))
MEMORY_LOG_PATH = Path(os.getenv("MEMORY_LOG_PATH", "output/reports/streamlit_memory_events.jsonl"))
ADMIN_LOG_PATH = Path(os.getenv("ADMIN_LOG_PATH", "output/reports/streamlit_admin_events.jsonl"))
LOG_PATHS = {
    "chat": Path(os.getenv("CHAT_LOG_PATH", "output/reports/streamlit_llm_interactions.jsonl")),
    "retrieval": Path(os.getenv("RETRIEVAL_LOG_PATH", "output/reports/streamlit_retrieval_events.jsonl")),
    "prompt": Path(os.getenv("PROMPT_LOG_PATH", "output/reports/streamlit_prompt_events.jsonl")),
    "memory": Path(os.getenv("MEMORY_LOG_PATH", "output/reports/streamlit_memory_events.jsonl")),
    "admin": Path(os.getenv("ADMIN_LOG_PATH", "output/reports/streamlit_admin_events.jsonl")),
    "neo4j_import": Path(os.getenv("NEO4J_IMPORT_LOG_PATH", "output/reports/streamlit_neo4j_import_events.jsonl")),
}

DEFAULT_NPC_ID = "minmin_lady"
DEFAULT_PLAYER_ROLE = "farmer"
DEFAULT_QUEST_ID = "q_glowing_mushroom"
DEFAULT_QUEST_STATE = "in_progress"
DEFAULT_HINT_LEVEL = 1
DEFAULT_MAX_MEMORY_COUNT = 40
MAX_CONTEXT_TOKENS = 4096
VLLM_MAX_RESPONSE_TOKENS = 512
MAX_PROMPT_CONTEXT_UNITS = MAX_CONTEXT_TOKENS - VLLM_MAX_RESPONSE_TOKENS
MEMORY_COMPACTION_RATIO = 0.9

NPC_METADATA = {
    "minmin_lady": {"player_role": "farmer", "quest_id": "q_glowing_mushroom"},
    "patrol_leader_rio": {"player_role": "knight", "quest_id": "q_pig_escape"},
    "mage_lumi": {"player_role": "mage", "quest_id": "q_jelly_color"},
    "chief_rowan": {"player_role": "lord", "quest_id": "q_main_spore_night"},
}

NPC_NAMES = {
    "minmin_lady": "민민 부인",
    "patrol_leader_rio": "순찰대장 리오",
    "mage_lumi": "마도사 루미",
    "chief_rowan": "헤이즐 촌장 로완",
}

NPC_OPTIONS = [
    "minmin_lady",
    "patrol_leader_rio",
    "mage_lumi",
    "chief_rowan",
]

ROLE_OPTIONS = [
    "farmer",
    "knight",
    "mage",
    "lord",
]

QUEST_OPTIONS = [
    "q_glowing_mushroom",
    "q_pig_escape",
    "q_jelly_color",
    "q_changed_signpost",
    "q_main_spore_night",
]

QUEST_STATE_OPTIONS = [
    "not_started",
    "in_progress",
    "hint_1_given",
    "hint_2_given",
    "ready_to_answer",
    "solved",
]

QUEST_STATE_HINT_LEVELS = {
    "not_started": 0,
    "in_progress": 1,
    "hint_1_given": 1,
    "hint_2_given": 2,
    "ready_to_answer": 3,
    "solved": 3,
}

def hint_level_for_quest_state(quest_state: str) -> int:
    return QUEST_STATE_HINT_LEVELS.get(quest_state, DEFAULT_HINT_LEVEL)


def sync_hint_level_from_quest_state() -> None:
    st.session_state.allowed_hint_level = hint_level_for_quest_state(
        st.session_state.quest_state,
    )
    persist_quest_state_for_current_quest()


def restore_quest_controls_for_current_quest() -> None:
    quest_id = st.session_state.quest_id
    st.session_state.quest_state = st.session_state.quest_state_by_quest.get(
        quest_id,
        DEFAULT_QUEST_STATE,
    )
    st.session_state.allowed_hint_level = hint_level_for_quest_state(st.session_state.quest_state)
    st.session_state.allowed_hint_level_by_quest[quest_id] = st.session_state.allowed_hint_level


def persist_quest_state_for_current_quest() -> None:
    st.session_state.quest_state_by_quest[st.session_state.quest_id] = st.session_state.quest_state
    st.session_state.allowed_hint_level = hint_level_for_quest_state(st.session_state.quest_state)
    st.session_state.allowed_hint_level_by_quest[st.session_state.quest_id] = st.session_state.allowed_hint_level


def persist_hint_level_for_current_quest() -> None:
    st.session_state.allowed_hint_level = hint_level_for_quest_state(st.session_state.quest_state)
    st.session_state.allowed_hint_level_by_quest[st.session_state.quest_id] = st.session_state.allowed_hint_level


def sync_npc_metadata() -> None:
    previous_npc_id = st.session_state.get("previous_npc_id", DEFAULT_NPC_ID)
    metadata = NPC_METADATA[st.session_state.npc_id]
    st.session_state.player_role = metadata["player_role"]
    st.session_state.quest_id = metadata["quest_id"]
    restore_quest_controls_for_current_quest()
    append_feature_log(
        "admin",
        {
            "event": "npc_changed",
            "previous_npc_id": previous_npc_id,
            "npc_id": st.session_state.npc_id,
        },
    )
    append_feature_log(
        "admin",
        {
            "event": "quest_auto_selected",
            "npc_id": st.session_state.npc_id,
            "quest_id": st.session_state.quest_id,
        },
    )
    append_feature_log(
        "admin",
        {
            "event": "role_changed",
            "npc_id": st.session_state.npc_id,
            "player_role": st.session_state.player_role,
            "source": "npc_auto_sync",
        },
    )
    st.session_state.previous_npc_id = st.session_state.npc_id


def log_player_role_change() -> None:
    append_feature_log(
        "admin",
        {
            "event": "role_changed",
            "npc_id": st.session_state.npc_id,
            "player_role": st.session_state.player_role,
            "source": "manual_select",
        },
    )


def ensure_session_option(key: str, options: list[str], default: str) -> None:
    if st.session_state.get(key) not in options:
        st.session_state[key] = default


def current_timestamp_ms() -> int:
    return int(time.time() * 1000)


def append_feature_log(category: str, record: dict[str, object]) -> None:
    path = LOG_PATHS[category]
    path.parent.mkdir(parents=True, exist_ok=True)
    record_with_timestamp = {"timestamp_ms": current_timestamp_ms(), **record}
    with path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record_with_timestamp, ensure_ascii=False) + "\n")


def build_chat_message(
    role: str,
    content: str,
    person_id: str,
    person_name: str,
    speaker_label: str,
) -> dict[str, str]:
    return {
        "role": role,
        "content": content,
        "person_id": person_id,
        "person_name": person_name,
        "speaker_label": speaker_label,
    }


def get_npc_memory_context(npc_id: str) -> str:
    summary = st.session_state.memory_summary_by_npc.get(npc_id, "")
    recent_turns = st.session_state.memory_by_npc.get(npc_id, [])
    return format_memory_context(summary=summary, recent_turns=recent_turns)


def merge_memory_summary(previous_summary: str, turns: list[dict[str, object]]) -> str:
    new_summary = summarize_memory_turns(turns)
    if not previous_summary:
        return new_summary
    return summarize_memory_turns(
        [
            {"speaker_label": "기존 요약", "content": previous_summary},
            {"speaker_label": "새 요약", "content": new_summary},
        ]
    )


def compact_npc_memory_if_needed(npc_id: str) -> None:
    turns = st.session_state.memory_by_npc.setdefault(npc_id, [])
    max_count = int(
        st.session_state.max_memory_count_by_npc.get(
            npc_id,
            DEFAULT_MAX_MEMORY_COUNT,
        )
    )
    if len(turns) > max_count:
        compacted_turns = turns[:-max_count]
        st.session_state.memory_summary_by_npc[npc_id] = merge_memory_summary(
            st.session_state.memory_summary_by_npc.get(npc_id, ""),
            compacted_turns,
        )
        st.session_state.memory_by_npc[npc_id] = turns[-max_count:]
        append_feature_log(
            "memory",
            {
                "event": "turn_count_compacted",
                "npc_id": npc_id,
                "max_memory_count": max_count,
            },
        )


def compact_npc_memory_for_prompt_if_needed(npc_id: str, prompt: str) -> bool:
    threshold = int(MAX_PROMPT_CONTEXT_UNITS * MEMORY_COMPACTION_RATIO)
    if estimate_prompt_units(prompt) < threshold:
        return False

    turns = st.session_state.memory_by_npc.setdefault(npc_id, [])
    if not turns:
        return False

    st.session_state.memory_summary_by_npc[npc_id] = merge_memory_summary(
        st.session_state.memory_summary_by_npc.get(npc_id, ""),
        turns,
    )
    st.session_state.memory_by_npc[npc_id] = []
    append_feature_log(
        "memory",
        {
            "event": "context_compacted",
            "npc_id": npc_id,
            "threshold": threshold,
            "prompt_units": estimate_prompt_units(prompt),
        },
    )
    return True


def add_npc_memory_turn(npc_id: str, message: dict[str, str]) -> None:
    st.session_state.memory_by_npc.setdefault(npc_id, []).append(message)
    append_feature_log(
        "memory",
        {
            "event": "memory_turn_added",
            "npc_id": npc_id,
            "speaker_label": message.get("speaker_label", ""),
            "content_units": len(message.get("content", "")),
        },
    )
    compact_npc_memory_if_needed(npc_id)


def render_sidebar_diagnostics(container: DeltaGenerator) -> None:
    with container:
        last_debug = st.session_state.last_debug
        with st.popover("Debug: Retrieved Chunks"):
            st.write(last_debug.get("retrieved_chunks", []))

        with st.popover("Debug: Prompt"):
            st.code(str(last_debug.get("prompt", "")))

        with st.popover("Debug: Runtime"):
            st.caption(f"Model: {MODEL_NAME}")
            st.caption(f"vLLM: {VLLM_URL}")
            st.caption(f"Neo4j: {NEO4J_URI}")
            st.caption(f"Log: {CHAT_LOG_PATH}")

        st.divider()
        st.subheader("대화 요약")
        for npc_id in NPC_OPTIONS:
            recent_turns = st.session_state.memory_by_npc.get(npc_id, [])
            summary = st.session_state.memory_summary_by_npc.get(npc_id, "")
            with st.expander(NPC_NAMES.get(npc_id, npc_id), expanded=npc_id == st.session_state.npc_id):
                st.caption(f"최근 대화 {len(recent_turns)}건")
                st.write(summary or "압축 요약 없음")
                st.text_area(
                    "현재 대화 요약",
                    value=summarize_memory_turns(recent_turns),
                    disabled=True,
                    key=f"sidebar_recent_summary_{npc_id}",
                )


# -----------------------------
# Streamlit page
# -----------------------------

st.set_page_config(page_title="persona chat")
st.title("persona_chat")


# -----------------------------
# Session state
# -----------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "npc_id" not in st.session_state:
    st.session_state.npc_id = DEFAULT_NPC_ID

if "previous_npc_id" not in st.session_state:
    st.session_state.previous_npc_id = st.session_state.npc_id

if "player_role" not in st.session_state:
    st.session_state.player_role = DEFAULT_PLAYER_ROLE

if "quest_id" not in st.session_state:
    st.session_state.quest_id = DEFAULT_QUEST_ID

if "quest_state" not in st.session_state:
    st.session_state.quest_state = DEFAULT_QUEST_STATE

if "allowed_hint_level" not in st.session_state:
    st.session_state.allowed_hint_level = hint_level_for_quest_state(
        st.session_state.quest_state,
    )

if "quest_state_by_quest" not in st.session_state:
    st.session_state.quest_state_by_quest = {
        quest_id: DEFAULT_QUEST_STATE for quest_id in QUEST_OPTIONS
    }
    st.session_state.quest_state_by_quest[st.session_state.quest_id] = st.session_state.quest_state

if "allowed_hint_level_by_quest" not in st.session_state:
    st.session_state.allowed_hint_level_by_quest = {
        quest_id: hint_level_for_quest_state(st.session_state.quest_state_by_quest[quest_id])
        for quest_id in QUEST_OPTIONS
    }
    st.session_state.allowed_hint_level_by_quest[st.session_state.quest_id] = st.session_state.allowed_hint_level

if "last_debug" not in st.session_state:
    st.session_state.last_debug = {
        "retrieved_chunks": [],
        "prompt": "",
    }

if "memory_by_npc" not in st.session_state:
    st.session_state.memory_by_npc = {npc_id: [] for npc_id in NPC_OPTIONS}

if "memory_summary_by_npc" not in st.session_state:
    st.session_state.memory_summary_by_npc = {npc_id: "" for npc_id in NPC_OPTIONS}

if "max_memory_count_by_npc" not in st.session_state:
    st.session_state.max_memory_count_by_npc = {
        npc_id: DEFAULT_MAX_MEMORY_COUNT for npc_id in NPC_OPTIONS
    }


# -----------------------------
# Neo4j
# -----------------------------

@st.cache_resource
def get_neo4j_driver():
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )


def get_npc_profile(npc_id: str) -> dict[str, object]:
    query = """
    MATCH (n:NPC {npc_id: $npc_id})
    RETURN
      n.npc_id AS npc_id,
      n.name AS name,
      n.role AS role,
      n.personality AS personality,
      n.speech_style AS speech_style,
      n.knowledge_scope AS knowledge_scope,
      n.restricted_knowledge AS restricted_knowledge,
      n.dialogue_must AS dialogue_must,
      n.dialogue_must_not AS dialogue_must_not
    """

    driver = get_neo4j_driver()
    records, _, _ = driver.execute_query(query, npc_id=npc_id)

    if not records:
        raise ValueError(f"NPC not found: {npc_id}")

    return records[0].data()


def get_allowed_chunks(
    npc_id: str,
    player_role: str,
    quest_id: str | None,
    quest_state: str,
    allowed_hint_level: int,
    limit: int = 8,
) -> list[dict[str, object]]:
    query = """
    MATCH (:NPC {npc_id: $npc_id})-[:KNOWS]->(k:KnowledgeChunk)
    WHERE
      ($quest_id IS NULL OR k.quest_id = $quest_id OR k.quest_id IS NULL)
      AND $player_role IN k.allowed_roles
      AND k.hint_level <= $allowed_hint_level
      AND (k.answer_sensitive = false OR $quest_state IN ["ready_to_answer", "solved"])
    RETURN
      k.chunk_id AS chunk_id,
      k.title AS title,
      k.knowledge_type AS knowledge_type,
      k.quest_id AS quest_id,
      k.hint_level AS hint_level,
      k.answer_sensitive AS answer_sensitive,
      k.text AS text
    ORDER BY
      CASE WHEN k.quest_id = $quest_id THEN 0 ELSE 1 END,
      k.hint_level DESC,
      k.chunk_id ASC
    LIMIT $limit
    """

    driver = get_neo4j_driver()
    records, _, _ = driver.execute_query(
        query,
        npc_id=npc_id,
        player_role=player_role,
        quest_id=quest_id,
        quest_state=quest_state,
        allowed_hint_level=allowed_hint_level,
        limit=limit,
    )

    return [record.data() for record in records]


def build_interaction_log(
    user_message: str,
    response_text: str,
) -> dict[str, object]:
    return {
        "model": MODEL_NAME,
        "vllm_url": VLLM_URL,
        "selection": {
            "npc_id": st.session_state.npc_id,
            "player_role": st.session_state.player_role,
            "quest_id": st.session_state.quest_id,
            "quest_state": st.session_state.quest_state,
            "allowed_hint_level": st.session_state.allowed_hint_level,
        },
        "input": user_message,
        "output": response_text,
    }


def append_interaction_log(record: dict[str, object]) -> None:
    append_feature_log("chat", record)


def normalize_stream_response(response: object) -> str:
    if isinstance(response, str):
        return response

    if isinstance(response, list):
        return "".join(str(item) for item in response)

    return str(response)


class VllmRequestError(Exception):
    def __init__(self, status_code: int | str, response_body: str, display_message: str) -> None:
        super().__init__(f"vLLM HTTP {status_code}")
        self.status_code: int | str = status_code
        self.response_body: str = response_body
        self.display_message: str = display_message


# -----------------------------
# LLM: vLLM OpenAI-compatible streaming
# -----------------------------

def stream_gemma_response(prompt: str):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": VLLM_MAX_RESPONSE_TOKENS,
        "stream": True,
    }

    try:
        with requests.post(
            VLLM_URL,
            json=payload,
            stream=True,
            timeout=180,
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue

                line = line.decode("utf-8")

                if not line.startswith("data: "):
                    continue

                data = line[len("data: "):].strip()

                if data == "[DONE]":
                    break

                obj = json.loads(data)
                delta = obj["choices"][0].get("delta", {})
                content = delta.get("content")

                if content:
                    yield content

    except requests.exceptions.ConnectionError:
        raise VllmRequestError(
            status_code="connection_error",
            response_body="",
            display_message=(
                "[vLLM 서버가 아직 준비 중] vLLM 컨테이너가 모델 로딩을 끝내고 "
                "`/health` 응답을 낼 때까지 기다린 뒤 다시 시도하세요. "
                "로컬 검증 스택은 `docker compose --env-file .env.design-test.example "
                "-f compose.design-test.yaml --profile gpu up -d neo4j vllm streamlit`로 vLLM을 함께 띄웁니다."
            ),
        )
    except requests.exceptions.Timeout:
        raise VllmRequestError(
            status_code="timeout",
            response_body="",
            display_message="[vLLM 호출 오류] vLLM 응답 시간이 초과되었습니다. 잠시 뒤 다시 시도하세요.",
        )
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "unknown"
        response_body = e.response.text if e.response is not None else ""
        raise VllmRequestError(
            status_code=status_code,
            response_body=response_body,
            display_message=f"[vLLM 호출 오류] vLLM 서버가 HTTP {status_code}를 반환했습니다.",
        ) from e
    except requests.exceptions.RequestException:
        raise VllmRequestError(
            status_code="request_error",
            response_body="",
            display_message="[vLLM 호출 오류] vLLM 서버 호출 중 네트워크 오류가 발생했습니다.",
        )
    except json.JSONDecodeError:
        raise VllmRequestError(
            status_code="invalid_stream",
            response_body="",
            display_message="[vLLM 호출 오류] vLLM 스트리밍 응답을 해석하지 못했습니다.",
        )


# -----------------------------
# Sidebar
# -----------------------------

with st.sidebar:
    st.header("Debug Settings")

    ensure_session_option("npc_id", NPC_OPTIONS, DEFAULT_NPC_ID)
    ensure_session_option("player_role", ROLE_OPTIONS, DEFAULT_PLAYER_ROLE)
    ensure_session_option("quest_id", QUEST_OPTIONS, DEFAULT_QUEST_ID)
    ensure_session_option("quest_state", QUEST_STATE_OPTIONS, DEFAULT_QUEST_STATE)

    st.selectbox(
        "NPC",
        NPC_OPTIONS,
        key="npc_id",
        on_change=sync_npc_metadata,
    )
    st.caption(f"인물 태그: {NPC_NAMES.get(st.session_state.npc_id, st.session_state.npc_id)}")

    st.selectbox(
        "Player Role",
        ROLE_OPTIONS,
        key="player_role",
        on_change=log_player_role_change,
    )

    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.session_state.memory_by_npc = {npc_id: [] for npc_id in NPC_OPTIONS}
        st.session_state.memory_summary_by_npc = {npc_id: "" for npc_id in NPC_OPTIONS}
        st.session_state.last_debug = {
            "retrieved_chunks": [],
            "prompt": "",
        }
        append_feature_log(
            "memory",
            {
                "event": "conversation_reset",
                "npc_count": len(NPC_OPTIONS),
            },
        )
        st.rerun()

    sidebar_diagnostics_container = st.container()

# -----------------------------
# Chat history render
# -----------------------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.caption(message.get("speaker_label", message["role"]))
        st.markdown(message["content"])


# -----------------------------
# Chat input
# -----------------------------

if user_message := st.chat_input("메세지를 입력하세요"):
    user_chat_message = build_chat_message(
        role="user",
        content=user_message,
        person_id="player",
        person_name="모험가",
        speaker_label="모험가",
    )
    st.session_state.messages.append(user_chat_message)

    with st.chat_message("user"):
        st.caption("모험가")
        st.markdown(user_message)

    prompt = ""
    try:
        npc = get_npc_profile(st.session_state.npc_id)
        npc_name = str(npc.get("name") or NPC_NAMES.get(st.session_state.npc_id, st.session_state.npc_id))

        chunks = get_allowed_chunks(
            npc_id=st.session_state.npc_id,
            player_role=st.session_state.player_role,
            quest_id=st.session_state.quest_id,
            quest_state=st.session_state.quest_state,
            allowed_hint_level=st.session_state.allowed_hint_level,
            limit=8,
        )
        append_feature_log(
            "retrieval",
            {
                "event": "chunks_retrieved",
                "npc_id": st.session_state.npc_id,
                "quest_id": st.session_state.quest_id,
                "chunk_count": len(chunks),
                "retrieved_chunks": chunks,
            },
        )

        prompt = build_prompt(
            npc=npc,
            chunks=chunks,
            user_message=user_message,
            quest_state=st.session_state.quest_state,
            player_role=st.session_state.player_role,
            allowed_hint_level=st.session_state.allowed_hint_level,
            conversation_context=get_npc_memory_context(st.session_state.npc_id),
        )
        if compact_npc_memory_for_prompt_if_needed(st.session_state.npc_id, prompt):
            prompt = build_prompt(
                npc=npc,
                chunks=chunks,
                user_message=user_message,
                quest_state=st.session_state.quest_state,
                player_role=st.session_state.player_role,
                allowed_hint_level=st.session_state.allowed_hint_level,
                conversation_context=get_npc_memory_context(st.session_state.npc_id),
            )
        append_feature_log(
            "prompt",
            {
                "event": "prompt_built",
                "npc_id": st.session_state.npc_id,
                "quest_id": st.session_state.quest_id,
                "prompt_units": estimate_prompt_units(prompt),
                "prompt": prompt,
            },
        )

        st.session_state.last_debug = {
            "retrieved_chunks": chunks,
            "prompt": prompt,
        }

        with st.chat_message("assistant"):
            st.caption(npc_name)
            response = st.write_stream(stream_gemma_response(prompt))

        response_text = normalize_stream_response(response)
        assistant_chat_message = build_chat_message(
            role="assistant",
            content=response_text,
            person_id=st.session_state.npc_id,
            person_name=npc_name,
            speaker_label=npc_name,
        )
        st.session_state.messages.append(assistant_chat_message)
        add_npc_memory_turn(st.session_state.npc_id, user_chat_message)
        add_npc_memory_turn(st.session_state.npc_id, assistant_chat_message)

        append_interaction_log(
            build_interaction_log(
                user_message=user_message,
                response_text=response_text,
            )
        )

    except VllmRequestError as e:
        append_feature_log(
            "prompt",
            {
                "event": "vllm_http_error",
                "npc_id": st.session_state.npc_id,
                "quest_id": st.session_state.quest_id,
                "status_code": e.status_code,
                "response_body": e.response_body[:2000],
                "prompt_units": estimate_prompt_units(prompt),
            },
        )
        with st.chat_message("assistant"):
            st.error(e.display_message)

    except Exception as e:
        error_message = f"오류 발생: {e}"

        with st.chat_message("assistant"):
            st.error(error_message)

        st.session_state.messages.append(
            build_chat_message(
                role="assistant",
                content=error_message,
                person_id=st.session_state.npc_id,
                person_name=NPC_NAMES.get(st.session_state.npc_id, st.session_state.npc_id),
                speaker_label=NPC_NAMES.get(st.session_state.npc_id, st.session_state.npc_id),
            )
        )

render_sidebar_diagnostics(sidebar_diagnostics_container)
