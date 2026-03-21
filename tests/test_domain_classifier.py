"""Tests for engine/domain_classifier.py"""

import pytest

from engine.calibration_models import (
    PredictionDomain,
    PredictionHorizon,
    QuestionComplexity,
)
from engine.domain_classifier import (
    classify_domain,
    classify_horizon,
    classify_complexity,
    compute_holdout_flag,
    generate_prediction_id,
    load_taxonomy,
    stance_to_probability,
)


@pytest.fixture
def taxonomy():
    return load_taxonomy()


class TestClassifyDomain:
    def test_policy_domain(self, taxonomy):
        text = "Will Congress pass new legislation on election regulation?"
        assert classify_domain(text, taxonomy) == PredictionDomain.POLICY

    def test_economics_domain(self, taxonomy):
        text = "Will the stock market recession cause GDP to decline?"
        assert classify_domain(text, taxonomy) == PredictionDomain.ECONOMICS

    def test_technology_domain(self, taxonomy):
        text = "Will AI software adoption reach 50% in the cloud computing sector?"
        assert classify_domain(text, taxonomy) == PredictionDomain.TECHNOLOGY

    def test_science_domain(self, taxonomy):
        text = "Will the clinical trial for the new cancer vaccine succeed?"
        assert classify_domain(text, taxonomy) == PredictionDomain.SCIENCE

    def test_environment_domain(self, taxonomy):
        text = "Will carbon emissions from fossil fuel cause temperature rise?"
        assert classify_domain(text, taxonomy) == PredictionDomain.ENVIRONMENT

    def test_social_domain(self, taxonomy):
        text = "Will consumer culture trend shift toward lifestyle education?"
        assert classify_domain(text, taxonomy) == PredictionDomain.SOCIAL

    def test_unclassified_domain(self, taxonomy):
        text = "What time is it?"
        assert classify_domain(text, taxonomy) == PredictionDomain.UNCLASSIFIED

    def test_case_insensitive(self, taxonomy):
        text = "Will CONGRESS pass new LEGISLATION?"
        assert classify_domain(text, taxonomy) == PredictionDomain.POLICY

    def test_deterministic(self, taxonomy):
        text = "Will the government impose new sanctions and tariff policies?"
        result1 = classify_domain(text, taxonomy)
        result2 = classify_domain(text, taxonomy)
        assert result1 == result2

    def test_highest_match_wins(self, taxonomy):
        # Economy has 3 matches, policy has 1 -> ECONOMICS wins
        text = "The market economy stock performance and government outlook"
        result = classify_domain(text, taxonomy)
        assert result == PredictionDomain.ECONOMICS


class TestClassifyHorizon:
    def test_short_week(self):
        assert classify_horizon("next week") == PredictionHorizon.SHORT

    def test_short_1_month(self):
        """SK-07 fix: '1 month' should be SHORT, not MEDIUM."""
        assert classify_horizon("1 month") == PredictionHorizon.SHORT

    def test_medium_quarter(self):
        assert classify_horizon("next quarter") == PredictionHorizon.MEDIUM

    def test_medium_3_month(self):
        assert classify_horizon("3 month outlook") == PredictionHorizon.MEDIUM

    def test_long_year(self):
        assert classify_horizon("by end of year") == PredictionHorizon.LONG

    def test_long_6_month(self):
        assert classify_horizon("6 month forecast") == PredictionHorizon.LONG

    def test_extended_years(self):
        assert classify_horizon("over the next 5 years") == PredictionHorizon.EXTENDED

    def test_extended_decade(self):
        assert classify_horizon("next decade") == PredictionHorizon.EXTENDED

    def test_default_medium(self):
        assert classify_horizon("sometime soon") == PredictionHorizon.MEDIUM

    def test_days_is_short(self):
        assert classify_horizon("within 10 days") == PredictionHorizon.SHORT


