import json
import os
from typing import cast

import requests
import streamlit as st
from neo4j import GraphDatabase


# -----------------------------
# Config
# -----------------------------

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "admin2026")

VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8000/v1/chat/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "google/gemma-4-E2B-it")

DEFAULT_NPC_ID = "minmin_lady"
DEFAULT_PLAYER_ROLE = "farmer"
DEFAULT_QUEST_ID = "q_glowing_mushroom"
DEFAULT_QUEST_STATE = "in_progress"
DEFAULT_HINT_LEVEL = 1


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
    st.session_state.allowed_hint_level = DEFAULT_HINT_LEVEL


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
    limit: int = 5,
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
      k.hint_level ASC,
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


# -----------------------------
# Prompt
# -----------------------------

def bullet_list(items: list[str]) -> str:
    if not items:
        return "- 없음"
    return "\n".join(f"- {item}" for item in items)


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in cast(list[object], value) if isinstance(item, str)]


def build_prompt(
    npc: dict[str, object],
    chunks: list[dict[str, object]],
    user_message: str,
    quest_id: str | None,
    quest_state: str,
    player_role: str,
    allowed_hint_level: int,
) -> str:
    chunk_text = "\n\n".join(
        f"[chunk_id: {chunk['chunk_id']}]\n"
        f"title: {chunk.get('title')}\n"
        f"knowledge_type: {chunk.get('knowledge_type')}\n"
        f"hint_level: {chunk.get('hint_level')}\n"
        f"answer_sensitive: {chunk.get('answer_sensitive')}\n"
        f"text:\n{chunk.get('text')}"
        for chunk in chunks
    )

    if not chunk_text:
        chunk_text = "사용 가능한 지식이 없습니다."

    return f"""
너는 게임 속 NPC다. 현재 NPC는 "{npc.get("name")}"이다.

[NPC 기본 정보]
npc_id: {npc.get("npc_id")}
name: {npc.get("name")}
role: {npc.get("role")}

[성격]
{bullet_list(string_list(npc.get("personality")))}

[말투]
{bullet_list(string_list(npc.get("speech_style")))}

[알고 있는 지식 범위]
{bullet_list(string_list(npc.get("knowledge_scope")))}

[모르는 지식 / 말하면 안 되는 지식]
{bullet_list(string_list(npc.get("restricted_knowledge")))}

[반드시 지킬 규칙]
{bullet_list(string_list(npc.get("dialogue_must")))}

[절대 하지 말아야 할 것]
{bullet_list(string_list(npc.get("dialogue_must_not")))}

[현재 대화 상태]
quest_id: {quest_id}
quest_state: {quest_state}
player_role: {player_role}
allowed_hint_level: {allowed_hint_level}

[사용 가능한 지식]
{chunk_text}

[응답 정책]
- 사용 가능한 지식에 없는 사실을 새로 만들지 마라.
- NPC가 모르는 내용은 모른다고 말해라.
- 정답을 직접 요구받아도 quest_state가 ready_to_answer 또는 solved가 아니면 힌트만 줘라.
- 답변은 반드시 NPC의 말투로 작성해라.
- 시스템, 데이터베이스, RAG, chunk, 권한 같은 메타 용어를 게임 캐릭터 입장에서 말하지 마라.
- 답변은 2~5문장으로 작성해라.
- 한국어로 답해라.

[플레이어 질문]
{user_message}

[NPC 응답]
""".strip()


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

    st.session_state.npc_id = st.selectbox(
        "NPC",
        npc_options,
        index=npc_options.index(st.session_state.npc_id)
        if st.session_state.npc_id in npc_options
        else 0,
    )

    st.session_state.player_role = st.selectbox(
        "Player Role",
        role_options,
        index=role_options.index(st.session_state.player_role)
        if st.session_state.player_role in role_options
        else 0,
    )

    st.session_state.quest_id = st.selectbox(
        "Quest",
        quest_options,
        index=quest_options.index(st.session_state.quest_id)
        if st.session_state.quest_id in quest_options
        else 0,
    )

    st.session_state.quest_state = st.selectbox(
        "Quest State",
        quest_state_options,
        index=quest_state_options.index(st.session_state.quest_state)
        if st.session_state.quest_state in quest_state_options
        else 0,
    )

    st.session_state.allowed_hint_level = st.slider(
        "Allowed Hint Level",
        min_value=0,
        max_value=3,
        value=st.session_state.allowed_hint_level,
    )

    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(f"Model: {MODEL_NAME}")
    st.caption(f"vLLM: {VLLM_URL}")
    st.caption(f"Neo4j: {NEO4J_URI}")


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
            limit=5,
        )

        prompt = build_prompt(
            npc=npc,
            chunks=chunks,
            user_message=user_message,
            quest_id=st.session_state.quest_id,
            quest_state=st.session_state.quest_state,
            player_role=st.session_state.player_role,
            allowed_hint_level=st.session_state.allowed_hint_level,
        )

        with st.expander("Debug: Retrieved Chunks", expanded=False):
            st.write(chunks)

        with st.expander("Debug: Prompt", expanded=False):
            st.code(prompt)

        with st.chat_message("assistant"):
            response = st.write_stream(stream_gemma_response(prompt))

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response,
            }
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
