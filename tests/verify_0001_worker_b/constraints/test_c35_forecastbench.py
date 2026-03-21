"""C-35: ForecastBench submission pipeline exists.

Spec says: ForecastBench export pipeline, median aggregation, modular export.
"""

import json
import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine
from engine.forecastbench import export_for_forecastbench


class TestC35ForecastBenchPipeline:
    """Verify ForecastBench export pipeline exists and works correctly."""

    def test_export_produces_valid_json(self):
        """Export should produce valid JSON file."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.7, confidence=0.7,
                base_rate_anchor="test", timeframe="3 month",
            )

            output_path = Path(tmp) / "export" / "submission.json"
            result = export_for_forecastbench(engine, "r1", output_path)

            assert output_path.exists()
            with open(output_path) as f:
                data = json.load(f)
            assert "predictions" in data
            assert "model_name" in data
            assert data["model_name"] == "OathFish"

    def test_uses_median_aggregation(self):
        """Multiple predictions for same question should be median-aggregated."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            # 3 predictions for same question
            for i, prob in enumerate([0.3, 0.5, 0.9]):
                engine.record_prediction(
                    run_id="r1", archetype_id=f"a{i}", question_id="q1",
                    question_text="Will the technology software platform launch?",
                    forecast_probability=prob, confidence=0.7,
                    base_rate_anchor="test", timeframe="3 month",
                )

            output_path = Path(tmp) / "export" / "submission.json"
            export_for_forecastbench(engine, "r1", output_path, use_corrected=False)

            with open(output_path) as f:
                data = json.load(f)

            assert len(data["predictions"]) == 1  # One unique question
            # Median of [0.3, 0.5, 0.9] = 0.5
            assert abs(data["predictions"][0]["probability"] - 0.5) < 0.01

    def test_excludes_baseline(self):
        """Baseline predictions should NOT be included in submission."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.7, confidence=0.7,
                base_rate_anchor="test", timeframe="3 month",
                is_baseline=True,
            )

            output_path = Path(tmp) / "export" / "submission.json"
            result = export_for_forecastbench(engine, "r1", output_path)
            assert result["n_predictions"] == 0

    def test_excludes_bootstrap(self):
        """Bootstrap predictions should NOT be included in submission."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.7, confidence=0.7,
                base_rate_anchor="test", timeframe="3 month",
                is_bootstrap=True,
            )

            output_path = Path(tmp) / "export" / "submission.json"
            result = export_for_forecastbench(engine, "r1", output_path)
            assert result["n_predictions"] == 0

    def test_submission_schema_fields(self):
        """Submission JSON should have required fields."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.7, confidence=0.7,
                base_rate_anchor="test", timeframe="3 month",
            )

            output_path = Path(tmp) / "export" / "submission.json"
            export_for_forecastbench(engine, "r1", output_path)

            with open(output_path) as f:
                data = json.load(f)

            assert "submission_id" in data
            assert "model_name" in data
            assert "submitted_at" in data
            assert "n_predictions" in data
            assert "predictions" in data
            for pred in data["predictions"]:
                assert "question_id" in pred
                assert "probability" in pred
                assert 0.0 <= pred["probability"] <= 1.0
