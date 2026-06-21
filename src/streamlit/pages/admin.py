# pyright: reportAny=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false
import json
import os
import time
from pathlib import Path

import streamlit as st
from neo4j import GraphDatabase


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "admin2026")

ADMIN_LOG_PATH = Path(os.getenv("ADMIN_LOG_PATH", "output/reports/streamlit_admin_events.jsonl"))
MEMORY_LOG_PATH = Path(os.getenv("MEMORY_LOG_PATH", "output/reports/streamlit_memory_events.jsonl"))
NEO4J_IMPORT_LOG_PATH = Path(os.getenv("NEO4J_IMPORT_LOG_PATH", "output/reports/streamlit_neo4j_import_events.jsonl"))

NPC_OPTIONS = [
    "minmin_lady",
    "patrol_leader_rio",
    "mage_lumi",
    "chief_rowan",
]

NPC_NAMES = {
    "minmin_lady": "민민 부인",
    "patrol_leader_rio": "순찰대장 리오",
    "mage_lumi": "마도사 루미",
    "chief_rowan": "헤이즐 촌장 로완",
}

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

DEFAULT_QUEST_STATE = "in_progress"
DEFAULT_MAX_MEMORY_COUNT = 40


def current_timestamp_ms() -> int:
    return int(time.time() * 1000)


def append_jsonl(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record_with_timestamp = {"timestamp_ms": current_timestamp_ms(), **record}
    with path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record_with_timestamp, ensure_ascii=False) + "\n")


def append_feature_log(category: str, record: dict[str, object]) -> None:
    if category == "memory":
        append_jsonl(MEMORY_LOG_PATH, record)
        return
    if category == "neo4j_import":
        append_jsonl(NEO4J_IMPORT_LOG_PATH, record)
        return
    append_jsonl(ADMIN_LOG_PATH, {"category": category, **record})


def hint_level_for_quest_state(quest_state: str) -> int:
    return QUEST_STATE_HINT_LEVELS.get(quest_state, 1)


def ensure_admin_session_state() -> None:
    if "memory_by_npc" not in st.session_state:
        st.session_state.memory_by_npc = {npc_id: [] for npc_id in NPC_OPTIONS}
    if "memory_summary_by_npc" not in st.session_state:
        st.session_state.memory_summary_by_npc = {npc_id: "" for npc_id in NPC_OPTIONS}
    if "max_memory_count_by_npc" not in st.session_state:
        st.session_state.max_memory_count_by_npc = {
            npc_id: DEFAULT_MAX_MEMORY_COUNT for npc_id in NPC_OPTIONS
        }
    if "quest_state_by_quest" not in st.session_state:
        st.session_state.quest_state_by_quest = {
            quest_id: DEFAULT_QUEST_STATE for quest_id in QUEST_OPTIONS
        }
    if "allowed_hint_level_by_quest" not in st.session_state:
        st.session_state.allowed_hint_level_by_quest = {
            quest_id: hint_level_for_quest_state(st.session_state.quest_state_by_quest[quest_id])
            for quest_id in QUEST_OPTIONS
        }
    if "concept_story_existing_text" not in st.session_state:
        st.session_state.concept_story_existing_text = ""
    if "concept_story_new_text" not in st.session_state:
        st.session_state.concept_story_new_text = ""


@st.cache_resource
def get_neo4j_driver():
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )


def fetch_concept_story(concept_id: str) -> dict[str, object] | None:
    query = """
    MATCH (c:ConceptStory {concept_id: $concept_id})
    RETURN
      c.concept_id AS concept_id,
      c.category AS category,
      c.title AS title,
      c.text AS text,
      c.quest_id AS quest_id,
      c.npc_id AS npc_id,
      c.updated_at_ms AS updated_at_ms
    """

    driver = get_neo4j_driver()
    records, _, _ = driver.execute_query(query, concept_id=concept_id)
    if not records:
        return None
    return records[0].data()


def upsert_concept_story(
    concept_id: str,
    category: str,
    title: str,
    text: str,
    quest_id: str | None,
    npc_id: str | None,
) -> None:
    query = """
    MERGE (c:ConceptStory {concept_id: $concept_id})
    SET
      c.category = $category,
      c.title = $title,
      c.text = $text,
      c.quest_id = $quest_id,
      c.npc_id = $npc_id,
      c.updated_at_ms = $updated_at_ms
    """

    driver = get_neo4j_driver()
    driver.execute_query(
        query,
        concept_id=concept_id,
        category=category,
        title=title,
        text=text,
        quest_id=quest_id,
        npc_id=npc_id,
        updated_at_ms=current_timestamp_ms(),
    )


st.set_page_config(page_title="persona admin")
st.title("persona_chat admin")
st.caption("대화 메모리는 세션 상태로만 관리하고, ConceptStory 적재는 별도 Neo4j 노드로만 처리합니다.")

ensure_admin_session_state()

memory_tab, quest_tab, concept_story_tab = st.tabs(["Memory Admin", "Quest Admin", "Concept Story Admin"])

