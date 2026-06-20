import unittest
from typing import final

from src.streamlit.prompting import build_prompt, format_chunk_for_prompt, string_list


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

    def test_string_list_filters_to_strings(self):
        self.assertEqual(string_list(["a", 1, None, "b"]), ["a", "b"])
        self.assertEqual(string_list("not-a-list"), [])


if __name__ == "__main__":
    _ = unittest.main()
