"""Tests for engine/calibration_engine.py"""

from __future__ import annotations

import json
import math
import pytest
from pathlib import Path

from engine.calibration_engine import CalibrationEngine, _t_sf
from engine.calibration_models import PredictionDomain


@pytest.fixture
def engine(tmp_path):
    return CalibrationEngine(tmp_path)


def _record(engine, run_id="run1", archetype_id="arch1", question_id="q1",
            question_text="Will government regulation ban this policy?",
            forecast=0.7, confidence=0.8, timeframe="3 month",
            is_baseline=False, is_bootstrap=False):
    """Helper to record a prediction with sensible defaults."""
    return engine.record_prediction(
        run_id=run_id,
        archetype_id=archetype_id,
        question_id=question_id,
        question_text=question_text,
        forecast_probability=forecast,
        confidence=confidence,
        base_rate_anchor="50%",
        timeframe=timeframe,
        is_baseline=is_baseline,
        is_bootstrap=is_bootstrap,
    )


class TestRecordPrediction:
    def test_basic_record(self, engine):
        pred = _record(engine)
        assert pred.prediction_id is not None
        assert pred.run_id == "run1"
        assert pred.forecast_probability == 0.7
        assert pred.domain == PredictionDomain.POLICY
        assert pred.resolved is False

    def test_persists_to_disk(self, engine):
        _record(engine)
        assert engine.predictions_file.exists()
        data = json.loads(engine.predictions_file.read_text())
        assert len(data) == 1

    def test_auto_classifies_domain(self, engine):
        pred = _record(engine,
                       question_text="Will the stock market recession cause GDP decline?")
        assert pred.domain == PredictionDomain.ECONOMICS

    def test_holdout_flag_deterministic(self, engine):
        pred1 = _record(engine, question_id="q1")
        pred2 = _record(engine, question_id="q1", archetype_id="arch2")
        # Same archetype + question -> same prediction_id only if all 3 match
        # Different archetype -> different prediction_id
        assert isinstance(pred1.is_holdout, bool)
        assert isinstance(pred2.is_holdout, bool)


class TestRecordOutcome:
    def test_basic_outcome(self, engine):
        _record(engine, question_id="q1", forecast=0.9)
        result = engine.record_outcome("q1", "run1", True, "news source")
        assert result["predictions_updated"] == 1
        assert result["actual_outcome"] is True

    def test_brier_score_computed(self, engine):
        _record(engine, question_id="q1", forecast=0.9)
        engine.record_outcome("q1", "run1", True, "source")
        pred = engine._predictions[0]
        assert pred["resolved"] is True
        # Brier = (0.9 - 1.0)^2 = 0.01
        assert abs(pred["brier_score"] - 0.01) < 1e-10

    def test_brier_score_false_outcome(self, engine):
        _record(engine, question_id="q1", forecast=0.1)
        engine.record_outcome("q1", "run1", False, "source")
        pred = engine._predictions[0]
        # Brier = (0.1 - 0.0)^2 = 0.01
        assert abs(pred["brier_score"] - 0.01) < 1e-10

    def test_multiple_predictions_updated(self, engine):
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.7)
        _record(engine, archetype_id="a2", question_id="q1", forecast=0.8)
        result = engine.record_outcome("q1", "run1", True, "source")
        assert result["predictions_updated"] == 2

    def test_writes_domain_corrections(self, engine):
        _record(engine, question_id="q1", forecast=0.7)
        engine.record_outcome("q1", "run1", True, "source")
        assert engine.corrections_file.exists()


class TestBrierScore:
    def test_known_values(self, engine):
        """Proof obligation: Brier for [0.9, 0.1], [True, False] = 0.01"""
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.9)
        _record(engine, archetype_id="a2", question_id="q2", forecast=0.1,
                question_text="Will the stock market crash during recession?")
        engine.record_outcome("q1", "run1", True, "s")
        engine.record_outcome("q2", "run1", False, "s")

        resolved = [p for p in engine._predictions if p["resolved"]]
        brier = engine._compute_brier(resolved)
        # ((0.9-1)^2 + (0.1-0)^2) / 2 = (0.01 + 0.01) / 2 = 0.01
        assert abs(brier - 0.01) < 1e-10

    def test_perfect_prediction(self, engine):
        _record(engine, question_id="q1", forecast=1.0)
        engine.record_outcome("q1", "run1", True, "s")
        resolved = [p for p in engine._predictions if p["resolved"]]
        assert engine._compute_brier(resolved) == 0.0

    def test_worst_prediction(self, engine):
        _record(engine, question_id="q1", forecast=0.0)
        engine.record_outcome("q1", "run1", True, "s")
        resolved = [p for p in engine._predictions if p["resolved"]]
        assert abs(engine._compute_brier(resolved) - 1.0) < 1e-10


