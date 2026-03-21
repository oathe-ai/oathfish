"""Research grounding verification -- verifies CONTENT is research-backed."""

import re

from tests.verify_0001_worker_d.conftest import (
    ARCHETYPE_NAMES, read_archetype, read_skill, read_sdk,
)


class TestSuperforecasterMethodologyAccuracy:
    def test_base_rate_anchoring(self):
        assert re.search(r"(?i)base\s*rate.*anchor|anchor.*base\s*rate", read_skill())

    def test_decomposition_methodology(self):
        assert re.search(r"(?i)decompos.*sub.*question|break.*question.*sub", read_skill())

    def test_calibration_discipline(self):
        assert re.search(r"(?i)calibrat.*confidence|confidence.*calibrat", read_skill())

    def test_falsification_criteria(self):
        assert re.search(r"(?i)falsif.*criteria|wrong\s+if", read_skill())

    def test_overconfidence_check(self):
        assert re.search(r"(?i)overconfiden|all.*confidence.*above.*80|recalibrat", read_skill())


class TestPersonaFidelityGrounding:
    def test_historian_has_specific_statistics(self):
        assert re.search(r"\d+%", read_archetype("historian"))

    def test_historian_has_specific_date_ranges(self):
        assert re.search(r"since\s+\d{4}|since\s+year|\d{4}", read_archetype("historian"))

    def test_systems_thinker_has_specific_framework_elements(self):
        c = read_archetype("systems-thinker").lower()
        found = [x for x in ["reinforcing", "balancing", "leverage point", "feedback loop", "delay", "cascade"]
                 if x in c]
        assert len(found) >= 4, f"Found {len(found)}/6: {found}"

    def test_contrarian_has_structural_adversarial_not_random(self):
        assert re.search(r"(?i)structurally\s+adversarial|not\s+random", read_archetype("contrarian"))

    def test_contrarian_references_steel_man(self):
        assert re.search(r"(?i)steel.man", read_archetype("contrarian"))

    def test_probabilist_has_bayesian_mechanics(self):
        assert re.search(r"(?i)prior.*posterior|likelihood\s+ratio|bayes.*rule", read_archetype("probabilist"))


class TestAntiAcquiescenceDesign:
    def test_historian_as_anti_acquiescence(self):
        assert re.search(r"(?i)anti.acquiescence|acquiescence", read_archetype("historian"))

    def test_stubbornness_is_principled(self):
        for name in ARCHETYPE_NAMES:
            assert re.search(r"(?i)structurally\s+stubborn", read_archetype(name))

    def test_arguments_only_rounds_1_5(self):
        for name in ARCHETYPE_NAMES:
            assert re.search(r"(?i)round.*1.*5.*argument|argument.*only|no\s+numeric.*prediction", read_archetype(name))


class TestSDKResearchAlignment:
    def test_baseline_before_informed(self):
        assert re.search(r"(?i)BASELINE.*stateless|baseline.*no.*session|C-26", read_sdk())

    def test_tool_free_amplification(self):
        assert re.search(r"allowed_tools.*=.*\[\]|tool.free", read_sdk())

    def test_digest_cost_efficiency(self):
        assert re.search(r"(?i)500.*1000\s*token|digest.*token|cost.*cheaper|50.*100x", read_sdk())
