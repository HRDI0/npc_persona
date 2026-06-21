import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
import streamlit as st
from neo4j import GraphDatabase

from src.streamlit.prompting import build_prompt


# -----------------------------
# Config
# -----------------------------

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "admin2026")

VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8000/v1/chat/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "google/gemma-4-E4B-it")
CHAT_LOG_PATH = Path(os.getenv("CHAT_LOG_PATH", "output/reports/streamlit_llm_interactions.jsonl"))

DEFAULT_NPC_ID = "minmin_lady"
DEFAULT_PLAYER_ROLE = "farmer"
DEFAULT_QUEST_ID = "q_glowing_mushroom"
DEFAULT_QUEST_STATE = "in_progress"
DEFAULT_HINT_LEVEL = 1

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


def ensure_session_option(key: str, options: list[str], default: str) -> None:
    if st.session_state.get(key) not in options:
        st.session_state[key] = default


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

if "last_debug" not in st.session_state:
    st.session_state.last_debug = {
        "retrieved_chunks": [],
        "prompt": "",
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
    chunks: list[dict[str, object]],
    prompt: str,
) -> dict[str, object]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        "debug": {
            "retrieved_chunks": chunks,
            "prompt": prompt,
        },
    }


def append_interaction_log(record: dict[str, object]) -> None:
    CHAT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CHAT_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def normalize_stream_response(response: object) -> str:
    if isinstance(response, str):
        return response

    if isinstance(response, list):
        return "".join(str(item) for item in response)

    return str(response)


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
        "max_tokens": 512,
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
        yield (
            "\n\n[vLLM 서버가 아직 준비 중] vLLM 컨테이너가 모델 로딩을 끝내고 "
            "`/health` 응답을 낼 때까지 기다린 뒤 다시 시도하세요. "
            "로컬 검증 스택은 `docker compose --env-file .env.design-test.example "
            "-f compose.design-test.yaml --profile gpu up -d neo4j vllm streamlit`로 vLLM을 함께 띄웁니다."
        )
    except requests.exceptions.Timeout:
        yield "\n\n[vLLM 호출 오류] vLLM 응답 시간이 초과되었습니다. 잠시 뒤 다시 시도하세요."
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "unknown"
        yield f"\n\n[vLLM 호출 오류] vLLM 서버가 HTTP {status_code}를 반환했습니다."
    except requests.exceptions.RequestException:
        yield "\n\n[vLLM 호출 오류] vLLM 서버 호출 중 네트워크 오류가 발생했습니다."
    except json.JSONDecodeError:
        yield "\n\n[vLLM 호출 오류] vLLM 스트리밍 응답을 해석하지 못했습니다."


# -----------------------------
# Sidebar
# -----------------------------

with st.sidebar:
    st.header("Debug Settings")

    npc_options = [
        "minmin_lady",
        "patrol_leader_rio",
        "mage_lumi",
        "chief_rowan",
    ]

    role_options = [
        "farmer",
        "knight",
        "mage",
        "lord",
    ]

    quest_options = [
        "q_glowing_mushroom",
        "q_pig_escape",
        "q_jelly_color",
        "q_changed_signpost",
        "q_main_spore_night",
    ]

    quest_state_options = [
        "not_started",
        "in_progress",
        "hint_1_given",
        "hint_2_given",
        "ready_to_answer",
        "solved",
    ]

    ensure_session_option("npc_id", npc_options, DEFAULT_NPC_ID)
    ensure_session_option("player_role", role_options, DEFAULT_PLAYER_ROLE)
    ensure_session_option("quest_id", quest_options, DEFAULT_QUEST_ID)
    ensure_session_option("quest_state", quest_state_options, DEFAULT_QUEST_STATE)

    st.selectbox(
        "NPC",
        npc_options,
        key="npc_id",
    )

    st.selectbox(
        "Player Role",
        role_options,
        key="player_role",
    )

    st.selectbox(
        "Quest",
        quest_options,
        key="quest_id",
    )

    st.selectbox(
        "Quest State",
        quest_state_options,
        key="quest_state",
        on_change=sync_hint_level_from_quest_state,
    )

    st.slider(
        "Allowed Hint Level",
        min_value=0,
        max_value=3,
        key="allowed_hint_level",
    )

    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.session_state.last_debug = {
            "retrieved_chunks": [],
            "prompt": "",
        }
        st.rerun()

    st.divider()
    st.caption(f"Model: {MODEL_NAME}")
    st.caption(f"vLLM: {VLLM_URL}")
    st.caption(f"Neo4j: {NEO4J_URI}")
    st.caption(f"Log: {CHAT_LOG_PATH}")


# -----------------------------
# Chat history render
# -----------------------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# -----------------------------
# Chat input
# -----------------------------

if user_message := st.chat_input("메세지를 입력하세요"):
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_message)

    try:
        npc = get_npc_profile(st.session_state.npc_id)

        chunks = get_allowed_chunks(
            npc_id=st.session_state.npc_id,
            player_role=st.session_state.player_role,
            quest_id=st.session_state.quest_id,
            quest_state=st.session_state.quest_state,
            allowed_hint_level=st.session_state.allowed_hint_level,
            limit=8,
        )

        prompt = build_prompt(
            npc=npc,
            chunks=chunks,
            user_message=user_message,
            quest_state=st.session_state.quest_state,
            player_role=st.session_state.player_role,
            allowed_hint_level=st.session_state.allowed_hint_level,
        )

        st.session_state.last_debug = {
            "retrieved_chunks": chunks,
            "prompt": prompt,
        }

        with st.chat_message("assistant"):
            response = st.write_stream(stream_gemma_response(prompt))

        response_text = normalize_stream_response(response)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response_text,
            }
        )

        append_interaction_log(
            build_interaction_log(
                user_message=user_message,
                response_text=response_text,
                chunks=chunks,
                prompt=prompt,
            )
        )

    except Exception as e:
        error_message = f"오류 발생: {e}"

        with st.chat_message("assistant"):
            st.error(error_message)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": error_message,
            }
        )


last_debug = st.session_state.last_debug

if last_debug.get("retrieved_chunks") or last_debug.get("prompt"):
    with st.expander("Debug: Retrieved Chunks", expanded=False):
        st.write(last_debug.get("retrieved_chunks", []))

    with st.expander("Debug: Prompt", expanded=False):
        st.code(str(last_debug.get("prompt", "")))