class TestClassifyComplexity:
    def test_simple_binary(self):
        text = "Will Bitcoin reach $100,000 by December?"
        assert classify_complexity(text) == QuestionComplexity.SIMPLE_BINARY

    def test_multi_factor(self):
        text = "How will trade sanctions affect the downstream impact on the ecosystem?"
        assert classify_complexity(text) == QuestionComplexity.MULTI_FACTOR

    def test_multi_factor_interaction(self):
        text = "What is the interaction between stakeholder interests and system outcomes?"
        assert classify_complexity(text) == QuestionComplexity.MULTI_FACTOR

    def test_single_indicator_not_enough(self):
        text = "How will this affect the outcome?"
        # Only "how will" and "affect" -> 2 matches -> MULTI_FACTOR
        assert classify_complexity(text) == QuestionComplexity.MULTI_FACTOR

    def test_zero_indicators(self):
        text = "Will it rain tomorrow?"
        assert classify_complexity(text) == QuestionComplexity.SIMPLE_BINARY


class TestComputeHoldoutFlag:
    def test_deterministic(self):
        pid = "abcdef1234567890"
        assert compute_holdout_flag(pid) == compute_holdout_flag(pid)

    def test_approximately_20_percent(self):
        """Property test: holdout rate is approximately 20% over many IDs."""
        holdout_count = 0
        total = 10000
        for i in range(total):
            pid = generate_prediction_id(f"run_{i}", "arch_0", "q_0")
            if compute_holdout_flag(pid):
                holdout_count += 1
        rate = holdout_count / total
        assert 0.18 <= rate <= 0.22, f"Holdout rate {rate} not near 20%"

    def test_direct_hex_parsing(self):
        """SK-09 fix: prediction_id parsed directly as hex, not double-hashed."""
        # "a" in hex = 10, 10 % 5 == 0 -> holdout
        assert compute_holdout_flag("a") is True
        # "1" in hex = 1, 1 % 5 != 0 -> not holdout
        assert compute_holdout_flag("1") is False


class TestGeneratePredictionId:
    def test_deterministic(self):
        id1 = generate_prediction_id("run1", "arch1", "q1")
        id2 = generate_prediction_id("run1", "arch1", "q1")
        assert id1 == id2

    def test_different_inputs_different_ids(self):
        id1 = generate_prediction_id("run1", "arch1", "q1")
        id2 = generate_prediction_id("run1", "arch1", "q2")
        assert id1 != id2

    def test_length_16(self):
        pid = generate_prediction_id("run1", "arch1", "q1")
        assert len(pid) == 16

    def test_hex_string(self):
        pid = generate_prediction_id("run1", "arch1", "q1")
        int(pid, 16)  # Should not raise


class TestStanceToProbability:
    def test_negative_one(self):
        assert stance_to_probability(-1.0) == 0.0

    def test_zero(self):
        assert stance_to_probability(0.0) == 0.5

    def test_positive_one(self):
        assert stance_to_probability(1.0) == 1.0

    def test_midpoint_negative(self):
        assert stance_to_probability(-0.5) == 0.25

    def test_midpoint_positive(self):
        assert stance_to_probability(0.5) == 0.75

    def test_linear_mapping(self):
        """Verify the mapping is linear across the range."""
        for stance in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            expected = (stance + 1.0) / 2.0
            assert stance_to_probability(stance) == expected


class TestLoadTaxonomy:
    def test_default_taxonomy(self):
        taxonomy = load_taxonomy()
        assert len(taxonomy.domains) == 6
        assert "POLICY" in taxonomy.domains
        assert "ECONOMICS" in taxonomy.domains
        assert "TECHNOLOGY" in taxonomy.domains
        assert "SCIENCE" in taxonomy.domains
        assert "ENVIRONMENT" in taxonomy.domains
        assert "SOCIAL" in taxonomy.domains
        assert taxonomy.min_keyword_matches == 2

    def test_from_config_file(self, tmp_path):
        from pathlib import Path
        import json

        config = {
            "domains": {
                "TEST": {"keywords": ["test", "example"], "description": "Test domain"},
            },
            "min_keyword_matches": 1,
        }
        config_path = tmp_path / "taxonomy.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        taxonomy = load_taxonomy(config_path)
        assert len(taxonomy.domains) == 1
        assert "TEST" in taxonomy.domains
        assert taxonomy.min_keyword_matches == 1

    def test_nonexistent_path_returns_default(self):
        from pathlib import Path
        taxonomy = load_taxonomy(Path("/nonexistent/path.json"))
        assert len(taxonomy.domains) == 6
