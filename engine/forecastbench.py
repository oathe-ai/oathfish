"""ForecastBench submission pipeline for OathFish.

Exports predictions in ForecastBench-compatible format.
Computes ensemble median per question with optional domain corrections.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from engine.calibration_engine import CalibrationEngine

UTC = timezone.utc


def export_for_forecastbench(
    calibration_engine: CalibrationEngine,
    run_id: str,
    output_path: Path,
    use_corrected: bool = True,
) -> dict:
    """Export predictions from a run in ForecastBench-compatible format.

    Format:
    {
      "submission_id": str,
      "model_name": "OathFish",
      "submitted_at": ISO datetime,
      "predictions": [
        {"question_id": str, "probability": float},
        ...
      ]
    }
    """

    predictions = [p for p in calibration_engine._predictions
                   if p["run_id"] == run_id
                   and not p["is_baseline"]
                   and not p["is_bootstrap"]]

    # Group by question_id and compute median
    question_forecasts: dict = {}
    for p in predictions:
        qid = p["question_id"]
        f = p["forecast_probability"]

        if use_corrected:
            f, _ = calibration_engine.apply_correction(f, p["domain"])

        if qid not in question_forecasts:
            question_forecasts[qid] = []
        question_forecasts[qid].append(f)

    submission_predictions = []
    for qid, forecasts in question_forecasts.items():
        forecasts_sorted = sorted(forecasts)
        n = len(forecasts_sorted)
        if n % 2 == 1:
            median = forecasts_sorted[n // 2]
        else:
            median = (forecasts_sorted[n // 2 - 1] + forecasts_sorted[n // 2]) / 2
        submission_predictions.append({
            "question_id": qid,
            "probability": round(median, 4),
        })

    submission = {
        "submission_id": "oathfish-{}-{}".format(run_id, datetime.now(UTC).strftime("%Y%m%dT%H%M%S")),
        "model_name": "OathFish",
        "model_version": "0.1.0",
        "submitted_at": datetime.now(UTC).isoformat(),
        "n_predictions": len(submission_predictions),
        "use_corrected": use_corrected,
        "predictions": submission_predictions,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(submission, f, indent=2)

    return {
        "submission_id": submission["submission_id"],
        "n_predictions": len(submission_predictions),
        "output_path": str(output_path),
    }
