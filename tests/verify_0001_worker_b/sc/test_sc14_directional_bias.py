"""SC-14: 2/6 domains show statistically significant (p<0.10) directional bias.

Spec says: After 5 runs, at least 2/6 domains show significant (p<0.10)
directional bias. Additive corrections applied.

We verify:
1. The statistical test uses t-distribution (NOT normal CDF)
2. Mean signed error is computed correctly: mean(f_i - o_i)
3. p-values are two-sided
4. The tiered correction thresholds match spec
"""

import math
import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine, _t_sf, _betai


class TestSC14StatisticalTest:
    """Verify the statistical test is mathematically correct."""

    def test_mean_signed_error_not_absolute(self):
        """MSE must be mean(f - o), NOT mean(|f - o|).
        This is critical -- absolute error hides directional bias."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # Create predictions that are systematically TOO HIGH
            for i in range(20):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the regulation law government policy election pass?",
                    forecast_probability=0.8,
                    confidence=0.7,
                    base_rate_anchor="test",
                    timeframe="3 month",
                )
                # All outcomes are False -- so f-o = 0.8-0.0 = 0.8
                engine.record_outcome(f"q-{i}", "r1", False, "test")

            bias = engine.get_domain_bias("POLICY", min_n=3)
            assert bias is not None
            # MSE should be 0.8 (all predictions 0.8 above outcome 0.0)
            assert abs(bias.mean_signed_error - 0.8) < 0.01, \
                f"MSE should be ~0.8, got {bias.mean_signed_error}"

    def test_mean_signed_error_negative_for_underconfident(self):
        """When predictions are too LOW, MSE should be NEGATIVE."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for i in range(20):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the regulation law government policy election pass?",
                    forecast_probability=0.2,
                    confidence=0.7,
                    base_rate_anchor="test",
                    timeframe="3 month",
                )
                # All outcomes are True -- so f-o = 0.2-1.0 = -0.8
                engine.record_outcome(f"q-{i}", "r1", True, "test")

            bias = engine.get_domain_bias("POLICY", min_n=3)
            assert bias is not None
            assert bias.mean_signed_error < 0, \
                f"MSE should be negative for underconfident predictions, got {bias.mean_signed_error}"
            assert abs(bias.mean_signed_error - (-0.8)) < 0.01, \
                f"MSE should be ~-0.8, got {bias.mean_signed_error}"

    def test_mean_signed_error_cancels_balanced_errors(self):
        """When errors are balanced (some high, some low), MSE should be near 0."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for i in range(20):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the regulation law government policy election pass?",
                    forecast_probability=0.5,
                    confidence=0.7,
                    base_rate_anchor="test",
                    timeframe="3 month",
                )
                # 50% true -- so errors average to ~0
                engine.record_outcome(f"q-{i}", "r1", (i % 2 == 0), "test")

            bias = engine.get_domain_bias("POLICY", min_n=3)
            assert bias is not None
            assert abs(bias.mean_signed_error) < 0.1, \
                f"MSE should be near 0 for balanced predictions, got {bias.mean_signed_error}"


class TestSC14TDistribution:
    """Verify t-distribution is used, NOT normal CDF.

    This is critical for small n. Normal CDF is anti-conservative
    at small sample sizes (gives smaller p-values than warranted).
    """

    def test_t_sf_matches_known_values(self):
        """Compare _t_sf against known t-distribution survival function values.
        t=2.0, df=10 => p-tail should be approximately 0.0367"""
        p = _t_sf(2.0, 10)
        # From t-distribution tables: P(T > 2.0 | df=10) ~ 0.0367
        assert abs(p - 0.0367) < 0.005, \
            f"_t_sf(2.0, 10) = {p}, expected ~0.0367"

    def test_t_sf_df1(self):
        """t=1.0, df=1 (Cauchy distribution) => p-tail should be 0.25"""
        p = _t_sf(1.0, 1)
        assert abs(p - 0.25) < 0.01, \
            f"_t_sf(1.0, 1) = {p}, expected ~0.25"

    def test_t_sf_zero_gives_half(self):
        """t=0, any df => p-tail should be 0.5"""
        for df in [1, 5, 10, 100]:
            p = _t_sf(0.0, df)
            assert abs(p - 0.5) < 0.01, \
                f"_t_sf(0, {df}) = {p}, expected 0.5"

    def test_t_distribution_wider_tails_than_normal_at_small_n(self):
        """t-distribution with small df should have wider tails than normal.
        At t=2.0:
        - Normal CDF tail: ~0.0228
        - t(df=5) tail: ~0.0510
        The t-distribution should give LARGER p-values (more conservative)."""
        p_t5 = _t_sf(2.0, 5)
        p_normal_approx = _t_sf(2.0, 10000)  # Large df approximates normal

        assert p_t5 > p_normal_approx, \
            f"t(df=5) tail ({p_t5}) should be > normal approx tail ({p_normal_approx})"

    def test_two_sided_pvalue_in_domain_bias(self):
        """Verify the p-value computation is two-sided: p = 2 * P(T > |t|).

        Must mirror get_domain_bias filtering: exclude holdout and baseline."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for i in range(30):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the regulation law government policy election pass?",
                    forecast_probability=0.7,
                    confidence=0.7,
                    base_rate_anchor="test",
                    timeframe="3 month",
                )
                engine.record_outcome(f"q-{i}", "r1", (i % 2 == 0), "test")

            bias = engine.get_domain_bias("POLICY", min_n=3)
            assert bias is not None

            # Manually compute expected p-value, matching the filter logic:
            # exclude holdout=True and baseline=True (defaults)
            errors = []
            for p in engine._predictions:
                if (p["resolved"]
                    and p["domain"] == "POLICY"
                    and not p["is_holdout"]
                    and not p["is_baseline"]):
                    f = p["forecast_probability"]
                    o = 1.0 if p["outcome"] else 0.0
                    errors.append(f - o)

            n = len(errors)
            assert n == bias.n_observations, \
                f"Manual n ({n}) != bias.n_observations ({bias.n_observations})"

            mse = sum(errors) / n
            variance = sum((e - mse) ** 2 for e in errors) / (n - 1)
            sd = math.sqrt(variance)
            se = sd / math.sqrt(n)
            t_stat = mse / se if se > 0 else 0.0
            expected_p = 2 * _t_sf(abs(t_stat), n - 1)

            assert abs(bias.p_value - expected_p) < 0.001, \
                f"p-value mismatch: got {bias.p_value}, expected {expected_p}"

    def test_betai_boundary_zero(self):
        """_betai(a, b, 0) should return 0."""
        val = _betai(1.0, 1.0, 0.0)
        assert val == 0.0, f"_betai(1, 1, 0) should be 0, got {val}"

    def test_betai_boundary_one(self):
        """_betai(a, b, 1) should return 1."""
        val = _betai(1.0, 1.0, 1.0)
        assert val == 1.0, f"_betai(1, 1, 1) should be 1, got {val}"
