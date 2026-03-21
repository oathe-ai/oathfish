"""Calibration data models for the OathFish calibration engine.

All models are Pydantic BaseModel subclasses for JSON serialization,
validation, and schema generation. Used by calibration_engine.py,
competence_classifier.py, and forecastbench.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict


class PredictionDomain(str, Enum):
    """6 calibration domains. Auto-classified via keyword matching."""
    POLICY = "POLICY"
    ECONOMICS = "ECONOMICS"
    TECHNOLOGY = "TECHNOLOGY"
    SCIENCE = "SCIENCE"
    ENVIRONMENT = "ENVIRONMENT"
    SOCIAL = "SOCIAL"
    UNCLASSIFIED = "UNCLASSIFIED"


class PredictionHorizon(str, Enum):
    """4 prediction horizons aligned with calibration paper's tau parameter."""
    SHORT = "SHORT"        # 1-4 weeks
    MEDIUM = "MEDIUM"      # 1-3 months
    LONG = "LONG"          # 3-12 months
    EXTENDED = "EXTENDED"  # 12+ months


class QuestionComplexity(str, Enum):
    """Question type for A/B stratification."""
    SIMPLE_BINARY = "SIMPLE_BINARY"
    MULTI_FACTOR = "MULTI_FACTOR"


class CalibrationPrediction(BaseModel):
    """A single archetype's prediction, recorded for calibration tracking.

    NOTE (SK-04): forecast_probability is [0,1]. When sourcing from Worker A's
    PredictionPosition.stance [-1,1], use stance_to_probability():
      forecast_probability = (stance + 1) / 2
    """
    prediction_id: str
    run_id: str
    archetype_id: str
    question_id: str
    question_text: str
    domain: PredictionDomain
    horizon: PredictionHorizon
    complexity: QuestionComplexity
    forecast_probability: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    base_rate_anchor: str
    is_baseline: bool = False
    is_bootstrap: bool = False
    is_holdout: bool
    created_at: datetime
    resolved: bool = False
    outcome: Optional[bool] = None
    brier_score: Optional[float] = None


class CalibrationOutcome(BaseModel):
    """Records the actual outcome for a question, triggering Brier computation."""
    question_id: str
    run_id: str
    actual_outcome: bool
    resolution_date: datetime
    resolution_source: str
    resolved_at: datetime


class DomainBias(BaseModel):
    """Computed domain-level directional bias (mean signed error)."""
    domain: PredictionDomain
    mean_signed_error: float
    standard_deviation: float
    n_observations: int
    t_statistic: float
    p_value: float
    correction_active: bool
    correction_value: float
    acquiescence_rate: float
    base_rate: float


class ArchetypeBias(BaseModel):
    """Per-archetype directional bias, optionally filtered by domain."""
    archetype_id: str
    domain: Optional[PredictionDomain] = None
    mean_signed_error: float
    n_observations: int
    brier_score: float
    acquiescence_rate: float


class EnsembleMetrics(BaseModel):
    """Overall ensemble calibration metrics.

    Delta sign convention (unified): POSITIVE = IMPROVEMENT.
    - brier_gap: raw - corrected (positive = correction helps)
    - deliberation_delta: baseline - informed (positive = deliberation helps)
    """
    brier_raw: float
    brier_corrected: float
    brier_gap: float
    brier_baseline: Optional[float] = None
    brier_informed: Optional[float] = None
    deliberation_delta: Optional[float] = None
    acquiescence_rate: float
    n_predictions: int
    n_resolved: int
    n_holdout: int
    brier_holdout: Optional[float] = None
    brier_training: Optional[float] = None
    overfitting_gap: Optional[float] = None
    overfitting_detected: bool
    domain_biases: list[DomainBias]
    correction_schedule_stage: str
    window_runs: int


class HoldoutReport(BaseModel):
    """Overfitting detection report comparing training vs holdout performance."""
    n_training: int
    n_holdout: int
    brier_training: float
    brier_holdout: float
    gap: float
    gap_trend: str
    overfitting_detected: bool
    recommendation: str


class CompetenceAssessment(BaseModel):
    """Output of the question competence classifier."""
    question_text: str
    domain: PredictionDomain
    complexity: QuestionComplexity
    domain_calibration_n: int
    domain_has_correction: bool
    routing_recommendation: str
    confidence_in_classification: float
    flags: list[str]


class DomainTaxonomyConfig(BaseModel):
    """Configurable domain taxonomy with keyword matching rules."""
    domains: dict[str, list[str]]
    min_keyword_matches: int = 2
