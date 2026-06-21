import unittest
from pathlib import Path
from typing import final


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "src" / "streamlit" / "test_app.py"
ADMIN_PAGE_SOURCE = ROOT / "src" / "streamlit" / "pages" / "admin.py"
PROMPTING_SOURCE = ROOT / "src" / "streamlit" / "prompting.py"
QUEST_AUTO_PROGRESSION_PLAN = ROOT / "docs" / "quest_auto_progression_plan.md"
COMPOSE_SOURCE = ROOT / "compose.yaml"
DESIGN_COMPOSE_SOURCE = ROOT / "compose.design-test.yaml"
ENV_EXAMPLE = ROOT / ".env.example"
DESIGN_ENV_EXAMPLE = ROOT / ".env.design-test.example"


@final
class StreamlitContractTest(unittest.TestCase):
    def test_defaults_match_server_mvp_settings(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn(
            'NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "admin2026")',
            source,
        )
        self.assertIn(
            'MODEL_NAME = os.getenv("MODEL_NAME", "google/gemma-4-E4B-it")',
            source,
        )

    def test_vllm_connection_refused_gets_readable_guidance(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn("requests.exceptions.ConnectionError", source)
        self.assertIn("vLLM 서버가 아직 준비 중", source)
        self.assertNotIn('yield f"\n\n[vLLM 호출 오류] {e}"', source)

    def test_chunk_retrieval_applies_hint_cap_before_answer_sensitivity(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn("AND k.hint_level <= $allowed_hint_level", source)
        self.assertIn(
            'AND (k.answer_sensitive = false OR $quest_state IN ["ready_to_answer", "solved"])',
            source,
        )
        self.assertLess(
            source.index("AND k.hint_level <= $allowed_hint_level"),
            source.index('AND (k.answer_sensitive = false OR $quest_state IN ["ready_to_answer", "solved"])'),
        )
        self.assertNotIn("OR k.hint_level <= $allowed_hint_level", source)

    def test_quest_state_synchronizes_hint_level(self):
        source = APP_SOURCE.read_text(encoding="utf-8")
        admin_source = ADMIN_PAGE_SOURCE.read_text(encoding="utf-8")

        self.assertIn("QUEST_STATE_HINT_LEVELS = {", source)
        self.assertIn('"not_started": 0', source)
        self.assertIn('"in_progress": 1', source)
        self.assertIn('"hint_1_given": 1', source)
        self.assertIn('"hint_2_given": 2', source)
        self.assertIn('"ready_to_answer": 3', source)
        self.assertIn('"solved": 3', source)
        self.assertIn("def sync_hint_level_from_quest_state()", source)
        self.assertNotIn("on_change=sync_hint_level_from_quest_state", source)
        self.assertIn('with st.form("quest_state_admin_form")', admin_source)
        self.assertIn('st.selectbox("Quest", QUEST_OPTIONS)', admin_source)
        self.assertIn('"Quest State"', admin_source)
        self.assertIn('"Allowed Hint Level"', admin_source)
        self.assertIn("linked_hint_level = hint_level_for_quest_state(quest_state)", admin_source)
        self.assertIn("st.session_state.quest_state_by_quest[admin_quest_id] = quest_state", admin_source)
        self.assertIn("value=linked_hint_level", admin_source)
        self.assertIn("disabled=True", admin_source)
        self.assertIn("st.session_state.allowed_hint_level_by_quest[admin_quest_id] = linked_hint_level", admin_source)
        self.assertNotIn("st.session_state.allowed_hint_level_by_quest[admin_quest_id] = int(allowed_hint_level)", admin_source)

    def test_debug_sections_persist_outside_chat_submit(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        chat_input_index = source.index('if user_message := st.chat_input("메세지를 입력하세요")')
        sidebar_index = source.index("with st.sidebar:")
        debug_function_index = source.index("def render_sidebar_diagnostics(container: DeltaGenerator) -> None:")
        debug_call_index = source.index("render_sidebar_diagnostics(sidebar_diagnostics_container)")

        self.assertIn('"last_debug" not in st.session_state', source)
        self.assertIn("st.session_state.last_debug = {", source)
        self.assertLess(debug_function_index, sidebar_index)
        self.assertGreater(debug_call_index, chat_input_index)
        self.assertIn(
            'with st.popover("Debug: Retrieved Chunks"):',
            source[debug_function_index:sidebar_index],
        )
        self.assertIn(
            'with st.popover("Debug: Prompt"):',
            source[debug_function_index:sidebar_index],
        )

    def test_prompt_hides_internal_chunk_metadata(self):
        app_source = APP_SOURCE.read_text(encoding="utf-8")
        prompt_source = PROMPTING_SOURCE.read_text(encoding="utf-8")

        self.assertIn("build_prompt", app_source)
        self.assertIn("def format_chunk_for_prompt", prompt_source)
        self.assertIn("format_chunk_for_prompt(chunk) for chunk in chunks", prompt_source)
        self.assertNotIn('f"[chunk_id:', prompt_source)
        self.assertNotIn('f"knowledge_type:', prompt_source)
        self.assertNotIn('f"hint_level:', prompt_source)
        self.assertNotIn('f"answer_sensitive:', prompt_source)
        self.assertNotIn('bullet_list(string_list(npc.get("knowledge_scope")))', prompt_source)
        self.assertNotIn('bullet_list(string_list(npc.get("restricted_knowledge")))', prompt_source)
        self.assertIn("내부 식별자, 영어 데이터 라벨, 지식 분류명", prompt_source)
        self.assertIn("이전 답변과 같은 표현을 반복하지 말고", prompt_source)
        self.assertIn("CASE WHEN k.quest_id = $quest_id THEN 0 ELSE 1 END", app_source)
        self.assertIn("limit=8", app_source)

    def test_interaction_logs_are_app_side_jsonl_with_debug_payload(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn("CHAT_LOG_PATH = Path(os.getenv", source)
        self.assertIn("def build_interaction_log", source)
        self.assertIn("def append_interaction_log", source)
        self.assertIn('"input": user_message', source)
        self.assertIn('"output": response_text', source)
        self.assertIn('"debug": {', source)
        self.assertIn('"retrieved_chunks": chunks', source)
        self.assertIn('"prompt": prompt', source)
        self.assertIn("json.dumps(record_with_timestamp, ensure_ascii=False) +", source)
        self.assertIn("append_interaction_log(", source)
        self.assertIn("normalize_stream_response(response)", source)

    def test_compose_persists_streamlit_jsonl_logs(self):
        for path in [COMPOSE_SOURCE, DESIGN_COMPOSE_SOURCE]:
            source = path.read_text(encoding="utf-8")
            self.assertIn(
                "CHAT_LOG_PATH",
                source,
                msg=f"{path.name} should define Streamlit log path",
            )

        for path in [ENV_EXAMPLE, DESIGN_ENV_EXAMPLE]:
            if not path.exists():
                continue
            source = path.read_text(encoding="utf-8")
            self.assertIn(
                "CHAT_LOG_PATH",
                source,
                msg=f"{path.name} should define Streamlit log path",
            )

        for path in [COMPOSE_SOURCE, DESIGN_COMPOSE_SOURCE]:
            source = path.read_text(encoding="utf-8")
            self.assertIn("./output:/app/output", source)
            self.assertIn("PYTHONPATH: /app", source)

    def test_npc_selection_auto_syncs_role_and_quest(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn("NPC_METADATA = {", source)
        self.assertIn('"minmin_lady": {"player_role": "farmer", "quest_id": "q_glowing_mushroom"}', source)
        self.assertIn('"patrol_leader_rio": {"player_role": "knight", "quest_id": "q_pig_escape"}', source)
        self.assertIn('"mage_lumi": {"player_role": "mage", "quest_id": "q_jelly_color"}', source)
        self.assertIn('"chief_rowan": {"player_role": "lord", "quest_id": "q_main_spore_night"}', source)
        self.assertIn("def sync_npc_metadata()", source)
        self.assertIn('on_change=sync_npc_metadata', source)
        self.assertIn('st.session_state.player_role = metadata["player_role"]', source)
        self.assertIn('st.session_state.quest_id = metadata["quest_id"]', source)

    def test_quest_state_and_hint_are_kept_per_quest(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn('"quest_state_by_quest" not in st.session_state', source)
        self.assertIn('"allowed_hint_level_by_quest" not in st.session_state', source)
        self.assertIn("def restore_quest_controls_for_current_quest()", source)
        self.assertIn("def persist_quest_state_for_current_quest()", source)
        self.assertIn("def persist_hint_level_for_current_quest()", source)
        self.assertIn("st.session_state.quest_state_by_quest[st.session_state.quest_id]", source)
        self.assertIn("st.session_state.allowed_hint_level_by_quest[st.session_state.quest_id]", source)
        self.assertIn("hint_level_for_quest_state(st.session_state.quest_state)", source)
        self.assertIn("st.session_state.allowed_hint_level = hint_level_for_quest_state(st.session_state.quest_state)", source)

    def test_debug_controls_render_in_sidebar_not_chat_area(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        chat_input_index = source.index('if user_message := st.chat_input("메세지를 입력하세요")')
        sidebar_index = source.index("with st.sidebar:")
        sidebar_source = source[sidebar_index:chat_input_index]
        diagnostics_source = source[source.index("def render_sidebar_diagnostics(container: DeltaGenerator) -> None:"):sidebar_index]
        self.assertIn('with st.popover("Debug: Retrieved Chunks"):', diagnostics_source)
        self.assertIn('with st.popover("Debug: Prompt"):', diagnostics_source)
        self.assertIn('with st.popover("Debug: Runtime"):', diagnostics_source)
        self.assertIn("last_debug = st.session_state.last_debug", diagnostics_source)
        self.assertIn("sidebar_diagnostics_container = st.container()", sidebar_source)
        self.assertIn("render_sidebar_diagnostics(sidebar_diagnostics_container)", source[chat_input_index:])
        self.assertIn('st.subheader("대화 요약")', diagnostics_source)
        self.assertIn('if st.button("대화 초기화"):', sidebar_source)
        self.assertIn('"현재 대화 요약"', diagnostics_source)
        self.assertIn("value=summarize_memory_turns(recent_turns)", diagnostics_source)
        self.assertNotIn('st.selectbox(\n        "Quest"', sidebar_source)
        self.assertNotIn('st.selectbox(\n        "Quest State"', sidebar_source)
        self.assertNotIn('st.slider(\n        "Allowed Hint Level"', sidebar_source)
        self.assertNotIn('st.subheader("Memory Admin")', sidebar_source)
        self.assertNotIn('st.subheader("Concept Story Admin")', sidebar_source)
        self.assertNotIn('with st.expander("Debug: Retrieved Chunks", expanded=False):', source[chat_input_index:])
        self.assertNotIn('with st.expander("Debug: Prompt", expanded=False):', source[chat_input_index:])
        runtime_popover_source = source[source.index('with st.popover("Debug: Runtime"):'):source.index('st.divider()\n        st.subheader("대화 요약")')]
        self.assertIn('st.caption(f"Model: {MODEL_NAME}")', runtime_popover_source)
        self.assertIn('st.caption(f"vLLM: {VLLM_URL}")', runtime_popover_source)
        self.assertIn('st.caption(f"Neo4j: {NEO4J_URI}")', runtime_popover_source)
        self.assertIn('st.caption(f"Log: {CHAT_LOG_PATH}")', runtime_popover_source)

    def test_chat_messages_are_tagged_and_rendered_with_speaker_labels(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn("def build_chat_message(", source)
        self.assertIn('speaker_label="모험가"', source)
        self.assertIn('person_id=st.session_state.npc_id', source)
        self.assertIn('person_name=npc_name', source)
        self.assertIn('st.caption(message.get("speaker_label", message["role"]))', source)
        self.assertIn('role="user"', source)
        self.assertIn('role="assistant"', source)

    def test_per_npc_memory_admin_and_compaction_are_session_only(self):
        source = APP_SOURCE.read_text(encoding="utf-8")
        admin_source = ADMIN_PAGE_SOURCE.read_text(encoding="utf-8")
        prompt_source = PROMPTING_SOURCE.read_text(encoding="utf-8")

        self.assertIn('"memory_by_npc" not in st.session_state', source)
        self.assertIn('"memory_summary_by_npc" not in st.session_state', source)
        self.assertIn("MAX_CONTEXT_TOKENS = 4096", source)
        self.assertIn("MEMORY_COMPACTION_RATIO = 0.9", source)
        self.assertIn("def get_npc_memory_context(npc_id: str)", source)
        self.assertIn("def compact_npc_memory_if_needed(npc_id: str)", source)
        self.assertIn("def compact_npc_memory_for_prompt_if_needed(npc_id: str, prompt: str) -> bool", source)
        self.assertIn("summarize_memory_turns", source)
        self.assertIn("estimate_prompt_units(prompt)", source)
        self.assertIn("if compact_npc_memory_for_prompt_if_needed(st.session_state.npc_id, prompt):", source)
        self.assertIn('st.number_input(', admin_source)
        self.assertIn('"Max Memory Count"', admin_source)
        self.assertIn("min_value=10", admin_source)
        self.assertIn("max_value=200", admin_source)
        self.assertIn("step=10", admin_source)
        self.assertIn('conversation_context=get_npc_memory_context(st.session_state.npc_id)', source)
        self.assertIn("conversation_context: str = \"\"", prompt_source)
        self.assertIn("[이전 대화 기억]", prompt_source)
        self.assertNotIn("MERGE (m:ChatMemory", source)

    def test_required_feature_events_are_logged(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        for event_name in [
            "npc_changed",
            "role_changed",
            "quest_auto_selected",
            "conversation_reset",
            "memory_turn_added",
        ]:
            with self.subTest(event=event_name):
                self.assertIn(f'"event": "{event_name}"', source)

        self.assertIn("def log_player_role_change() -> None", source)
        self.assertIn("on_change=log_player_role_change", source)
        self.assertIn("append_feature_log(\n        \"memory\"", source)

    def test_admin_controls_live_on_separate_streamlit_page(self):
        source = APP_SOURCE.read_text(encoding="utf-8")
        admin_source = ADMIN_PAGE_SOURCE.read_text(encoding="utf-8")

        self.assertTrue(ADMIN_PAGE_SOURCE.exists())
        self.assertIn('st.set_page_config(page_title="persona admin")', admin_source)
        self.assertIn('st.title("persona_chat admin")', admin_source)
        self.assertIn('st.tabs(["Memory Admin", "Quest Admin", "Concept Story Admin"])', admin_source)
        self.assertIn('st.subheader("Memory Admin")', admin_source)
        self.assertIn('st.subheader("Quest Admin")', admin_source)
        self.assertIn('st.subheader("Concept Story Admin")', admin_source)
        self.assertNotIn('st.subheader("Memory Admin")', source)
        self.assertNotIn('st.subheader("Concept Story Admin")', source)

    def test_feature_logs_are_split_by_category_with_millisecond_timestamps(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn("LOG_PATHS = {", source)
        self.assertIn('"chat": Path(os.getenv("CHAT_LOG_PATH"', source)
        self.assertIn('"memory": Path(os.getenv("MEMORY_LOG_PATH"', source)
        self.assertIn('"admin": Path(os.getenv("ADMIN_LOG_PATH"', source)
        self.assertIn("def current_timestamp_ms() -> int", source)
        self.assertIn("int(time.time() * 1000)", source)
        self.assertIn("def append_feature_log(category: str, record: dict[str, object])", source)
        self.assertIn('record_with_timestamp = {"timestamp_ms": current_timestamp_ms(), **record}', source)

    def test_admin_concept_story_import_is_button_driven_and_separate_from_chat_memory(self):
        source = APP_SOURCE.read_text(encoding="utf-8")
        admin_source = ADMIN_PAGE_SOURCE.read_text(encoding="utf-8")

        self.assertIn("def upsert_concept_story(", admin_source)
        self.assertIn("def fetch_concept_story(", admin_source)
        self.assertIn("MERGE (c:ConceptStory {concept_id: $concept_id})", admin_source)
        self.assertIn("MATCH (c:ConceptStory {concept_id: $concept_id})", admin_source)
        self.assertIn("st.form(\"concept_story_lookup_form\")", admin_source)
        self.assertIn("st.form(\"concept_story_import_form\")", admin_source)
        self.assertIn('st.form_submit_button("Load Concept Story to Neo4j")', admin_source)
        self.assertIn('st.form_submit_button("Check Existing Concept Story")', admin_source)
        self.assertIn('st.text_area("Existing DB Text"', admin_source)
        self.assertIn('st.text_area("Additional Input Text"', admin_source)
        self.assertIn("clean_concept_id = concept_id.strip()", admin_source)
        self.assertIn("clean_concept_text = concept_text.strip()", admin_source)
        self.assertIn("if not clean_concept_id or not clean_concept_text:", admin_source)
        self.assertIn('st.error("Concept ID and Story / Concept Text are required.")', admin_source)
        self.assertIn('"event": "concept_story_validation_failed"', admin_source)
        self.assertIn("upsert_concept_story(\n                concept_id=clean_concept_id", admin_source)
        self.assertIn('concept_category_options = ["global", "quest", "monster", "npc"]', admin_source)
        self.assertIn("append_feature_log(\n            \"admin\"", admin_source)
        self.assertNotIn("ConceptStory", source[source.index('if user_message := st.chat_input("메세지를 입력하세요")'):])

    def test_future_quest_progression_is_documented_but_not_implemented(self):
        app_source = APP_SOURCE.read_text(encoding="utf-8")
        plan_source = QUEST_AUTO_PROGRESSION_PLAN.read_text(encoding="utf-8")

        self.assertIn("# Future Automatic Quest-State Progression Plan", plan_source)
        self.assertIn("Do not implement in the current Streamlit app", plan_source)
        self.assertIn("button-driven admin controls remain separate from chat memory", plan_source)
        self.assertNotIn("def auto_progress_quest_state", app_source)
        self.assertNotIn("auto_progress_quest_state(", app_source)


if __name__ == "__main__":
    _ = unittest.main()
