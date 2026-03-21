"""Integration smoke test: End-to-end calibration pipeline.

Tests the full flow from prediction recording through outcome resolution
to domain bias computation, ensemble metrics, and ForecastBench export.
"""

import json
import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine
from engine.competence_classifier import classify_question
from engine.forecastbench import export_for_forecastbench
from engine.domain_classifier import stance_to_probability


class TestIntegrationHappyPath:
    """Full pipeline integration test."""

    def test_end_to_end_calibration_pipeline(self):
        """Simulate 3 runs of predictions, outcomes, and corrections."""
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            engine = CalibrationEngine(data_dir)

            # Step 1: Competence classification (pre-UNDERSTAND)
            assessment = classify_question(
                "How will AI regulation affect the technology startup ecosystem "
                "between multiple stakeholders with downstream cascade effects?",
                engine,
            )
            assert assessment.routing_recommendation == "FULL_PIPELINE"
            assert assessment.complexity.value == "MULTI_FACTOR"

            # Step 2: Record predictions across 3 runs
            questions = [
                ("q-tech-1", "Will the technology software platform AI product launch?", True),
                ("q-tech-2", "Will the technology software adoption rate exceed 50%?", False),
                ("q-policy-1", "Will the government regulation law policy on AI pass?", True),
                ("q-policy-2", "Will the government regulation law election affect policy?", False),
                ("q-econ-1", "Will the market economy revenue GDP growth continue?", True),
            ]

            for run_idx in range(3):
                run_id = f"run-{run_idx:03d}"
                for qid, qtext, outcome in questions:
                    full_qid = f"{qid}-run{run_idx}"
                    # Baseline prediction
                    engine.record_prediction(
                        run_id=run_id, archetype_id="historian",
                        question_id=full_qid, question_text=qtext,
                        forecast_probability=0.6,  # Baseline (before deliberation)
                        confidence=0.5, base_rate_anchor="50%", timeframe="3 month",
                        is_baseline=True,
                    )
                    # Informed prediction (after deliberation)
                    # Use stance_to_probability to convert a stance
                    prob = stance_to_probability(0.4)  # stance=0.4 => prob=0.7
                    engine.record_prediction(
                        run_id=run_id, archetype_id="historian",
                        question_id=full_qid, question_text=qtext,
                        forecast_probability=prob,
                        confidence=0.7, base_rate_anchor="60%", timeframe="3 month",
                        is_baseline=False,
                    )
                    # Bootstrap prediction
                    engine.record_prediction(
                        run_id=run_id, archetype_id="historian",
                        question_id=f"{full_qid}-bootstrap",
                        question_text=qtext,
                        forecast_probability=0.65,
                        confidence=0.6, base_rate_anchor="55%", timeframe="1 week",
                        is_bootstrap=True,
                    )

            # Step 3: Record outcomes
            for run_idx in range(3):
                run_id = f"run-{run_idx:03d}"
                for qid, qtext, outcome in questions:
                    full_qid = f"{qid}-run{run_idx}"
                    engine.record_outcome(full_qid, run_id, outcome, "test")
                    engine.record_outcome(f"{full_qid}-bootstrap", run_id, outcome, "test")

            # Step 4: Get ensemble metrics
            metrics = engine.get_ensemble_metrics()
            assert metrics.n_resolved > 0
            assert metrics.brier_raw >= 0
            assert metrics.brier_corrected >= 0
            assert isinstance(metrics.brier_gap, float)
            assert metrics.correction_schedule_stage == "DOMAIN_ADDITIVE"  # 3 runs

            # Step 5: Get domain bias for each domain with data
            for domain in ["TECHNOLOGY", "POLICY", "ECONOMICS"]:
                bias = engine.get_domain_bias(domain, min_n=1)
                if bias:
                    assert bias.n_observations > 0

            # Step 6: Get archetype bias
            archetype_bias = engine.get_archetype_bias("historian", min_n=1)
            if archetype_bias:
                assert archetype_bias.archetype_id == "historian"

            # Step 7: A/B comparison
            comparison = engine.get_deliberation_comparison()
            assert "strata" in comparison
            assert "recommendation" in comparison

            # Step 8: ForecastBench export
            output_path = data_dir / "export" / "submission.json"
            result = export_for_forecastbench(engine, "run-000", output_path)
            assert output_path.exists()

            with open(output_path) as f:
                submission = json.load(f)
            assert submission["model_name"] == "OathFish"
            assert submission["n_predictions"] > 0

            # Step 9: Verify domain_corrections.json exists and is valid
            corrections_path = data_dir / "calibration" / "domain_corrections.json"
            assert corrections_path.exists()

            with open(corrections_path) as f:
                corrections = json.load(f)
            assert "corrections" in corrections
            assert "correction_schedule_stage" in corrections

    def test_stance_to_probability_in_pipeline(self):
        """Verify stance_to_probability correctly maps for calibration recording."""
        # Simulate the mapping that happens when archetype predictions flow
        # from Worker A's PredictionPosition to Worker B's CalibrationPrediction
        test_cases = [
            (-1.0, 0.0),   # Strongly oppose -> 0% probability
            (-0.5, 0.25),  # Moderately oppose -> 25%
            (0.0, 0.5),    # Neutral -> 50%
            (0.5, 0.75),   # Moderately support -> 75%
            (1.0, 1.0),    # Strongly support -> 100%
        ]
        for stance, expected_prob in test_cases:
            actual = stance_to_probability(stance)
            assert abs(actual - expected_prob) < 1e-10, \
                f"stance={stance}: expected prob={expected_prob}, got {actual}"

    def test_dual_metric_reporting_in_pipeline(self):
        """Verify C-28: both corrected and uncorrected Brier appear in metrics."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for i in range(10):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the technology software platform AI product launch?",
                    forecast_probability=0.7, confidence=0.7,
                    base_rate_anchor="test", timeframe="3 month",
                )
                engine.record_outcome(f"q-{i}", "r1", (i % 2 == 0), "test")

            metrics = engine.get_ensemble_metrics()

            # Both must be present
            assert metrics.brier_raw is not None
            assert metrics.brier_corrected is not None
            assert metrics.brier_gap is not None

            # Serialization preserves both
            dumped = metrics.model_dump()
            assert "brier_raw" in dumped
            assert "brier_corrected" in dumped
            assert "brier_gap" in dumped
