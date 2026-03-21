"""Tests for engine/forecastbench.py"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from engine.calibration_engine import CalibrationEngine
from engine.forecastbench import export_for_forecastbench


@pytest.fixture
def engine(tmp_path):
    return CalibrationEngine(tmp_path)


def _record(engine, run_id="run1", archetype_id="arch1", question_id="q1",
            question_text="Will government regulation ban this policy?",
            forecast=0.7, is_baseline=False, is_bootstrap=False):
    return engine.record_prediction(
        run_id=run_id,
        archetype_id=archetype_id,
        question_id=question_id,
        question_text=question_text,
        forecast_probability=forecast,
        confidence=0.8,
        base_rate_anchor="50%",
        timeframe="3 month",
        is_baseline=is_baseline,
        is_bootstrap=is_bootstrap,
    )


class TestExportForForecastbench:
    def test_basic_export(self, engine, tmp_path):
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.7)
        _record(engine, archetype_id="a2", question_id="q1", forecast=0.8)

        output_path = tmp_path / "submissions" / "test.json"
        result = export_for_forecastbench(engine, "run1", output_path)

        assert result["n_predictions"] == 1  # 1 question
        assert output_path.exists()

    def test_valid_json_output(self, engine, tmp_path):
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.7)

        output_path = tmp_path / "test.json"
        export_for_forecastbench(engine, "run1", output_path)

        data = json.loads(output_path.read_text())
        assert data["model_name"] == "OathFish"
        assert "submission_id" in data
        assert "submitted_at" in data
        assert "predictions" in data
        assert isinstance(data["predictions"], list)

    def test_median_computation_odd(self, engine, tmp_path):
        """Median of odd number of predictions."""
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.3)
        _record(engine, archetype_id="a2", question_id="q1", forecast=0.7)
        _record(engine, archetype_id="a3", question_id="q1", forecast=0.5)

        output_path = tmp_path / "test.json"
        export_for_forecastbench(engine, "run1", output_path, use_corrected=False)

        data = json.loads(output_path.read_text())
        # Median of [0.3, 0.5, 0.7] = 0.5
        assert data["predictions"][0]["probability"] == 0.5

    def test_median_computation_even(self, engine, tmp_path):
        """Median of even number of predictions."""
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.3)
        _record(engine, archetype_id="a2", question_id="q1", forecast=0.7)

        output_path = tmp_path / "test.json"
        export_for_forecastbench(engine, "run1", output_path, use_corrected=False)

        data = json.loads(output_path.read_text())
        # Median of [0.3, 0.7] = 0.5
        assert data["predictions"][0]["probability"] == 0.5

    def test_excludes_baseline(self, engine, tmp_path):
        """Baseline predictions should not be exported."""
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.7, is_baseline=True)
        _record(engine, archetype_id="a2", question_id="q1", forecast=0.8)

        output_path = tmp_path / "test.json"
        result = export_for_forecastbench(engine, "run1", output_path)

        data = json.loads(output_path.read_text())
        # Only 1 non-baseline prediction -> 1 question
        assert result["n_predictions"] == 1
        # The median should be 0.8 (only non-baseline)
        assert data["predictions"][0]["probability"] == 0.8

    def test_excludes_bootstrap(self, engine, tmp_path):
        """Bootstrap predictions should not be exported."""
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.7, is_bootstrap=True)
        _record(engine, archetype_id="a2", question_id="q2", forecast=0.8,
                question_text="Will the stock market economy crash?")

        output_path = tmp_path / "test.json"
        result = export_for_forecastbench(engine, "run1", output_path)
        assert result["n_predictions"] == 1

    def test_multiple_questions(self, engine, tmp_path):
        """Export should handle multiple questions."""
        _record(engine, archetype_id="a1", question_id="q1", forecast=0.7)
        _record(engine, archetype_id="a1", question_id="q2", forecast=0.5,
                question_text="Will the stock market economy crash?")

        output_path = tmp_path / "test.json"
        result = export_for_forecastbench(engine, "run1", output_path)
        assert result["n_predictions"] == 2

    def test_empty_run(self, engine, tmp_path):
        """Export of non-existent run should produce empty predictions."""
        output_path = tmp_path / "test.json"
        result = export_for_forecastbench(engine, "nonexistent", output_path)
        assert result["n_predictions"] == 0

    def test_creates_parent_directories(self, engine, tmp_path):
        """Should create parent directories for output path."""
        output_path = tmp_path / "deep" / "nested" / "test.json"
        _record(engine, question_id="q1", forecast=0.7)
        export_for_forecastbench(engine, "run1", output_path)
        assert output_path.exists()
