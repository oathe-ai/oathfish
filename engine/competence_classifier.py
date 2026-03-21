"""Question competence classifier for the OathFish pipeline.

Stage 1 (pre-UNDERSTAND) operates on question text alone.
Routes questions to appropriate pipeline depth based on
domain classification confidence and question complexity.
"""

from __future__ import annotations

from engine.calibration_models import (
    CompetenceAssessment,
    PredictionDomain,
    QuestionComplexity,
)
from engine.domain_classifier import classify_domain, classify_complexity
from engine.calibration_engine import CalibrationEngine


def classify_question(
    question_text: str,
    calibration_engine: CalibrationEngine,
) -> CompetenceAssessment:
    """Stage 1 competence classifier (pre-UNDERSTAND).

    Routing logic:
    - SIMPLE_BINARY -> SKIP_DELIBERATE (direct amplification)
    - MULTI_FACTOR -> FULL_PIPELINE (full deliberation)
    - UNCLASSIFIED domain -> LOW_CONFIDENCE
    """

    taxonomy = calibration_engine.taxonomy
    domain = classify_domain(question_text, taxonomy)
    complexity = classify_complexity(question_text)

    # Check domain calibration data
    domain_n = 0
    domain_has_correction = False
    if domain != PredictionDomain.UNCLASSIFIED:
        bias = calibration_engine.get_domain_bias(domain.value, min_n=1)
        if bias:
            domain_n = bias.n_observations
            domain_has_correction = bias.correction_active

    # Compute keyword match confidence
    text_lower = question_text.lower()
    if domain != PredictionDomain.UNCLASSIFIED:
        domain_keywords = taxonomy.domains.get(domain.value, [])
        matches = sum(1 for kw in domain_keywords if kw.lower() in text_lower)
        confidence = min(1.0, matches / 5.0)
    else:
        confidence = 0.0

    # Routing recommendation
    flags = []

    if domain == PredictionDomain.UNCLASSIFIED:
        flags.append("UNCLASSIFIED_DOMAIN")
        routing = "LOW_CONFIDENCE"
    elif domain_n == 0:
        flags.append("UNCALIBRATED_DOMAIN")
        if complexity == QuestionComplexity.SIMPLE_BINARY:
            routing = "SKIP_DELIBERATE"
        else:
            routing = "FULL_PIPELINE"
    elif complexity == QuestionComplexity.SIMPLE_BINARY:
        routing = "SKIP_DELIBERATE"
    else:
        routing = "FULL_PIPELINE"

    if confidence < 0.4:
        flags.append("LOW_CLASSIFICATION_CONFIDENCE")

    return CompetenceAssessment(
        question_text=question_text,
        domain=domain,
        complexity=complexity,
        domain_calibration_n=domain_n,
        domain_has_correction=domain_has_correction,
        routing_recommendation=routing,
        confidence_in_classification=round(confidence, 2),
        flags=flags,
    )