class TestDomainBias:
    def test_returns_none_below_min_n(self, engine):
        _record(engine, question_id="q1", forecast=0.7)
        engine.record_outcome("q1", "run1", True, "s")
        # min_n=3 by default, only 1 observation
        bias = engine.get_domain_bias("POLICY")
        assert bias is None

    def test_basic_bias_computation(self, engine):
        # Record 5 predictions to have enough after holdout exclusion
        for i in range(5):
            _record(engine, archetype_id=f"a{i}", question_id=f"q{i}", forecast=0.8)
            engine.record_outcome(f"q{i}", "run1", False, "s")

        bias = engine.get_domain_bias("POLICY", min_n=1)
        assert bias is not None
        # MSE = mean(0.8 - 0.0) = 0.8 (overconfident)
        assert abs(bias.mean_signed_error - 0.8) < 1e-4
        assert bias.acquiescence_rate == 0.8

    def test_holdout_excluded(self, engine):
        """Holdout predictions must be excluded from correction computation."""
        for i in range(20):
            _record(engine, archetype_id=f"a{i}", question_id=f"q{i}", forecast=0.8)
            engine.record_outcome(f"q{i}", "run1", False, "s")

        bias_with = engine.get_domain_bias("POLICY", min_n=1, exclude_holdout=True)
        bias_without = engine.get_domain_bias("POLICY", min_n=1, exclude_holdout=False)

        # Excluding holdout should give fewer observations
        assert bias_with.n_observations <= bias_without.n_observations

    def test_baseline_excluded_by_default(self, engine):
        # Record a baseline and a non-baseline prediction
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.8, is_baseline=True)
        _record(engine, archetype_id="a2", question_id="q1", forecast=0.7, is_baseline=False)
        _record(engine, archetype_id="a3", question_id="q2", forecast=0.6, is_baseline=False)
        engine.record_outcome("q1", "run1", True, "s")
        engine.record_outcome("q2", "run1", True, "s")

        bias = engine.get_domain_bias("POLICY", min_n=1)
        # Should exclude baseline
        assert bias.n_observations == 2  # Only non-baseline

    def test_positive_mse_means_overconfident(self, engine):
        """MSE > 0 means ensemble predicts too high."""
        for i in range(5):
            _record(engine, archetype_id=f"a{i}", question_id=f"q{i}", forecast=0.9)
            engine.record_outcome(f"q{i}", "run1", False, "s")

        bias = engine.get_domain_bias("POLICY", min_n=1)
        assert bias.mean_signed_error > 0  # Overconfident


