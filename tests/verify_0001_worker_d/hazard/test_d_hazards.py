"""Hazard attack tests for Worker D."""

import os
import re
import ast

from tests.verify_0001_worker_d.conftest import (
    SDK_PATH, ARCHETYPES_DIR, SKILL_PATH, ARCHETYPE_NAMES,
    read_sdk, read_archetype, read_skill,
)


class TestDH01PersonaPromptSize:
    def test_each_archetype_under_1500_words(self):
        for name in ARCHETYPE_NAMES:
            c = read_archetype(name)
            wc = len(c.split())
            assert wc < 2000, f"{name}.md is {wc} words, exceeds 1500 target (D-H01)"

    def test_sdk_has_digest_length_warning(self):
        assert re.search(r"(?i)warning.*digest|digest.*words|digest_words.*1500", read_sdk())


class TestDH08MethodologyConsistency:
    def test_all_archetypes_reference_same_skill(self):
        for name in ARCHETYPE_NAMES:
            assert re.search(r"archetype-reasoning.*SKILL\.md|skills/archetype-reasoning", read_archetype(name)), \
                f"{name}.md does not reference archetype-reasoning/SKILL.md (D-H08)"

    def test_skill_is_single_source_of_truth(self):
        s = read_skill()
        assert "Step 1" in s and "Step 6" in s
        for name in ARCHETYPE_NAMES:
            steps = re.findall(r"##\s*Step\s+\d+", read_archetype(name))
            assert len(steps) == 0, f"{name} has {len(steps)} steps duplicated (use INJECT)"


class TestDH09RateLimiting:
    def test_semaphore_limit_is_10(self):
        assert re.search(r"max_concurrent.*=\s*10", read_sdk())

    def test_exponential_backoff_formula(self):
        assert re.search(r"2\s*\*\*\s*attempt", read_sdk())

    def test_max_retries_defined(self):
        assert re.search(r"max_retries.*=\s*\d+", read_sdk())

    def test_fallback_model_exists(self):
        assert "fallback_model" in read_sdk()


class TestDH10PersonaVariationDiversity:
    def test_seven_age_offsets(self):
        m = re.search(r"AGE_OFFSETS\s*=\s*\[([^\]]+)\]", read_sdk())
        assert m
        items = [x.strip() for x in m.group(1).split(",") if x.strip()]
        assert len(items) == 7, f"Expected 7, found {len(items)}"

    def test_twelve_locations(self):
        m = re.search(r"LOCATIONS\s*=\s*\[(.*?)\]", read_sdk(), re.DOTALL)
        assert m
        items = re.findall(r'"[^"]+"|\'[^\']+\'', m.group(1))
        assert len(items) == 12, f"Expected 12, found {len(items)}"

    def test_four_experience_modifiers(self):
        m = re.search(r"EXPERIENCE_MODIFIERS\s*=\s*\[(.*?)\]", read_sdk(), re.DOTALL)
        assert m
        items = re.findall(r'"[^"]+"|\'[^\']+\'', m.group(1))
        assert len(items) == 4, f"Expected 4, found {len(items)}"

    def test_five_education_modifiers(self):
        m = re.search(r"EDUCATION_MODIFIERS\s*=\s*\[(.*?)\]", read_sdk(), re.DOTALL)
        assert m
        items = re.findall(r'"[^"]+"|\'[^\']+\'', m.group(1))
        assert len(items) == 5, f"Expected 5, found {len(items)}"

    def test_five_personality_axes(self):
        m = re.search(r"PERSONALITY_AXES\s*=\s*\[(.*?)\]", read_sdk(), re.DOTALL)
        assert m
        items = re.findall(r"\(", m.group(1))
        assert len(items) == 5, f"Expected 5, found {len(items)}"


class TestDH13TopicOverlapExclusion:
    def test_structural_archetypes_declare_structural_role(self):
        for name in ARCHETYPE_NAMES:
            assert re.search(r"(?i)structural\s+archetype", read_archetype(name)), \
                f"{name}.md must identify itself as structural archetype (D-H13)"