with memory_tab:
    st.subheader("Memory Admin")
    with st.form("memory_admin_form"):
        memory_npc_id = st.selectbox(
            "NPC Memory Target",
            NPC_OPTIONS,
            format_func=lambda npc_id: str(NPC_NAMES.get(str(npc_id), str(npc_id))),
        )
        max_memory_count = st.number_input(
            "Max Memory Count",
            min_value=10,
            max_value=200,
            step=10,
            value=int(st.session_state.max_memory_count_by_npc.get(memory_npc_id, DEFAULT_MAX_MEMORY_COUNT)),
        )
        save_memory = st.form_submit_button("Save Memory Setting")

    if save_memory:
        st.session_state.max_memory_count_by_npc[memory_npc_id] = int(max_memory_count)
        append_feature_log(
            "memory",
            {
                "event": "memory_setting_saved",
                "npc_id": memory_npc_id,
                "max_memory_count": int(max_memory_count),
            },
        )
        st.success("Memory setting saved.")

    if st.button("선택 NPC 메모리 초기화"):
        st.session_state.memory_by_npc[memory_npc_id] = []
        st.session_state.memory_summary_by_npc[memory_npc_id] = ""
        append_feature_log(
            "memory",
            {
                "event": "memory_cleared",
                "npc_id": memory_npc_id,
            },
        )
        st.success("Memory cleared.")

    st.text_area(
        "Current Summary",
        value=st.session_state.memory_summary_by_npc.get(memory_npc_id, ""),
        disabled=True,
    )

with quest_tab:
    st.subheader("Quest Admin")
    with st.form("quest_state_admin_form"):
        admin_quest_id = st.selectbox("Quest", QUEST_OPTIONS)
        current_state = st.session_state.quest_state_by_quest.get(admin_quest_id, DEFAULT_QUEST_STATE)
        quest_state = st.selectbox(
            "Quest State",
            QUEST_STATE_OPTIONS,
            index=QUEST_STATE_OPTIONS.index(current_state),
        )
        linked_hint_level = hint_level_for_quest_state(quest_state)
        allowed_hint_level = st.slider(
            "Allowed Hint Level",
            min_value=0,
            max_value=3,
            value=linked_hint_level,
            disabled=True,
        )
        save_quest = st.form_submit_button("Save Quest State")

    if save_quest:
        st.session_state.quest_state_by_quest[admin_quest_id] = quest_state
        st.session_state.allowed_hint_level_by_quest[admin_quest_id] = linked_hint_level
        if st.session_state.get("quest_id") == admin_quest_id:
            st.session_state.quest_state = quest_state
            st.session_state.allowed_hint_level = linked_hint_level
        append_feature_log(
            "admin",
            {
                "event": "quest_state_saved",
                "quest_id": admin_quest_id,
                "quest_state": quest_state,
                "allowed_hint_level": linked_hint_level,
            },
        )
        st.success("Quest state saved.")

with concept_story_tab:
    st.subheader("Concept Story Admin")
    concept_category_options = ["global", "quest", "monster", "npc"]

    with st.form("concept_story_lookup_form"):
        lookup_concept_id = st.text_input("Concept ID", key="lookup_concept_id")
        lookup_submitted = st.form_submit_button("Check Existing Concept Story")

    if lookup_submitted:
        existing_story = fetch_concept_story(lookup_concept_id.strip()) if lookup_concept_id.strip() else None
        st.session_state.concept_story_existing_text = str(existing_story.get("text", "")) if existing_story else ""
        append_feature_log(
            "admin",
            {
                "event": "concept_story_checked",
                "concept_id": lookup_concept_id.strip(),
                "found": existing_story is not None,
            },
        )

    with st.form("concept_story_import_form"):
        concept_category = st.selectbox("Concept Category", concept_category_options)
        concept_id = st.text_input("Concept ID", key="import_concept_id")
        concept_title = st.text_input("Title")
        concept_text = st.text_area("Story / Concept Text")
        concept_quest_id = st.selectbox("Quest Link", [""] + QUEST_OPTIONS)
        concept_npc_id = st.selectbox("NPC Link", [""] + NPC_OPTIONS)
        submitted = st.form_submit_button("Load Concept Story to Neo4j")

    if submitted:
        clean_concept_id = concept_id.strip()
        clean_concept_text = concept_text.strip()
        if not clean_concept_id or not clean_concept_text:
            st.error("Concept ID and Story / Concept Text are required.")
            append_feature_log(
                "admin",
                {
                    "event": "concept_story_validation_failed",
                    "concept_id": clean_concept_id,
                    "has_text": bool(clean_concept_text),
                },
            )
        else:
            existing_story = fetch_concept_story(clean_concept_id)
            st.session_state.concept_story_existing_text = str(existing_story.get("text", "")) if existing_story else ""
            st.session_state.concept_story_new_text = clean_concept_text
            upsert_concept_story(
                concept_id=clean_concept_id,
                category=concept_category,
                title=concept_title.strip(),
                text=clean_concept_text,
                quest_id=concept_quest_id or None,
                npc_id=concept_npc_id or None,
            )
            append_feature_log(
                "admin",
                {
                    "event": "concept_story_loaded",
                    "concept_id": clean_concept_id,
                    "category": concept_category,
                },
            )
            append_feature_log(
                "neo4j_import",
                {
                    "event": "concept_story_upserted",
                    "concept_id": clean_concept_id,
                    "category": concept_category,
                },
            )
            st.success("ConceptStory node loaded.")

    st.text_area("Existing DB Text", value=st.session_state.concept_story_existing_text, disabled=True)
    st.text_area("Additional Input Text", value=st.session_state.concept_story_new_text, disabled=True)
