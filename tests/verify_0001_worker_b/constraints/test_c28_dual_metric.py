"""C-28: Report both calibration-corrected AND raw uncorrected Brier scores.

Spec says: Dual metrics in every quantitative output.
"""

import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine


class TestC28DualMetricReporting:
    """Verify both corrected and uncorrected Brier are reported."""

    def test_ensemble_metrics_has_both_brier_fields(self):
        """EnsembleMetrics must have brier_raw AND brier_corrected."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            metrics = engine.get_ensemble_metrics()
            assert hasattr(metrics, 'brier_raw'), "Missing brier_raw field"
            assert hasattr(metrics, 'brier_corrected'), "Missing brier_corrected field"

    def test_ensemble_metrics_has_brier_gap(self):
        """EnsembleMetrics must have brier_gap = raw - corrected."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            metrics = engine.get_ensemble_metrics()
            assert hasattr(metrics, 'brier_gap'), "Missing brier_gap field"

    def test_with_data_both_brier_computed(self):
        """With resolved predictions, both Brier scores should be real numbers."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for i in range(5):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the technology software platform launch?",
                    forecast_probability=0.7, confidence=0.7,
                    base_rate_anchor="test", timeframe="3 month",
                )
                engine.record_outcome(f"q-{i}", "r1", (i % 2 == 0), "test")

            metrics = engine.get_ensemble_metrics()
            assert isinstance(metrics.brier_raw, float)
            assert isinstance(metrics.brier_corrected, float)
            assert metrics.brier_raw >= 0
            assert metrics.brier_corrected >= 0

    def test_baseline_brier_field_exists(self):
        """Must also have brier_baseline and brier_informed for A/B."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            metrics = engine.get_ensemble_metrics()
            assert hasattr(metrics, 'brier_baseline'), "Missing brier_baseline"
            assert hasattr(metrics, 'brier_informed'), "Missing brier_informed"
            assert hasattr(metrics, 'deliberation_delta'), "Missing deliberation_delta"
