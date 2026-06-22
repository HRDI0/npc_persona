from pathlib import Path
import re
import unittest
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
PRESENTATION_DIR = DOCS_DIR / "presentation"
AFFINE_DIR = DOCS_DIR / "affine"


FORBIDDEN_PUBLIC_TERMS = [
    "127.0.0.1",
    "localhost",
    "bolt://",
    "/v1/models",
    "http://vllm:8000",
    "google/gemma-4-E2B-it",
    "google/gemma-4-E4B-it",
    "max_model_len",
    "VLLM_GPU_MEMORY_UTILIZATION",
    "VLLM_MAX_MODEL_LEN",
    "current main compose",
    "design-test stack access details",
    "neo4j / admin2026",
    "http://127.0.0.1:17474",
    "http://127.0.0.1:8501",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:18501",
    "http://127.0.0.1:18000",
]


class PresentationArtifactContract(unittest.TestCase):
    def read_html(self) -> str:
        return (PRESENTATION_DIR / "index.html").read_text(encoding="utf-8")

    def read_css(self) -> str:
        return (PRESENTATION_DIR / "styles.css").read_text(encoding="utf-8")

    def test_static_deck_files_exist(self):
        expected = [
            PRESENTATION_DIR / "index.html",
            PRESENTATION_DIR / "styles.css",
            PRESENTATION_DIR / "deck.js",
        ]
        missing = [path.relative_to(ROOT).as_posix() for path in expected if not path.exists()]

        self.assertEqual(missing, [], f"missing presentation artifact files: {missing}")

    def test_slide_count_matches_detailed_portfolio_scope(self):
        html = self.read_html()
        slide_count = html.count('<section class="slide')
        counter_match = re.search(r'<span id="slideCounter">1 / (\d+)</span>', html)

        if counter_match is None:
            self.fail("missing initial slide counter")

        self.assertEqual(slide_count, int(counter_match.group(1)))
        self.assertGreaterEqual(slide_count, 30)
        self.assertLessEqual(slide_count, 50)

    def test_public_deck_uses_detailed_architecture_storyline(self):
        html = self.read_html()
        required = [
            'data-slide-id="portfolio-cover"',
            'data-slide-id="portfolio-thesis"',
            'data-slide-id="problem-boundary"',
            'data-slide-id="portfolio-scope"',
            'data-slide-id="system-map"',
            'data-slide-id="story-data-sources"',
            'data-slide-id="story-chunk-metadata"',
            'data-slide-id="data-splitting-criteria"',
            'data-slide-id="loading-validation-criteria"',
            'data-slide-id="neo4j-design-goals"',
            'data-slide-id="neo4j-node-model"',
            'data-slide-id="neo4j-relationship-model"',
            'data-slide-id="neo4j-design-process"',
            'data-slide-id="neo4j-overview-evidence"',
            'data-slide-id="neo4j-quest-evidence"',
            'data-slide-id="npc-minmin-graph-evidence"',
            'data-slide-id="npc-rio-graph-evidence"',
            'data-slide-id="npc-lumi-graph-evidence"',
            'data-slide-id="npc-rowan-graph-evidence"',
            'data-slide-id="access-control-model"',
            'data-slide-id="retrieval-query-gates"',
            'data-slide-id="retrieval-sort-limit"',
            'data-slide-id="retrieval-debug-evidence"',
            'data-slide-id="prompt-assembly"',
            'data-slide-id="prompt-metadata-hiding"',
            'data-slide-id="prompt-leak-mitigation"',
            'data-slide-id="phrase-repetition-mitigation"',
            'data-slide-id="prompt-debug-evidence"',
            'data-slide-id="session-memory-model"',
            'data-slide-id="memory-compaction-path"',
            'data-slide-id="memory-admin-evidence"',
            'data-slide-id="quest-admin-evidence"',
            'data-slide-id="concept-story-admin-evidence"',
            'data-slide-id="admin-tab-separation"',
            'data-slide-id="runtime-chat-evidence"',
            'data-slide-id="npc-query-minmin-evidence"',
            'data-slide-id="npc-query-rio-evidence"',
            'data-slide-id="npc-query-lumi-evidence"',
            'data-slide-id="npc-query-rowan-evidence"',
            'data-slide-id="outcomes-limits-next"',
            'data-slide-id="source-to-graph"',
            "기술 포트폴리오",
            "Story Data Architecture",
            "GraphRAG",
            "Neo4j",
            "KnowledgeChunk",
            "인물별",
            "퀘스트별",
            "정보 접근 권한",
            "메모리 기능",
            "요약 저장 프로세스",
            "Memory Admin",
            "Quest Admin",
            "Concept Story Admin",
            "실제 캡처",
            "남은 한계",
        ]

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, html)

    def test_public_deck_omits_user_instruction_copy_and_boxed_layout(self):
        html = self.read_html()
        css = self.read_css()

        forbidden_copy = [
            "단순 챗봇이 아니다",
            "단순 챗봇이 아니라",
            "외부 포트폴리오",
            "내 지시사항",
            "참고용으로",
            "제발",
            "정신차리고",
            "목업 이미지나 생성 이미지는 사용하지 않는다",
        ]
        for text in forbidden_copy:
            with self.subTest(forbidden_copy=text):
                self.assertNotIn(text, html)

        forbidden_css = [
            "box-shadow",
            "border-radius",
            "clip-path",
            "mask",
            "background-image",
            "writing-mode",
        ]
        for text in forbidden_css:
            with self.subTest(forbidden_css=text):
                self.assertNotIn(text, css)

        h2_block_match = re.search(r"\.slide h2 \{(?P<body>.*?)\}", css, re.DOTALL)
        if h2_block_match is None:
            self.fail("missing slide title CSS block")
        max_size_match = re.search(r"font-size:\s*clamp\([^,]+,[^,]+,\s*(\d+)px\)", h2_block_match.group("body"))
        if max_size_match is None:
            self.fail("slide title font-size must use clamp with px max")
        self.assertLessEqual(int(max_size_match.group(1)), 31)
        self.assertIn("word-break: keep-all", css)
        self.assertIn("grid-template-columns", css)

    def test_public_deck_hides_local_runtime_and_model_internals(self):
        html = self.read_html()

        for text in FORBIDDEN_PUBLIC_TERMS:
            with self.subTest(text=text):
                self.assertNotIn(text, html)

    def test_every_slide_contains_explanation_copy(self):
        html = self.read_html()
        slides = cast(
            list[str],
            re.findall(r'<section class="slide.*?</section>', html, re.DOTALL),
        )

        self.assertTrue(slides, "expected slides in presentation")
        for index, slide in enumerate(slides, start=1):
            with self.subTest(slide=index):
                self.assertIn('class="explain"', slide)
                plain_text = re.sub(r"<[^>]+>", " ", slide)
                compact = re.sub(r"\s+", " ", plain_text).strip()
                self.assertGreaterEqual(len(compact), 180)

    def test_deck_documents_graph_loading_access_memory_and_admin_contracts(self):
        html = self.read_html()
        required = [
            "chunk_id",
            "phase",
            "title",
            "knowledge_type",
            "quest_id",
            "location_ids",
            "event_ids",
            "clue_ids",
            "allowed_roles",
            "answer_sensitive",
            "hint_level",
            "tags",
            "answer_sensitive requires hint_level 3",
            "NPC-[:KNOWS]->KnowledgeChunk",
            "RELATED_TO",
            "MENTIONS",
            "ABOUT",
            "POINTS_TO",
            "player_role IN k.allowed_roles",
            "k.hint_level &lt;= $allowed_hint_level",
            "quest_state IN [ready_to_answer, solved]",
            "LIMIT 8",
            "chunk title/text only",
            "내부 metadata를 직접 보여주지 않는다",
            "이전 답변과 같은 표현을 반복하지 않도록",
            "session-only memory",
            "memory_by_npc",
            "memory_summary_by_npc",
            "summarize_memory_turns",
            "summary compaction toward future long-term memory",
            "ConceptStory is not the current retrieval source",
            "자동 퀘스트 진행은 현재 구현 범위가 아니다",
        ]

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, html)

    def test_real_screenshots_are_existing_plain_rectangular_assets(self):
        html = self.read_html()
        css = self.read_css()
        image_sources = cast(list[str], re.findall(r'<img src="([^"]+)"', html))
        image_block_match = re.search(r"\.evidence-card img \{(?P<body>.*?)\}", css, re.DOTALL)

        if image_block_match is None:
            self.fail("missing direct evidence image CSS block")

        self.assertIn("실제 실행 캡처", html)
        self.assertIn("검증 화면", html)
        self.assertGreaterEqual(len(set(image_sources)), 14, "expected broad real screenshot evidence")

        required_assets = [
            "assets/neo4j-live-overview.png",
            "assets/neo4j-live-quests.png",
            "assets/neo4j-live-minmin.png",
            "assets/neo4j-live-rio.png",
            "assets/neo4j-live-lumi.png",
            "assets/neo4j-live-rowan.png",
            "assets/streamlit-live-chat-e2b.png",
            "assets/streamlit-debug-chunks.png",
            "assets/streamlit-debug-prompt.png",
            "assets/streamlit-admin-memory.png",
            "assets/streamlit-admin-quest.png",
            "assets/streamlit-admin-concept-story.png",
            "assets/streamlit-minmin-query.png",
            "assets/streamlit-rio-query.png",
            "assets/streamlit-lumi-query.png",
            "assets/streamlit-rowan-query.png",
        ]

        for asset in required_assets:
            with self.subTest(required_asset=asset):
                self.assertIn(asset, image_sources)

        for source in image_sources:
            with self.subTest(source=source):
                self.assertTrue(source.startswith("assets/"))
                self.assertTrue(source.endswith(".png"))
                self.assertTrue((PRESENTATION_DIR / source).exists(), f"missing asset: {source}")

        image_css = image_block_match.group("body")
        self.assertIn("object-fit: contain", image_css)
        self.assertNotIn("border-radius", image_css)
        self.assertNotIn("background-image", css)
        self.assertNotIn("clip-path", css)
        self.assertNotIn("mask", css)
        self.assertNotIn("url(", css)

    def test_image_slides_use_at_most_one_image_unless_marked_comparison(self):
        html = self.read_html()
        slides = cast(
            list[str],
            re.findall(r'<section class="slide.*?</section>', html, re.DOTALL),
        )

        self.assertTrue(slides, "expected slides in presentation")
        for index, slide in enumerate(slides, start=1):
            image_count = slide.count("<img ")
            with self.subTest(slide=index):
                if 'data-layout="comparison"' in slide:
                    self.assertLessEqual(image_count, 2)
                else:
                    self.assertLessEqual(image_count, 1)

    def test_deck_stays_offline_double_clickable(self):
        html = self.read_html()
        css = self.read_css()
        js = (PRESENTATION_DIR / "deck.js").read_text(encoding="utf-8")

        forbidden = [
            "https://",
            "http://",
            "//cdn",
            "fonts.googleapis",
            "type=\"module\"",
        ]
        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, html)
                self.assertNotIn(text, css)
                self.assertNotIn(text, js)

        self.assertIn('href="styles.css"', html)
        self.assertIn('src="deck.js"', html)
        self.assertIn("ArrowRight", js)
        self.assertIn("ArrowLeft", js)
        self.assertIn("slides.length", js)

    def test_css_supports_detailed_portfolio_layouts_and_accessibility(self):
        css = self.read_css()
        required = [
            ":root",
            ".topbar",
            ".slide.is-active",
            ".evidence-card img",
            ".detail-list",
            ".architecture-map",
            ".code-panel",
            ".section-divider",
            ":focus-visible",
            "@media (max-width: 820px)",
            "@media (prefers-reduced-motion: reduce)",
        ]

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, css)

    def test_image_alt_text_and_captions_are_public_facing(self):
        html = self.read_html()
        figures = cast(
            list[tuple[str, str, str]],
            re.findall(
                r'<figure class="evidence-card[^">]*">\s*<img src="([^"]+)" alt="([^"]+)"[^>]*>\s*<figcaption>(.*?)</figcaption>',
                html,
                re.DOTALL,
            ),
        )

        self.assertTrue(figures, "expected screenshot figures with captions")
        for source, alt, caption in figures:
            with self.subTest(source=source):
                self.assertIn("실제", alt)
                self.assertGreaterEqual(len(alt), 12)
                self.assertGreaterEqual(len(caption.strip()), 8)
                for term in FORBIDDEN_PUBLIC_TERMS:
                    self.assertNotIn(term, caption)

    def test_docs_readme_keeps_affine_private_and_consolidates_duplicates(self):
        docs_readme = (DOCS_DIR / "README.md").read_text(encoding="utf-8")

        self.assertNotIn("affine/README.md", docs_readme)
        self.assertNotIn("Affine 주간 포트폴리오", docs_readme)
        self.assertIn("개인 작업 노트는 공개 문서 지도에서 제외", docs_readme)
        self.assertNotIn("presentation_visualization.md", docs_readme)
        self.assertFalse((DOCS_DIR / "presentation_visualization.md").exists())
        self.assertFalse((DOCS_DIR / "architecture_usage_flows.md").exists())

    def test_affine_notes_are_private_process_documents(self):
        expected_files = [
            AFFINE_DIR / "README.md",
            AFFINE_DIR / "week-01-planning.md",
            AFFINE_DIR / "week-02-design.md",
            AFFINE_DIR / "week-03-development.md",
            AFFINE_DIR / "week-04-fixes-runtime.md",
            AFFINE_DIR / "week-05-completed-examples.md",
        ]

        for path in expected_files:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertTrue(path.exists())
                text = path.read_text(encoding="utf-8")
                self.assertIn("고민과정과 해결과정", text)
                self.assertIn("왜 이 선택을 했는가", text)
                self.assertIn("어떻게 확인했는가", text)
                for term in ["127.0.0.1", "google/gemma-4-E2B-it", "max_model_len", "VLLM_GPU_MEMORY_UTILIZATION"]:
                    self.assertNotIn(term, text)

    def test_presentation_artifact_contains_no_huggingface_token(self):
        token_pattern = re.compile(r"hf_[A-Za-z0-9_=-]{10,}")
        checked = [
            PRESENTATION_DIR / "index.html",
            PRESENTATION_DIR / "styles.css",
            PRESENTATION_DIR / "deck.js",
        ]
        leaked = [path.relative_to(ROOT).as_posix() for path in checked if token_pattern.search(path.read_text(encoding="utf-8"))]

        self.assertEqual(leaked, [], f"presentation artifact contains token-like values: {leaked}")


if __name__ == "__main__":
    _ = unittest.main()
