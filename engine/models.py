"""All Pydantic models for OathFish MCP server.

CANONICAL source -- all workers import from here.
~30 models across: enums, run state, archetype, positions, evolution, rounds, graph, amplification, metrics.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RunPhase(str, Enum):
    """8-state machine: 7 pipeline phases + INIT start state + ERROR recovery."""
    INIT = "INIT"
    UNDERSTAND = "UNDERSTAND"
    BASELINE_AMPLIFY = "BASELINE_AMPLIFY"
    DELIBERATE = "DELIBERATE"
    AMPLIFY = "AMPLIFY"
    SYNTHESIZE = "SYNTHESIZE"
    INTERACT = "INTERACT"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class RoundType(str, Enum):
    FREE_FORM = "FREE_FORM"
    STRUCTURED_DEBATE = "STRUCTURED_DEBATE"
    SCENARIO_REACTION = "SCENARIO_REACTION"
    PREDICTION = "PREDICTION"


class ConvergenceRecommendation(str, Enum):
    CONTINUE = "CONTINUE"
    CONVERGE = "CONVERGE"
    INJECT_CONTRARIAN = "INJECT_CONTRARIAN"


# ---------------------------------------------------------------------------
# Run-level
# ---------------------------------------------------------------------------

class RunConfig(BaseModel):
    topic: str
    archetype_count: int = 30
    deliberation_rounds: int = 6
    amplification_per_archetype: int = 50
    amplification_model: str = "haiku"
    checkpoint_interval: int = 3
    seed_documents: list[str] = Field(default_factory=list)


class StateHistoryEntry(BaseModel):
    state: RunPhase
    timestamp: str  # ISO 8601


class CheckpointData(BaseModel):
    checkpoint_id: str
    phase: RunPhase
    data: dict
    timestamp: str


class RunState(BaseModel):
    run_id: str
    state: RunPhase
    config: RunConfig
    state_history: list[StateHistoryEntry] = Field(default_factory=list)
    checkpoints: list[CheckpointData] = Field(default_factory=list)
    previous_state: RunPhase | None = None  # For ERROR -> resume
    created_at: str
    run_dir: str


# ---------------------------------------------------------------------------
# Archetype
# ---------------------------------------------------------------------------

class Archetype(BaseModel):
    id: str
    name: str
    segment: str
    demographics: dict = Field(default_factory=dict)
    values: list[str] = Field(default_factory=list)
    incentives: list[str] = Field(default_factory=list)
    blind_spots: list[str] = Field(default_factory=list)
    communication_style: str = ""
    initial_stance: str = ""
    persona_prompt: str = ""
    grounding_sources: list[str] = Field(default_factory=list)
    grounding_rung: int = 1  # 1-4 per C-29
    # Worker D proposed additions (non-breaking, all have defaults)
    is_structural: bool = False
    archetype_type: str = "topic"
    stubbornness_domain: str = ""
    grounding_search_queries: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Deliberation Positions (SPEC-01 split)
# ---------------------------------------------------------------------------

class ArgumentPosition(BaseModel):
    """Used in rounds 1-5 (qualitative arguments only, no numbers shared). C-33."""
    archetype_id: str
    round_n: int
    position_text: str
    key_arguments: list[str]
    concerns: list[str] = Field(default_factory=list)
    influenced_by: list[str] = Field(default_factory=list)
    base_rate_anchor: str = ""
    key_uncertainties: list[str] = Field(default_factory=list)


class PredictionPosition(BaseModel):
    """Used in round 6 (independent structured prediction, --json-schema enforced). C-33.
    13 fields per feature-request.md:546-561 (including coalition_alignment at line 560).
    """
    archetype_id: str
    round_n: int
    prediction: str = Field(description="The core prediction statement")
    decision: str = Field(description="adopt | wait | reject | mixed")
    stance: float = Field(ge=-1.0, le=1.0, description="Position on the issue scale")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in prediction")
    timeframe: str = Field(default="", description="Expected timeframe for outcome")
    base_rate_anchor: str = Field(default="", description="Historical base rate reference")
    key_uncertainties: list[str] = Field(default_factory=list, description="Key uncertainty factors")
    falsification_criteria: str = Field(default="", description="What would prove this wrong")
    second_order_effects: list[str] = Field(default_factory=list, description="Downstream consequences")
    cascade_susceptibility: float = Field(default=0.5, ge=0.0, le=1.0, description="Vulnerability to cascade effects")
    coalition_alignment: list[str] = Field(default_factory=list, description="Aligned archetype IDs")


# Type alias for polymorphic positions
Position = Union[ArgumentPosition, PredictionPosition]


# ---------------------------------------------------------------------------
# Evolution tracking
# ---------------------------------------------------------------------------

class ArgumentEvolution(BaseModel):
    archetype_id: str
    round_n: int
    jaccard_similarity: float  # vs previous round
    new_arguments: list[str]
    dropped_arguments: list[str]
    influence_chain: list[str]
    shift_summary: str = ""


class PredictionEvolution(BaseModel):
    archetype_id: str
    round_n: int  # Always 6 (or final prediction round)
    stance: float
    confidence: float
    stance_vs_initial: float  # Delta against Archetype.initial_stance (not round 5)


# ---------------------------------------------------------------------------
# Round
# ---------------------------------------------------------------------------

class RoundPlan(BaseModel):
    round_n: int
    round_type: RoundType


class RoundSummary(BaseModel):
    round_n: int
    round_type: RoundType
    positions: list[Position]  # Union via type alias
    key_themes: list[str] = Field(default_factory=list)
    notable_exchanges: list[str] = Field(default_factory=list)
    position_shifts: list[dict] = Field(default_factory=list)
    coalitions: list[list[str]] = Field(default_factory=list)


class DeliberationState(BaseModel):
    deliberation_id: str
    archetypes: list[Archetype]
    round_count: int
    round_plan: list[RoundPlan]
    current_round: int = 0
    rounds: dict[int, list[Position]] = Field(default_factory=dict)  # round_n -> positions
    evolutions: dict[int, list[Union[ArgumentEvolution, PredictionEvolution]]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

class EntityType(BaseModel):
    name: str
    description: str = ""


class EdgeType(BaseModel):
    name: str
    description: str = ""


class GraphOntology(BaseModel):
    entity_types: list[EntityType]
    edge_types: list[EdgeType]


class GraphNode(BaseModel):
    node_id: str
    name: str
    type: str
    summary: str = ""
    attributes: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    edge_id: str
    from_node: str
    to_node: str
    type: str
    facts: str = ""
    metadata: dict = Field(default_factory=dict)
    valid_at: str | None = None   # ISO timestamp or round number
    invalid_at: str | None = None


class GraphState(BaseModel):
    graph_id: str
    ontology: GraphOntology
    nodes: dict[str, GraphNode] = Field(default_factory=dict)
    edges: dict[str, GraphEdge] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Amplification
# ---------------------------------------------------------------------------

class AmplificationResult(BaseModel):
    persona_id: str
    archetype_id: str
    action: str  # adopt, wait, reject, modify
    reasoning: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    demographic_variation: dict = Field(default_factory=dict)


class AmplificationConfig(BaseModel):
    config_id: str
    archetypes: list[Archetype]
    variations_per_archetype: int
    model: str
    scenario: str
    total_calls: int
    is_baseline: bool = False  # True for BASELINE_AMPLIFY phase


class ArchetypeDistribution(BaseModel):
    archetype_id: str
    action_dist: dict[str, float]  # e.g., {"adopt": 0.6, "wait": 0.25, "reject": 0.15}
    avg_confidence: float
    top_themes: list[str] = Field(default_factory=list)


class AggregateResult(BaseModel):
    per_archetype: list[ArchetypeDistribution]
    overall: dict  # adoption_rate, rejection_rate, polarization_index, etc.
    network_effects: dict = Field(default_factory=dict)
    raw: dict = Field(default_factory=dict)      # Uncorrected
    debiased: dict = Field(default_factory=dict)  # After domain correction
    corrections_applied: list[dict] = Field(default_factory=list)


class AmplificationState(BaseModel):
    config: AmplificationConfig
    batches: dict[str, list[AmplificationResult]] = Field(default_factory=dict)
    total_recorded: int = 0


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class RoundMetrics(BaseModel):
    round_n: int
    diversity: float | None    # Distinct argument clusters / total unique args; null if < 5 args
    engagement: float          # Avg argument count per archetype
    stability: float           # Avg Jaccard between consecutive rounds
    coalitions: list[list[str]]  # Groups of aligned archetypes
    cluster_count: int         # Absolute number of argument clusters
    total_unique_arguments: int  # Raw count for consumers
    timestamp: str
    diversity_flag: str = ""   # "INSUFFICIENT_DATA" when total_unique_arguments < 5


class SentimentResult(BaseModel):
    score: float = Field(ge=-1.0, le=1.0)
    label: str  # positive, neutral, negative
    confidence: float = Field(ge=0.0, le=1.0)


class TrendResult(BaseModel):
    metric: str
    values: list[dict]  # [{round, value}, ...]
    trend: str  # increasing, decreasing, stable


class ConvergenceResult(BaseModel):
    converged: bool
    stability_metric: float
    diversity_index: float | None  # null when total_unique_arguments < 5
    cluster_count: int
    total_unique_arguments: int  # Raw count for context
    recommendation: ConvergenceRecommendation
    diversity_flag: str = ""  # "INSUFFICIENT_DATA" when total_unique_arguments < 5
