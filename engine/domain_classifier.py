"""Deterministic domain, horizon, and complexity classification.

All functions are pure -- no LLM calls, no randomness. Keyword-based
classification ensures consistent results across runs (C-B05).
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Optional

from engine.calibration_models import (
    PredictionDomain,
    PredictionHorizon,
    QuestionComplexity,
    DomainTaxonomyConfig,
)


def load_taxonomy(config_path: Optional[Path] = None) -> DomainTaxonomyConfig:
    """Load domain taxonomy from JSON config file.
    Falls back to built-in defaults if no config file found."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            data = json.load(f)
        return DomainTaxonomyConfig(
            domains={k: v["keywords"] for k, v in data["domains"].items()},
            min_keyword_matches=data.get("min_keyword_matches", 2),
        )
    return _default_taxonomy()


def _default_taxonomy() -> DomainTaxonomyConfig:
    """Built-in default taxonomy matching engine/config/domain_taxonomy.json."""
    return DomainTaxonomyConfig(
        domains={
            "POLICY": ["regulation", "law", "government", "policy", "election",
                        "legislation", "ban", "mandate", "congress", "senate",
                        "court", "ruling", "executive order", "sanctions", "tariff",
                        "treaty", "vote", "ballot", "referendum", "political"],
            "ECONOMICS": ["market", "economy", "revenue", "GDP", "stock", "funding",
                           "IPO", "recession", "inflation", "interest rate", "bond",
                           "profit", "valuation", "acquisition", "merger", "startup",
                           "venture capital", "bankruptcy", "trade", "fiscal"],
            "TECHNOLOGY": ["technology", "software", "AI", "adoption", "launch",
                            "product", "platform", "app", "semiconductor", "chip",
                            "cloud", "SaaS", "open source", "API", "model",
                            "algorithm", "computing", "robot", "autonomous", "digital"],
            "SCIENCE": ["science", "research", "clinical", "health", "medical",
                         "study", "vaccine", "disease", "trial", "FDA",
                         "peer review", "publication", "lab", "genome", "protein",
                         "cancer", "therapy", "diagnosis", "pharmaceutical", "drug"],
            "ENVIRONMENT": ["climate", "environment", "emission", "weather", "energy",
                             "renewable", "carbon", "temperature", "sea level", "ice",
                             "solar", "wind", "fossil fuel", "pollution", "wildfire",
                             "hurricane", "flood", "drought", "biodiversity", "ecosystem"],
            "SOCIAL": ["social", "culture", "consumer", "media", "public opinion",
                        "trend", "demographic", "population", "migration", "protest",
                        "movement", "entertainment", "sports", "brand", "sentiment",
                        "lifestyle", "education", "inequality", "urbanization", "community"],
        },
        min_keyword_matches=2,
    )


def classify_domain(
    text: str,
    taxonomy: DomainTaxonomyConfig,
) -> PredictionDomain:
    """Deterministic keyword-based domain classification.
    Returns the domain with the most keyword matches.
    Returns UNCLASSIFIED if no domain meets min_keyword_matches threshold."""
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for domain_id, keywords in taxonomy.domains.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        scores[domain_id] = score

    best_domain = max(scores, key=lambda k: scores[k])
    best_score = scores[best_domain]

    if best_score < taxonomy.min_keyword_matches:
        return PredictionDomain.UNCLASSIFIED

    return PredictionDomain(best_domain)


def classify_horizon(timeframe: str) -> PredictionHorizon:
    """Deterministic horizon classification from timeframe string.

    NOTE (SK-07 fix): Check order is extended -> long -> short -> medium.
    Short is checked BEFORE medium to prevent "month" in medium_indicators
    from matching "1 month" (which should be SHORT).
    """
    text_lower = timeframe.lower()

    short_indicators = ["week", "1 month", "2 week", "3 week", "days"]
    medium_indicators = ["quarter", "2 month", "3 month", "90 day"]
    long_indicators = ["6 month", "year", "12 month", "9 month", "annual"]
    extended_indicators = ["years", "2 year", "3 year", "5 year", "decade", "long-term"]

    for indicator in extended_indicators:
        if indicator in text_lower:
            return PredictionHorizon.EXTENDED
    for indicator in long_indicators:
        if indicator in text_lower:
            return PredictionHorizon.LONG
    # SHORT checked before MEDIUM to avoid "month" substring matching "1 month"
    for indicator in short_indicators:
        if indicator in text_lower:
            return PredictionHorizon.SHORT
    for indicator in medium_indicators:
        if indicator in text_lower:
            return PredictionHorizon.MEDIUM

    return PredictionHorizon.MEDIUM  # Default


def classify_complexity(question_text: str) -> QuestionComplexity:
    """Deterministic complexity classification.
    MULTI_FACTOR if question mentions multiple interacting entities/factors."""
    text_lower = question_text.lower()

    multi_indicators = [
        "how will", "affect", "impact", "cascade", "interaction",
        "stakeholder", "multiple", "combination", "joint", "system",
        "feedback loop", "second-order", "downstream", "ecosystem",
        "between", "cross-sector", "interdepend",
    ]

    multi_score = sum(1 for ind in multi_indicators if ind in text_lower)

    if multi_score >= 2:
        return QuestionComplexity.MULTI_FACTOR
    return QuestionComplexity.SIMPLE_BINARY


def compute_holdout_flag(prediction_id: str) -> bool:
    """Deterministic holdout partition using prediction ID hex value.
    Exactly 20% of predictions are holdout.

    NOTE (SK-09 fix): prediction_id is already a hex string from SHA-256.
    Parse directly instead of double-hashing."""
    return int(prediction_id, 16) % 5 == 0


def generate_prediction_id(run_id: str, archetype_id: str, question_id: str) -> str:
    """Deterministic prediction ID generation."""
    raw = f"{run_id}:{archetype_id}:{question_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def stance_to_probability(stance: float) -> float:
    """Convert Worker A's PredictionPosition.stance [-1, 1] to
    CalibrationPrediction.forecast_probability [0, 1].

    Formula: forecast_probability = (stance + 1) / 2
    """
    return (stance + 1.0) / 2.0
