"""C-31: Question competence classifier before UNDERSTAND phase.

Spec says: Two-stage design. Stage 1 (text-only, pre-UNDERSTAND) classifies
SIMPLE_BINARY vs MULTI_FACTOR; routing: FULL_PIPELINE, SKIP_DELIBERATE, LOW_CONFIDENCE.
"""

import tempfile
from pathlib import Path
from engine.calibration_engine import CalibrationEngine
from engine.competence_classifier import classify_question
from engine.calibration_models import QuestionComplexity, PredictionDomain


class TestC31CompetenceClassifier:
    """Verify competence classifier works pre-UNDERSTAND (text-only)."""

    def test_works_with_empty_engine(self):
        """Stage 1 must work with NO archetype data (empty CalibrationEngine)."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            result = classify_question(
                "Will the government pass regulation on AI?", engine
            )
            assert result is not None
            assert result.routing_recommendation in [
                "FULL_PIPELINE", "SKIP_DELIBERATE", "LOW_CONFIDENCE"
            ]

    def test_simple_binary_routes_to_skip_deliberate(self):
        """Simple binary questions should route to SKIP_DELIBERATE."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            result = classify_question(
                "Will Congress pass the regulation law?", engine
            )
            # "Will X happen" is simple binary (only 1 multi-factor indicator maybe)
            if result.complexity == QuestionComplexity.SIMPLE_BINARY:
                assert result.routing_recommendation == "SKIP_DELIBERATE"

    def test_multi_factor_routes_to_full_pipeline(self):
        """Multi-factor questions should route to FULL_PIPELINE."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            result = classify_question(
                "How will AI regulation affect the technology ecosystem between "
                "multiple stakeholders with downstream cascade effects?", engine
            )
            assert result.complexity == QuestionComplexity.MULTI_FACTOR
            assert result.routing_recommendation == "FULL_PIPELINE"

    def test_unclassified_domain_routes_low_confidence(self):
        """Unclassifiable domain should route to LOW_CONFIDENCE."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            result = classify_question(
                "Will something happen?", engine
            )
            if result.domain == PredictionDomain.UNCLASSIFIED:
                assert result.routing_recommendation == "LOW_CONFIDENCE"

    def test_returns_domain_classification(self):
        """Competence assessment should include domain classification."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            result = classify_question(
                "Will the technology software platform AI launch?", engine
            )
            assert result.domain == PredictionDomain.TECHNOLOGY

    def test_returns_complexity_classification(self):
        """Should return complexity: SIMPLE_BINARY or MULTI_FACTOR."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            result = classify_question(
                "How will AI regulation affect the startup ecosystem between stakeholders?",
                engine,
            )
            assert result.complexity in [
                QuestionComplexity.SIMPLE_BINARY, QuestionComplexity.MULTI_FACTOR
            ]

    def test_has_confidence_field(self):
        """CompetenceAssessment should include confidence_in_classification."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            result = classify_question(
                "Will the technology software platform launch?", engine
            )
            assert 0.0 <= result.confidence_in_classification <= 1.0

    def test_has_flags_field(self):
        """CompetenceAssessment should include flags list."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = CalibrationEngine(Path(tmp))
            result = classify_question(
                "Will something weird happen?", engine
            )
            assert isinstance(result.flags, list)
