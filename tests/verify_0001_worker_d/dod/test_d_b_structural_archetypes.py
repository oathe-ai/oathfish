"""DoD D-B.1 through D-B.4: Structural archetype prompts."""

import os
import re
import pytest

from tests.verify_0001_worker_d.conftest import (
    ARCHETYPE_FILES, ARCHETYPE_NAMES, ARCHETYPES_DIR, read_archetype,
)


class TestAllFourExist:
    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_file_exists(self, name):
        assert os.path.isfile(ARCHETYPE_FILES[name]), f"Missing: {ARCHETYPE_FILES[name]}"


class TestEpistemicLensLanguage:
    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_contains_epistemic_lens(self, name):
        assert "EPISTEMIC LENS" in read_archetype(name), f"{name}.md must contain 'EPISTEMIC LENS'"

    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_contains_not_stakeholder(self, name):
        assert re.search(r"(?i)not\s+a\s+stakeholder", read_archetype(name))

    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_no_demographic_identity(self, name):
        c = read_archetype(name)
        assert not re.search(r"(?i)^age:\s*\d+", c, re.MULTILINE)
        assert not re.search(r"(?i)^gender:", c, re.MULTILINE)


class TestGroundingSources:
    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_has_grounding_section(self, name):
        assert re.search(r"(?i)grounding\s+sources", read_archetype(name))

    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_rung_3_claimed(self, name):
        assert re.search(r"(?i)rung\s*3|domain.grounded", read_archetype(name))

    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_at_least_5_sources(self, name):
        c = read_archetype(name)
        gs = c.lower().find("grounding sources")
        section = c[gs:]
        nh = re.search(r"\n##\s", section[1:])
        if nh: section = section[:nh.start() + 1]
        sources = re.findall(r"^-\s+.+", section, re.MULTILINE)
        assert len(sources) >= 5, f"{name} has {len(sources)} sources, need 5+"

    def test_historian_has_perez(self):
        assert re.search(r"(?i)perez", read_archetype("historian"))

    def test_historian_has_gartner(self):
        assert re.search(r"(?i)gartner", read_archetype("historian"))

    def test_historian_has_tetlock(self):
        assert re.search(r"(?i)tetlock", read_archetype("historian"))

    def test_systems_thinker_has_meadows(self):
        assert re.search(r"(?i)meadows", read_archetype("systems-thinker"))

    def test_systems_thinker_has_taleb(self):
        assert re.search(r"(?i)taleb", read_archetype("systems-thinker"))

    def test_contrarian_has_failure_literature(self):
        assert re.search(r"(?i)why\s+most\s+things\s+fail|ormerod", read_archetype("contrarian"))

    def test_contrarian_has_short_seller(self):
        assert re.search(r"(?i)short.seller|chanos", read_archetype("contrarian"))

    def test_probabilist_has_tetlock(self):
        assert re.search(r"(?i)tetlock|superforecasting", read_archetype("probabilist"))

    def test_probabilist_has_kahneman(self):
        assert re.search(r"(?i)kahneman", read_archetype("probabilist"))


class TestStubbornnessDomainsDistinct:
    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_has_stubbornness_section(self, name):
        assert re.search(r"(?i)stubbornness\s+domain|structurally\s+stubborn", read_archetype(name))

    def test_historian_stubborn_on_base_rates(self):
        s = read_archetype("historian")[read_archetype("historian").lower().find("stubbornness"):]
        assert re.search(r"(?i)base\s*rate|historical", s)

    def test_systems_thinker_stubborn_on_second_order(self):
        s = read_archetype("systems-thinker")[read_archetype("systems-thinker").lower().find("stubbornness"):]
        assert re.search(r"(?i)second.order|feedback", s)

    def test_contrarian_stubborn_on_dissent(self):
        s = read_archetype("contrarian")[read_archetype("contrarian").lower().find("stubbornness"):]
        assert re.search(r"(?i)dissent|consensus|contrarian", s)

    def test_probabilist_stubborn_on_calibration(self):
        s = read_archetype("probabilist")[read_archetype("probabilist").lower().find("stubbornness"):]
        assert re.search(r"(?i)calibration|uncertainty|probabilistic", s)


class TestMethodologyInjection:
    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_references_methodology(self, name):
        assert re.search(r"(?i)superforecaster|methodology|archetype-reasoning", read_archetype(name))

    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_inject_tag_present(self, name):
        c = read_archetype(name)
        assert re.search(r"\[INJECT.*SKILL\.md\]|skills/archetype-reasoning", c)


class TestC33Compliance:
    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_no_numbers_rule(self, name):
        assert re.search(r"(?i)no\s+numeric|argument.*only", read_archetype(name))

    @pytest.mark.parametrize("name", ARCHETYPE_NAMES)
    def test_round_6_prediction_mentioned(self, name):
        assert re.search(r"(?i)round\s*6.*prediction|prediction.*round\s*6|independent.*prediction", read_archetype(name))


class TestUniqueFrameworks:
    def test_historian_framework_content(self):
        assert re.search(r"(?i)historical\s+pattern|base\s+rate|cycle\s+aware", read_archetype("historian"))

    def test_systems_thinker_framework_content(self):
        assert re.search(r"(?i)feedback\s+loop|leverage\s+point|cascade|network\s+effect", read_archetype("systems-thinker"))

    def test_contrarian_framework_content(self):
        assert re.search(r"(?i)consensus\s+attack|failure\s+mode|minority\s+report|adversarial", read_archetype("contrarian"))

    def test_probabilist_framework_content(self):
        assert re.search(r"(?i)bayesian|calibration|joint\s+probability|uncertainty\s+quantif", read_archetype("probabilist"))

    def test_no_framework_overlap(self):
        historian = read_archetype("historian")
        for name, content in [("systems-thinker", read_archetype("systems-thinker")),
                              ("contrarian", read_archetype("contrarian")),
                              ("probabilist", read_archetype("probabilist"))]:
            gs = content.lower().find("grounding")
            fw = content[:gs] if gs > 0 else content
            assert "gartner" not in fw.lower(), f"{name} should not use Gartner in its framework"
