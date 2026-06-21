import unittest
from typing import final

from src.streamlit.prompting import (
    build_prompt,
    estimate_context_units,
    estimate_prompt_units,
    format_chunk_for_prompt,
    format_memory_context,
    string_list,
    summarize_memory_turns,
)


@final
class StreamlitPromptingTest(unittest.TestCase):
    def test_format_chunk_for_prompt_uses_title_and_text_only(self):
        chunk: dict[str, object] = {
            "chunk_id": "secret_chunk_id",
            "title": "버섯 관찰",
            "knowledge_type": "observation",
            "hint_level": 2,
            "answer_sensitive": True,
            "text": "달빛 아래에서만 버섯이 밝게 보였다.",
        }

        formatted = format_chunk_for_prompt(chunk)

        self.assertIn("참고 제목: 버섯 관찰", formatted)
        self.assertIn("참고 내용:\n달빛 아래에서만 버섯이 밝게 보였다.", formatted)
        self.assertNotIn("secret_chunk_id", formatted)
        self.assertNotIn("observation", formatted)
        self.assertNotIn("hint_level", formatted)
        self.assertNotIn("answer_sensitive", formatted)

    def test_build_prompt_preserves_policy_labels_and_empty_chunk_fallback(self):
        prompt = build_prompt(
            npc={
                "name": "민민 부인",
                "role": "farmer",
                "personality": ["차분하다"],
                "speech_style": ["느릿하게 말한다"],
                "dialogue_must": ["관찰한 것만 말한다"],
                "dialogue_must_not": ["정답을 단정하지 않는다"],
            },
            chunks=[],
            user_message="버섯이 왜 빛나요?",
            quest_state="ready_to_answer",
            player_role="lord",
            allowed_hint_level=3,
        )

        self.assertIn('현재 NPC는 "민민 부인"이다.', prompt)
        self.assertIn("역할: 농부", prompt)
        self.assertIn("플레이어 역할: 영주", prompt)
        self.assertIn("퀘스트 진행: 정답 확인 가능", prompt)
        self.assertIn("사용 가능한 지식이 없습니다.", prompt)
        self.assertIn("내부 식별자, 영어 데이터 라벨, 지식 분류명", prompt)
        self.assertIn("이전 답변과 같은 표현을 반복하지 말고", prompt)
        self.assertIn("버섯이 왜 빛나요?", prompt)

    def test_build_prompt_does_not_include_raw_knowledge_scope_fields(self):
        prompt = build_prompt(
            npc={
                "name": "로완",
                "role": "lord",
                "personality": [],
                "speech_style": [],
                "knowledge_scope": ["RAW_SCOPE_SHOULD_NOT_APPEAR"],
                "restricted_knowledge": ["RAW_RESTRICTED_SHOULD_NOT_APPEAR"],
                "dialogue_must": [],
                "dialogue_must_not": [],
            },
            chunks=[{"title": "보고", "text": "회의에서 들은 내용만 말한다."}],
            user_message="아는 걸 말해 주세요.",
            quest_state="in_progress",
            player_role="farmer",
            allowed_hint_level=1,
        )

        self.assertIn("회의에서 들은 내용만 말한다.", prompt)
        self.assertNotIn("RAW_SCOPE_SHOULD_NOT_APPEAR", prompt)
        self.assertNotIn("RAW_RESTRICTED_SHOULD_NOT_APPEAR", prompt)

    def test_build_prompt_includes_prior_per_npc_memory_context(self):
        prompt = build_prompt(
            npc={
                "name": "마도사 루미",
                "role": "mage",
                "personality": [],
                "speech_style": [],
                "dialogue_must": [],
                "dialogue_must_not": [],
            },
            chunks=[{"title": "젤리", "text": "방울젤리는 마나 흐름에 반응한다."}],
            user_message="전에 뭘 말했죠?",
            quest_state="in_progress",
            player_role="mage",
            allowed_hint_level=1,
            conversation_context="요약: 플레이어가 젤리 색 변화를 이미 물었다.",
        )

        self.assertIn("[이전 대화 기억]", prompt)
        self.assertIn("요약: 플레이어가 젤리 색 변화를 이미 물었다.", prompt)
        self.assertLess(prompt.index("[이전 대화 기억]"), prompt.index("[플레이어 질문]"))

    def test_format_memory_context_uses_summary_and_recent_turns_without_fixed_policy_repetition(self):
        context = format_memory_context(
            summary="요약: 버섯 빛을 확인했다.",
            recent_turns=[
                {"speaker_label": "모험가", "content": "버섯은 어디 있나요?"},
                {"speaker_label": "민민 부인", "content": "동쪽 밭 끝을 보세요."},
            ],
        )

        self.assertIn("요약: 버섯 빛을 확인했다.", context)
        self.assertIn("모험가: 버섯은 어디 있나요?", context)
        self.assertIn("민민 부인: 동쪽 밭 끝을 보세요.", context)
        self.assertNotIn("너는 게임 속 NPC다", context)
        self.assertNotIn("[응답 정책]", context)

    def test_summarize_memory_turns_is_deterministic_and_local(self):
        turns = [
            {"speaker_label": "모험가", "content": "첫 질문"},
            {"speaker_label": "민민 부인", "content": "첫 답변"},
            {"speaker_label": "모험가", "content": "둘째 질문"},
        ]

        first = summarize_memory_turns(turns)
        second = summarize_memory_turns(turns)

        self.assertEqual(first, second)
        self.assertIn("모험가: 첫 질문", first)
        self.assertIn("민민 부인: 첫 답변", first)
        self.assertNotIn("LLM", first)

    def test_estimate_context_units_counts_text_for_compaction_thresholds(self):
        turns = [
            {"speaker_label": "모험가", "content": "12345"},
            {"speaker_label": "민민 부인", "content": "67890"},
        ]

        self.assertGreaterEqual(estimate_context_units(turns), 10)

    def test_estimate_prompt_units_counts_full_prompt_text(self):
        self.assertEqual(len("전체 프롬프트 abc"), estimate_prompt_units("전체 프롬프트 abc"))

    def test_string_list_filters_to_strings(self):
        self.assertEqual(string_list(["a", 1, None, "b"]), ["a", "b"])
        self.assertEqual(string_list("not-a-list"), [])


if __name__ == "__main__":
    _ = unittest.main()