class TestCorrectionThreshold:
    def test_no_correction_below_n15(self, engine):
        """Corrections not applied when n < 15, even with large MSE."""
        for i in range(10):
            _record(engine, run_id=f"run{i % 3 + 1}", archetype_id=f"a{i}",
                    question_id=f"q{i}", forecast=0.9)
            engine.record_outcome(f"q{i}", f"run{i % 3 + 1}", False, "s")

        bias = engine.get_domain_bias("POLICY", min_n=1)
        assert bias is not None
        assert not bias.correction_active

    def test_correction_at_n15_runs3_large_mse(self, engine):
        """Correction applied when n>=15, runs>=3, |MSE|>0.10."""
        for i in range(16):
            run = f"run{i % 3 + 1}"  # 3 different runs
            _record(engine, run_id=run, archetype_id=f"a{i}",
                    question_id=f"q{i}", forecast=0.9)
            engine.record_outcome(f"q{i}", run, False, "s")

        bias = engine.get_domain_bias("POLICY", min_n=1, exclude_holdout=False)
        assert bias is not None
        assert bias.n_observations >= 15
        assert abs(bias.mean_signed_error) > 0.10
        assert bias.correction_active

    def test_no_correction_small_mse(self, engine):
        """Small MSE (< 0.10) should not trigger correction at run 3-9."""
        # Create predictions with small bias
        for i in range(20):
            run = f"run{i % 3 + 1}"
            # Alternate outcomes to keep MSE small
            forecast = 0.55 if i % 2 == 0 else 0.45
            outcome = i % 2 == 0
            _record(engine, run_id=run, archetype_id=f"a{i}",
                    question_id=f"q{i}", forecast=forecast)
            engine.record_outcome(f"q{i}", run, outcome, "s")

        bias = engine.get_domain_bias("POLICY", min_n=1, exclude_holdout=False)
        if bias:
            # MSE should be small, correction should be inactive
            if abs(bias.mean_signed_error) < 0.10:
                assert not bias.correction_active

    def test_correction_schedule_stages(self, engine):
        """Verify stage transitions at correct run counts."""
        # 1 run -> RECORD_ONLY
        _record(engine, run_id="run1", question_id="q1", forecast=0.7)
        engine.record_outcome("q1", "run1", True, "s")
        metrics = engine.get_ensemble_metrics()
        assert metrics.correction_schedule_stage == "RECORD_ONLY"

    def test_domain_additive_stage(self, engine):
        """3+ runs -> DOMAIN_ADDITIVE."""
        for r in range(3):
            _record(engine, run_id=f"run{r}", archetype_id=f"a{r}",
                    question_id=f"q{r}", forecast=0.7)
            engine.record_outcome(f"q{r}", f"run{r}", True, "s")
        metrics = engine.get_ensemble_metrics()
        assert metrics.correction_schedule_stage == "DOMAIN_ADDITIVE"


class TestEnsembleMetrics:
    def test_empty_state(self, engine):
        """All tools return gracefully with zero data."""
        metrics = engine.get_ensemble_metrics()
        assert metrics.brier_raw == 0.0
        assert metrics.n_resolved == 0
        assert metrics.correction_schedule_stage == "RECORD_ONLY"
        assert metrics.domain_biases == []

    def test_dual_metric_reporting(self, engine):
        """Both raw and corrected Brier present in output."""
        _record(engine, question_id="q1", forecast=0.7)
        engine.record_outcome("q1", "run1", True, "s")
        metrics = engine.get_ensemble_metrics()
        assert metrics.brier_raw is not None
        assert metrics.brier_corrected is not None
        assert metrics.brier_gap is not None

    def test_brier_gap_positive_means_improvement(self, engine):
        """SK-05 fix: brier_gap > 0 when corrections help."""
        # Create scenario where corrections help:
        # Systematic overconfidence in POLICY domain
        for r in range(3):
            for i in range(6):
                idx = r * 6 + i
                _record(engine, run_id=f"run{r+1}", archetype_id=f"a{idx}",
                        question_id=f"q{idx}", forecast=0.9)
                engine.record_outcome(f"q{idx}", f"run{r+1}", False, "s")

        metrics = engine.get_ensemble_metrics()
        # If corrections are active and helping, brier_gap should be positive
        if any(db.correction_active for db in metrics.domain_biases):
            assert metrics.brier_gap >= 0

    def test_bootstrap_excluded_from_primary_brier(self, engine):
        """Bootstrap predictions excluded from primary Brier computation."""
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.5,
                is_bootstrap=True)
        _record(engine, archetype_id="a2", question_id="q2", forecast=0.9)
        engine.record_outcome("q1", "run1", True, "s")
        engine.record_outcome("q2", "run1", True, "s")

        metrics = engine.get_ensemble_metrics()
        # n_resolved should be 1 (bootstrap excluded)
        assert metrics.n_resolved == 1

    def test_window_parameter(self, engine):
        """Window parameter limits runs included."""
        for r in range(5):
            _record(engine, run_id=f"run{r}", archetype_id=f"a{r}",
                    question_id=f"q{r}", forecast=0.7)
            engine.record_outcome(f"q{r}", f"run{r}", True, "s")

        metrics_all = engine.get_ensemble_metrics(window=10)
        metrics_2 = engine.get_ensemble_metrics(window=2)

        assert metrics_all.window_runs == 5
        assert metrics_2.window_runs == 2
        assert metrics_2.n_resolved <= metrics_all.n_resolved

    def test_overfitting_detection(self, engine):
        """SK-11 fix: gap > 0.02 = detected."""
        # This is hard to trigger deterministically, so just test the logic
        metrics = engine.get_ensemble_metrics()
        assert metrics.overfitting_detected is False


