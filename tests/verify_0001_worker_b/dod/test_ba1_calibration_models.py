"""DoD: B-A.1 -- All calibration Pydantic models validate and serialize.

Spec says: CalibrationPrediction, CalibrationOutcome, DomainBias,
ArchetypeBias, EnsembleMetrics, HoldoutReport, CompetenceAssessment.
PredictionDomain enum: 7 values. PredictionHorizon: 4 values.
QuestionComplexity: 2 values.
"""

from datetime import datetime, timezone
from engine.calibration_models import (
    CalibrationPrediction,
    CalibrationOutcome,
    DomainBias,
    ArchetypeBias,
    EnsembleMetrics,
    HoldoutReport,
    CompetenceAssessment,
    PredictionDomain,
    PredictionHorizon,
    QuestionComplexity,
    DomainTaxonomyConfig,
)

UTC = timezone.utc


class TestBA1ModelsExist:
    """Verify all spec-required models are importable."""

    def test_calibration_prediction_exists(self):
        assert CalibrationPrediction is not None

    def test_calibration_outcome_exists(self):
        assert CalibrationOutcome is not None

    def test_domain_bias_exists(self):
        assert DomainBias is not None

    def test_archetype_bias_exists(self):
        assert ArchetypeBias is not None

    def test_ensemble_metrics_exists(self):
        assert EnsembleMetrics is not None

    def test_holdout_report_exists(self):
        assert HoldoutReport is not None

    def test_competence_assessment_exists(self):
        assert CompetenceAssessment is not None


class TestBA1Enums:
    """Verify enum values match spec."""

    def test_prediction_domain_has_7_values(self):
        """Spec: POLICY, ECONOMICS, TECHNOLOGY, SCIENCE, ENVIRONMENT, SOCIAL, UNCLASSIFIED"""
        assert len(PredictionDomain) == 7
        expected = {"POLICY", "ECONOMICS", "TECHNOLOGY", "SCIENCE",
                    "ENVIRONMENT", "SOCIAL", "UNCLASSIFIED"}
        actual = {d.value for d in PredictionDomain}
        assert actual == expected, f"PredictionDomain values: {actual} != {expected}"

    def test_prediction_horizon_has_4_values(self):
        """Spec: SHORT, MEDIUM, LONG, EXTENDED"""
        assert len(PredictionHorizon) == 4
        expected = {"SHORT", "MEDIUM", "LONG", "EXTENDED"}
        actual = {h.value for h in PredictionHorizon}
        assert actual == expected

    def test_question_complexity_has_2_values(self):
        """Spec: SIMPLE_BINARY, MULTI_FACTOR"""
        assert len(QuestionComplexity) == 2
        expected = {"SIMPLE_BINARY", "MULTI_FACTOR"}
        actual = {c.value for c in QuestionComplexity}
        assert actual == expected


class TestBA1Serialization:
    """Verify models serialize and deserialize correctly."""

    def test_calibration_prediction_roundtrip(self):
        pred = CalibrationPrediction(
            prediction_id="abc123",
            run_id="r1",
            archetype_id="a1",
            question_id="q1",
            question_text="test",
            domain=PredictionDomain.TECHNOLOGY,
            horizon=PredictionHorizon.SHORT,
            complexity=QuestionComplexity.SIMPLE_BINARY,
            forecast_probability=0.7,
            confidence=0.8,
            base_rate_anchor="50% historical",
            is_holdout=False,
            created_at=datetime.now(UTC),
        )
        dumped = pred.model_dump_json()
        restored = CalibrationPrediction.model_validate_json(dumped)
        assert restored.prediction_id == pred.prediction_id
        assert restored.forecast_probability == pred.forecast_probability

    def test_ensemble_metrics_delta_convention(self):
        """Spec: POSITIVE = IMPROVEMENT.
        brier_gap = raw - corrected. deliberation_delta = baseline - informed."""
        metrics = EnsembleMetrics(
            brier_raw=0.20, brier_corrected=0.18, brier_gap=0.02,
            brier_baseline=0.25, brier_informed=0.20, deliberation_delta=0.05,
            acquiescence_rate=0.57, n_predictions=100, n_resolved=50,
            n_holdout=10, brier_holdout=0.19, brier_training=0.18,
            overfitting_gap=0.01, overfitting_detected=False,
            domain_biases=[], correction_schedule_stage="DOMAIN_ADDITIVE",
            window_runs=5,
        )
        assert metrics.brier_gap == 0.02  # raw - corrected
        assert metrics.deliberation_delta == 0.05  # baseline - informed
        # Both positive = improvement
        assert metrics.brier_gap > 0
        assert metrics.deliberation_delta > 0

    def test_forecast_probability_bounded(self):
        """forecast_probability must be [0, 1]."""
        import pytest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CalibrationPrediction(
                prediction_id="abc", run_id="r1", archetype_id="a1",
                question_id="q1", question_text="test",
                domain=PredictionDomain.TECHNOLOGY,
                horizon=PredictionHorizon.SHORT,
                complexity=QuestionComplexity.SIMPLE_BINARY,
                forecast_probability=1.5,  # > 1.0 should fail
                confidence=0.8, base_rate_anchor="test",
                is_holdout=False, created_at=datetime.now(UTC),
            )

    def test_confidence_bounded(self):
        """confidence must be [0, 1]."""
        import pytest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CalibrationPrediction(
                prediction_id="abc", run_id="r1", archetype_id="a1",
                question_id="q1", question_text="test",
                domain=PredictionDomain.TECHNOLOGY,
                horizon=PredictionHorizon.SHORT,
                complexity=QuestionComplexity.SIMPLE_BINARY,
                forecast_probability=0.5,
                confidence=-0.1,  # < 0.0 should fail
                base_rate_anchor="test",
                is_holdout=False, created_at=datetime.now(UTC),
            )
