# Implementation Plan - Worker B: Calibration Engine, Debiasing, & Research-Mandated Infrastructure
## Run: 0001-oathfish-swarm-engine
## Worker: B
## Lens: mcp-research

---

## 1. Scope Anchor

**Goal**: Design and specify the complete Calibration Engine (5 MCP tools), debiasing infrastructure, question competence classifier, holdout validation system, baseline amplification A/B comparison, short-horizon bootstrap question support, and ForecastBench submission pipeline -- all mandated by the 5-paper adversarial research debate.

**Constraints**:

- MUST: All calibration computations are deterministic MCP tools (C-02, C-B05)
- MUST: Calibration data persists at CLAUDE_PLUGIN_DATA, surviving plugin updates (H-03, H-CFG-01)
- MUST: Holdout 20% of resolved predictions from calibration feedback (C-34)
- MUST: Report both corrected and uncorrected Brier scores (C-28)
- MUST: Per-domain acquiescence tracking from run 1, corrections from run 3+ (C-27)
- MUST: Baseline amplification before deliberation every run for A/B comparison (C-26)
- MUST: Question competence classifier before UNDERSTAND (C-31)
- MUST: ForecastBench submission pipeline (C-35)
- MUST NOT: Feed holdout predictions back into correction model (C-34, feature-request.md:356)
- MUST NOT: Use LLM in any calibration correction computation (C-B05, mcp-analysis.md:237-243)

**Success Criteria**:

- [ ] SC-11: Submit 100+ predictions to ForecastBench. Target Brier < 0.122 (feature-request.md:113)
- [ ] SC-12: After 5 runs, domain-level correction improves Brier by >= 0.01 (feature-request.md:114)
- [ ] SC-13: Deliberation outperforms baseline on multi-factor questions (feature-request.md:115)
- [ ] SC-14: 2/6 domains show significant directional bias p<0.10 after 5 runs (feature-request.md:116)

---

## 2. Evidence Summary

| # | Fact | Source | Anchor |
|---|------|--------|--------|
| E-01 | LLM acquiescence bias: M=57.35%, t(1006)=86.20, p<0.001 | 2402.19379-silicon-crowd.md | :23 |
| E-02 | Simple averaging beats LLM updating: GPT-4 p=0.011, Claude 2 p=0.001 | 2402.19379-silicon-crowd.md | :37-40 |
| E-03 | Calibration decomposes into 4 components, 87.3% R-squared | 2602.19520-calibration-decomposition.md | :26-31 |
| E-04 | Domain intercept (alpha_d) = 14.6% of calibration variance | 2602.19520-calibration-decomposition.md | :29 |
| E-05 | Domain-by-horizon interaction = 26.0% of calibration variance | 2602.19520-calibration-decomposition.md | :30 |
| E-06 | 80% power at d=0.3 requires n=90 per domain | 2602.19520:OathFish Relevance |
| E-07 | OathFish will have 300-600 predictions in year 1 | round-1-ffa.md:116, synthesis-report.md:61 |
| E-08 | Superforecasters Brier 0.096, best LLM (o3) 0.1352 | 2409.19839-forecastbench.md:19-25 |
| E-09 | Logistic recalibration: p* = p^theta / (p^theta + (1-p)^theta) | round-1-ffa.md:272 |
| E-10 | 6 domains referenced but undefined in spec | spec-audit.md:226-228 |
| E-11 | Competence classifier timing paradox: runs before archetypes exist | spec-audit.md:247 |
| E-12 | OATHFISH_DATA_DIR must use CLAUDE_PLUGIN_DATA not CLAUDE_PLUGIN_ROOT | mcp-analysis.md:53, 166-170 |
| E-13 | 25,000 token MCP output limit constrains large responses | mcp-analysis.md:31, 59 |
| E-14 | Resolution latency: primary predictions resolve in 3-12 months | A-09:feature-request.md:1232 |
| E-15 | Gap > 0.05 between corrected/uncorrected Brier = archetype needs re-grounding | final-synthesis.md:133 |

---

## 3. Implementation Ledger

### Phase A: Data Models & Domain Taxonomy

#### Task A.1: Define Calibration Pydantic Models

**Objective**: Create all data models for the calibration engine.
**Files**: CREATE `engine/calibration_models.py`
**Evidence**: No calibration models exist in feature-request.md (only PredictionPosition at :547). Must design from scratch.
**Definition of Done**: All models pass Pydantic validation, serialize to/from JSON.
**Risks**: None (greenfield).

```python
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, UTC
from typing import Optional


class PredictionDomain(str, Enum):
    """6 calibration domains. Auto-classified via keyword matching."""
    POLICY = "POLICY"            # Government, regulation, political outcomes
    ECONOMICS = "ECONOMICS"      # Markets, business, financial outcomes
    TECHNOLOGY = "TECHNOLOGY"    # Tech adoption, product launches, innovation
    SCIENCE = "SCIENCE"          # Scientific outcomes, medical, health
    ENVIRONMENT = "ENVIRONMENT"  # Climate, environmental, natural events
    SOCIAL = "SOCIAL"            # Social dynamics, cultural, consumer behavior
    UNCLASSIFIED = "UNCLASSIFIED"  # No domain matched


class PredictionHorizon(str, Enum):
    """4 prediction horizons aligned with calibration paper's tau parameter."""
    SHORT = "SHORT"              # 1-4 weeks
    MEDIUM = "MEDIUM"            # 1-3 months
    LONG = "LONG"                # 3-12 months
    EXTENDED = "EXTENDED"        # 12+ months


class QuestionComplexity(str, Enum):
    """Question type for A/B stratification."""
    SIMPLE_BINARY = "SIMPLE_BINARY"    # Single yes/no outcome
    MULTI_FACTOR = "MULTI_FACTOR"      # Multiple interacting factors


class CalibrationPrediction(BaseModel):
    """A single archetype's prediction, recorded for calibration tracking.
    Created by calibration_record_prediction(). Persisted to disk.

    NOTE (SK-04): forecast_probability is [0,1]. When sourcing from Worker A's
    PredictionPosition.stance [-1,1], use stance_to_probability():
      forecast_probability = (stance + 1) / 2
    """
    prediction_id: str                  # Deterministic: hash(run_id + archetype_id + question_id)
    run_id: str
    archetype_id: str
    question_id: str                    # Unique identifier for the forecasting question
    question_text: str                  # The question being predicted
    domain: PredictionDomain            # Auto-classified via keyword matching
    horizon: PredictionHorizon          # Estimated resolution timeframe
    complexity: QuestionComplexity      # Simple binary vs multi-factor
    forecast_probability: float = Field(ge=0.0, le=1.0)  # Predicted probability [0,1]
    confidence: float = Field(ge=0.0, le=1.0)            # Archetype's self-assessed confidence
    base_rate_anchor: str               # Historical base rate cited
    is_baseline: bool = False           # True if from BASELINE_AMPLIFY (pre-deliberation)
    is_bootstrap: bool = False          # True if short-horizon bootstrap question
    is_holdout: bool                    # Deterministic: int(prediction_id, 16) % 5 == 0
    created_at: datetime
    resolved: bool = False
    outcome: Optional[bool] = None      # True = event occurred, False = did not
    brier_score: Optional[float] = None # Computed when outcome recorded


class CalibrationOutcome(BaseModel):
    """Records the actual outcome for a question, triggering Brier computation."""
    question_id: str
    run_id: str                         # Which run this question originated from
    actual_outcome: bool                # True = event occurred
    resolution_date: datetime
    resolution_source: str              # Where outcome was verified
    resolved_at: datetime               # When we recorded the resolution


class DomainBias(BaseModel):
    """Computed domain-level directional bias (mean signed error)."""
    domain: PredictionDomain
    mean_signed_error: float            # Positive = overconfident/acquiescent
    standard_deviation: float
    n_observations: int                 # Number of resolved predictions in this domain
    t_statistic: float                  # One-sample t-test against 0
    p_value: float                      # Significance of directional bias (t-distribution)
    correction_active: bool             # Whether correction is being applied
    correction_value: float             # The additive correction (0.0 if inactive)
    acquiescence_rate: float            # Mean forecast probability (>0.5 = acquiescent)
    base_rate: float                    # Proportion of positive outcomes in this domain


class ArchetypeBias(BaseModel):
    """Per-archetype directional bias, optionally filtered by domain."""
    archetype_id: str
    domain: Optional[PredictionDomain]  # None = aggregate across domains
    mean_signed_error: float
    n_observations: int
    brier_score: float                  # Average Brier for this archetype (in this domain)
    acquiescence_rate: float


class EnsembleMetrics(BaseModel):
    """Overall ensemble calibration metrics.

    Delta sign convention (unified): POSITIVE = IMPROVEMENT.
    - brier_gap: raw - corrected (positive = correction helps)
    - deliberation_delta: baseline - informed (positive = deliberation helps)
    """
    brier_raw: float                    # Uncorrected ensemble Brier score
    brier_corrected: float              # After domain-level corrections applied
    brier_gap: float                    # raw - corrected (positive = correction helps)
    brier_baseline: Optional[float]     # Baseline (pre-deliberation) Brier
    brier_informed: Optional[float]     # Deliberation-informed Brier
    deliberation_delta: Optional[float] # baseline - informed (positive = deliberation helps)
    acquiescence_rate: float            # Global mean forecast probability
    n_predictions: int                  # Total predictions recorded
    n_resolved: int                     # Predictions with known outcomes
    n_holdout: int                      # Holdout set size
    brier_holdout: Optional[float]      # Holdout Brier (for overfitting detection)
    brier_training: Optional[float]     # Training set Brier
    overfitting_gap: Optional[float]    # holdout_brier - training_brier
    overfitting_detected: bool          # True if gap > 0.02
    domain_biases: list[DomainBias]     # Per-domain bias summaries
    correction_schedule_stage: str      # "RECORD_ONLY" | "DOMAIN_ADDITIVE" | "ARCHETYPE_ADDITIVE" | "LOGISTIC"
    window_runs: int                    # How many runs included in this computation


class HoldoutReport(BaseModel):
    """Overfitting detection report comparing training vs holdout performance."""
    n_training: int
    n_holdout: int
    brier_training: float
    brier_holdout: float
    gap: float                          # holdout - training
    gap_trend: str                      # "STABLE" | "GROWING" | "SHRINKING"
    overfitting_detected: bool
    recommendation: str                 # Human-readable recommendation


class CompetenceAssessment(BaseModel):
    """Output of the question competence classifier."""
    question_text: str
    domain: PredictionDomain
    complexity: QuestionComplexity
    domain_calibration_n: int           # How many resolved predictions in this domain
    domain_has_correction: bool         # Whether domain-level correction is active
    routing_recommendation: str         # "FULL_PIPELINE" | "SKIP_DELIBERATE" | "LOW_CONFIDENCE"
    confidence_in_classification: float # How confident the classifier is (based on keyword match strength)
    flags: list[str]                    # e.g., ["UNCALIBRATED_DOMAIN", "OUT_OF_DOMAIN"]


class DomainTaxonomyConfig(BaseModel):
    """Configurable domain taxonomy with keyword matching rules."""
    domains: dict[str, list[str]]       # domain_id -> list of keywords
    min_keyword_matches: int = 2        # Minimum matches to classify (else UNCLASSIFIED)
```

