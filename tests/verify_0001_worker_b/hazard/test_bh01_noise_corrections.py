"""B-H01: Noise corrections at small n.

Mitigation: Tiered thresholds.
Attack: Force corrections with very small n and verify they DON'T activate.
"""

import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine


class TestBH01NoiseCorrections:
    """Attack: Try to trigger corrections with insufficient data."""

    def test_no_correction_with_single_run(self):
        """With only 1 run (even large n), NO correction should activate
        because tiered thresholds require >= 3 runs."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for i in range(30):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the regulation law government policy pass?",
                    forecast_probability=0.99,
                    confidence=0.9,
                    base_rate_anchor="test", timeframe="3 month",
                )
                engine.record_outcome(f"q-{i}", "r1", False, "test")

            bias = engine.get_domain_bias("POLICY", min_n=3)
            assert bias is not None, "Should have enough data for bias computation"
            assert not bias.correction_active, \
                "Correction should NOT activate with only 1 run"

    def test_no_correction_at_n14_run3(self):
        """At run 3 with n<15 (after holdout exclusion), correction should NOT activate."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # 3 runs, but very few predictions total to keep n < 15 after holdout
            for run_idx in range(3):
                for i in range(4):
                    engine.record_prediction(
                        run_id=f"r{run_idx}", archetype_id="a1",
                        question_id=f"q-{run_idx}-{i}",
                        question_text="Will the regulation law government policy pass?",
                        forecast_probability=0.95,
                        confidence=0.9,
                        base_rate_anchor="test", timeframe="3 month",
                    )
                    engine.record_outcome(
                        f"q-{run_idx}-{i}", f"r{run_idx}", False, "test"
                    )

            bias = engine.get_domain_bias("POLICY", min_n=3)
            if bias and bias.n_observations < 15:
                assert not bias.correction_active, \
                    f"Correction should NOT activate at n={bias.n_observations} < 15"

    def test_t_distribution_gives_larger_pvalues_than_normal_at_small_n(self):
        """Attack: Verify t-distribution is MORE CONSERVATIVE than normal CDF.
        At small n (e.g., df=5), the t-distribution should give LARGER p-values."""
        from engine.calibration_engine import _t_sf

        # At t=2.0:
        # t(df=5): tail ~ 0.051
        # t(df=1000): tail ~ 0.023 (approximates normal)
        p_small_df = _t_sf(2.0, 5)
        p_large_df = _t_sf(2.0, 1000)

        assert p_small_df > p_large_df, \
            f"t(df=5) tail ({p_small_df}) should be > t(df=1000) tail ({p_large_df})"
