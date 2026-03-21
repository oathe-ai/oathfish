"""Integration / cross-worker verification tests for Worker D."""

import os
import re
import ast

from tests.verify_0001_worker_d.conftest import (
    PROJECT_ROOT, ARCHETYPES_DIR, AGENTS_DIR, ENGINE_DIR,
    ARCHETYPE_NAMES, read_sdk, read_file,
)


class TestAmplificationSDKImportsWorkerA:
    def test_import_statement_correct(self):
        assert re.search(r"from\s+\.models\s+import\s+PredictionPosition", read_sdk())

    def test_archetype_import_correct(self):
        assert re.search(r"from\s+\.models\s+import.*Archetype", read_sdk())

    def test_prediction_position_fields_match(self):
        models_src = read_file(os.path.join(ENGINE_DIR, "models.py"))
        tree = ast.parse(models_src)
        pp_fields = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "PredictionPosition":
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        pp_fields.add(item.target.id)
        expected = {"archetype_id", "round_n", "prediction", "decision", "stance",
                    "confidence", "timeframe", "base_rate_anchor", "key_uncertainties",
                    "falsification_criteria", "second_order_effects",
                    "cascade_susceptibility", "coalition_alignment"}
        for f in expected:
            assert f in pp_fields, f"PredictionPosition missing: {f}"

    def test_prediction_position_has_13_fields(self):
        tree = ast.parse(read_file(os.path.join(ENGINE_DIR, "models.py")))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "PredictionPosition":
                fields = [i for i in node.body if isinstance(i, ast.AnnAssign)]
                assert len(fields) == 13, f"Expected 13, found {len(fields)}"
                return
        assert False, "PredictionPosition not found"

    def test_archetype_has_worker_d_extensions(self):
        s = read_file(os.path.join(ENGINE_DIR, "models.py"))
        for f in ["is_structural", "archetype_type", "stubbornness_domain",
                   "grounding_search_queries", "persona_prompt", "grounding_rung"]:
            assert f in s, f"Archetype missing field: {f}"


class TestArchetypeAgentReferencesSkill:
    def test_skill_reference_in_frontmatter(self):
        c = read_file(os.path.join(AGENTS_DIR, "archetype-agent.md"))
        assert re.search(r"skills:.*archetype-reasoning", c, re.DOTALL)

    def test_agent_has_memory_project(self):
        c = read_file(os.path.join(AGENTS_DIR, "archetype-agent.md"))
        assert re.search(r"memory:\s*project", c)


class TestStructuralArchetypesAtCorrectPath:
    def test_directory_exists(self):
        assert os.path.isdir(ARCHETYPES_DIR)

    def test_all_four_files_at_correct_path(self):
        expected = {"historian.md", "systems-thinker.md", "contrarian.md", "probabilist.md"}
        actual = {f for f in os.listdir(ARCHETYPES_DIR) if f.endswith(".md")}
        assert expected == actual, f"Expected {expected}, found {actual}"


class TestSDKReferencesClaudeAgentSDK:
    def test_imports_claude_agent_sdk(self):
        assert re.search(r"from\s+claude_agent_sdk\s+import", read_sdk())

    def test_imports_query_function(self):
        assert "query" in read_sdk()

    def test_imports_claude_agent_options(self):
        assert "ClaudeAgentOptions" in read_sdk()

    def test_uses_output_format_json_schema(self):
        assert re.search(r'output_format.*json_schema|"type".*"json_schema"', read_sdk())
