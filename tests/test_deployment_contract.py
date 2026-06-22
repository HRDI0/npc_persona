import unittest
from pathlib import Path
from subprocess import run
from typing import cast, final

import yaml


ROOT = Path(__file__).resolve().parents[1]
TARGET_MODEL = "google/gemma-4-E4B-it"
DESIGN_TEST_MODEL = "google/gemma-4-E2B-it"


@final
class DeploymentContractTest(unittest.TestCase):
    def test_docker_compose_defines_mvp_services_and_defaults(self):
        compose_path = ROOT / "compose.yaml"
        self.assertTrue(compose_path.exists())

        compose = cast(
            dict[str, object],
            yaml.safe_load(compose_path.read_text(encoding="utf-8")),
        )
        services = cast(dict[str, dict[str, object]], compose["services"])

        self.assertIn("neo4j", services)
        self.assertIn("streamlit", services)
        self.assertIn("vllm", services)
        neo4j_ports = cast(list[str], services["neo4j"]["ports"])
        streamlit_ports = cast(list[str], services["streamlit"]["ports"])
        vllm_profiles = cast(list[str], services["vllm"]["profiles"])
        neo4j_env = cast(dict[str, str], services["neo4j"]["environment"])
        self.assertEqual(["127.0.0.1:7474:7474", "127.0.0.1:7687:7687"], neo4j_ports)
        self.assertEqual(["127.0.0.1:8501:8501"], streamlit_ports)
        self.assertIn("gpu", vllm_profiles)
        self.assertIn("NEO4J_AUTH", neo4j_env)
        self.assertNotIn("NEO4J_USER", neo4j_env)
        self.assertNotIn("NEO4J_PASSWORD", neo4j_env)

        streamlit_env = cast(dict[str, str], services["streamlit"]["environment"])
        self.assertEqual("bolt://neo4j:7687", streamlit_env["NEO4J_URI"])
        self.assertIn("admin2026", streamlit_env["NEO4J_PASSWORD"])
        self.assertIn(TARGET_MODEL, streamlit_env["MODEL_NAME"])

        vllm_command = cast(list[str], services["vllm"]["command"])
        self.assertIn("${VLLM_GPU_MEMORY_UTILIZATION:-0.9}", vllm_command)
        self.assertIn("${VLLM_MAX_MODEL_LEN:-4096}", vllm_command)

    def test_local_vllm_services_expose_readiness_before_streamlit_uses_them(self):
        for compose_name in ["compose.yaml", "compose.design-test.yaml"]:
            with self.subTest(compose=compose_name):
                compose = cast(
                    dict[str, object],
                    yaml.safe_load((ROOT / compose_name).read_text(encoding="utf-8")),
                )
                services = cast(dict[str, dict[str, object]], compose["services"])
                vllm = services["vllm"]
                healthcheck = cast(dict[str, object], vllm["healthcheck"])
                self.assertIn("/health", " ".join(cast(list[str], healthcheck["test"])))

                streamlit_depends_on = cast(
                    dict[str, dict[str, object]],
                    services["streamlit"]["depends_on"],
                )
                self.assertEqual("service_healthy", streamlit_depends_on["vllm"]["condition"])
                self.assertIs(False, streamlit_depends_on["vllm"]["required"])

    def test_compose_files_validate_without_gpu_profile_for_ubuntu_server(self):
        for compose_name, env_name in [
            ("compose.yaml", ".env.example"),
            ("compose.design-test.yaml", ".env.design-test.example"),
        ]:
            with self.subTest(compose=compose_name):
                result = run(
                    [
                        "docker",
                        "compose",
                        "--env-file",
                        env_name,
                        "-f",
                        compose_name,
                        "config",
                        "--quiet",
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                self.assertEqual("", result.stderr, result.stderr)
                self.assertEqual(0, result.returncode)

    def test_dockerfile_env_example_and_docs_exist(self):
        for relative_path in [
            "Dockerfile",
            ".dockerignore",
            ".env.example",
            "docs/db_design.md",
            "docs/deployment.md",
            "scripts/story_pipeline/run_pipeline.py",
        ]:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).exists())

        db_design = (ROOT / "docs" / "db_design.md").read_text(encoding="utf-8")
        deployment = (ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")

        self.assertIn("KnowledgeChunk", db_design)
        self.assertIn("NPCs: 4", db_design)
        self.assertIn("KnowledgeChunks: 26", db_design)
        self.assertIn("git pull --ff-only origin main", deployment)
        self.assertIn("docker compose up -d neo4j streamlit", deployment)

    def test_design_test_stack_is_isolated_and_uses_project_model(self):
        compose_path = ROOT / "compose.design-test.yaml"
        self.assertTrue(compose_path.exists())

        compose = cast(
            dict[str, object],
            yaml.safe_load(compose_path.read_text(encoding="utf-8")),
        )
        self.assertEqual("hazel_design_test", compose["name"])
        services = cast(dict[str, dict[str, object]], compose["services"])
        self.assertEqual(["127.0.0.1:17474:7474", "127.0.0.1:17687:7687"], services["neo4j"]["ports"])
        self.assertEqual(["127.0.0.1:18501:8501"], services["streamlit"]["ports"])
        self.assertEqual(["127.0.0.1:18000:8000"], services["vllm"]["ports"])

        streamlit_env = cast(dict[str, str], services["streamlit"]["environment"])
        self.assertEqual("bolt://neo4j:7687", streamlit_env["NEO4J_URI"])
        self.assertIn("http://vllm:8000/v1/chat/completions", streamlit_env["VLLM_URL"])
        self.assertIn(DESIGN_TEST_MODEL, streamlit_env["MODEL_NAME"])

        vllm = services["vllm"]
        vllm_command = cast(list[str], vllm["command"])
        vllm_volumes = cast(list[str], vllm["volumes"])
        self.assertIn("/models/gemma-4-E2B-it", vllm_command)
        self.assertIn("--served-model-name", vllm_command)
        self.assertIn(DESIGN_TEST_MODEL, vllm_command)
        self.assertIn("${VLLM_GPU_MEMORY_UTILIZATION:-0.9}", vllm_command)
        self.assertIn("${VLLM_MAX_MODEL_LEN:-4096}", vllm_command)
        self.assertIn("${LOCAL_MODEL_DIR:-./models/google-gemma-4-E2B-it}:/models/gemma-4-E2B-it:ro", vllm_volumes)

    def test_design_test_docs_env_and_download_script_exist(self):
        for relative_path in [
            ".env.design-test.example",
            "docs/design_test_docker.md",
            "scripts/download_model.ps1",
        ]:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).exists())

        env_example = (ROOT / ".env.design-test.example").read_text(encoding="utf-8")
        default_env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "design_test_docker.md").read_text(encoding="utf-8")
        script = (ROOT / "scripts" / "download_model.ps1").read_text(encoding="utf-8")

        self.assertIn(f"VLLM_MODEL={DESIGN_TEST_MODEL}", env_example)
        self.assertIn("NEO4J_DATABASE=neo4j", env_example)
        self.assertIn("NEO4J_DATABASE=neo4j", default_env_example)
        self.assertIn("LOCAL_MODEL_DIR=./models/google-gemma-4-E2B-it", env_example)
        self.assertIn("VLLM_GPU_MEMORY_UTILIZATION=0.9", env_example)
        self.assertIn("VLLM_MAX_MODEL_LEN=4096", env_example)
        hf_token_lines = [
            line
            for line in default_env_example.splitlines()
            if line.startswith("HF_TOKEN=")
        ]
        self.assertEqual(1, len(hf_token_lines))
        self.assertEqual("HF_TOKEN=", hf_token_lines[0])
        self.assertIn("Windows Docker Desktop", docs)
        self.assertIn("기존 Neo4j/vLLM", docs)
        self.assertIn("compose.design-test.yaml", docs)
        self.assertIn(DESIGN_TEST_MODEL, docs)
        self.assertIn(DESIGN_TEST_MODEL, script)
        self.assertIn("huggingface-cli download", script)

    def test_streamlit_project_does_not_depend_on_local_torch(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertNotIn('"torch', pyproject)
        self.assertIn('"python-dotenv', pyproject)

    def test_sensitive_local_artifacts_are_gitignored(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        for pattern in ["data_export/", ".hf-cache/", ".omo/", ".playwright-cli/", "__pycache__/", "models/", ".env.design-test", "playwright-report/", "test-results/", "workspace_source/"]:
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, gitignore)

    def test_docker_context_excludes_local_artifacts(self):
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

        for pattern in ["data_export/", ".hf-cache/", ".omo/", ".playwright-cli/", "__pycache__/", "models/", ".env.design-test", ".env.example", "playwright-report/", "test-results/", "workspace_source/", "output/", "output/playwright/"]:
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, dockerignore)

    def test_source_importer_defaults_to_canonical_rsc_data(self):
        importer = (ROOT / "src" / "db_control" / "import_story_source_to_neo4j.py").read_text(encoding="utf-8")

        self.assertIn('default="rsc/data"', importer)
        self.assertIn("Path to rsc/data source directory", importer)

    def test_deployment_docs_explain_vllm_runtime_requirement(self):
        deployment = (ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")

        self.assertIn("docker compose --profile gpu up -d neo4j vllm streamlit", deployment)
        self.assertIn("외부 vLLM", deployment)

    def test_expansion_guide_matches_current_mvp_defaults(self):
        guide = (ROOT / "docs" / "MVP_NPC_EXPANSION_GUIDE.md").read_text(encoding="utf-8")

        self.assertIn(f"MODEL_NAME=\"{TARGET_MODEL}\"", guide)
        self.assertNotIn("湲곕낯 紐⑤뜽紐낆씠 `google/gemma-4-E4B`", guide)
        self.assertIn("--model", guide)
        self.assertIn("/models/gemma-4-E4B-it", guide)
        self.assertIn("/models/gemma-4-E4B-it:ro", guide)
        self.assertIn("KnowledgeChunks: 26", guide)


if __name__ == "__main__":
    _ = unittest.main()

