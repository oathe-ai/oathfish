"""DoD: B-B.1 -- CalibrationEngine with 5 MCP tools + write_domain_corrections.

Spec says: All 5 tools work; corrections improve synthetic biased data; holdout excluded.
Tools: record_prediction, record_outcome, get_domain_bias, get_archetype_bias, get_ensemble_metrics.
"""

import json
import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine


class TestBB1RecordPrediction:
    """Verify record_prediction tool."""

    def test_records_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            pred = engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.7, confidence=0.8,
                base_rate_anchor="50%", timeframe="3 month",
            )
            assert pred.prediction_id is not None
            assert pred.forecast_probability == 0.7
            # Should persist immediately
            assert engine.predictions_file.exists()

    def test_auto_classifies_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            pred = engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform AI product launch?",
                forecast_probability=0.7, confidence=0.8,
                base_rate_anchor="50%", timeframe="3 month",
            )
            assert pred.domain.value == "TECHNOLOGY"


class TestBB1RecordOutcome:
    """Verify record_outcome tool computes Brier scores."""

    def test_computes_brier_on_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.7, confidence=0.8,
                base_rate_anchor="50%", timeframe="3 month",
            )
            result = engine.record_outcome("q1", "r1", True, "test")
            assert result["predictions_updated"] == 1

            # Check brier score was computed
            pred = engine._predictions[0]
            assert pred["brier_score"] is not None
            expected_brier = (0.7 - 1.0) ** 2
            assert abs(pred["brier_score"] - expected_brier) < 1e-6


class TestBB1GetDomainBias:
    """Verify get_domain_bias tool."""

    def test_returns_none_below_min_n(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.7, confidence=0.8,
                base_rate_anchor="50%", timeframe="3 month",
            )
            engine.record_outcome("q1", "r1", True, "test")

            bias = engine.get_domain_bias("TECHNOLOGY", min_n=10)
            assert bias is None

    def test_returns_bias_when_enough_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for i in range(10):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the technology software platform AI product launch?",
                    forecast_probability=0.7, confidence=0.8,
                    base_rate_anchor="50%", timeframe="3 month",
                )
                engine.record_outcome(f"q-{i}", "r1", (i % 2 == 0), "test")

            bias = engine.get_domain_bias("TECHNOLOGY", min_n=3)
            assert bias is not None
            assert bias.n_observations >= 3


class TestBB1GetArchetypeBias:
    """Verify get_archetype_bias tool."""

    def test_returns_archetype_specific_bias(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for i in range(10):
                engine.record_prediction(
                    run_id="r1", archetype_id="arch-1",
                    question_id=f"q-{i}",
                    question_text="Will the technology software platform AI product launch?",
                    forecast_probability=0.8, confidence=0.8,
                    base_rate_anchor="50%", timeframe="3 month",
                )
                engine.record_outcome(f"q-{i}", "r1", (i % 2 == 0), "test")

            bias = engine.get_archetype_bias("arch-1", min_n=3)
            assert bias is not None
            assert bias.archetype_id == "arch-1"
            assert bias.n_observations >= 3


class TestBB1GetEnsembleMetrics:
    """Verify get_ensemble_metrics tool."""

    def test_returns_metrics_with_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for i in range(10):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the technology software platform launch?",
                    forecast_probability=0.7, confidence=0.8,
                    base_rate_anchor="50%", timeframe="3 month",
                )
                engine.record_outcome(f"q-{i}", "r1", (i % 2 == 0), "test")

            metrics = engine.get_ensemble_metrics()
            assert metrics.n_resolved > 0
            assert metrics.brier_raw >= 0


class TestBB1WriteDomainCorrections:
    """Verify write_domain_corrections produces spec-compliant JSON."""

    def test_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for i in range(10):
                engine.record_prediction(
                    run_id="r1", archetype_id="a1",
                    question_id=f"q-{i}",
                    question_text="Will the technology software platform AI product launch?",
                    forecast_probability=0.7, confidence=0.8,
                    base_rate_anchor="50%", timeframe="3 month",
                )
                engine.record_outcome(f"q-{i}", "r1", (i % 2 == 0), "test")

            engine.write_domain_corrections()
            assert engine.corrections_file.exists()

            with open(engine.corrections_file) as f:
                data = json.load(f)

            assert "corrections" in data
            assert "last_updated" in data
            assert "correction_schedule_stage" in data

    def test_schema_matches_cross_worker_contract(self):
        """Spec: each correction entry has offset, n, direction, p_value, correction_active."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            for run_idx in range(5):
                for i in range(10):
                    engine.record_prediction(
                        run_id=f"r{run_idx}", archetype_id="a1",
                        question_id=f"q-{run_idx}-{i}",
                        question_text="Will the technology software platform AI product launch?",
                        forecast_probability=0.8, confidence=0.8,
                        base_rate_anchor="50%", timeframe="3 month",
                    )
                    engine.record_outcome(f"q-{run_idx}-{i}", f"r{run_idx}",
                                          (i % 2 == 0), "test")

            engine.write_domain_corrections()

            with open(engine.corrections_file) as f:
                data = json.load(f)

            for domain, entry in data["corrections"].items():
                assert "offset" in entry, f"Missing 'offset' in {domain}"
                assert "n" in entry, f"Missing 'n' in {domain}"
                assert "direction" in entry, f"Missing 'direction' in {domain}"
                assert entry["direction"] in ("over", "under"), \
                    f"Invalid direction '{entry['direction']}' in {domain}"
                assert "p_value" in entry, f"Missing 'p_value' in {domain}"
                assert "correction_active" in entry, f"Missing 'correction_active' in {domain}"
