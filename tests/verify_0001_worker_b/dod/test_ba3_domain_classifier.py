"""DoD: B-A.3 -- Domain classifier is deterministic + stance_to_probability correct.

Spec says:
- classify_domain(): keyword matching, returns PredictionDomain
- classify_horizon(): order extended -> long -> short -> medium
- classify_complexity(): SIMPLE_BINARY vs MULTI_FACTOR
- stance_to_probability(): (stance + 1) / 2
- compute_holdout_flag(): int(prediction_id, 16) % 5 == 0
"""

from engine.domain_classifier import (
    classify_domain,
    classify_horizon,
    classify_complexity,
    stance_to_probability,
    compute_holdout_flag,
    generate_prediction_id,
    load_taxonomy,
)
from engine.calibration_models import (
    PredictionDomain,
    PredictionHorizon,
    QuestionComplexity,
)


class TestBA3StanceToProbability:
    """Verify stance_to_probability: (stance + 1) / 2."""

    def test_stance_minus_one_gives_zero(self):
        """stance=-1 => probability=0"""
        assert stance_to_probability(-1.0) == 0.0

    def test_stance_zero_gives_half(self):
        """stance=0 => probability=0.5"""
        assert stance_to_probability(0.0) == 0.5

    def test_stance_plus_one_gives_one(self):
        """stance=+1 => probability=1"""
        assert stance_to_probability(1.0) == 1.0

    def test_formula_is_linear(self):
        """Verify the formula is exactly (stance + 1) / 2."""
        for stance in [-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]:
            expected = (stance + 1.0) / 2.0
            actual = stance_to_probability(stance)
            assert abs(actual - expected) < 1e-10, \
                f"stance_to_probability({stance}) = {actual}, expected {expected}"


class TestBA3HorizonOrdering:
    """Verify horizon classification order: extended -> long -> short -> medium.

    Critical: "1 month" must classify as SHORT, not MEDIUM.
    SK-07 fix: short checked before medium to avoid substring mismatch.
    """

    def test_1_month_is_short(self):
        """'1 month' should be SHORT, NOT MEDIUM."""
        assert classify_horizon("1 month") == PredictionHorizon.SHORT

    def test_3_month_is_medium(self):
        """'3 month' should be MEDIUM."""
        assert classify_horizon("3 month") == PredictionHorizon.MEDIUM

    def test_2_weeks_is_short(self):
        assert classify_horizon("2 weeks") == PredictionHorizon.SHORT

    def test_6_month_is_long(self):
        assert classify_horizon("6 month") == PredictionHorizon.LONG

    def test_3_years_is_extended(self):
        assert classify_horizon("3 years") == PredictionHorizon.EXTENDED

    def test_decade_is_extended(self):
        assert classify_horizon("decade") == PredictionHorizon.EXTENDED

    def test_default_is_medium(self):
        """Unknown timeframes default to MEDIUM."""
        assert classify_horizon("whenever") == PredictionHorizon.MEDIUM


class TestBA3Determinism:
    """Verify all classifiers are deterministic."""

    def test_domain_deterministic(self):
        taxonomy = load_taxonomy(None)
        d1 = classify_domain("Will the regulation law government policy pass?", taxonomy)
        d2 = classify_domain("Will the regulation law government policy pass?", taxonomy)
        assert d1 == d2

    def test_horizon_deterministic(self):
        h1 = classify_horizon("3 month")
        h2 = classify_horizon("3 month")
        assert h1 == h2

    def test_complexity_deterministic(self):
        c1 = classify_complexity("How will AI affect the ecosystem?")
        c2 = classify_complexity("How will AI affect the ecosystem?")
        assert c1 == c2

    def test_holdout_deterministic(self):
        pid = "abcdef0123456789"
        f1 = compute_holdout_flag(pid)
        f2 = compute_holdout_flag(pid)
        assert f1 == f2

    def test_prediction_id_deterministic(self):
        id1 = generate_prediction_id("r1", "a1", "q1")
        id2 = generate_prediction_id("r1", "a1", "q1")
        assert id1 == id2