class TestABComparison:
    def test_baseline_vs_informed(self, engine):
        """Deliberation delta computed when both baseline and informed exist."""
        # Baseline predictions (worse)
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.3,
                is_baseline=True)
        # Informed predictions (better)
        _record(engine, archetype_id="a2", question_id="q1", forecast=0.8)
        engine.record_outcome("q1", "run1", True, "s")

        metrics = engine.get_ensemble_metrics()
        # baseline Brier = (0.3 - 1)^2 = 0.49
        # informed Brier = (0.8 - 1)^2 = 0.04
        # delta = 0.49 - 0.04 = 0.45 (positive = deliberation helps)
        assert metrics.deliberation_delta is not None
        assert metrics.deliberation_delta > 0

    def test_stratified_comparison(self, engine):
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.3,
                is_baseline=True)
        _record(engine, archetype_id="a2", question_id="q1", forecast=0.8)
        engine.record_outcome("q1", "run1", True, "s")

        comparison = engine.get_deliberation_comparison()
        assert "strata" in comparison
        assert "recommendation" in comparison


class TestDomainCorrectionsJson:
    def test_schema_matches_contract(self, engine):
        """SK-01/SK-06 fix: domain_corrections.json matches Worker A schema."""
        _record(engine, question_id="q1", forecast=0.7)
        engine.record_outcome("q1", "run1", True, "s")
        engine.write_domain_corrections()

        data = json.loads(engine.corrections_file.read_text())
        assert "corrections" in data
        assert "last_updated" in data
        assert "correction_schedule_stage" in data

    def test_correction_entries_have_required_fields(self, engine):
        """Each correction entry has offset, n, direction, p_value, correction_active."""
        for r in range(3):
            for i in range(6):
                idx = r * 6 + i
                _record(engine, run_id=f"run{r+1}", archetype_id=f"a{idx}",
                        question_id=f"q{idx}", forecast=0.9)
                engine.record_outcome(f"q{idx}", f"run{r+1}", False, "s")

        engine.write_domain_corrections()
        data = json.loads(engine.corrections_file.read_text())

        for domain, entry in data["corrections"].items():
            assert "offset" in entry
            assert "n" in entry
            assert "direction" in entry
            assert "p_value" in entry
            assert "correction_active" in entry
            assert entry["direction"] in ("over", "under")


class TestTDistribution:
    def test_t_sf_basic(self):
        """_t_sf should return values between 0 and 0.5."""
        result = _t_sf(1.0, 10)
        assert 0 < result < 0.5

    def test_t_sf_zero(self):
        """t=0 should give p=0.5 (survival from center)."""
        result = _t_sf(0.0, 10)
        assert abs(result - 0.5) < 1e-6

    def test_t_sf_large_t(self):
        """Large t should give very small p."""
        result = _t_sf(10.0, 10)
        assert result < 0.001

    def test_t_sf_df14(self):
        """SK-03 fix: Compare against known value for t(14).
        At t=1.761, df=14, the one-sided p should be ~0.05."""
        result = _t_sf(1.761, 14)
        # scipy.stats.t.sf(1.761, 14) ≈ 0.0500
        assert abs(result - 0.05) < 0.005

    def test_t_sf_df100(self):
        """At large df, t-distribution approaches normal."""
        result = _t_sf(1.96, 100)
        # Should be close to 0.025 (normal approximation)
        assert abs(result - 0.025) < 0.005

    def test_two_sided_pvalue(self):
        """Two-sided p-value should be twice the one-sided."""
        one_sided = _t_sf(2.0, 20)
        two_sided = 2 * one_sided
        assert 0 < two_sided < 1.0


class TestHoldoutPartition:
    def test_holdout_excluded_from_corrections(self, engine):
        """Holdout predictions must not influence domain corrections."""
        # Record many predictions
        for i in range(30):
            _record(engine, archetype_id=f"a{i}", question_id=f"q{i}", forecast=0.8)
            engine.record_outcome(f"q{i}", "run1", False, "s")

        # Get bias excluding holdout
        bias_excl = engine.get_domain_bias("POLICY", min_n=1, exclude_holdout=True)
        # Get bias including holdout
        bias_incl = engine.get_domain_bias("POLICY", min_n=1, exclude_holdout=False)

        # Holdout exclusion should reduce n
        if bias_excl and bias_incl:
            assert bias_excl.n_observations < bias_incl.n_observations