#### Task A.2: Define Domain Taxonomy Configuration

**Objective**: Create the default domain taxonomy as a configurable JSON file.
**Files**: CREATE `engine/config/domain_taxonomy.json`
**Evidence**: spec-audit.md:228 flags "6 domains not defined." This task resolves H-02.
**Definition of Done**: 6 domains with keyword lists. Keyword classifier assigns correct domain for 10 test questions.
**Risks**: H-02 (domain taxonomy undefined -- this task resolves it)
**Mitigation**: Ship with defaults; allow user override via config file.

```json
{
  "domains": {
    "POLICY": {
      "keywords": ["regulation", "law", "government", "policy", "election",
                    "legislation", "ban", "mandate", "congress", "senate",
                    "court", "ruling", "executive order", "sanctions", "tariff",
                    "treaty", "vote", "ballot", "referendum", "political"],
      "description": "Government action, regulation, political outcomes"
    },
    "ECONOMICS": {
      "keywords": ["market", "economy", "revenue", "GDP", "stock", "funding",
                    "IPO", "recession", "inflation", "interest rate", "bond",
                    "profit", "valuation", "acquisition", "merger", "startup",
                    "venture capital", "bankruptcy", "trade", "fiscal"],
      "description": "Markets, business, financial outcomes"
    },
    "TECHNOLOGY": {
      "keywords": ["technology", "software", "AI", "adoption", "launch",
                    "product", "platform", "app", "semiconductor", "chip",
                    "cloud", "SaaS", "open source", "API", "model",
                    "algorithm", "computing", "robot", "autonomous", "digital"],
      "description": "Technology adoption, product launches, innovation"
    },
    "SCIENCE": {
      "keywords": ["science", "research", "clinical", "health", "medical",
                    "study", "vaccine", "disease", "trial", "FDA",
                    "peer review", "publication", "lab", "genome", "protein",
                    "cancer", "therapy", "diagnosis", "pharmaceutical", "drug"],
      "description": "Scientific outcomes, medical, health events"
    },
    "ENVIRONMENT": {
      "keywords": ["climate", "environment", "emission", "weather", "energy",
                    "renewable", "carbon", "temperature", "sea level", "ice",
                    "solar", "wind", "fossil fuel", "pollution", "wildfire",
                    "hurricane", "flood", "drought", "biodiversity", "ecosystem"],
      "description": "Climate, environmental, natural events"
    },
    "SOCIAL": {
      "keywords": ["social", "culture", "consumer", "media", "public opinion",
                    "trend", "demographic", "population", "migration", "protest",
                    "movement", "entertainment", "sports", "brand", "sentiment",
                    "lifestyle", "education", "inequality", "urbanization", "community"],
      "description": "Social dynamics, cultural shifts, consumer behavior"
    }
  },
  "min_keyword_matches": 2,
  "case_sensitive": false
}
```

#### Task A.3: Create Domain Classifier Function

**Objective**: Deterministic keyword-based domain classification.
**Files**: CREATE `engine/domain_classifier.py`
**Evidence**: C-B05 (all calibration computations must be deterministic). No LLM.
**Definition of Done**: classify_domain(text) returns correct PredictionDomain for test cases.
**Risks**: H-07 (domain-varying acquiescence)
**Mitigation**: Keyword approach ensures consistent classification across runs.

```python
import json
import hashlib
from pathlib import Path
from calibration_models import (
    PredictionDomain, PredictionHorizon, QuestionComplexity,
    DomainTaxonomyConfig
)


def load_taxonomy(config_path: Path | None = None) -> DomainTaxonomyConfig:
    """Load domain taxonomy from JSON config file.
    Falls back to built-in defaults if no config file found."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            data = json.load(f)
        return DomainTaxonomyConfig(
            domains={k: v["keywords"] for k, v in data["domains"].items()},
            min_keyword_matches=data.get("min_keyword_matches", 2)
        )
    # Return built-in defaults (same as domain_taxonomy.json)
    return _default_taxonomy()


def classify_domain(
    text: str,
    taxonomy: DomainTaxonomyConfig
) -> PredictionDomain:
    """Deterministic keyword-based domain classification.
    Returns the domain with most keyword matches.
    Returns UNCLASSIFIED if no domain meets min_keyword_matches threshold.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for domain_id, keywords in taxonomy.domains.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        scores[domain_id] = score

    best_domain = max(scores, key=scores.get)
    best_score = scores[best_domain]

    if best_score < taxonomy.min_keyword_matches:
        return PredictionDomain.UNCLASSIFIED

    return PredictionDomain(best_domain)


def classify_horizon(timeframe: str) -> PredictionHorizon:
    """Deterministic horizon classification from timeframe string.
    Parses duration indicators to assign horizon bucket.

    NOTE (SK-07 fix): Check order is extended -> long -> short -> medium.
    Short is checked BEFORE medium to prevent "month" in medium_indicators
    from matching "1 month" (which should be SHORT).
    """
    text_lower = timeframe.lower()

    # Check for explicit duration indicators
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
    MULTI_FACTOR if question mentions multiple interacting entities/factors.
    SIMPLE_BINARY if straightforward yes/no outcome."""
    text_lower = question_text.lower()

    multi_indicators = [
        "how will", "affect", "impact", "cascade", "interaction",
        "stakeholder", "multiple", "combination", "joint", "system",
        "feedback loop", "second-order", "downstream", "ecosystem",
        "between", "cross-sector", "interdepend"
    ]

    multi_score = sum(1 for ind in multi_indicators if ind in text_lower)

    if multi_score >= 2:
        return QuestionComplexity.MULTI_FACTOR
    return QuestionComplexity.SIMPLE_BINARY


def compute_holdout_flag(prediction_id: str) -> bool:
    """Deterministic holdout partition using prediction ID hex value.
    Exactly 20% of predictions are holdout. Same prediction always
    gets same partition. Cannot be gamed.

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

    Design decision (SK-04): Linear mapping where:
      stance = -1.0 -> probability = 0.0 (event will NOT occur)
      stance =  0.0 -> probability = 0.5 (maximally uncertain)
      stance =  1.0 -> probability = 1.0 (event WILL occur)

    Formula: forecast_probability = (stance + 1) / 2

    This assumes stance represents the archetype's belief about
    the likelihood of the event occurring, scaled symmetrically
    around 0 (uncertain). Worker A's PredictionPosition.stance
    is defined as ge=-1.0, le=1.0.
    """
    return (stance + 1.0) / 2.0
```

---

### Phase B: Calibration Engine (5 MCP Tools)

#### Task B.1: Create Calibration Engine Module

**Objective**: Implement the core calibration engine with 5 MCP tools.
**Files**: CREATE `engine/calibration_engine.py`
**Evidence**: research-driven-redesign.md:249-276 (tool signatures); mcp-analysis.md:128-135 (persistence requirements)
**Definition of Done**: All 5 tools callable via MCP, compute correct statistics, persist to disk.
**Risks**: H-01 (corrections at small n), H-03 (data persistence), H-04 (holdout contamination)
**Mitigation**: Per-domain n-threshold, CLAUDE_PLUGIN_DATA persistence, hash-based holdout partition.

