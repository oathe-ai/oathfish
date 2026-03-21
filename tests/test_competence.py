"""Tests for engine/competence_classifier.py"""

from __future__ import annotations

import pytest
from pathlib import Path

from engine.calibration_engine import CalibrationEngine
from engine.calibration_models import PredictionDomain, QuestionComplexity
from engine.competence_classifier import classify_question


@pytest.fixture
def engine(tmp_path):
    return CalibrationEngine(tmp_path)


class TestClassifyQuestion:
    def test_simple_binary_skip_deliberate(self, engine):
        """SIMPLE_BINARY questions should route to SKIP_DELIBERATE."""
        result = classify_question(
            "Will Congress pass the new election regulation law?",
            engine,
        )
        assert result.complexity == QuestionComplexity.SIMPLE_BINARY
        assert result.routing_recommendation == "SKIP_DELIBERATE"

    def test_multi_factor_full_pipeline(self, engine):
        """MULTI_FACTOR questions should route to FULL_PIPELINE."""
        result = classify_question(
            "How will government regulation affect the downstream impact on the ecosystem of stakeholder interests?",
            engine,
        )
        assert result.complexity == QuestionComplexity.MULTI_FACTOR
        assert result.routing_recommendation == "FULL_PIPELINE"

    def test_unclassified_low_confidence(self, engine):
        """Unclassifiable questions should route to LOW_CONFIDENCE."""
        result = classify_question(
            "What time is it?",
            engine,
        )
        assert result.domain == PredictionDomain.UNCLASSIFIED
        assert result.routing_recommendation == "LOW_CONFIDENCE"
        assert "UNCLASSIFIED_DOMAIN" in result.flags

    def test_uncalibrated_domain_flagged(self, engine):
        """Domain with no calibration data should be flagged."""
        result = classify_question(
            "Will Congress pass new legislation on election regulation?",
            engine,
        )
        assert "UNCALIBRATED_DOMAIN" in result.flags

    def test_domain_with_calibration_data(self, engine):
        """Domain with calibration data should not have UNCALIBRATED flag."""
        # Record some calibration data in POLICY domain
        engine.record_prediction(
            run_id="run1", archetype_id="a1", question_id="q1",
            question_text="Will government regulation ban this policy?",
            forecast_probability=0.7, confidence=0.8,
            base_rate_anchor="50%", timeframe="3 month",
        )
        engine.record_outcome("q1", "run1", True, "news")

        result = classify_question(
            "Will Congress pass new legislation on election regulation?",
            engine,
        )
        assert "UNCALIBRATED_DOMAIN" not in result.flags

    def test_works_with_empty_engine(self, engine):
        """Classifier works with no prediction data at all."""
        result = classify_question("Will AI transform computing?", engine)
        assert result.domain is not None
        assert result.routing_recommendation in ("SKIP_DELIBERATE", "FULL_PIPELINE", "LOW_CONFIDENCE")

    def test_confidence_value(self, engine):
        """Confidence should be between 0 and 1."""
        result = classify_question(
            "Will government regulation policy legislation ban mandate this?",
            engine,
        )
        assert 0.0 <= result.confidence_in_classification <= 1.0

    def test_low_confidence_flag(self, engine):
        """Low keyword match count should flag LOW_CLASSIFICATION_CONFIDENCE."""
        result = classify_question(
            "Will there be a new policy?",
            engine,
        )
        # Only "policy" matches (1 match), confidence = 1/5 = 0.2 < 0.4
        if result.confidence_in_classification < 0.4:
            assert "LOW_CLASSIFICATION_CONFIDENCE" in result.flags

    def test_domain_classification_passthrough(self, engine):
        """Domain should match what classify_domain would return."""
        result = classify_question(
            "Will the stock market recession cause GDP decline?",
            engine,
        )
        assert result.domain == PredictionDomain.ECONOMICS

    def test_multi_factor_uncalibrated_still_full_pipeline(self, engine):
        """MULTI_FACTOR with uncalibrated domain should still route to FULL_PIPELINE."""
        result = classify_question(
            "How will government regulation affect the downstream impact of this policy?",
            engine,
        )
        assert result.complexity == QuestionComplexity.MULTI_FACTOR
        assert result.routing_recommendation == "FULL_PIPELINE"
