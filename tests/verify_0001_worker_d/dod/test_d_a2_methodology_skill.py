"""DoD D-A.2: skills/archetype-reasoning/SKILL.md -- Superforecaster methodology protocol.
DoD D-A.3: 4-rung grounding rubric with criteria and examples.
"""

import os
import re

from tests.verify_0001_worker_d.conftest import SKILL_PATH, read_skill


class TestMethodologySkillExists:
    def test_skill_file_exists(self):
        assert os.path.isfile(SKILL_PATH), f"SKILL.md not found at {SKILL_PATH}"


class TestMethodologySkillFrontmatter:
    def test_has_frontmatter(self):
        content = read_skill()
        assert content.startswith("---"), "SKILL.md must start with YAML frontmatter"
        second_fence = content.index("---", 3)
        assert second_fence > 3, "Frontmatter must have closing ---"

    def test_name_field(self):
        content = read_skill()
        assert re.search(r"^name:\s*archetype-reasoning", content, re.MULTILINE)

    def test_user_invocable_false(self):
        content = read_skill()
        assert re.search(r"^user-invocable:\s*false", content, re.MULTILINE)

    def test_has_description(self):
        content = read_skill()
        assert re.search(r"^description:", content, re.MULTILINE)


class TestMethodologySixSteps:
    def test_step1_base_rate(self):
        assert re.search(r"(?i)step\s*1.*base\s*rate", read_skill())

    def test_step2_decompose(self):
        assert re.search(r"(?i)step\s*2.*decompose", read_skill())

    def test_step3_uncertainties(self):
        assert re.search(r"(?i)step\s*3.*uncertaint", read_skill())

    def test_step4_falsification(self):
        assert re.search(r"(?i)step\s*4.*falsif", read_skill())

    def test_step5_second_order(self):
        assert re.search(r"(?i)step\s*5.*second.order", read_skill())

    def test_step6_calibrate(self):
        assert re.search(r"(?i)step\s*6.*calibrat", read_skill())

    def test_all_six_steps_present(self):
        step_matches = re.findall(r"##\s*Step\s+(\d+)", read_skill())
        step_numbers = sorted(set(int(s) for s in step_matches))
        assert step_numbers == [1, 2, 3, 4, 5, 6], f"Expected 1-6, found: {step_numbers}"


class TestMethodologyOutputFormat:
    def test_output_format_section_exists(self):
        assert re.search(r"(?i)output\s*format", read_skill())

    def test_output_format_mentions_prediction(self):
        c = read_skill(); s = c[c.lower().find("output format"):]
        assert "prediction" in s.lower()

    def test_output_format_mentions_decision(self):
        c = read_skill(); s = c[c.lower().find("output format"):]
        assert "decision" in s.lower()

    def test_output_format_mentions_base_rate_anchor(self):
        c = read_skill(); s = c[c.lower().find("output format"):]
        assert "base_rate" in s.lower() or "base rate" in s.lower()

    def test_output_format_mentions_falsification(self):
        c = read_skill(); s = c[c.lower().find("output format"):]
        assert "falsification" in s.lower()

    def test_output_format_mentions_second_order(self):
        c = read_skill(); s = c[c.lower().find("output format"):]
        assert "second_order" in s.lower() or "second order" in s.lower()

    def test_output_format_mentions_confidence(self):
        c = read_skill(); s = c[c.lower().find("output format"):]
        assert "confidence" in s.lower()


class TestGroundingRungRubric:
    def test_rubric_section_exists(self):
        assert re.search(r"(?i)grounding.*rubric|rung.*rubric", read_skill())

    def test_all_four_rungs(self):
        c = read_skill()
        rungs = {i for i in [1, 2, 3, 4] if f"| {i} |" in c or f"Rung {i}" in c}
        assert rungs == {1, 2, 3, 4}, f"Expected all 4 rungs, found: {rungs}"


class TestSkillSizeLimit:
    def test_under_500_lines(self):
        n = len(read_skill().splitlines())
        assert n < 500, f"SKILL.md is {n} lines, must be under 500"

    def test_under_100_lines_for_preloading(self):
        n = len(read_skill().splitlines())
        assert n < 100, f"SKILL.md is {n} lines; C-H10 targets under 100"