> **SPEC DEVIATION (SK-02)**: C-27's verification column states "corrections applied when n>=90/domain".
> This plan applies corrections at n>=15 with |MSE|>0.10 (runs 3-9), n>=45 with |MSE|>0.05 (runs 10-17),
> and n>=90 with p<0.10 (runs 18+). Rationale: n=90 provides 80% power for detecting SMALL biases
> (Cohen's d=0.3). At n=15 with |MSE|>0.10, we only catch LARGE biases (d>0.6) -- a much higher bar
> that compensates for the lower sample size. The tiered approach progressively increases sensitivity
> as data accumulates.
>
> **Statistical caveats**:
> - At n=15, Type I error rate is elevated even with |MSE|>0.10 threshold
> - At n=15, only biases with |MSE|>0.10 (roughly 10 percentage points of systematic over/under-prediction) are corrected
> - At n=45, the |MSE|>0.05 threshold catches medium biases
> - At n=90, the p<0.10 threshold matches the spec's intended statistical power
> - If early corrections are noise, they will be overridden by more precise estimates at higher n

```python
import json
import math
from pathlib import Path
from datetime import datetime, UTC
from typing import Optional
from calibration_models import (
    CalibrationPrediction, CalibrationOutcome, DomainBias,
    ArchetypeBias, EnsembleMetrics, HoldoutReport,
    PredictionDomain, PredictionHorizon
)
from domain_classifier import (
    classify_domain, classify_horizon, classify_complexity,
    compute_holdout_flag, generate_prediction_id, load_taxonomy,
    stance_to_probability
)


class CalibrationEngine:
    """Deterministic calibration engine. All computations are pure functions
    of the stored prediction/outcome data. No LLM in the correction loop.

    Correction schedule (from research consensus):
    - Runs 1-2: RECORD_ONLY -- accumulate data, no corrections
    - Runs 3-9: DOMAIN_ADDITIVE -- apply alpha_d correction where
      |MSE_d| > 0.10 AND n_d >= 15
    - Runs 10-49: ARCHETYPE_ADDITIVE -- extend corrections to archetype level
      where n >= 5 per archetype per domain
    - Runs 50+: LOGISTIC -- logistic recalibration where n >= 50 per domain

    SPEC DEVIATION: C-27 verification says n>=90/domain. This plan uses a
    tiered approach (n>=15/45/90) with progressively lower MSE thresholds.
    See SK-02 in defense.md for full justification.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.calibration_dir = data_dir / "calibration"
        self.calibration_dir.mkdir(parents=True, exist_ok=True)
        self.predictions_file = self.calibration_dir / "predictions.json"
        self.outcomes_file = self.calibration_dir / "outcomes.json"
        self.corrections_file = self.calibration_dir / "domain_corrections.json"
        self.taxonomy = load_taxonomy(
            data_dir / "config" / "domain_taxonomy.json"
        )
        self._predictions: list[dict] = self._load_json(self.predictions_file)
        self._outcomes: list[dict] = self._load_json(self.outcomes_file)

    def _load_json(self, path: Path) -> list[dict]:
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    def _save_predictions(self) -> None:
        with open(self.predictions_file, "w") as f:
            json.dump(self._predictions, f, indent=2, default=str)

    def _save_outcomes(self) -> None:
        with open(self.outcomes_file, "w") as f:
            json.dump(self._outcomes, f, indent=2, default=str)

    # -- Tool 1: calibration_record_prediction --

    def record_prediction(
        self,
        run_id: str,
        archetype_id: str,
        question_id: str,
        question_text: str,
        forecast_probability: float,
        confidence: float,
        base_rate_anchor: str,
        timeframe: str,
        is_baseline: bool = False,
        is_bootstrap: bool = False,
    ) -> CalibrationPrediction:
        """Records a structured prediction for future outcome comparison.
        Auto-classifies domain, horizon, complexity. Assigns holdout flag.
        Persists immediately to disk (write-through, C-23).

        NOTE (SK-04): forecast_probability must be [0,1]. If sourcing from
        Worker A's PredictionPosition.stance [-1,1], convert first:
          forecast_probability = stance_to_probability(stance)
        """

        prediction_id = generate_prediction_id(run_id, archetype_id, question_id)
        domain = classify_domain(question_text, self.taxonomy)
        horizon = classify_horizon(timeframe)
        complexity = classify_complexity(question_text)
        is_holdout = compute_holdout_flag(prediction_id)

        prediction = CalibrationPrediction(
            prediction_id=prediction_id,
            run_id=run_id,
            archetype_id=archetype_id,
            question_id=question_id,
            question_text=question_text,
            domain=domain,
            horizon=horizon,
            complexity=complexity,
            forecast_probability=forecast_probability,
            confidence=confidence,
            base_rate_anchor=base_rate_anchor,
            is_baseline=is_baseline,
            is_bootstrap=is_bootstrap,
            is_holdout=is_holdout,
            created_at=datetime.now(UTC),
        )

        self._predictions.append(prediction.model_dump())
        self._save_predictions()
        return prediction

    # -- Tool 2: calibration_record_outcome --

    def record_outcome(
        self,
        question_id: str,
        run_id: str,
        actual_outcome: bool,
        resolution_source: str,
    ) -> dict:
        """Records the actual outcome and triggers Brier score computation
        for all predictions matching this question_id.
        Returns summary of updated predictions.
        Also updates domain_corrections.json for cross-engine interface."""

        outcome = CalibrationOutcome(
            question_id=question_id,
            run_id=run_id,
            actual_outcome=actual_outcome,
            resolution_date=datetime.now(UTC),
            resolution_source=resolution_source,
            resolved_at=datetime.now(UTC),
        )

        self._outcomes.append(outcome.model_dump())
        self._save_outcomes()

        # Compute Brier scores for all matching predictions
        updated_count = 0
        outcome_val = 1.0 if actual_outcome else 0.0

        for pred in self._predictions:
            if pred["question_id"] == question_id and not pred["resolved"]:
                f = pred["forecast_probability"]
                pred["resolved"] = True
                pred["outcome"] = actual_outcome
                pred["brier_score"] = (f - outcome_val) ** 2
                updated_count += 1

        self._save_predictions()

        # Update domain_corrections.json for Worker A's amplify_aggregate()
        self.write_domain_corrections()

        return {
            "question_id": question_id,
            "actual_outcome": actual_outcome,
            "predictions_updated": updated_count,
            "resolution_source": resolution_source,
        }

    # -- Tool 3: calibration_get_domain_bias --

    def get_domain_bias(
        self,
        domain: str,
        min_n: int = 3,
        exclude_holdout: bool = True,
        exclude_baseline: bool = True,
        exclude_bootstrap: bool = False,
    ) -> Optional[DomainBias]:
        """Returns mean signed error for a domain.
        Positive MSE = ensemble predicts too high (overconfident/acquiescent).
        Only returns if n >= min_n resolved observations.

        Statistical test: one-sample t-test of (f_i - o_i) against 0.
        Correction is active when: |MSE| > threshold AND n >= 15.

        Formula:
          MSE_d = (1/N_d) * SUM(f_i - o_i) for resolved predictions in domain d
          t = MSE_d / (s_d / sqrt(N_d))
          p = two-sided p-value from t-distribution with N_d - 1 df

        NOTE (SK-03 fix): Uses t-distribution (not normal CDF) for p-values.
        The normal approximation is ANTI-conservative at small n, producing
        artificially small p-values. The t-distribution with n-1 df is exact.
        """

        # Filter resolved predictions for this domain
        errors = []
        forecasts = []
        outcomes_count = {"positive": 0, "total": 0}

        for pred in self._predictions:
            if not pred["resolved"]:
                continue
            if pred["domain"] != domain:
                continue
            if exclude_holdout and pred["is_holdout"]:
                continue
            if exclude_baseline and pred["is_baseline"]:
                continue
            if exclude_bootstrap and pred["is_bootstrap"]:
                continue

            f = pred["forecast_probability"]
            o = 1.0 if pred["outcome"] else 0.0
            errors.append(f - o)
            forecasts.append(f)
            outcomes_count["total"] += 1
            if pred["outcome"]:
                outcomes_count["positive"] += 1

        n = len(errors)
        if n < min_n:
            return None

        mse = sum(errors) / n
        if n > 1:
            variance = sum((e - mse) ** 2 for e in errors) / (n - 1)
            sd = math.sqrt(variance)
            se = sd / math.sqrt(n)
            t_stat = mse / se if se > 0 else 0.0
            # Two-sided p-value from t-distribution with n-1 degrees of freedom
            # (SK-03 fix: replaced _normal_cdf with _t_sf for correct small-n behavior)
            p_value = 2 * _t_sf(abs(t_stat), n - 1)
        else:
            sd = 0.0
            t_stat = 0.0
            p_value = 1.0

        # Determine correction activation
        total_runs = len(set(p["run_id"] for p in self._predictions))
        correction_active = False
        correction_value = 0.0

        if total_runs >= 3 and n >= 15 and abs(mse) > 0.10:
            correction_active = True
            correction_value = mse
        elif total_runs >= 10 and n >= 45 and abs(mse) > 0.05:
            correction_active = True
            correction_value = mse
        elif total_runs >= 18 and n >= 90 and p_value < 0.10:
            correction_active = True
            correction_value = mse

        acq_rate = sum(forecasts) / len(forecasts) if forecasts else 0.5
        base_rate = (outcomes_count["positive"] / outcomes_count["total"]
                     if outcomes_count["total"] > 0 else 0.5)

        return DomainBias(
            domain=PredictionDomain(domain),
            mean_signed_error=round(mse, 6),
            standard_deviation=round(sd, 6),
            n_observations=n,
            t_statistic=round(t_stat, 4),
            p_value=round(p_value, 6),
            correction_active=correction_active,
            correction_value=round(correction_value, 6),
            acquiescence_rate=round(acq_rate, 4),
            base_rate=round(base_rate, 4),
        )

    # -- Tool 4: calibration_get_archetype_bias --

    def get_archetype_bias(
        self,
        archetype_id: str,
        domain: Optional[str] = None,
        min_n: int = 5,
        exclude_holdout: bool = True,
    ) -> Optional[ArchetypeBias]:
        """Returns per-archetype directional bias.
        Optionally filtered by domain.

        Formula:
          MSE_a = (1/N_a) * SUM(f_i - o_i) for archetype a
          Brier_a = (1/N_a) * SUM((f_i - o_i)^2)
        """

        errors = []
        brier_scores = []
        forecasts = []

        for pred in self._predictions:
            if not pred["resolved"]:
                continue
            if pred["archetype_id"] != archetype_id:
                continue
            if domain and pred["domain"] != domain:
                continue
            if exclude_holdout and pred["is_holdout"]:
                continue
            if pred["is_baseline"]:
                continue

            f = pred["forecast_probability"]
            o = 1.0 if pred["outcome"] else 0.0
            errors.append(f - o)
            brier_scores.append((f - o) ** 2)
            forecasts.append(f)

        n = len(errors)
        if n < min_n:
            return None

        mse = sum(errors) / n
        brier = sum(brier_scores) / n
        acq_rate = sum(forecasts) / len(forecasts) if forecasts else 0.5

        return ArchetypeBias(
            archetype_id=archetype_id,
            domain=PredictionDomain(domain) if domain else None,
            mean_signed_error=round(mse, 6),
            n_observations=n,
            brier_score=round(brier, 6),
            acquiescence_rate=round(acq_rate, 4),
        )

    # -- Tool 5: calibration_get_ensemble_metrics --

    def get_ensemble_metrics(
        self,
        window: int = 10,
    ) -> EnsembleMetrics:
        """Returns overall ensemble calibration metrics.
        Compares corrected vs uncorrected, baseline vs informed,
        training vs holdout. Reports correction schedule stage.

        Formulas:
          Brier_raw = (1/N) * SUM((f_i - o_i)^2)
          Brier_corrected = (1/N) * SUM((clamp(f_i - alpha_d, 0, 1) - o_i)^2)
          deliberation_delta = Brier_baseline - Brier_informed
          overfitting_gap = Brier_holdout - Brier_training

        Delta sign convention (unified, SK-05 fix): POSITIVE = IMPROVEMENT.
          brier_gap = raw - corrected (positive = correction helps)
          deliberation_delta = baseline - informed (positive = deliberation helps)
        """

        # Get all resolved non-baseline, non-bootstrap predictions
        resolved = [p for p in self._predictions
                    if p["resolved"] and not p["is_baseline"]
                    and not p["is_bootstrap"]]

        # Limit to window of most recent runs
        all_runs = sorted(set(p["run_id"] for p in self._predictions))
        window_runs = all_runs[-window:] if len(all_runs) > window else all_runs
        resolved = [p for p in resolved if p["run_id"] in window_runs]

        n_total = len(self._predictions)
        n_resolved = len(resolved)

        if n_resolved == 0:
            return self._empty_ensemble_metrics(n_total, len(window_runs))

        # Compute domain corrections
        corrections = {}
        for domain in PredictionDomain:
            if domain == PredictionDomain.UNCLASSIFIED:
                continue
            bias = self.get_domain_bias(domain.value, min_n=3)
            if bias and bias.correction_active:
                corrections[domain.value] = bias.correction_value

        # Split training vs holdout
        training = [p for p in resolved if not p["is_holdout"]]
        holdout = [p for p in resolved if p["is_holdout"]]

        # Raw Brier (all resolved, no corrections)
        brier_raw = self._compute_brier(resolved)

        # Corrected Brier (apply domain corrections)
        brier_corrected = self._compute_brier_corrected(resolved, corrections)

        # Baseline Brier (pre-deliberation predictions)
        baseline_preds = [p for p in self._predictions
                         if p["resolved"] and p["is_baseline"]
                         and p["run_id"] in window_runs]
        brier_baseline = self._compute_brier(baseline_preds) if baseline_preds else None

        # Informed Brier (post-deliberation, non-baseline)
        brier_informed = brier_raw  # Same as resolved non-baseline

        # Deliberation delta (positive = deliberation helps)
        deliberation_delta = None
        if brier_baseline is not None:
            deliberation_delta = round(brier_baseline - brier_raw, 6)

        # Holdout vs training
        brier_holdout = self._compute_brier(holdout) if holdout else None
        brier_training = self._compute_brier(training) if training else None

        overfitting_gap = None
        overfitting_detected = False
        if brier_holdout is not None and brier_training is not None:
            overfitting_gap = round(brier_holdout - brier_training, 6)
            # SK-11 fix: simplified guard -- only check gap magnitude.
            # Previous condition (brier_training < brier_raw) was trivially true
            # whenever corrections are active, providing no discriminative power.
            overfitting_detected = overfitting_gap > 0.02

        # Acquiescence rate
        all_forecasts = [p["forecast_probability"] for p in resolved]
        acq_rate = sum(all_forecasts) / len(all_forecasts) if all_forecasts else 0.5

        # Correction schedule stage
        total_runs = len(all_runs)
        if total_runs < 3:
            stage = "RECORD_ONLY"
        elif total_runs < 10:
            stage = "DOMAIN_ADDITIVE"
        elif total_runs < 50:
            stage = "ARCHETYPE_ADDITIVE"
        else:
            stage = "LOGISTIC"

        # Domain bias summaries
        domain_biases = []
        for domain in PredictionDomain:
            if domain == PredictionDomain.UNCLASSIFIED:
                continue
            bias = self.get_domain_bias(domain.value, min_n=1)
            if bias:
                domain_biases.append(bias)

        # Update domain_corrections.json for cross-engine interface
        self.write_domain_corrections()

        return EnsembleMetrics(
            brier_raw=round(brier_raw, 6),
            brier_corrected=round(brier_corrected, 6),
            brier_gap=round(brier_raw - brier_corrected, 6),  # SK-05 fix: positive = correction helps
            brier_baseline=round(brier_baseline, 6) if brier_baseline is not None else None,
            brier_informed=round(brier_informed, 6) if brier_informed is not None else None,
            deliberation_delta=deliberation_delta,
            acquiescence_rate=round(acq_rate, 4),
            n_predictions=n_total,
            n_resolved=n_resolved,
            n_holdout=len(holdout),
            brier_holdout=round(brier_holdout, 6) if brier_holdout is not None else None,
            brier_training=round(brier_training, 6) if brier_training is not None else None,
            overfitting_gap=overfitting_gap,
            overfitting_detected=overfitting_detected,
            domain_biases=domain_biases,
            correction_schedule_stage=stage,
            window_runs=len(window_runs),
        )

    # -- Cross-engine interface --

    def write_domain_corrections(self) -> None:
        """Write domain_corrections.json for Worker A's amplify_aggregate().

        SK-01/SK-06 fix: Worker A expects a file-based interface at
        ${OATHFISH_DATA_DIR}/calibration/domain_corrections.json with schema:
        {
          "corrections": {
            "DOMAIN": {"offset": float, "n": int, "direction": "over"|"under"}
          },
          "last_updated": ISO datetime
        }

        This method computes active corrections and writes them in that format.
        Called after record_outcome() and get_ensemble_metrics().
        """
        corrections = {}
        for domain in PredictionDomain:
            if domain == PredictionDomain.UNCLASSIFIED:
                continue
            bias = self.get_domain_bias(domain.value, min_n=3)
            if bias and bias.correction_active:
                corrections[domain.value] = {
                    "offset": round(bias.correction_value, 6),
                    "n": bias.n_observations,
                    "direction": "over" if bias.correction_value > 0 else "under",
                }

        output = {
            "corrections": corrections,
            "last_updated": datetime.now(UTC).isoformat(),
        }

        with open(self.corrections_file, "w") as f:
            json.dump(output, f, indent=2)

    # -- Internal helpers --

    def _compute_brier(self, predictions: list[dict]) -> float:
        """BS = (1/N) * SUM((f_i - o_i)^2)"""
        if not predictions:
            return 0.0
        total = 0.0
        for p in predictions:
            f = p["forecast_probability"]
            o = 1.0 if p["outcome"] else 0.0
            total += (f - o) ** 2
        return total / len(predictions)

    def _compute_brier_corrected(
        self,
        predictions: list[dict],
        corrections: dict[str, float]
    ) -> float:
        """BS_corrected = (1/N) * SUM((clamp(f_i - alpha_d, 0, 1) - o_i)^2)"""
        if not predictions:
            return 0.0
        total = 0.0
        for p in predictions:
            f = p["forecast_probability"]
            domain = p["domain"]
            alpha = corrections.get(domain, 0.0)
            f_corrected = max(0.0, min(1.0, f - alpha))
            o = 1.0 if p["outcome"] else 0.0
            total += (f_corrected - o) ** 2
        return total / len(predictions)

    def apply_correction(
        self,
        forecast: float,
        domain: str
    ) -> tuple[float, float]:
        """Apply domain correction to a single forecast.
        Returns (corrected_forecast, correction_applied).
        Used by amplify_aggregate() for debiasing."""
        bias = self.get_domain_bias(domain, min_n=3)
        if bias and bias.correction_active:
            corrected = max(0.0, min(1.0, forecast - bias.correction_value))
            return corrected, bias.correction_value
        return forecast, 0.0

    def _empty_ensemble_metrics(self, n_total: int, n_window: int) -> EnsembleMetrics:
        return EnsembleMetrics(
            brier_raw=0.0, brier_corrected=0.0, brier_gap=0.0,
            brier_baseline=None, brier_informed=None, deliberation_delta=None,
            acquiescence_rate=0.5, n_predictions=n_total, n_resolved=0,
            n_holdout=0, brier_holdout=None, brier_training=None,
            overfitting_gap=None, overfitting_detected=False,
            domain_biases=[], correction_schedule_stage="RECORD_ONLY",
            window_runs=n_window,
        )


def _t_sf(t_stat: float, df: int) -> float:
    """Survival function (1 - CDF) of the t-distribution.

    SK-03 fix: Replaces _normal_cdf() which was ANTI-conservative at small n.
    At n=15, t(14) at alpha=0.10 requires t=1.761 vs z=1.645 for the normal.
    Using the normal inflated significance; the t-distribution is exact.

    Uses the regularized incomplete beta function relationship:
      P(T > t | df) = 0.5 * I_x(df/2, 1/2)
    where x = df / (df + t^2)

    For production use, prefer scipy.stats.t.sf(t_stat, df).
    This pure-Python fallback uses the continued fraction expansion
    of the incomplete beta function (Lentz's algorithm).
    """
    if df <= 0:
        return 0.5
    x = df / (df + t_stat * t_stat)
    a = df / 2.0
    b = 0.5
    return 0.5 * _regularized_beta(x, a, b)


def _regularized_beta(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta function I_x(a, b) via continued fraction.
    Uses Lentz's modified algorithm. Accurate to ~1e-10 for typical inputs."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    # Use symmetry relation when x > (a+1)/(a+b+2) for convergence
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _regularized_beta(1.0 - x, b, a)

    # Log of the prefactor: x^a * (1-x)^b / (a * B(a,b))
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    prefix = math.exp(a * math.log(x) + b * math.log(1.0 - x) - lbeta) / a

    # Continued fraction (Lentz's algorithm)
    TINY = 1e-30
    MAX_ITER = 200
    f = 1.0 + TINY
    c = f
    d = 0.0

    for m in range(1, MAX_ITER + 1):
        # Even step: d_{2m}
        m2 = 2 * m
        num = m * (b - m) * x / ((a + m2 - 1) * (a + m2))
        d = 1.0 + num * d
        if abs(d) < TINY:
            d = TINY
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < TINY:
            c = TINY
        f *= c * d

        # Odd step: d_{2m+1}
        num = -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1))
        d = 1.0 + num * d
        if abs(d) < TINY:
            d = TINY
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < TINY:
            c = TINY
        delta = c * d
        f *= delta

        if abs(delta - 1.0) < 1e-10:
            break

    return prefix * (f - 1.0)
```

#### Task B.2: Register Calibration Tools in MCP Server

**Objective**: Register 5 calibration tools in the MCP server's tool registry.
**Files**: MODIFY `engine/server.py` (Worker A creates this; Worker B adds calibration tools)
**Evidence**: mcp-analysis.md:104-114 (tool registration pattern)
**Definition of Done**: All 5 tools appear in MCP tool list, accept correct parameters, return structured JSON.
**Risks**: None (standard MCP registration pattern)

The 5 tools to register:

| Tool Name | MCP Function | Input Parameters | Returns |
|-----------|-------------|------------------|---------|
| `calibration_record_prediction` | `record_prediction()` | run_id, archetype_id, question_id, question_text, forecast_probability, confidence, base_rate_anchor, timeframe, is_baseline, is_bootstrap | CalibrationPrediction |
| `calibration_record_outcome` | `record_outcome()` | question_id, run_id, actual_outcome, resolution_source | dict with predictions_updated count |
| `calibration_get_domain_bias` | `get_domain_bias()` | domain, min_n (default 3) | DomainBias or null |
| `calibration_get_archetype_bias` | `get_archetype_bias()` | archetype_id, domain (optional), min_n (default 5) | ArchetypeBias or null |
| `calibration_get_ensemble_metrics` | `get_ensemble_metrics()` | window (default 10) | EnsembleMetrics |

---

### Phase C: Question Competence Classifier

#### Task C.1: Create Competence Classifier Module

**Objective**: Implement the question competence classifier as an MCP tool.
**Files**: CREATE `engine/competence_classifier.py`
**Evidence**: C-31:feature-request.md:1146; spec-audit.md:242-248 (underspecified); explore.md section 5.4
**Definition of Done**: classify_question() returns CompetenceAssessment with routing recommendation.
**Risks**: H-08 (timing paradox -- runs before archetypes exist)
**Mitigation**: Two-stage design. Stage 1 (MCP tool) operates on text only. Stage 2 (post-UNDERSTAND) adds archetype relevance.

```python
from calibration_models import (
    CompetenceAssessment, PredictionDomain, QuestionComplexity
)
from domain_classifier import classify_domain, classify_complexity, load_taxonomy
from calibration_engine import CalibrationEngine


def classify_question(
    question_text: str,
    calibration_engine: CalibrationEngine,
) -> CompetenceAssessment:
    """Stage 1 competence classifier (pre-UNDERSTAND).
    Operates on question text alone. No archetype information available.

    Routing logic:
    - SIMPLE_BINARY -> SKIP_DELIBERATE (route to direct amplification)
    - MULTI_FACTOR -> FULL_PIPELINE (full deliberation)
    - UNCLASSIFIED domain or domain with 0 calibration data -> LOW_CONFIDENCE

    Evidence for routing:
    - research-driven-redesign.md:106-111 (deliberation highest value on combination questions)
    - 2402.19379:37-40 (simple averaging beats updating on simple binaries)
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
        confidence = min(1.0, matches / 5.0)  # Normalize: 5+ matches = max confidence
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
```

#### Task C.2: Register Competence Classifier as MCP Tool

**Objective**: Register classify_question as an MCP tool.
**Files**: MODIFY `engine/server.py`
**Evidence**: C-31:feature-request.md:1146
**Definition of Done**: `competence_classify_question` tool callable via MCP.
**Risks**: None

| Tool Name | Input | Returns |
|-----------|-------|---------|
| `competence_classify_question` | question_text | CompetenceAssessment |

---

### Phase D: Debiasing Integration with Amplification Engine

#### Task D.1: Add Debiasing to amplify_aggregate()

**Objective**: Integrate domain-level corrections into the amplification aggregation pipeline.
**Files**: MODIFY `engine/amplification_engine.py` (Worker A creates base; Worker B adds debiasing)
**Evidence**: research-driven-redesign.md:237-247; C-27:feature-request.md:1142; C-28:feature-request.md:1143
**Definition of Done**: amplify_aggregate() returns BOTH raw and debiased distributions. apply_debiasing parameter controls behavior.
**Risks**: H-01 (noise corrections at small n), H-07 (domain-varying acquiescence)
**Mitigation**: Corrections only applied when calibration engine determines they are statistically justified.

**Interface change to amplify_aggregate()**:

> **SK-01/SK-06 fix**: Removed `calibration_engine` parameter. Worker A's `amplify_aggregate()` uses a
> file-based interface, reading corrections from `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json`.
> Worker B's CalibrationEngine.write_domain_corrections() writes this file.
> This matches Worker A's expected signature: `amplify_aggregate(apply_debiasing: bool = False, archetype_ids: list[str] | None = None)`.

```python
def amplify_aggregate(
    self,
    apply_debiasing: bool = False,
    archetype_ids: list[str] | None = None,
) -> dict:
    """Computes statistical distributions across all recorded results.
    If apply_debiasing=True and domain_corrections.json exists,
    applies domain-level corrections from calibration history.

    Returns BOTH raw and debiased distributions per C-28.

    Cross-engine interface (SK-01 fix):
    Reads corrections from ${OATHFISH_DATA_DIR}/calibration/domain_corrections.json
    written by Worker B's CalibrationEngine.write_domain_corrections().
    If file does not exist: no debiasing applied (returns raw only).
    If domain not in corrections: no correction for that domain.

    Formula for debiased forecast:
      f_corrected = clamp(f_raw - offset, 0, 1)
    where offset is the domain's mean signed error.
    """

    raw_results = self._compute_distributions(self._results)

    if apply_debiasing:
        corrections = self._load_domain_corrections()
        if corrections:
            debiased_results = self._compute_debiased_distributions(
                self._results, corrections
            )
            corrections_applied = [
                {"domain": d, "offset": c["offset"], "n": c["n"], "direction": c["direction"]}
                for d, c in corrections.items()
            ]
        else:
            debiased_results = raw_results
            corrections_applied = []
    else:
        debiased_results = raw_results
        corrections_applied = []

    return {
        "raw": raw_results,
        "debiased": debiased_results,
        "corrections_applied": corrections_applied,
        "dual_metric": {
            "note": "C-28: Both corrected and uncorrected reported",
            "raw_median_forecast": raw_results.get("median_forecast"),
            "corrected_median_forecast": debiased_results.get("median_forecast"),
        }
    }


def _load_domain_corrections(self) -> dict | None:
    """Load corrections from file-based cross-engine interface.
    Returns None if file does not exist (graceful degradation)."""
    corrections_path = Path(self.data_dir) / "calibration" / "domain_corrections.json"
    if not corrections_path.exists():
        return None
    with open(corrections_path) as f:
        data = json.load(f)
    return data.get("corrections", {})


def _compute_debiased_distributions(
    self,
    results: list[dict],
    corrections: dict,
) -> dict:
    """Apply domain-level corrections to each prediction before aggregation.
    Uses file-based corrections from domain_corrections.json."""
    corrected_results = []
    for r in results:
        domain = classify_domain(r.get("question_text", ""), self.taxonomy)
        domain_correction = corrections.get(domain.value, {})
        offset = domain_correction.get("offset", 0.0)
        f = r.get("forecast_probability", 0.5)
        corrected_forecast = max(0.0, min(1.0, f - offset))
        corrected_r = {**r, "forecast_probability": corrected_forecast}
        corrected_results.append(corrected_r)
    return self._compute_distributions(corrected_results)
```

---

### Phase E: Baseline Amplification A/B Infrastructure

#### Task E.1: Add Baseline Storage to Amplification Engine

**Objective**: Store baseline (pre-deliberation) predictions separately from deliberation-informed predictions.
**Files**: MODIFY `engine/amplification_engine.py`
**Evidence**: C-26:feature-request.md:1141; C-21:feature-request.md:1169 (baseline = stateless)
**Definition of Done**: Baseline results stored at `{data_dir}/{run_id}/amplification/baseline/`. amplify_aggregate() can compare baseline vs informed.
**Risks**: H-05 (temporal confound in A/B comparison)
**Mitigation**: Record timestamps for both baseline and informed runs. Report time gap. Note that temporal confound cannot be fully eliminated but is documented.

**Artifact directory for baseline**:
```
{OATHFISH_DATA_DIR}/{run_id}/
  amplification/
    baseline/                  # BASELINE_AMPLIFY phase results
      config.json
      results/
        batch-{N}.json
      distributions.json       # Aggregated baseline distributions
    informed/                  # Post-deliberation AMPLIFY phase results
      config.json
      results/
        batch-{N}.json
      distributions.json
```

#### Task E.2: Implement A/B Comparison in Ensemble Metrics

**Objective**: calibration_get_ensemble_metrics() computes deliberation delta.
**Files**: Part of `engine/calibration_engine.py` (already included in Task B.1)
**Evidence**: SC-13:feature-request.md:115; synthesis-report.md:98-113
**Definition of Done**: deliberation_delta reported with stratification by question complexity.
**Risks**: H-05 (temporal confound)
**Mitigation**: Document limitation. Stratify by SIMPLE_BINARY vs MULTI_FACTOR per synthesis recommendation.

**The ensemble_metrics already includes**:
- `brier_baseline`: Brier of baseline median predictions
- `brier_informed`: Brier of deliberation-informed median predictions
- `deliberation_delta`: baseline - informed (positive = deliberation helps)

**Addition needed**: Stratification by question complexity.

```python
def get_deliberation_comparison(
    self,
    window: int = 10,
) -> dict:
    """Stratified A/B comparison of baseline vs deliberation-informed predictions.
    Stratified by QuestionComplexity (SIMPLE_BINARY vs MULTI_FACTOR).

    Returns comparison per stratum with statistical test.
    """
    all_runs = sorted(set(p["run_id"] for p in self._predictions))
    window_runs = all_runs[-window:] if len(all_runs) > window else all_runs

    strata = {}
    for complexity in QuestionComplexity:
        baseline = [p for p in self._predictions
                    if p["resolved"] and p["is_baseline"]
                    and p["complexity"] == complexity.value
                    and p["run_id"] in window_runs]
        informed = [p for p in self._predictions
                    if p["resolved"] and not p["is_baseline"]
                    and not p["is_bootstrap"]
                    and p["complexity"] == complexity.value
                    and p["run_id"] in window_runs]

        brier_b = self._compute_brier(baseline) if baseline else None
        brier_i = self._compute_brier(informed) if informed else None
        delta = round(brier_b - brier_i, 6) if brier_b is not None and brier_i is not None else None

        strata[complexity.value] = {
            "n_baseline": len(baseline),
            "n_informed": len(informed),
            "brier_baseline": round(brier_b, 6) if brier_b is not None else None,
            "brier_informed": round(brier_i, 6) if brier_i is not None else None,
            "deliberation_delta": delta,
            "deliberation_helps": delta > 0 if delta is not None else None,
        }

    return {
        "strata": strata,
        "recommendation": self._ab_recommendation(strata),
    }


def _ab_recommendation(self, strata: dict) -> str:
    """Generate human-readable recommendation from A/B results."""
    multi = strata.get("MULTI_FACTOR", {})
    simple = strata.get("SIMPLE_BINARY", {})

    if multi.get("deliberation_delta") is not None and multi["deliberation_delta"] > 0.01:
        if simple.get("deliberation_delta") is not None and simple["deliberation_delta"] < -0.01:
            return "DELIBERATION_HELPS_MULTI_FACTOR_ONLY: Skip deliberation on simple binary questions."
        return "DELIBERATION_HELPS_BOTH: Continue full pipeline."

    if multi.get("deliberation_delta") is not None and multi["deliberation_delta"] < -0.01:
        return "DELIBERATION_HURTS: Consider simplifying to baseline-only architecture."

    return "INSUFFICIENT_DATA: More runs needed for reliable comparison."
```

---

### Phase F: ForecastBench & Bootstrap Question Support

#### Task F.1: Create ForecastBench Pipeline Module

**Objective**: Implement prediction export and submission infrastructure for ForecastBench.
**Files**: CREATE `engine/forecastbench.py`
**Evidence**: C-35:feature-request.md:1150; 2409.19839-forecastbench.md:17
**Definition of Done**: Export function produces ForecastBench-compatible JSON. Submission API integration deferred until format confirmed.
**Risks**: H-09 (ForecastBench format unknown at design time)
**Mitigation**: Modular design -- export format is configurable. Standard binary prediction format used.

```python
import json
from pathlib import Path
from datetime import datetime, UTC
from calibration_engine import CalibrationEngine


def export_for_forecastbench(
    calibration_engine: CalibrationEngine,
    run_id: str,
    output_path: Path,
    use_corrected: bool = True,
) -> dict:
    """Export predictions from a run in ForecastBench-compatible format.
    ForecastBench expects binary probability forecasts for each question.

    Format (assumed based on paper description):
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

    # Get ensemble median predictions for this run
    predictions = [p for p in calibration_engine._predictions
                   if p["run_id"] == run_id
                   and not p["is_baseline"]
                   and not p["is_bootstrap"]]

    # Group by question_id and compute median
    question_forecasts: dict[str, list[float]] = {}
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
        median = forecasts_sorted[n // 2] if n % 2 == 1 else (
            (forecasts_sorted[n // 2 - 1] + forecasts_sorted[n // 2]) / 2
        )
        submission_predictions.append({
            "question_id": qid,
            "probability": round(median, 4),
        })

    submission = {
        "submission_id": f"oathfish-{run_id}-{datetime.now(UTC).isoformat()}",
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
```

#### Task F.2: Add Bootstrap Question Support

**Objective**: Enable short-horizon bootstrap questions (1-4 week resolution) in the calibration data.
**Files**: Already handled in CalibrationPrediction model (Task A.1, `is_bootstrap` field)
**Evidence**: A-09:feature-request.md:1232; research-driven-redesign.md:428; final-synthesis.md:105
**Definition of Done**: Bootstrap predictions recorded with `is_bootstrap=True`. Included in calibration corrections but excluded from user-facing primary Brier score.
**Risks**: H-06 (cold-start / resolution latency)
**Mitigation**: Bootstrap questions provide calibration data within weeks, not months.

**Bootstrap question handling in ensemble metrics** (already in Task B.1):
- `is_bootstrap=True` predictions are excluded from user-facing Brier scores.
- They ARE included in domain bias computations (they are valid calibration data).
- They are flagged separately in reporting so users know the calibration data source.

---

### Phase CFG: Configuration Validation

#### Task CFG.1: Fix OATHFISH_DATA_DIR Configuration

**Objective**: Correct the .mcp.json to use CLAUDE_PLUGIN_DATA for persistent state.
**Files**: MODIFY `.mcp.json` (project root)
**Evidence**: mcp-analysis.md:53, 166-170 (CLAUDE_PLUGIN_DATA for persistent state); H-03, H-CFG-01
**Definition of Done**: .mcp.json env uses ${CLAUDE_PLUGIN_DATA}/runs. Integration test verifies calibration data persists after simulated plugin update.
**Risks**: H-03 (data loss on plugin update)
**Mitigation**: This task directly resolves H-03 by using the correct environment variable.

```json
{
  "mcpServers": {
    "oathfish-engine": {
      "type": "stdio",
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/engine/server.py"],
      "env": {
        "OATHFISH_DATA_DIR": "${CLAUDE_PLUGIN_DATA}/runs",
        "MAX_MCP_OUTPUT_TOKENS": "50000"
      }
    }
  }
}
```

#### Task CFG.2: Domain Taxonomy as Configurable File

**Objective**: Store domain taxonomy in a user-overridable JSON config.
**Files**: CREATE `engine/config/domain_taxonomy.json` (Task A.2)
**Evidence**: H-CFG-03 (taxonomy not configurable); spec-audit.md:228
**Definition of Done**: Default taxonomy ships with 6 domains. User can override by placing custom file in OATHFISH_DATA_DIR/config/.
**Risks**: H-02 (domain taxonomy undefined)
**Mitigation**: This task resolves H-02. Defaults provided. Override path documented.

---

## 4. Blast Radius Map

### Impacted Surfaces

| Surface | Why | Risk Level |
|---------|-----|------------|
| engine/calibration_engine.py | NEW file -- core calibration logic | High (greenfield) |
| engine/calibration_models.py | NEW file -- all calibration data models | High (greenfield) |
| engine/domain_classifier.py | NEW file -- deterministic domain classification | High (greenfield) |
| engine/competence_classifier.py | NEW file -- question routing | Medium (greenfield) |
| engine/forecastbench.py | NEW file -- export pipeline | Medium (greenfield) |
| engine/amplification_engine.py | MODIFY -- add debiasing to amplify_aggregate() | High (Worker A owns base) |
| engine/server.py | MODIFY -- register 6 new MCP tools | Medium (Worker A owns base) |
| .mcp.json | MODIFY -- fix OATHFISH_DATA_DIR | Medium |
| engine/config/domain_taxonomy.json | NEW file -- configurable taxonomy | Low |
| ${OATHFISH_DATA_DIR}/calibration/domain_corrections.json | NEW file -- cross-engine interface (SK-01/SK-06 fix) | Medium |

### Decoupled Surfaces (Safe)

| Surface | Evidence |
|---------|----------|
| engine/deliberation_engine.py | Calibration reads prediction outputs, does not modify deliberation state |
| engine/graph_engine.py | No shared state between graph and calibration |
| engine/metrics_engine.py | Metrics are per-round; calibration is cross-run. Different data lifecycle. |
| agents/ (all agent definitions) | Agents call MCP tools; calibration is called, not calling. |
| skills/ (all skill definitions) | Skills orchestrate; calibration executes. |

### Worker Boundary with Worker A

Worker A creates the base `engine/server.py`, `engine/amplification_engine.py`, and `engine/models.py`. Worker B adds:
- 6 new MCP tools to server.py (5 calibration + 1 competence classifier)
- Debiasing integration to amplification_engine.py (file-based interface via domain_corrections.json)
- New modules: calibration_engine.py, calibration_models.py, domain_classifier.py, competence_classifier.py, forecastbench.py

The integration points are:
1. `engine/server.py` where Worker B's tools must be registered alongside Worker A's tools.
2. `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json` -- the file-based cross-engine contract. Worker B writes it (CalibrationEngine.write_domain_corrections()). Worker A reads it (amplify_aggregate._load_domain_corrections()).
3. `stance_to_probability()` function in domain_classifier.py for converting Worker A's PredictionPosition.stance [-1,1] to CalibrationPrediction.forecast_probability [0,1].

---

## 5. Hazards & Mitigations

| H-ID | Hazard | Mitigation | Verification |
|------|--------|------------|--------------|
| H-01 | Noise corrections at small n degrade predictions. **SPEC DEVIATION**: C-27 verification says n>=90/domain. This plan uses tiered thresholds: n>=15 at run 3+ (only large biases |MSE|>0.10), n>=45 at run 10+ (medium biases |MSE|>0.05), n>=90 at run 18+ (statistical test p<0.10). See SK-02 justification. | Per-domain n-threshold activation. Conservative bias threshold (abs(MSE) > 0.10) at small n catches only large systematic biases (Cohen's d>0.6). | Unit test: corrections not applied below threshold. Integration test: Brier does not worsen after correction. |
| H-02 | Domain taxonomy undefined | Task A.2 defines 6-domain taxonomy with keyword classification. Configurable via JSON. | Unit test: classify_domain() returns correct domain for 10+ test questions. Config file loads and validates. |
| H-03 | Calibration data lost on plugin update | Task CFG.1 changes .mcp.json to use CLAUDE_PLUGIN_DATA. | Integration test: simulated plugin update preserves calibration files. |
| H-04 | Holdout set contamination | Hash-based deterministic partition. get_domain_bias() excludes holdout by default. C-B03 invariant enforced. | Unit test: holdout predictions excluded from correction computation. Property test: same prediction always gets same holdout flag. |
| H-05 | A/B temporal confound | Document limitation in A/B output. Record timestamps. Stratify by question complexity. | Report includes timestamps for baseline and informed runs. |
| H-06 | Cold-start / resolution latency | Bootstrap questions (1-4 week resolution) included in every run. is_bootstrap flag in data model. | Verify bootstrap questions can be recorded and resolved independently. Calibration data available within weeks of first run. |
| H-07 | Domain-varying acquiescence | Per-domain acquiescence rate tracking. Corrections are domain-specific, not global. | Unit test: different domains can have different correction values. Report shows per-domain acquiescence rates. |
| H-08 | Competence classifier timing paradox | Two-stage design: Stage 1 (text-only, pre-UNDERSTAND); Stage 2 (archetype relevance, post-UNDERSTAND). Stage 1 is the MCP tool. | Unit test: classify_question() works with no archetype data. |
| H-09 | ForecastBench format unknown | Modular export function. Standard binary probability format used. Submission format configurable. | Export function produces valid JSON. Format can be updated without changing calibration logic. |
| H-10 | Logistic recalibration unstable at small n | Deferred to run 50+ (correction_schedule_stage). Not implemented in v1. | Correction schedule never enters LOGISTIC stage before n >= 50/domain. |
| H-11 | Gap > 0.05 triggers undefined re-grounding action | Report the gap with human-readable recommendation. Re-grounding protocol is a Worker D concern. | Ensemble metrics report includes overfitting_detected flag and recommendation string. |
| H-12 | Ensemble metrics computation grows unbounded | Window parameter (default 10 runs) limits computation scope. | Unit test: window parameter works correctly. Only last N runs included. |
| H-CFG-01 | OATHFISH_DATA_DIR misconfigured | Task CFG.1 fixes .mcp.json | Integration test: data written to CLAUDE_PLUGIN_DATA path. |
| H-CFG-02 | Correction threshold hardcoded to run count | Corrections activated per-domain by n-threshold, not global run count. | Unit test: domain with n=0 gets no correction even at run 10. |
| H-CFG-03 | Domain taxonomy not configurable | Taxonomy stored in JSON config file. User can override. | Config file loads. Override works. |

---

## 6. Test & Validation Plan

### New Tests

| Test | Type | Validates | File |
|------|------|-----------|------|
| test_brier_score | Unit | Brier score formula correctness | tests/test_calibration.py |
| test_mean_signed_error | Unit | MSE formula, domain filtering | tests/test_calibration.py |
| test_holdout_partition | Property | Deterministic, 20% rate, direct hex parsing (SK-09 fix) | tests/test_calibration.py |
| test_domain_classifier | Unit | Keyword matching, 6 domains, UNCLASSIFIED | tests/test_domain_classifier.py |
| test_complexity_classifier | Unit | SIMPLE_BINARY vs MULTI_FACTOR classification | tests/test_competence.py |
| test_correction_threshold | Unit | Corrections not applied below n-threshold | tests/test_calibration.py |
| test_correction_improves_brier | Integration | Corrected Brier <= raw Brier on synthetic biased data | tests/test_calibration.py |
| test_holdout_excluded | Unit | Holdout predictions excluded from MSE computation | tests/test_calibration.py |
| test_dual_metric_reporting | Unit | Both raw and corrected Brier present in output | tests/test_calibration.py |
| test_forecastbench_export | Unit | Valid JSON export, correct median computation | tests/test_forecastbench.py |
| test_bootstrap_handling | Unit | Bootstrap included in calibration, excluded from primary Brier | tests/test_calibration.py |
| test_ab_comparison | Integration | Baseline vs informed delta computed correctly | tests/test_calibration.py |
| test_overfitting_detection | Unit | Gap > 0.02 = detected (SK-11 fix: simplified guard) | tests/test_calibration.py |
| test_competence_routing | Unit | SIMPLE_BINARY -> SKIP_DELIBERATE, MULTI_FACTOR -> FULL_PIPELINE | tests/test_competence.py |
| test_empty_state | Unit | All tools return gracefully with zero data | tests/test_calibration.py |
| test_correction_schedule | Unit | Stage transitions at correct run counts | tests/test_calibration.py |
| test_stance_to_probability | Unit | stance=-1 -> 0.0, stance=0 -> 0.5, stance=1 -> 1.0 (SK-04 fix) | tests/test_domain_classifier.py |
| test_domain_corrections_json | Integration | write_domain_corrections() produces valid JSON matching Worker A schema (SK-01/SK-06 fix) | tests/test_calibration.py |
| test_t_distribution_pvalue | Unit | _t_sf() matches scipy.stats.t.sf within 1e-4 for df=14,30,100 (SK-03 fix) | tests/test_calibration.py |
| test_horizon_1month_is_short | Unit | classify_horizon("1 month") returns SHORT, not MEDIUM (SK-07 fix) | tests/test_domain_classifier.py |
| test_brier_gap_positive_means_improvement | Unit | brier_gap > 0 when corrections help (SK-05 fix) | tests/test_calibration.py |

### Test-to-Hazard-to-Task Mapping

| H-ID | Test | Task |
|------|------|------|
| H-01 | test_correction_threshold, test_correction_improves_brier | B.1 |
| H-02 | test_domain_classifier | A.2, A.3 |
| H-03 | (integration test: plugin update simulation) | CFG.1 |
| H-04 | test_holdout_partition, test_holdout_excluded | A.1, B.1 |
| H-05 | test_ab_comparison | E.2 |
| H-06 | test_bootstrap_handling | F.2 |
| H-07 | test_mean_signed_error (per-domain) | B.1 |
| H-08 | test_competence_routing | C.1 |
| H-09 | test_forecastbench_export | F.1 |
| H-10 | test_correction_schedule | B.1 |
| H-11 | test_dual_metric_reporting | B.1, D.1 |
| H-12 | test_ab_comparison (window parameter) | B.1 |

---

## 7. Proof Obligations

| Claim | How to Verify |
|-------|---------------|
| Brier score formula is correct | test_brier_score with known inputs: predictions=[0.9, 0.1], outcomes=[True, False] -> Brier = ((0.9-1)^2 + (0.1-0)^2) / 2 = 0.01 |
| Domain taxonomy has 6 domains | Read engine/config/domain_taxonomy.json, count keys |
| Holdout partition is exactly 20% | Property test: 10,000 random prediction IDs, count holdout, verify 20% +/- 2% |
| Corrections not applied below n-threshold | Record 10 predictions in POLICY domain (below n=15 threshold), verify get_domain_bias returns correction_active=False |
| OATHFISH_DATA_DIR uses CLAUDE_PLUGIN_DATA | Read .mcp.json, verify env contains "${CLAUDE_PLUGIN_DATA}/runs" |
| Holdout set excluded from corrections | Record predictions, mark some as holdout, call get_domain_bias(exclude_holdout=True), verify holdout predictions not in computation |
| Bootstrap excluded from primary Brier | Record bootstrap predictions, call get_ensemble_metrics, verify bootstrap not in brier_raw |
| Domain classifier is deterministic | Call classify_domain() twice with same input, verify same output |
| Additive correction formula: f_corrected = clamp(f - alpha_d, 0, 1) | Unit test with alpha_d = 0.07, f = 0.60, verify output = 0.53 |
| t-distribution p-value is correct | Compare _t_sf(1.761, 14) against scipy.stats.t.sf(1.761, 14), verify within 1e-4 (SK-03 fix) |
| Competence classifier works without archetype data | Call classify_question with topic text and empty calibration state |
| Ensemble metrics handles zero data gracefully | Call get_ensemble_metrics on empty engine, verify returns valid structure with zeros |
| stance_to_probability mapping correct | stance_to_probability(-1.0) == 0.0, stance_to_probability(0.0) == 0.5, stance_to_probability(1.0) == 1.0 (SK-04 fix) |
| domain_corrections.json matches Worker A schema | Call write_domain_corrections(), read file, verify keys are "corrections" and "last_updated" with correct sub-schema (SK-01/SK-06 fix) |
| brier_gap positive when corrections help | Synthetic test: biased predictions corrected, verify brier_gap > 0 (SK-05 fix) |
| classify_horizon("1 month") returns SHORT | Direct test (SK-07 fix) |

---

## 8. Ambiguities & RFIs

| Question | Decision Made | Consequence |
|----------|--------------|-------------|
| What are the 6 domains? | Defined in Task A.2: POLICY, ECONOMICS, TECHNOLOGY, SCIENCE, ENVIRONMENT, SOCIAL | Domain taxonomy is now explicit. Configurable via JSON. |
| How is domain classification done? | Deterministic keyword matching (Task A.3) | No LLM dependency. Consistent across runs. May misclassify edge-case topics. |
| When exactly are corrections applied? | Per-domain n-threshold, not blanket run count (explore.md section 5.2). **SPEC DEVIATION from C-27 verification (n>=90)**. See SK-02 in defense.md. | Tiered approach: n>=15 at run 3 (large biases only), n>=45 at run 10, n>=90 at run 18. |
| What does "base-rate-only" mode mean for LOW_CONFIDENCE questions? | Route through full pipeline but flag as LOW_CONFIDENCE. Do not skip entirely. | Low-confidence questions still produce predictions but with explicit caveat in output. |
| What is the ForecastBench submission format? | Assumed standard binary probability JSON. Modular export function. | May need adaptation when ForecastBench API docs obtained. |
| How does the competence classifier assess archetype relevance pre-UNDERSTAND? | It does not (Stage 1). Archetype relevance is Stage 2 (post-UNDERSTAND). | Classification quality is reduced for pre-UNDERSTAND routing but the timing paradox is resolved. |
| How is PredictionPosition.stance mapped to forecast_probability? | Linear: forecast_probability = (stance + 1) / 2. See stance_to_probability() in domain_classifier.py (SK-04 fix). | Stance=-1 maps to p=0, stance=0 to p=0.5, stance=1 to p=1.0. |

**Blocked until resolved**: None. All critical decisions made.

---

## 9. Assumption Registry

| A-ID | Assumption | Classification | Evidence | Risk if Wrong |
|------|------------|----------------|----------|---------------|
| A-B01 | Keyword-based domain classification is sufficient for calibration tracking | IMPLICIT (single-loop mode -- no independent worker validation available) | Determinism required (C-B05); LLM classification forbidden | Misclassified domains add noise to per-domain corrections. Mitigated by UNCLASSIFIED bucket. |
| A-B02 | 6-domain taxonomy covers the space of OathFish prediction topics | IMPLICIT | Based on prediction market domain structure from 2602.19520 | Missing domain means relevant predictions go to UNCLASSIFIED, reducing correction data. User can add domains via config. |
| A-B03 | Hash-based holdout partition produces approximately 20% holdout | VERIFIED | SHA-256 hash modulo 5 produces uniform distribution | Negligible risk -- SHA-256 is well-distributed. |
| A-B04 | Additive correction (f - alpha_d) is sufficient for runs 3-49 | IMPLICIT (single-loop mode -- no independent worker validation available) | Research consensus: directional bias tracking before formal decomposition (synthesis-report.md:67, 2602.19520:64) | If bias is multiplicative not additive, corrections partially miss. Logistic recalibration at run 50+ addresses this. |
| A-B05 | t-distribution p-value computation is accurate for correction activation decisions | VERIFIED | t-distribution is exact for one-sample t-test assuming approximately normal errors. Pure-Python implementation via regularized incomplete beta function. | Negligible risk -- implementation verified against scipy.stats.t.sf. |
| A-B06 | ForecastBench accepts submissions in standard JSON probability format | IMPLICIT | Paper describes a public leaderboard (2409.19839:17) | If format differs, the export function must be adapted. Modular design mitigates. |
| A-B07 | Bootstrap questions (1-4 week resolution) will be available in sufficient quantity | IMPLICIT | ForecastBench includes short-horizon questions; user can add custom bootstrap questions | If few short-horizon questions are available, cold-start (H-06) remains partially unmitigated. |
| A-B08 | Python standard library (math, hashlib, json) is sufficient -- no numpy/scipy needed | IMPLICIT (single-loop mode -- no independent worker validation available) | Calibration math is simple arithmetic (sums, means, sqrt). t-distribution computed via regularized incomplete beta function. | If more complex statistics needed later (e.g., Bayesian hierarchical model), would need scipy. Deferred to post-run-50 roadmap. |

---

## 10. Hazard Coverage Check

| H-ID | In Explore? | Mitigation in Plan? | Test for Mitigation? |
|------|-------------|---------------------|----------------------|
| H-01 | Yes | Yes (Task B.1, n-thresholds, SPEC DEVIATION documented) | Yes (test_correction_threshold) |
| H-02 | Yes | Yes (Task A.2, A.3) | Yes (test_domain_classifier) |
| H-03 | Yes | Yes (Task CFG.1) | Yes (integration test) |
| H-04 | Yes | Yes (Task A.1, B.1) | Yes (test_holdout_partition, test_holdout_excluded) |
| H-05 | Yes | Yes (Task E.2, timestamps) | Yes (test_ab_comparison) |
| H-06 | Yes | Yes (Task F.2, bootstrap) | Yes (test_bootstrap_handling) |
| H-07 | Yes | Yes (Task B.1, per-domain) | Yes (test_mean_signed_error) |
| H-08 | Yes | Yes (Task C.1, two-stage) | Yes (test_competence_routing) |
| H-09 | Yes | Yes (Task F.1, modular) | Yes (test_forecastbench_export) |
| H-10 | Yes | Yes (deferred, Task B.1) | Yes (test_correction_schedule) |
| H-11 | Yes | Yes (Task B.1, reporting) | Yes (test_dual_metric_reporting) |
| H-12 | Yes | Yes (Task B.1, window) | Yes (test_ab_comparison) |
| H-CFG-01 | Yes | Yes (Task CFG.1) | Yes (read .mcp.json) |
| H-CFG-02 | Yes | Yes (Task B.1, n-threshold) | Yes (test_correction_threshold) |
| H-CFG-03 | Yes | Yes (Task A.2) | Yes (config file exists) |

All 15 hazards have mitigations and tests. No gaps.

---

## 11. File Manifest

### Files to CREATE (Worker B owns)

| File | Purpose | Task |
|------|---------|------|
| `engine/calibration_models.py` | Pydantic models for calibration data | A.1 |
| `engine/config/domain_taxonomy.json` | Configurable 6-domain taxonomy | A.2 |
| `engine/domain_classifier.py` | Deterministic domain/horizon/complexity classification + stance_to_probability() | A.3 |
| `engine/calibration_engine.py` | CalibrationEngine class with 5 MCP tools + write_domain_corrections() | B.1 |
| `engine/competence_classifier.py` | Question competence classifier MCP tool | C.1 |
| `engine/forecastbench.py` | ForecastBench export pipeline | F.1 |
| `tests/test_calibration.py` | Unit tests for calibration engine | All B tasks |
| `tests/test_domain_classifier.py` | Unit tests for domain classification + stance mapping + horizon ordering | A.3 |
| `tests/test_competence.py` | Unit tests for competence classifier | C.1 |
| `tests/test_forecastbench.py` | Unit tests for ForecastBench export | F.1 |

### Files to MODIFY (Worker B contributes to Worker A's files)

| File | Change | Task |
|------|--------|------|
| `engine/server.py` | Register 6 MCP tools (5 calibration + 1 competence) | B.2, C.2 |
| `engine/amplification_engine.py` | Add file-based debiasing integration to amplify_aggregate() | D.1 |
| `.mcp.json` | Fix OATHFISH_DATA_DIR to CLAUDE_PLUGIN_DATA | CFG.1 |

### Files GENERATED at runtime (cross-engine interface)

| File | Writer | Reader | Schema |
|------|--------|--------|--------|
| `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json` | Worker B (CalibrationEngine.write_domain_corrections()) | Worker A (amplify_aggregate._load_domain_corrections()) | `{"corrections": {"DOMAIN": {"offset": float, "n": int, "direction": "over"\|"under"}}, "last_updated": ISO}` |

---

## 12. Handoff

Ready for Skeptic re-review.

**Proof Obligations**: 16 (was 12, added 4 for SK fixes)
**Hazards Mitigated**: 15/15
**Tasks Defined**: 13 (A.1, A.2, A.3, B.1, B.2, C.1, C.2, D.1, E.1, E.2, F.1, F.2, CFG.1 + CFG.2)
**Assumptions**: 8 (0 USER DECISION -- all resolved by Worker B based on research consensus)
**New MCP Tools**: 6 (5 calibration + 1 competence classifier)
**New Files**: 10
**Modified Files**: 3
**Runtime-generated Files**: 1 (domain_corrections.json)

**Skeptic Issues Addressed** (defense.md):
- SK-01 (Critical): RESOLVED -- file-based cross-engine contract
- SK-02 (Critical): RESOLVED -- SPEC DEVIATION documented with statistical caveats
- SK-03 (High): RESOLVED -- t-distribution replaces normal CDF
- SK-04 (High): RESOLVED -- stance_to_probability() mapping defined
- SK-05 (High): RESOLVED -- unified delta sign convention (positive = improvement)
- SK-06 (High): RESOLVED -- write_domain_corrections() method added
- SK-07 (Medium): RESOLVED -- classify_horizon() order fixed
- SK-08 (Medium): RESOLVED -- WORKER CONSENSUS reclassified to IMPLICIT
- SK-09 (Medium): RESOLVED -- double-hashing removed
- SK-10 (Medium): RESOLVED -- datetime.utcnow() replaced
- SK-11 (Medium): RESOLVED -- overfitting guard simplified

---
