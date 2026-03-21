"""Edge case tests for Worker B's calibration components."""

import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine, _t_sf
from engine.domain_classifier import (
    classify_domain,
    classify_horizon,
    classify_complexity,
    stance_to_probability,
    compute_holdout_flag,
    generate_prediction_id,
    load_taxonomy,
)
from engine.calibration_models import PredictionDomain


class TestEdgeDomainClassifier:
    """Edge cases for domain classifier."""

    def test_empty_string(self):
        """Empty question text should return UNCLASSIFIED."""
        taxonomy = load_taxonomy(None)
        assert classify_domain("", taxonomy) == PredictionDomain.UNCLASSIFIED

    def test_very_long_text(self):
        """Very long text should not crash."""
        taxonomy = load_taxonomy(None)
        long_text = "technology software " * 10000
        result = classify_domain(long_text, taxonomy)
        assert result is not None

    def test_special_characters(self):
        """Text with special characters should not crash."""
        taxonomy = load_taxonomy(None)
        result = classify_domain("Will @#$% technology *&^! launch?!?", taxonomy)
        assert result is not None

    def test_unicode_text(self):
        """Unicode text should not crash."""
        taxonomy = load_taxonomy(None)
        result = classify_domain("Will technology launch?", taxonomy)
        assert result is not None


class TestEdgeHorizonClassifier:
    """Edge cases for horizon classifier."""

    def test_empty_timeframe(self):
        """Empty timeframe should return default MEDIUM."""
        from engine.calibration_models import PredictionHorizon
        result = classify_horizon("")
        assert result == PredictionHorizon.MEDIUM

    def test_numeric_only_timeframe(self):
        """Purely numeric timeframe should default to MEDIUM."""
        from engine.calibration_models import PredictionHorizon
        result = classify_horizon("42")
        assert result == PredictionHorizon.MEDIUM


class TestEdgeStanceToProbability:
    """Edge cases for stance_to_probability."""

    def test_stance_boundary_minus_one(self):
        assert stance_to_probability(-1.0) == 0.0

    def test_stance_boundary_plus_one(self):
        assert stance_to_probability(1.0) == 1.0

    def test_stance_out_of_range_high(self):
        """stance > 1.0 -- should still compute (no clamping in spec)."""
        result = stance_to_probability(2.0)
        assert result == 1.5  # (2 + 1) / 2 = 1.5

    def test_stance_out_of_range_low(self):
        """stance < -1.0 -- should still compute (no clamping in spec)."""
        result = stance_to_probability(-2.0)
        assert result == -0.5  # (-2 + 1) / 2 = -0.5


class TestEdgeCalibrationEngine:
    """Edge cases for CalibrationEngine."""

    def test_duplicate_question_id_outcome(self):
        """Recording outcome for same question twice should update only once."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.7, confidence=0.7,
                base_rate_anchor="test", timeframe="3 month",
            )
            result1 = engine.record_outcome("q1", "r1", True, "test")
            result2 = engine.record_outcome("q1", "r1", True, "test")

            # Second call should update 0 (already resolved)
            assert result2["predictions_updated"] == 0

    def test_nonexistent_question_outcome(self):
        """Recording outcome for nonexistent question should update 0."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            result = engine.record_outcome("nonexistent", "r1", True, "test")
            assert result["predictions_updated"] == 0

    def test_prediction_with_probability_zero(self):
        """Extreme probability 0.0 should be accepted."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            pred = engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.0, confidence=0.5,
                base_rate_anchor="test", timeframe="3 month",
            )
            assert pred.forecast_probability == 0.0

    def test_prediction_with_probability_one(self):
        """Extreme probability 1.0 should be accepted."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            pred = engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=1.0, confidence=0.5,
                base_rate_anchor="test", timeframe="3 month",
            )
            assert pred.forecast_probability == 1.0

    def test_engine_persistence_survives_reload(self):
        """Data should survive engine reload from same directory."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create and populate
            engine1 = CalibrationEngine(Path(tmp))
            engine1.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.7, confidence=0.7,
                base_rate_anchor="test", timeframe="3 month",
            )

            # Reload from same directory
            engine2 = CalibrationEngine(Path(tmp))
            assert len(engine2._predictions) == 1
            assert engine2._predictions[0]["forecast_probability"] == 0.7


class TestEdgeTDistribution:
    """Edge cases for t-distribution implementation."""

    def test_t_sf_negative_df(self):
        """Negative df should return 0.5 (guard)."""
        assert _t_sf(2.0, -1) == 0.5

    def test_t_sf_zero_df(self):
        """df=0 should return 0.5 (guard)."""
        assert _t_sf(2.0, 0) == 0.5

    def test_t_sf_very_large_t(self):
        """Very large t should give p near 0."""
        p = _t_sf(100.0, 10)
        assert p < 0.001, f"Very large t should give tiny p, got {p}"

    def test_t_sf_df1_known_value(self):
        """t(df=1) = Cauchy. P(T > 1 | df=1) = 0.25 exactly."""
        p = _t_sf(1.0, 1)
        assert abs(p - 0.25) < 0.01


class TestEdgeCorrectionSchedule:
    """Edge cases for correction schedule stages."""

    def test_stage_record_only_at_run1(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.7, confidence=0.7,
                base_rate_anchor="test", timeframe="3 month",
            )
            engine.record_outcome("q1", "r1", True, "test")
            metrics = engine.get_ensemble_metrics()
            assert metrics.correction_schedule_stage == "RECORD_ONLY"

    def test_stage_domain_additive_at_run3(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for r in range(3):
                engine.record_prediction(
                    run_id=f"r{r}", archetype_id="a1", question_id=f"q-{r}",
                    question_text="Will the technology software platform launch?",
                    forecast_probability=0.7, confidence=0.7,
                    base_rate_anchor="test", timeframe="3 month",
                )
                engine.record_outcome(f"q-{r}", f"r{r}", True, "test")
            metrics = engine.get_ensemble_metrics()
            assert metrics.correction_schedule_stage == "DOMAIN_ADDITIVE"
