"""Edge case tests for Worker D components."""

import os
import re
import ast

from tests.verify_0001_worker_d.conftest import (
    SDK_PATH, SKILL_PATH, ARCHETYPE_NAMES, read_sdk, read_archetype, read_skill,
)


class TestEdgeSDKRobustness:
    def test_error_result_has_is_error_flag(self):
        assert re.search(r"is_error.*=\s*True", read_sdk())

    def test_error_result_has_error_message(self):
        assert "error_message" in read_sdk()

    def test_progress_tracks_retries(self):
        assert "retried" in read_sdk()

    def test_zero_archetypes_handled(self):
        assert re.search(r"total.*=.*len.*archetypes.*\*.*variations", read_sdk())

    def test_calls_per_second_handles_zero_elapsed(self):
        assert re.search(r"elapsed.*==\s*0|elapsed.*<=\s*0", read_sdk())

    def test_async_nature_of_engine(self):
        tree = ast.parse(read_sdk())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "AmplificationEngine":
                methods = {n.name: n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
                assert "run" in methods
                assert isinstance(methods["run"], ast.AsyncFunctionDef)

    def test_single_call_is_async(self):
        tree = ast.parse(read_sdk())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "AmplificationEngine":
                methods = {n.name: n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
                for m in ["_execute_single_call", "_do_call"]:
                    if m in methods:
                        assert isinstance(methods[m], ast.AsyncFunctionDef), f"{m} must be async"


class TestEdgeArchetypeContent:
    def test_no_empty_sections(self):
        for name in ARCHETYPE_NAMES:
            lines = read_archetype(name).splitlines()
            for i, line in enumerate(lines):
                if line.startswith("## "):
                    found_content = False
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if lines[j].strip():
                            found_content = True
                            break
                    assert found_content, f"{name} empty section at line {i+1}: {line}"

    def test_rules_section_exists(self):
        for name in ARCHETYPE_NAMES:
            assert re.search(r"##\s+Rules", read_archetype(name))

    def test_role_section_exists(self):
        for name in ARCHETYPE_NAMES:
            assert re.search(r"##\s+Your\s+Role", read_archetype(name))

    def test_framework_section_exists(self):
        for name in ARCHETYPE_NAMES:
            assert re.search(r"(?i)##\s+Your\s+Analytical\s+Framework", read_archetype(name))


class TestEdgeSkillContent:
    def test_step_numbering_is_sequential(self):
        steps = re.findall(r"##\s+Step\s+(\d+)", read_skill())
        assert [int(s) for s in steps] == [1, 2, 3, 4, 5, 6]

    def test_no_broken_markdown_links(self):
        broken = re.findall(r"\[([^\]]+)\]\(\)", read_skill())
        assert len(broken) == 0, f"Broken links: {broken}"

    def test_table_has_header_separator(self):
        c = read_skill()
        tables = re.findall(r"\|.*\|", c)
        if len(tables) >= 2:
            assert re.search(r"\|[\s-]+\|", c)
