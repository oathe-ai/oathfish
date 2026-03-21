"""Constraint verification: C-29, C-30, C-33, C-36, C-37."""

import os
import re

from tests.verify_0001_worker_d.conftest import (
    ARCHETYPES_DIR, SKILL_PATH, ARCHETYPE_NAMES, AGENTS_DIR,
    read_archetype, read_skill, read_file,
)


class TestC29GroundingSources:
    def test_historian_real_authors_cited(self):
        found = [a for a in ["Perez", "Tetlock", "Gartner", "Olson"]
                 if a.lower() in read_archetype("historian").lower()]
        assert len(found) >= 3, f"Found {found}, need 3+"

    def test_systems_thinker_real_authors_cited(self):
        found = [a for a in ["Meadows", "Taleb", "Arthur", "Santa Fe"]
                 if a.lower() in read_archetype("systems-thinker").lower()]
        assert len(found) >= 3, f"Found {found}, need 3+"

    def test_contrarian_real_authors_cited(self):
        found = [a for a in ["Chanos", "Morozov", "Ormerod", "Taleb"]
                 if a.lower() in read_archetype("contrarian").lower()]
        assert len(found) >= 3, f"Found {found}, need 3+"

    def test_probabilist_real_authors_cited(self):
        found = [a for a in ["Tetlock", "Kahneman", "Silver", "Brier"]
                 if a.lower() in read_archetype("probabilist").lower()]
        assert len(found) >= 3, f"Found {found}, need 3+"

    def test_sources_are_specific_works(self):
        for name in ARCHETYPE_NAMES:
            c = read_archetype(name)
            gs = c.lower().find("grounding sources")
            if gs == -1: continue
            section = c[gs:]
            nh = re.search(r"\n##\s", section[1:])
            if nh: section = section[:nh.start() + 1]
            assert re.search(r'(?i)"[^"]{10,}"|[A-Z][a-z]+,\s*"[^"]+"|framework|methodology', section), \
                f"{name} grounding must include specific works"


class TestC30SuperforecasterInEveryArchetype:
    def test_skill_contains_all_six_steps(self):
        s = read_skill()
        for i in range(1, 7):
            assert f"Step {i}" in s

    def test_every_archetype_references_methodology(self):
        for name in ARCHETYPE_NAMES:
            c = read_archetype(name)
            has_inject = "[INJECT" in c and "SKILL.md" in c
            has_section = bool(re.search(r"(?i)superforecaster\s+methodology", c))
            assert has_inject or has_section, f"{name} must reference methodology (C-30)"

    def test_archetype_agent_template_references_skill(self):
        c = read_file(os.path.join(AGENTS_DIR, "archetype-agent.md"))
        assert "archetype-reasoning" in c


class TestC33NoNumericPredictions:
    def test_every_archetype_has_c33_rule(self):
        for name in ARCHETYPE_NAMES:
            assert re.search(r"(?i)no\s+numeric|arguments?\s+only", read_archetype(name))

    def test_every_archetype_mentions_round_6_prediction(self):
        for name in ARCHETYPE_NAMES:
            assert re.search(r"(?i)round\s*6|independent.*prediction|PredictionPosition", read_archetype(name))


class TestC36FourStructuralArchetypes:
    def test_all_four_files_exist(self):
        for name in ARCHETYPE_NAMES:
            assert os.path.isfile(os.path.join(ARCHETYPES_DIR, f"{name}.md"))

    def test_exactly_four_files_in_directory(self):
        md = [f for f in os.listdir(ARCHETYPES_DIR) if f.endswith(".md")]
        assert len(md) == 4, f"Expected 4, found {len(md)}: {md}"


class TestC37EpistemicLensInvariant:
    def test_all_use_lens_language(self):
        for name in ARCHETYPE_NAMES:
            assert "EPISTEMIC LENS" in read_archetype(name)

    def test_none_define_persona_demographics(self):
        for name in ARCHETYPE_NAMES:
            c = read_archetype(name)
            assert not re.search(r"(?i)^income:", c, re.MULTILINE)
            assert not re.search(r"(?i)^occupation:", c, re.MULTILINE)

    def test_framework_over_identity(self):
        for name in ARCHETYPE_NAMES:
            assert re.search(r"(?i)analytical\s+framework|your\s+analytical", read_archetype(name))
