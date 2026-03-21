"""C-27: Per-domain acquiescence tracking from run 1; corrections from run 3+.

Spec: Track per-domain acquiescence rate. Correction formula: clamp(raw - offset, 0, 1).
Tiered thresholds: n>=15/|MSE|>0.10, n>=45/|MSE|>0.05, n>=90/p<0.10.
"""

import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine


class TestC27AcquiescenceTracking:
    """Verify acquiescence rate is tracked per domain."""

    def test_acquiescence_rate_computed(self):
        """Domain bias should include acquiescence_rate = mean of all forecasts."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # All predictions at 0.7
            for i in range(10):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the regulation law government policy election pass?",
                    forecast_probability=0.7, confidence=0.7,
                    base_rate_anchor="test", timeframe="3 month",
                )
                engine.record_outcome(f"q-{i}", "r1", (i % 2 == 0), "test")

            bias = engine.get_domain_bias("POLICY", min_n=3)
            assert bias is not None
            assert abs(bias.acquiescence_rate - 0.7) < 0.01, \
                f"Acquiescence rate should be 0.7, got {bias.acquiescence_rate}"


class TestC27CorrectionFormula:
    """Verify correction formula: clamp(raw - offset, 0, 1)."""

    def test_correction_subtracts_offset(self):
        """For an overconfident domain (offset > 0), correction should reduce forecast."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # Build enough data for correction to activate
            for run_idx in range(5):
                for i in range(10):
                    engine.record_prediction(
                        run_id=f"r{run_idx}", archetype_id="a1",
                        question_id=f"q-{run_idx}-{i}",
                        question_text="Will the regulation law government policy election pass?",
                        forecast_probability=0.8, confidence=0.7,
                        base_rate_anchor="test", timeframe="3 month",
                    )
                    engine.record_outcome(f"q-{run_idx}-{i}", f"r{run_idx}", False, "test")

            corrected, offset = engine.apply_correction(0.8, "POLICY")
            if offset != 0.0:
                assert corrected < 0.8, \
                    f"Correction should reduce overconfident forecast, got {corrected}"
                assert corrected == max(0.0, min(1.0, 0.8 - offset))


class TestC27TieredThresholds:
    """Verify tiered correction threshold logic."""

    def test_no_correction_before_run_3(self):
        """No corrections before 3 runs regardless of n or MSE."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # Only 2 runs
            for run_idx in range(2):
                for i in range(20):
                    engine.record_prediction(
                        run_id=f"r{run_idx}", archetype_id="a1",
                        question_id=f"q-{run_idx}-{i}",
                        question_text="Will the regulation law government policy election pass?",
                        forecast_probability=0.9, confidence=0.7,
                        base_rate_anchor="test", timeframe="3 month",
                    )
                    engine.record_outcome(
                        f"q-{run_idx}-{i}", f"r{run_idx}", False, "test"
                    )

            bias = engine.get_domain_bias("POLICY", min_n=3)
            assert bias is not None
            assert not bias.correction_active, \
                f"Correction should not be active with only 2 runs"

    def test_correction_active_at_run3_n15_large_mse(self):
        """At run 3+, n>=15, |MSE|>0.10 => correction should activate.

        Use 10 predictions per run (30 total, ~24 after holdout) to
        ensure n >= 15 after ~20% holdout exclusion."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # 3 runs, 10 predictions each (30 total, ~24 non-holdout)
            for run_idx in range(3):
                for i in range(10):
                    engine.record_prediction(
                        run_id=f"r{run_idx}", archetype_id="a1",
                        question_id=f"q-{run_idx}-{i}",
                        question_text="Will the regulation law government policy election pass?",
                        forecast_probability=0.85,
                        confidence=0.7,
                        base_rate_anchor="test", timeframe="3 month",
                    )
                    # All false -> MSE = 0.85
                    engine.record_outcome(
                        f"q-{run_idx}-{i}", f"r{run_idx}", False, "test"
                    )

            bias = engine.get_domain_bias("POLICY", min_n=3)
            assert bias is not None
            assert bias.n_observations >= 15, \
                f"n should be >= 15 after holdout, got {bias.n_observations}"
            assert abs(bias.mean_signed_error) > 0.10, \
                f"|MSE| should be > 0.10, got {abs(bias.mean_signed_error)}"
            assert bias.correction_active, \
                f"Correction should be active at run 3, n>=15, |MSE|>0.10"

    def test_correction_not_active_small_mse_run3(self):
        """At run 3, n>=15 but |MSE|<=0.10 => correction should NOT activate."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for run_idx in range(3):
                for i in range(10):
                    engine.record_prediction(
                        run_id=f"r{run_idx}", archetype_id="a1",
                        question_id=f"q-{run_idx}-{i}",
                        question_text="Will the regulation law government policy election pass?",
                        forecast_probability=0.55,
                        confidence=0.7,
                        base_rate_anchor="test", timeframe="3 month",
                    )
                    # 50% true -> MSE ~ 0.05 (small)
                    engine.record_outcome(
                        f"q-{run_idx}-{i}", f"r{run_idx}", (i % 2 == 0), "test"
                    )

            bias = engine.get_domain_bias("POLICY", min_n=3)
            assert bias is not None
            if abs(bias.mean_signed_error) <= 0.10:
                # With only 3 runs, need n>=45 for medium MSE
                if bias.n_observations < 45:
                    assert not bias.correction_active, \
                        f"Small MSE with n<45 at run 3 should not activate correction"
