import unittest
from pathlib import Path
from typing import final


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "src" / "streamlit" / "test_app.py"
PROMPTING_SOURCE = ROOT / "src" / "streamlit" / "prompting.py"
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

        self.assertIn("QUEST_STATE_HINT_LEVELS = {", source)
        self.assertIn('"not_started": 0', source)
        self.assertIn('"in_progress": 1', source)
        self.assertIn('"hint_1_given": 1', source)
        self.assertIn('"hint_2_given": 2', source)
        self.assertIn('"ready_to_answer": 3', source)
        self.assertIn('"solved": 3', source)
        self.assertIn("def sync_hint_level_from_quest_state()", source)
        self.assertIn("on_change=sync_hint_level_from_quest_state", source)
        self.assertIn('key="allowed_hint_level"', source)

    def test_debug_sections_persist_outside_chat_submit(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        chat_input_index = source.index('if user_message := st.chat_input("메세지를 입력하세요")')
        debug_render_index = source.rindex("last_debug = st.session_state.last_debug")

        self.assertIn('"last_debug" not in st.session_state', source)
        self.assertIn("st.session_state.last_debug = {", source)
        self.assertGreater(debug_render_index, chat_input_index)
        self.assertIn(
            'with st.expander("Debug: Retrieved Chunks", expanded=False):',
            source[debug_render_index:],
        )
        self.assertIn(
            'with st.expander("Debug: Prompt", expanded=False):',
            source[debug_render_index:],
        )

    def test_prompt_hides_internal_chunk_metadata(self):
        app_source = APP_SOURCE.read_text(encoding="utf-8")
        prompt_source = PROMPTING_SOURCE.read_text(encoding="utf-8")

        self.assertIn("from src.streamlit.prompting import build_prompt", app_source)
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
        self.assertIn("json.dumps(record, ensure_ascii=False) +", source)
        self.assertIn("append_interaction_log(", source)
        self.assertIn("normalize_stream_response(response)", source)

    def test_compose_persists_streamlit_jsonl_logs(self):
        for path in [
            COMPOSE_SOURCE,
            DESIGN_COMPOSE_SOURCE,
            ENV_EXAMPLE,
            DESIGN_ENV_EXAMPLE,
        ]:
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


if __name__ == "__main__":
    _ = unittest.main()
