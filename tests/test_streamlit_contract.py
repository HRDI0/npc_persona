import unittest
from pathlib import Path
from typing import final


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "src" / "streamlit" / "test_app.py"


@final
class StreamlitContractTest(unittest.TestCase):
    def test_defaults_match_server_mvp_settings(self):
        source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn(
            'NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "admin2026")',
            source,
        )
        self.assertIn(
            'MODEL_NAME = os.getenv("MODEL_NAME", "google/gemma-4-E2B-it")',
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


if __name__ == "__main__":
    _ = unittest.main()
