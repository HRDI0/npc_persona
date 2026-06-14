from pathlib import Path
import re
import unittest
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
PRESENTATION_DIR = ROOT / "docs" / "presentation"


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

    def test_slide_count_matches_latest_handoff_scope(self):
        html = self.read_html()
        slide_count = html.count('<section class="slide')
        counter_match = re.search(r'<span id="slideCounter">1 / (\d+)</span>', html)

        if counter_match is None:
            self.fail("missing initial slide counter")

        self.assertEqual(slide_count, int(counter_match.group(1)))
        self.assertGreaterEqual(slide_count, 30)
        self.assertLessEqual(slide_count, 80)

    def test_every_slide_contains_detailed_explanation(self):
        html = self.read_html()
        slides = cast(
            list[str],
            re.findall(r'<section class="slide.*?</section>', html, re.DOTALL),
        )

        self.assertTrue(slides, "expected slides in presentation")
        for index, slide in enumerate(slides, start=1):
            with self.subTest(slide=index):
                self.assertIn('class="explain"', slide)

    def test_visualization_first_project_structure_from_large_to_small(self):
        html = self.read_html()
        required = [
            'data-slide-id="project-root-overview"',
            'data-slide-id="handoff-map"',
            'data-slide-id="architecture-overview"',
            'data-slide-id="source-folder-visual"',
            'data-slide-id="source-deep-map"',
            "root-map",
            "stack-diagram",
            "lane-diagram",
            "source-detail-map",
            "rsc/data",
            "scripts/story_pipeline",
            "src/db_control/import_story_source_to_neo4j.py",
            "src/streamlit/test_app.py",
            "output/reports",
            "output/integrated",
            "output/neo4j_import",
        ]

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, html)

    def test_data_augmentation_describes_added_content_with_actual_examples(self):
        html = self.read_html()
        required = [
            'data-slide-id="augmentation-location"',
            'data-slide-id="augmentation-added-items"',
            'data-slide-id="quest-expansion-schema"',
            'data-slide-id="quest-example-glowing"',
            'data-slide-id="quest-example-main"',
            "데이터 증강은 quest YAML의 story_expansion과 NPC Markdown의 story-chunk 두 곳에서 이루어졌다",
            "증강으로 추가된 것은",
            "퀘스트 목적",
            "진행 단계",
            "오답 가설",
            "힌트 흐름",
            "정답 공개 정책",
            "NPC 지식 조각",
            "story_expansion은 rsc/data/quests/*.yaml 안에 통합한다",
            "story_purpose",
            "quest_steps",
            "wrong_hypotheses",
            "hint_flow",
            "answer_reveal_policy",
            "completion",
            "rsc/data/quests/q_glowing_mushroom.yaml",
            "observe_light",
            "달이 밝으면 더 보였단다",
            "whm_bad_weather",
            "날씨 때문에 버섯이 밝아졌다",
            "rsc/data/quests/q_main_spore_night.yaml",
            "align_direction",
            "single_culprit_only",
            "한 명의 장난이나 한 사건만으로 모든 일이 벌어졌다",
            "can_reveal_truth_before_required_clues: false",
        ]

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, html)

    def test_minmin_data_load_criteria_and_graph_structure_are_visualized(self):
        html = self.read_html()
        required = [
            'data-slide-id="minmin-source-overview"',
            'data-slide-id="minmin-frontmatter-visual"',
            'data-slide-id="minmin-chunk-distribution"',
            'data-slide-id="minmin-chunk-to-dict"',
            'data-slide-id="minmin-load-criteria"',
            'data-slide-id="minmin-graph-structure"',
            'data-slide-id="minmin-runtime-trace"',
            "minmin-map",
            "profile-visual",
            "chunk-distribution",
            "transform-board",
            "load-criteria",
            "minmin-graph",
            "runtime-trace",
            "npc_id: minmin_lady",
            "role: farmer",
            "location_id: east_farm",
            "main_quest: q_glowing_mushroom",
            "minmin_chronicle_003",
            "민민 부인이 본 몽실버섯의 변화",
            "몽실버섯이 밤에 빛나고, 달이 밝은 날에는 더 눈에 띄며",
            "고유 ID",
            "출처 보존",
            "관계 생성",
            "공개 정책",
            "NPC<br>minmin_lady",
            "KnowledgeChunk<br>003 mushroom",
            "RELATED_TO",
            "POINTS_TO",
        ]

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, html)

    def test_neo4j_runtime_and_streamlit_evidence_use_live_docker_assets(self):
        html = self.read_html()
        required_assets = [
            "assets/neo4j-live-overview.png",
            "assets/neo4j-live-minmin.png",
            "assets/streamlit-minmin-query.png",
            "assets/streamlit-rio-query.png",
            "assets/streamlit-lumi-query.png",
            "assets/streamlit-rowan-query.png",
        ]
        required_text = [
            'data-slide-id="neo4j-graph-evidence"',
            'data-slide-id="neo4j-minmin-evidence"',
            'data-slide-id="runtime-filter-query"',
            'data-slide-id="runtime-gates-visual"',
            'data-slide-id="prompt-build-process"',
            'data-slide-id="streamlit-minmin-query"',
            'data-slide-id="streamlit-rio-query"',
            'data-slide-id="streamlit-lumi-query"',
            'data-slide-id="streamlit-rowan-query"',
            "NPC-[:KNOWS]->KnowledgeChunk",
            "MATCH (:NPC {npc_id: $npc_id})-[:KNOWS]->(k:KnowledgeChunk)",
            "$player_role IN k.allowed_roles",
            "k.hint_level <= $allowed_hint_level",
            "k.answer_sensitive = false OR $quest_state IN",
            "get_allowed_chunks",
            "build_prompt",
            "stream_gemma_response",
            "/v1/chat/completions",
            "stream=true",
            "실제 Docker Neo4j 캡처",
            "실제 Docker Streamlit 캡처",
            "캡처 메타데이터",
            "http://127.0.0.1:17474",
            "http://127.0.0.1:18501",
        ]

        for asset in required_assets:
            with self.subTest(asset=asset):
                self.assertIn(asset, html)
                self.assertTrue((PRESENTATION_DIR / asset).exists(), f"missing asset: {asset}")

        for text in required_text:
            with self.subTest(text=text):
                self.assertIn(text, html)

        stale_text = [
            "Docker가 중지된 상태",
            "기존 Streamlit 질의 캡처를 그대로 활용했다",
            "신규 live capture는 만들지 않았다",
            "KnowledgeChunk 22개",
        ]
        for text in stale_text:
            with self.subTest(text=text):
                self.assertNotIn(text, html)

    def test_image_pages_have_at_most_one_image(self):
        html = self.read_html()
        slides = cast(
            list[str],
            re.findall(r'<section class="slide.*?</section>', html, re.DOTALL),
        )

        self.assertTrue(slides, "expected slides in presentation")
        for index, slide in enumerate(slides, start=1):
            image_count = slide.count("<img ")
            with self.subTest(slide=index):
                self.assertLessEqual(image_count, 1)

    def test_all_npc_query_examples_are_documented(self):
        html = self.read_html()
        required = [
            'data-slide-id="npc-query-matrix"',
            'data-slide-id="npc-query-minmin"',
            'data-slide-id="npc-query-rio"',
            'data-slide-id="npc-query-lumi"',
            'data-slide-id="npc-query-rowan"',
            "민민 부인 질의 예시",
            "순찰대장 리오 질의 예시",
            "마도사 루미 질의 예시",
            "헤이즐 촌장 로완 질의 예시",
            "몽실버섯이 왜 빛나는지 정답만 알려줘",
            "말랑돼지가 왜 같은 방향으로 움직였는지 순찰 기록으로 말해줘",
            "방울젤리 색 변화와 버섯 빛이 같은 현상인지 설명해줘",
            "필수 단서가 모였을 때 최종 대조 결과를 정리해줘",
            "minmin_lady",
            "patrol_leader_rio",
            "mage_lumi",
            "chief_rowan",
        ]

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, html)

    def test_detailed_process_structure_is_not_a_simple_five_node_chain(self):
        html = self.read_html()
        required = [
            'data-slide-id="full-process-blueprint"',
            'data-slide-id="source-to-graph-detail"',
            'data-slide-id="runtime-process-detail"',
            'data-slide-id="operations-feedback-loop"',
            "process-swimlane",
            "process-step-grid",
            "frontmatter parse",
            "story-chunk fence scan",
            "import plan validation",
            "relationship upsert",
            "sidebar state",
            "Cypher gate",
            "prompt assembly",
            "streaming response",
            "debug expander",
        ]

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, html)

    def test_operations_server_apply_is_documented(self):
        html = self.read_html()
        required = [
            'data-slide-id="production-apply-overview"',
            'data-slide-id="production-commands"',
            'data-slide-id="production-env"',
            'data-slide-id="production-verify"',
            "git pull --ff-only origin main",
            "cp .env.example .env",
            "docker compose --env-file .env build streamlit",
            "docker compose --env-file .env up -d neo4j streamlit",
            "--source-dir rsc/data",
            "운영 DB에는 기본적으로 --reset을 붙이지 않는다",
            "NEO4J_URI",
            "NEO4J_PASSWORD",
            "VLLM_URL",
            "MODEL_NAME",
            "google/gemma-4-E2B-it",
        ]

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, html)

    def test_access_details_navigation_and_forbidden_phrasing(self):
        html = self.read_html()
        js = (PRESENTATION_DIR / "deck.js").read_text(encoding="utf-8")
        required = [
            "docker compose --env-file .env.design-test.example -f compose.design-test.yaml --profile gpu up -d",
            "http://127.0.0.1:17474",
            "bolt://127.0.0.1:17687",
            "http://127.0.0.1:18501",
            "http://127.0.0.1:18000/v1/models",
            "neo4j / admin2026",
            "prevSlide",
            "nextSlide",
            "slideCounter",
        ]
        forbidden = [
            "발표에서는",
            "발표 중",
            "발표 시",
            "발표에서",
            "qa-thumb",
            "Streamlit 질문 테스트 결과 매트릭스",
            "개발 프로젝트 handoff deck의 시각 기준",
        ]

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, html)

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, html)

        self.assertIn("ArrowRight", js)
        self.assertIn("ArrowLeft", js)
        self.assertIn("currentSlide", js)

    def test_deck_font_sizes_stay_within_requested_point_range(self):
        css = self.read_css()
        font_size_matches = cast(
            list[tuple[str, str]],
            re.findall(r"font-size:\s*(?:clamp\()?([0-9.]+)(px|pt)", css),
        )
        sizes: list[float] = []

        for value, unit in font_size_matches:
            size = float(value)
            sizes.append(size if unit == "pt" else size * 0.75)

        self.assertTrue(sizes, "expected explicit font-size declarations")
        self.assertGreaterEqual(min(sizes), 9)
        self.assertLessEqual(max(sizes), 21)

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
