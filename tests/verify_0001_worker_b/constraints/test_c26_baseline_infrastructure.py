"""C-26: A/B test -- run baseline amplification BEFORE deliberation every run.

Spec says: Baseline vs deliberation-informed predictions compared in every report.
Verify: Separate storage for baseline vs informed predictions.
"""

import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine


class TestC26BaselineInfrastructure:
    """Verify baseline predictions can be stored and distinguished from informed."""

    def test_baseline_flag_stored(self):
        """Predictions with is_baseline=True should be stored as such."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            pred = engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.6, confidence=0.7,
                base_rate_anchor="test", timeframe="3 month",
                is_baseline=True,
            )
            assert pred.is_baseline is True

    def test_informed_flag_stored(self):
        """Predictions with is_baseline=False (default) are informed."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            pred = engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.6, confidence=0.7,
                base_rate_anchor="test", timeframe="3 month",
            )
            assert pred.is_baseline is False

    def test_baseline_excluded_from_domain_bias_by_default(self):
        """Domain bias computation should exclude baseline by default."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # Add only baseline predictions
            for i in range(10):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the regulation law government policy election pass?",
                    forecast_probability=0.8, confidence=0.7,
                    base_rate_anchor="test", timeframe="3 month",
                    is_baseline=True,
                )
                engine.record_outcome(f"q-{i}", "r1", False, "test")

            bias = engine.get_domain_bias("POLICY", min_n=3, exclude_baseline=True)
            assert bias is None, "Baseline-only data should be excluded from domain bias"

    def test_ab_comparison_separates_baseline_and_informed(self):
        """get_deliberation_comparison should separate baseline from informed."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # Baseline predictions
            for i in range(5):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="How will this technology software AI product affect the ecosystem between stakeholders?",
                    forecast_probability=0.6, confidence=0.7,
                    base_rate_anchor="test", timeframe="3 month",
                    is_baseline=True,
                )
            # Informed predictions (same questions)
            for i in range(5):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-informed-{i}",
                    question_text="How will this technology software AI product affect the ecosystem between stakeholders?",
                    forecast_probability=0.65, confidence=0.7,
                    base_rate_anchor="test", timeframe="3 month",
                    is_baseline=False,
                )
            # Resolve all
            for i in range(5):
                engine.record_outcome(f"q-{i}", "r1", True, "test")
                engine.record_outcome(f"q-informed-{i}", "r1", True, "test")

            comparison = engine.get_deliberation_comparison()
            # Should have strata
            assert "strata" in comparison
            assert "recommendation" in comparison

    def test_deliberation_delta_positive_means_helps(self):
        """Spec: deliberation_delta = baseline - informed. Positive = deliberation helps."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # Baseline predictions: bad (0.3 for True outcomes -> Brier = 0.49)
            for i in range(10):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"qb-{i}",
                    question_text="Will the technology software platform launch?",
                    forecast_probability=0.3, confidence=0.7,
                    base_rate_anchor="test", timeframe="3 month",
                    is_baseline=True,
                )
                engine.record_outcome(f"qb-{i}", "r1", True, "test")

            # Informed predictions: better (0.8 for True outcomes -> Brier = 0.04)
            for i in range(10):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"qi-{i}",
                    question_text="Will the technology software platform launch?",
                    forecast_probability=0.8, confidence=0.7,
                    base_rate_anchor="test", timeframe="3 month",
                    is_baseline=False,
                )
                engine.record_outcome(f"qi-{i}", "r1", True, "test")

            metrics = engine.get_ensemble_metrics()
            assert metrics.deliberation_delta is not None
            assert metrics.deliberation_delta > 0, \
                f"When informed is better, delta should be positive, got {metrics.deliberation_delta}"
