"""B-H08: Competence classifier timing paradox.

Mitigation: Two-stage design -- text-only pre-UNDERSTAND, archetype-aware post-UNDERSTAND.
Attack: Verify Stage 1 works without archetype data.
"""

import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine
from engine.competence_classifier import classify_question


class TestBH08CompetenceTimingParadox:
    """Attack: Call competence classifier before any data exists."""

    def test_works_with_zero_predictions(self):
        """Stage 1 must work with an empty CalibrationEngine (no predictions)."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            result = classify_question(
                "Will AI regulation affect the technology startup ecosystem?",
                engine,
            )
            assert result is not None
            assert result.routing_recommendation in [
                "FULL_PIPELINE", "SKIP_DELIBERATE", "LOW_CONFIDENCE"
            ]

    def test_works_with_no_resolved_predictions(self):
        """Should work even if predictions exist but none are resolved."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            engine.record_prediction(
                run_id="r1", archetype_id="a1", question_id="q1",
                question_text="Will the technology software platform launch?",
                forecast_probability=0.7, confidence=0.7,
                base_rate_anchor="test", timeframe="3 month",
            )
            # No outcomes recorded

            result = classify_question(
                "Will Congress pass new regulation law?",
                engine,
            )
            assert result is not None

    def test_does_not_require_archetype_data(self):
        """Stage 1 uses only question text -- no archetype info needed."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            result = classify_question(
                "How will climate emission environment affect the ecosystem?",
                engine,
            )
            assert result.domain is not None
            assert result.complexity is not None
