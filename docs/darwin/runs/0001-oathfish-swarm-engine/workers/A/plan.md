# Implementation Plan - Worker A: MCP Server Core Engines
## Run: 0001-oathfish-swarm-engine
## Worker: A
## Lens: mcp-core
## Revision: r2 (post-skeptic defense)

---

## Scope Anchor

**Goal**: Implement the OathFish MCP server (`oathfish-engine`) with 5 core engines (state machine, deliberation, graph, amplification, metrics), all Pydantic models, and write-through persistence. 21 MCP tools total.

**Constraints**:
- MUST: Python 3.11+, Pydantic v2+, `mcp` PyPI package, stdio transport (C-06, C-19)
- MUST: Write-through disk persistence after every mutation (C-15, C-23)
- MUST: All computation deterministic -- same inputs produce same outputs (C-02)
- MUST: No heavy external dependencies -- stdlib + mcp + pydantic only (C-19)
- MUST: 8-state state machine (7 pipeline phases + INIT start state): INIT->UNDERSTAND->BASELINE_AMPLIFY->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT->COMPLETE (C-07). Note: C-07 lists 7 phases excluding INIT; INIT is the implicit start state, not counted as a pipeline phase. The RunPhase enum also includes ERROR as a 9th state for error recovery.
- MUST: Split position types -- ArgumentPosition (rounds 1-5, text-only) + PredictionPosition (round 6, numeric) (C-14, C-33, SPEC-01)
- MUST: Diversity index tracking with premature consensus detection (C-32)
- MUST: Argument evolution via Jaccard similarity on argument sets (AMB-01 resolution)
- MUST NOT: Use LLM/NLP libraries for any computation (C-02, C-19)
- MUST NOT: Store run data under `${CLAUDE_PLUGIN_ROOT}` (use `${CLAUDE_PLUGIN_DATA}` per mcp-analysis.md:53)

**Success Criteria**:
- [ ] MCP server starts via stdio and responds to all 21 tool calls with valid JSON (SC-01)
- [ ] `state_transition()` rejects illegal transitions and records history
- [ ] `deliberation_record_round()` accepts ArgumentPosition for rounds 1-5 and PredictionPosition for round 6, rejecting mismatches
- [ ] `deliberation_check_convergence()` returns diversity index and INJECT_CONTRARIAN when appropriate
- [ ] All state mutations flush to disk atomically before tool returns
- [ ] `deliberation_get_position_map()` supports detail_level parameter to stay under 25,000 token limit
- [ ] Server can be killed and restarted, then `state_resume()` returns correct state

---

## Evidence Summary

| Fact | Source | Anchor |
|------|--------|--------|
| 7-phase state machine with BASELINE_AMPLIFY between UNDERSTAND and DELIBERATE (INIT is implicit start state, not counted as a phase per C-07) | Feature request v3 (SPEC-02 resolution) | feature-request.md:376, 1128 |
| ArgumentPosition: text-only for rounds 1-5 (no stance/confidence floats) | Feature request v3 (SPEC-01 resolution) | feature-request.md:535-545 |
| PredictionPosition: full numeric for round 6 (13 fields including coalition_alignment) | Feature request v3 (SPEC-01 resolution) | feature-request.md:546-561 |
| Jaccard similarity on argument sets for evolution tracking rounds 1-5 | AMB-01 resolution | feature-request.md:411 |
| Diversity index = distinct argument clusters; premature consensus if < 3 clusters before round 5 | C-32 + AMB-01 | feature-request.md:419 |
| INJECT_CONTRARIAN recommendation when diversity drops below threshold | C-32 | feature-request.md:420 |
| Write-through: every mutation flushes to disk immediately | C-23 invariant | feature-request.md:1177 |
| Data directory must use ${CLAUDE_PLUGIN_DATA} not ${CLAUDE_PLUGIN_ROOT} (SPEC CORRECTION: feature request at line 1064 uses CLAUDE_PLUGIN_ROOT which is wrong per mcp-analysis.md:53) | MCP analysis | mcp-analysis.md:53 |
| Tool output limit: 25,000 tokens default, configurable via MAX_MCP_OUTPUT_TOKENS env var, warning at 10,000 | MCP docs | mcp.md:158-167 |
| Graph edges need valid_at/invalid_at for temporal tracking | Research redesign | research-driven-redesign.md:148-150 |
| Convergence is NOT success -- false consensus warning | Paper 2305.14325 | papers/2305.14325:16 |
| amplify_aggregate() must output both raw and debiased distributions | Research redesign | research-driven-redesign.md:237-246 |
| Keyword sentiment is 0.7-weight component (deterministic) | D-01 user decision | feature-request.md:1134 |
| No existing Python code -- greenfield | Project scan | `find` returned 0 .py files |

---

## Cross-Worker Integration Contracts

**[NEW SECTION - Added in r2 to resolve SK-01, SK-03, SK-04, SK-06]**

### File Ownership Table

| File | Owner | Other Workers | Notes |
|------|-------|---------------|-------|
| `engine/models.py` | **Worker A** | Worker D imports from it (does NOT create independently) | Worker A defines all ~30 Pydantic models. Worker D's PredictionPosition is identical -- both match feature-request.md:546-561 (13 fields). Worker D may propose additional fields via coordination but Worker A is the canonical source. |
| `engine/amplification_engine.py` | **Worker A** (base) | Worker B MODIFIES (adds debiasing logic in Task D.1) | Worker A creates the base with 3 MCP tools. Worker B adds debiasing integration but MUST use the file-based interface (domain_corrections.json), NOT CalibrationEngine object injection. |
| `engine/server.py` | **Worker A** (base) | Worker B MODIFIES (registers 6 calibration MCP tools) | Worker A creates with 21 core tools. Worker B adds tool registration. |
| `.mcp.json` | **Worker C** | Worker A specifies env requirements (see Task G.4) | Worker C creates .mcp.json as part of plugin scaffold. Worker A does NOT create this file. |
| `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json` | **Worker B** (writes) | Worker A (reads) | File-based integration point. See contract in Task E.1. |

### Debiasing Interface Contract (SK-01/SK-06 Resolution)

Worker A's `amplify_aggregate()` reads calibration corrections from a file. Worker B's CalibrationEngine writes this file as a materialized view.

**Integration flow**:
1. Worker B's `CalibrationEngine.apply_correction()` computes domain biases and writes `domain_corrections.json`
2. Worker A's `amplify_aggregate(apply_debiasing=True)` reads `domain_corrections.json` from disk
3. No cross-engine Python imports required. Decoupled via filesystem.

**Worker A's canonical signature** (Worker B MUST preserve these parameters when modifying):
```python
async def amplify_aggregate(
    apply_debiasing: bool = False,    # Conservative default; no correction early runs
    archetype_ids: list[str] | None = None  # Pagination filter for H-07
) -> dict
```

Worker B's debiasing modification adds file-read logic INSIDE the function body but does NOT change the function signature. The `calibration_engine: Optional[CalibrationEngine]` parameter in Worker B's plan is replaced by internal file reads.

---

## Implementation Ledger

### Phase A: Foundation (models.py + persistence)

#### Task A.1: Create engine/models.py -- All Pydantic Models

**Objective**: Define every data structure used by all 5 engines.
**Files**: CREATE `engine/models.py`
**Ownership**: Worker A OWNS this file as the canonical model source. Worker D imports from `engine.models`, it does NOT independently create `engine/models.py`. Worker D's "extends planned file" language (Worker D plan line 62) means Worker D proposes additions through coordination; Worker A is authoritative.
**Evidence**: feature-request.md:522-587 defines 7 models; explore.md identifies 12+ additional models needed.

**Model Definitions:**

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Union
from enum import Enum
from datetime import datetime

# --- Enums ---

class RunPhase(str, Enum):
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

# --- Run-level ---

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

# --- Archetype ---

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

# --- Deliberation Positions (SPEC-01 split) ---

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
    Note: Worker D's plan incorrectly says "12 fields" -- the spec has 13."""
    archetype_id: str
    round_n: int
    prediction: str
    decision: str  # adopt | wait | reject | mixed
    stance: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    timeframe: str = ""
    base_rate_anchor: str = ""
    key_uncertainties: list[str] = Field(default_factory=list)
    falsification_criteria: str = ""
    second_order_effects: list[str] = Field(default_factory=list)
    cascade_susceptibility: float = Field(default=0.5, ge=0.0, le=1.0)
    coalition_alignment: list[str] = Field(default_factory=list)  # Spec-mandated: feature-request.md:560

# Type alias for polymorphic positions
Position = Union[ArgumentPosition, PredictionPosition]

# --- Evolution tracking ---

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
    round_n: int  # Always 6
    stance: float
    confidence: float
    stance_vs_initial: float  # Delta against Archetype.initial_stance (not round 5)

# --- Round ---

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

# --- Graph ---

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

# --- Amplification ---

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

# --- Metrics ---

class RoundMetrics(BaseModel):
    round_n: int
    diversity: float | None    # Distinct argument clusters / total unique args; null if < 5 args (INSUFFICIENT_DATA)
    engagement: float          # Avg argument count per archetype
    stability: float           # Avg Jaccard between consecutive rounds
    coalitions: list[list[str]]  # Groups of aligned archetypes
    cluster_count: int         # Absolute number of argument clusters
    total_unique_arguments: int  # [r2] Raw count for consumers to assess diversity_index quality
    timestamp: str
    diversity_flag: str = ""   # [r2] "INSUFFICIENT_DATA" when total_unique_arguments < 5

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
    diversity_index: float | None  # [r2] null when total_unique_arguments < 5
    cluster_count: int
    total_unique_arguments: int  # [r2] Raw count for context
    recommendation: ConvergenceRecommendation
    diversity_flag: str = ""  # [r2] "INSUFFICIENT_DATA" when total_unique_arguments < 5
```

**Definition of Done**: All models import cleanly. `mypy engine/models.py` passes with no errors.
**Risks**: H-10 (Position type alias)
**Mitigation**: Explicit `Position = Union[ArgumentPosition, PredictionPosition]` type alias defined.

---

#### Task A.2: Create engine/persistence.py -- Atomic Write-Through Layer

**Objective**: Cross-cutting persistence abstraction used by ALL engines.
**Files**: CREATE `engine/persistence.py`
**Evidence**: C-23 (feature-request.md:1177), C-15 (feature-request.md:1159)

**Implementation:**

```python
"""Write-through persistence layer for OathFish MCP server.

Every engine mutation MUST use these functions to ensure:
- C-15: State persists to disk after every mutation
- C-23: All state changes flush to disk immediately
- Crash safety: Atomic writes via temp+rename
"""

import json
import os
import tempfile
from pathlib import Path
from pydantic import BaseModel


def atomic_write_json(path: Path, data: BaseModel | dict | list) -> None:
    """Atomically write JSON data to path.

    Uses write-to-temp-then-rename pattern for POSIX atomicity.
    Ensures parent directories exist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(data, BaseModel):
        content = data.model_dump_json(indent=2)
    else:
        content = json.dumps(data, indent=2, default=str)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        suffix='.tmp',
        prefix='.oathfish_'
    )
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Force flush to disk
        os.replace(tmp_path, str(path))  # Atomic on POSIX
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_json(path: Path) -> dict | list | None:
    """Read JSON from path. Returns None if file does not exist."""
    if not path.exists():
        return None
    with open(path, 'r') as f:
        return json.load(f)


def ensure_run_dir(data_dir: Path, run_id: str) -> Path:
    """Create and return the run directory structure."""
    run_dir = data_dir / run_id
    for subdir in [
        '_meta',
        'understanding',
        'graph',
        'deliberation',
        'amplification',
        'amplification/results',
        'amplification/prompts',
        'synthesis',
        'team',
    ]:
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)
    return run_dir
```

**Definition of Done**: `atomic_write_json` passes crash-safety test: write is either fully committed or absent (no partial writes).
**Risks**: H-02 (disk full, permission error)
**Mitigation**: All writes wrapped in try/except with temp file cleanup. `os.fsync()` forces OS buffer flush.

---

### Phase B: State Machine Engine

#### Task B.1: Create engine/state_machine.py -- 5 MCP Tools

**Objective**: Run lifecycle management with 8-state state machine (7 pipeline phases + INIT start state).
**Files**: CREATE `engine/state_machine.py`
**Evidence**: feature-request.md:366-391

**Tool Signatures:**

```python
# Legal transitions (adjacency set)
# 9 states total: 7 pipeline phases + INIT + ERROR
# C-07 counts 7 phases: UNDERSTAND through COMPLETE (excluding INIT)
LEGAL_TRANSITIONS: dict[RunPhase, set[RunPhase]] = {
    RunPhase.INIT: {RunPhase.UNDERSTAND},
    RunPhase.UNDERSTAND: {RunPhase.BASELINE_AMPLIFY},
    RunPhase.BASELINE_AMPLIFY: {RunPhase.DELIBERATE},
    RunPhase.DELIBERATE: {RunPhase.AMPLIFY},
    RunPhase.AMPLIFY: {RunPhase.SYNTHESIZE},
    RunPhase.SYNTHESIZE: {RunPhase.INTERACT},
    RunPhase.INTERACT: {RunPhase.COMPLETE},
    # ERROR can be entered from any state
    # ERROR can resume to previous_state
}

async def state_init(run_id: str, config: dict) -> dict:
    """Creates run directory structure and run.json.

    Args:
        run_id: Unique run identifier
        config: RunConfig fields (topic, archetype_count, etc.)

    Returns:
        { run_id, run_dir, state: "INIT", created_at }
    """

async def state_transition(new_state: str) -> dict:
    """Validates transition is legal, records in run.json with timestamp.

    Handles:
    - Normal: INIT->UNDERSTAND->...->COMPLETE
    - Error: any->ERROR (stores previous_state for resume)
    - Resume: ERROR->{previous_state}

    Returns:
        { previous_state, new_state, timestamp }

    Raises tool error if transition is illegal.
    """

async def state_get() -> dict:
    """Returns current run state, config, and full state history.

    Returns:
        { run_id, state, config, state_history: [{state, timestamp}...] }
    """

async def state_checkpoint(phase: str, data: dict) -> dict:
    """Saves checkpoint data for the current phase (enables resume).

    Returns:
        { checkpoint_id, phase, timestamp }
    """

async def state_resume() -> dict:
    """Returns last valid state and checkpoint data.

    Returns:
        { state, checkpoint, resume_instructions }
    """
```

**Definition of Done**: All 5 tools respond with valid JSON. Illegal transitions rejected with error message. State survives server restart.
**Risks**: H-09 (ERROR resume after server restart)
**Mitigation**: `previous_state` persisted in run.json. `state_resume()` reads from disk, not memory.

---

### Phase C: Deliberation Engine

#### Task C.1: Create engine/deliberation_engine.py -- 5 MCP Tools

**Objective**: Round management, polymorphic position tracking, Jaccard-based evolution, diversity-preserving convergence.
**Files**: CREATE `engine/deliberation_engine.py`
**Evidence**: feature-request.md:393-425, AMB-01 resolution, C-32

**Tool Signatures:**

```python
async def deliberation_init(
    archetypes: list[dict],
    round_count: int,
    round_types: list[dict]
) -> dict:
    """Initializes deliberation state with archetype registry and round plan.

    Args:
        archetypes: List of Archetype dicts (from understand phase)
        round_count: Total rounds (default 6)
        round_types: List of {round_n, round_type} mappings

    Returns:
        { deliberation_id, archetype_count, round_plan }
    """

async def deliberation_record_round(
    round_n: int,
    positions: list[dict]
) -> dict:
    """Saves each archetype's position for round N.

    POLYMORPHIC (SPEC-01):
    - Rounds 1-5: Validates each position as ArgumentPosition
    - Round 6 (or final round): Validates as PredictionPosition

    The round_type is determined from the round_plan set in deliberation_init().
    NOT from a hardcoded "round 6 = prediction" rule.

    Args:
        round_n: Round number (1-indexed)
        positions: List of position dicts

    Returns:
        { round_n, positions_recorded, round_type: "argument"|"prediction", timestamp }
    """

async def deliberation_track_evolution(round_n: int) -> dict:
    """Computes argument evolution between round N and N-1.

    Rounds 1-5 (ArgumentPosition):
      - Jaccard similarity on key_arguments sets per archetype
      - New arguments introduced, arguments dropped
      - Influence chains from influenced_by field
      - Base rate anchor changes

    Round 6 (PredictionPosition):
      - Stance value (no delta -- this is the first numeric round)
      - Confidence value
      - Comparison to Archetype.initial_stance (qualitative parse if possible)

    Args:
        round_n: Round to compute evolution for (must be >= 2 for argument rounds)

    Returns:
        { round_n, evolutions: [{archetype_id, ...}...] }
    """

async def deliberation_check_convergence(window_size: int = 3) -> dict:
    """Checks if archetype arguments are stabilizing. Returns diversity index.

    Rounds 1-5 (Argument-based convergence):
      - Jaccard stability: avg Jaccard similarity across window
      - Converged if Jaccard > 0.8 for window_size consecutive rounds
      - Diversity index: distinct_clusters / total_unique_arguments
        [r2] GUARD: if total_unique_arguments < 5, diversity_index = null
        and diversity_flag = "INSUFFICIENT_DATA" (prevents misleading ratios)
      - PREMATURE_CONSENSUS if cluster_count < 3 before round 5
        OR diversity_index < 0.15 before round 5

    Round 6 (Prediction-based):
      - Standard deviation of stances across archetypes
      - If early convergence (all stances within 0.1): WARNING

    Args:
        window_size: Number of consecutive rounds to check

    Returns:
        { converged: bool, stability_metric: float,
          diversity_index: float | null, cluster_count: int,
          total_unique_arguments: int,
          recommendation: "CONTINUE"|"CONVERGE"|"INJECT_CONTRARIAN",
          diversity_flag: "" | "INSUFFICIENT_DATA" }
    """

async def deliberation_get_position_map(
    detail_level: str = "summary",
    archetype_ids: list[str] | None = None
) -> dict:
    """Returns position map with pagination support.

    detail_level="summary": Latest position per archetype (compact)
    detail_level="full": Full evolution history across all rounds

    archetype_ids filter: Only return specified archetypes

    Returns:
        { archetypes: [{id, name, segment, current_position, evolution: [...]}...] }
    """
```

**Key Implementation Details:**

1. **Type discrimination** (H-01 mitigation): The round plan (from `deliberation_init()`) maps each round_n to a RoundType. `deliberation_record_round()` checks the plan: if `round_type == PREDICTION`, validate as PredictionPosition; otherwise validate as ArgumentPosition. This avoids hardcoding "round 6" and supports configurable round counts.

2. **Jaccard computation** (AMB-01):
   ```python
   def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
       if not set_a and not set_b:
           return 1.0
       if not set_a or not set_b:
           return 0.0
       return len(set_a & set_b) / len(set_a | set_b)
   ```

3. **Argument clustering** for diversity index:
   ```python
   def cluster_arguments(all_arguments: list[str], threshold: float = 0.5) -> list[set[str]]:
       """Single-linkage clustering based on word-level Jaccard."""
       # Tokenize each argument into word sets (lowercase, strip stopwords)
       # Build adjacency: if jaccard(words_a, words_b) > threshold, link them
       # Find connected components via union-find
       # Return list of clusters
   ```

4. **Round 6 evolution** (H-11 mitigation): Since round 5 is ArgumentPosition (no numbers), round 6 PredictionEvolution computes:
   - `stance`: The absolute stance value from PredictionPosition
   - `confidence`: The absolute confidence value
   - `stance_vs_initial`: No numeric delta is meaningful. Instead, include the initial_stance text for reference. The coordinator (creative agent) interprets qualitative-to-quantitative shift.

5. **[r2] Diversity index minimum-N guard** (SK-11 mitigation): When `total_unique_arguments < 5`, the diversity index is set to `null` and `diversity_flag = "INSUFFICIENT_DATA"` is returned. This prevents misleading ratios where, e.g., 3 arguments in 3 clusters produces the same diversity (1.0) as 30 arguments in 30 clusters. The `total_unique_arguments` field is always reported so consumers have the raw count for their own assessment.

**Definition of Done**: Polymorphic round recording works. Diversity index computed. INJECT_CONTRARIAN fires when cluster_count < 3 before round 5.
**Risks**: H-01, H-06, H-11
**Mitigation**: Type discrimination via round plan (not hardcoded round number). Configurable clustering threshold. Round 6 deltas are absolute values, not deltas vs round 5. Minimum argument count guard on diversity index.

---

### Phase D: Graph Engine

#### Task D.1: Create engine/graph_engine.py -- 5 MCP Tools

**Objective**: Entity/relationship CRUD with temporal tracking and centrality computation.
**Files**: CREATE `engine/graph_engine.py`
**Evidence**: feature-request.md:427-454, research-driven-redesign.md:148-152

**Tool Signatures:**

```python
async def graph_init(ontology: dict) -> dict:
    """Creates graph with entity/relationship type definitions.

    Args:
        ontology: { entity_types: [{name, description}], edge_types: [{name, description}] }

    Returns:
        { graph_id, entity_types_count, edge_types_count }
    """

async def graph_add_node(
    name: str,
    type: str,
    summary: str = "",
    attributes: dict | None = None
) -> dict:
    """Adds an entity node. Type must match ontology.

    Returns:
        { node_id, name, type }
    """

async def graph_add_edge(
    from_node: str,
    to_node: str,
    type: str,
    facts: str = "",
    metadata: dict | None = None,
    valid_at: str | None = None,
    invalid_at: str | None = None
) -> dict:
    """Adds a relationship edge with optional temporal bounds.

    Args:
        from_node: Node ID or name
        to_node: Node ID or name
        type: Edge type (must match ontology)
        facts: Textual description of the relationship
        metadata: Optional key-value metadata
        valid_at: When this fact became true (ISO timestamp or round label)
        invalid_at: When this fact became false (None = still valid)

    Returns:
        { edge_id, from, to, type }
    """

async def graph_query(
    name_or_id: str,
    depth: int = 1,
    as_of: str | None = None,
    max_results: int = 50
) -> dict:
    """Returns a node with edges and neighbors up to depth.

    Args:
        name_or_id: Node identifier
        depth: Traversal depth (default 1)
        as_of: Temporal filter -- only return edges valid at this time (H-04 mitigation)
        max_results: Max edges returned (H-07 mitigation)

    Returns:
        { node, edges: [...], neighbors: [...] }
    """

async def graph_compute_centrality() -> dict:
    """Ranks all nodes by degree centrality.

    Returns:
        { rankings: [{node_id, name, type, degree, rank}...] }
    """
```

**Temporal Query Semantics** (H-04 mitigation):
- `as_of=None`: Return all edges (including expired ones)
- `as_of="2026-03-18T10:00:00Z"`: Return edges where `valid_at <= as_of` AND (`invalid_at IS NULL` OR `invalid_at > as_of`)
- `as_of="round-3"`: Return edges valid as of round 3

**Definition of Done**: Graph CRUD works. Temporal filtering returns only currently-valid edges when `as_of` is provided. Centrality ranks nodes correctly.
**Risks**: H-04 (temporal filtering)
**Mitigation**: `as_of` parameter with clear filtering semantics.

---

### Phase E: Amplification Engine

#### Task E.1: Create engine/amplification_engine.py -- 3 MCP Tools

**Objective**: Batch management, result recording, statistical aggregation with debiasing.
**Files**: CREATE `engine/amplification_engine.py`
**Evidence**: feature-request.md:456-481, research-driven-redesign.md:227-246

**Tool Signatures:**

```python
async def amplify_init(
    archetypes: list[dict],
    variations_per_archetype: int = 50,
    model: str = "haiku",
    scenario: str = "",
    is_baseline: bool = False
) -> dict:
    """Initializes mass amplification config.

    Args:
        archetypes: Archetype dicts (with or without evolved positions)
        variations_per_archetype: Persona variations per archetype (default 50)
        model: Model for claude -p calls (default haiku)
        scenario: The prompt each variation receives
        is_baseline: True for BASELINE_AMPLIFY phase (pre-deliberation control)

    Returns:
        { total_calls, estimated_cost, config_id, is_baseline }
    """

async def amplify_record_batch(
    batch_id: str,
    results: list[dict]
) -> dict:
    """Records a batch of claude -p results.

    Args:
        batch_id: Unique batch identifier
        results: List of AmplificationResult dicts

    Returns:
        { batch_id, results_recorded, running_total }
    """

async def amplify_aggregate(
    apply_debiasing: bool = False,
    archetype_ids: list[str] | None = None
) -> dict:
    """Computes statistical distributions across all recorded results.

    Aggregation (deterministic):
    - Per archetype: action distribution, confidence distribution, theme clusters
    - Overall: adoption rate, rejection rate, polarization index
    - Network effects: viral potential, resistance clusters, bridge archetypes

    Debiasing (when apply_debiasing=True AND calibration data exists):
    - Reads domain corrections from domain_corrections.json (file-based interface)
    - Applies additive correction per domain
    - Returns BOTH raw and debiased distributions (C-28)

    Args:
        apply_debiasing: Whether to apply calibration corrections (default False;
            conservative for early runs with no calibration data)
        archetype_ids: Filter to specific archetypes (pagination, H-07)

    Returns:
        { per_archetype: [...], overall: {...}, network_effects: {...},
          raw: {...}, debiased: {...}, corrections_applied: [...] }
    """
```

**Cross-Engine Interface Contract** (H-03 mitigation):

The amplification engine reads calibration corrections from a file managed by Worker B's calibration engine. This is a file-based integration point -- no cross-engine Python imports required.

**[r2] Explicit JSON schema for domain_corrections.json:**

```json
{
  "$schema": "domain_corrections.json contract v1",
  "description": "Written by Worker B's CalibrationEngine as a materialized view of domain bias computations. Read by Worker A's amplify_aggregate(). No cross-engine Python imports.",
  "corrections": {
    "<domain_name>": {
      "offset": "<float: mean signed error. >0 = overconfident (reduce), <0 = underconfident (increase)>",
      "n": "<int: number of resolved predictions in this domain>",
      "direction": "<str: 'over' | 'under'>",
      "p_value": "<float: statistical significance of directional bias>",
      "correction_active": "<bool: whether CalibrationEngine deems this correction statistically justified>"
    }
  },
  "last_updated": "<str: ISO 8601 timestamp>",
  "correction_schedule_stage": "<str: 'RECORD_ONLY' | 'DOMAIN_ADDITIVE' | 'ARCHETYPE_ADDITIVE' | 'LOGISTIC'>"
}
```

**Example:**
```json
{
  "corrections": {
    "TECHNOLOGY": {"offset": 0.05, "n": 95, "direction": "over", "p_value": 0.03, "correction_active": true},
    "POLICY": {"offset": -0.03, "n": 110, "direction": "under", "p_value": 0.08, "correction_active": true},
    "ECONOMICS": {"offset": 0.01, "n": 40, "direction": "over", "p_value": 0.45, "correction_active": false}
  },
  "last_updated": "2026-03-18T10:00:00Z",
  "correction_schedule_stage": "DOMAIN_ADDITIVE"
}
```

**File path**: `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json`

**Contract rules**:
- If file does not exist: no debiasing applied (returns raw only). This is the expected state for runs 1-2.
- If domain not in corrections: no correction for that domain
- If `correction_active` is false: skip that domain's correction even if offset is non-zero
- Correction is additive: `adjusted_confidence = clamp(raw_confidence - offset, 0.0, 1.0)`
- Offset > 0 means overconfident (reduce); offset < 0 means underconfident (increase)
- Worker B writes this file via `CalibrationEngine.apply_correction()` (Worker B plan Task D.1)
- Worker A reads this file; Worker A NEVER writes to it

**Definition of Done**: Batch recording and aggregation work. Debiasing applies when calibration data exists and is skipped gracefully when absent.
**Risks**: H-03 (cross-engine interface)
**Mitigation**: File-based interface with graceful degradation. Contract documented above. Worker B writes, Worker A reads.

---

### Phase F: Metrics Engine

#### Task F.1: Create engine/metrics_engine.py -- 3 MCP Tools

**Objective**: Round metrics computation, keyword sentiment, trend analysis.
**Files**: CREATE `engine/metrics_engine.py`
**Evidence**: feature-request.md:483-502

**Tool Signatures:**

```python
async def metrics_compute_round(round_n: int) -> dict:
    """Aggregate metrics for a deliberation round.

    Computes:
    - diversity: distinct_argument_clusters / total_unique_arguments
      [r2] Returns null with diversity_flag="INSUFFICIENT_DATA" when total_unique_arguments < 5
    - engagement: avg argument count per archetype
    - stability: avg Jaccard similarity vs previous round (0.0 for round 1)
    - coalitions: groups of archetypes with pairwise argument Jaccard > 0.6
    - cluster_count: absolute number of distinct argument clusters
    - total_unique_arguments: [r2] raw count for consumers

    Returns:
        { round_n, diversity, engagement, stability,
          coalitions, cluster_count, total_unique_arguments,
          diversity_flag, timestamp }
    """

async def metrics_sentiment_keyword(text: str) -> dict:
    """Deterministic keyword-based sentiment score (0.7-weight component of D-01).

    Uses positive/negative/neutral word lists from sentiment.py.
    Score computed as: (positive_count - negative_count) / total_count

    Args:
        text: Text to analyze

    Returns:
        { score: float (-1.0 to 1.0), label: str, confidence: float }
    """

async def metrics_get_trend(
    metric_name: str,
    last_n_rounds: int = 6
) -> dict:
    """Returns time series of a named metric across rounds.

    Args:
        metric_name: diversity, engagement, stability, cluster_count
        last_n_rounds: How many rounds to include

    Returns:
        { metric, values: [{round, value}...],
          trend: "increasing"|"decreasing"|"stable" }
    """
```

**Definition of Done**: Round metrics computed deterministically. Sentiment scores are reproducible (same text = same score). Trend direction correctly identified.
**Risks**: H-05 (format coupling with deliberation engine)
**Mitigation**: Metrics engine reads position data via the same Pydantic models (ArgumentPosition/PredictionPosition) as the deliberation engine. Shared model = shared format.

---

#### Task F.2: Create engine/sentiment.py -- Keyword Sentiment Module

**Objective**: Deterministic word-list-based sentiment scoring.
**Files**: CREATE `engine/sentiment.py`
**Evidence**: feature-request.md:492-496, 516

**Implementation:**
- `POSITIVE_WORDS`: ~200 positive sentiment keywords
- `NEGATIVE_WORDS`: ~200 negative sentiment keywords
- `STOP_WORDS`: Common stop words to filter
- `compute_sentiment(text: str) -> SentimentResult`: Pure function, deterministic

**Definition of Done**: Same text always produces same score. Score range is [-1.0, 1.0].

---

### Phase G: MCP Server Entry Point

#### Task G.1: Create engine/server.py -- MCP stdio Server

**Objective**: Register all 21 tools with the MCP Python SDK, configure stdio transport.
**Files**: CREATE `engine/server.py`
**Evidence**: feature-request.md:504-518, mcp.md:28-36

**Implementation:**

```python
"""OathFish MCP Server -- Deterministic computation core.

stdio transport. 21 tools across 5 engines.
All state mutations flush to disk before returning (C-23).
All computation is deterministic (C-02).
"""

import os
import sys
from pathlib import Path
from mcp.server import Server

# Server-level instructions for Tool Search discoverability
SERVER_INSTRUCTIONS = """
OathFish Engine: Deterministic computation core for swarm-based predictive intelligence.
Use these tools for: state management (run lifecycle, checkpoints, resume),
deliberation tracking (round recording, position evolution, convergence detection),
graph operations (entity/relationship CRUD, centrality computation),
mass amplification aggregation (batch recording, statistical distributions),
metrics computation (round metrics, keyword sentiment, trend analysis).
NEVER compute these deterministically yourself -- always delegate to oathfish-engine tools.
"""

app = Server("oathfish-engine", instructions=SERVER_INSTRUCTIONS)

# Data directory from environment
DATA_DIR = Path(os.environ.get("OATHFISH_DATA_DIR", "./data/runs"))

# Import and register tool handlers from each engine module
from .state_machine import register_tools as register_state_tools
from .deliberation_engine import register_tools as register_deliberation_tools
from .graph_engine import register_tools as register_graph_tools
from .amplification_engine import register_tools as register_amplification_tools
from .metrics_engine import register_tools as register_metrics_tools

register_state_tools(app, DATA_DIR)
register_deliberation_tools(app, DATA_DIR)
register_graph_tools(app, DATA_DIR)
register_amplification_tools(app, DATA_DIR)
register_metrics_tools(app, DATA_DIR)

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream)

    asyncio.run(main())
```

**Definition of Done**: Server starts via `python engine/server.py`, accepts stdio JSON-RPC, responds to all 21 tools.
**Risks**: H-12 (data directory)
**Mitigation**: `DATA_DIR` reads from `OATHFISH_DATA_DIR` env var, which `.mcp.json` sets to `${CLAUDE_PLUGIN_DATA}/runs`.

---

#### Task G.2: Create engine/__init__.py

**Objective**: Package initialization.
**Files**: CREATE `engine/__init__.py`
**Content**: Empty or with version string.

---

#### Task G.3: Create engine/requirements.txt

**Objective**: Python dependencies.
**Files**: CREATE `engine/requirements.txt`
**Content**:
```
mcp>=1.0.0
pydantic>=2.0.0
```

**Definition of Done**: `pip install -r engine/requirements.txt` succeeds.

---

#### Task G.4: MCP Environment Requirements Specification

**[r2] CHANGED: Worker A no longer creates .mcp.json. Worker C owns this file (Worker C plan Task A.2). This task now documents the env var requirements that Worker C must include.**

**Objective**: Specify the environment variables Worker C must include in .mcp.json for the MCP server to function correctly.
**Files**: NONE (Worker C creates `.mcp.json`)
**Evidence**: feature-request.md:1057-1069, mcp-analysis.md:53, mcp.md:158-167

**Required env vars for Worker C's .mcp.json:**

| Env Var | Value | Rationale |
|---------|-------|-----------|
| `OATHFISH_DATA_DIR` | `${CLAUDE_PLUGIN_DATA}/runs` | **SPEC CORRECTION**: Feature request at line 1064 uses `${CLAUDE_PLUGIN_ROOT}/docs/runs` which is WRONG. `CLAUDE_PLUGIN_ROOT` is wiped on plugin update. Must use `CLAUDE_PLUGIN_DATA` (persistent) per mcp-analysis.md:53. This ensures calibration history (C-27), run data (C-15), and holdout sets (C-34) survive plugin updates. |
| `MAX_MCP_OUTPUT_TOKENS` | `50000` | Overrides the 25,000 token default for MCP tool outputs. Documented at mcp.md:162-163. Needed to accommodate large outputs from `deliberation_get_position_map()` (detail_level="full") and `amplify_aggregate()`. This is defense-in-depth alongside the primary mitigation (pagination parameters `detail_level`, `archetype_ids`, `max_results`). |

**Worker C's .mcp.json should also use `python3`** (not `python`) for the command, as `python` may not be available on all systems.

**Note on MAX_MCP_OUTPUT_TOKENS validity**: The skeptic (SK-08) claimed this env var is "not a standard MCP configuration parameter." This is incorrect. `references/raw/mcp.md:162-163` explicitly documents: "Configure via `MAX_MCP_OUTPUT_TOKENS` env var" with example `export MAX_MCP_OUTPUT_TOKENS=50000`. However, the primary mitigation for H-07 is the pagination parameters (`detail_level`, `archetype_ids`, `max_results`) on large-output tools. MAX_MCP_OUTPUT_TOKENS is defense-in-depth.

**Definition of Done**: Worker C's .mcp.json includes both env vars. MCP server auto-starts when plugin is enabled.
**Risks**: H-12 (data directory path)
**Mitigation**: Explicit `${CLAUDE_PLUGIN_DATA}` requirement documented for Worker C.

---

## Blast Radius Map

### Impacted Surfaces

| Surface | Why | Risk Level |
|---------|-----|------------|
| `engine/models.py` | All Pydantic models -- foundation for every engine. Worker A OWNS. | Critical |
| `engine/persistence.py` | Write-through layer -- used by every mutation | Critical |
| `engine/server.py` | MCP entry point -- tool registration and startup | High |
| `engine/state_machine.py` | State transitions -- gates all phase progression | High |
| `engine/deliberation_engine.py` | Polymorphic positions, Jaccard evolution, diversity index | High |
| `engine/graph_engine.py` | Entity/relationship storage with temporal tracking | Medium |
| `engine/amplification_engine.py` | Batch recording, aggregation, cross-engine debiasing | Medium |
| `engine/metrics_engine.py` | Round metrics, sentiment, trends | Medium |
| `engine/sentiment.py` | Keyword word lists for sentiment scoring | Low |
| `engine/requirements.txt` | Dependencies | Low |
| `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json` | Cross-engine interface with Worker B's calibration engine (Worker B writes, Worker A reads) | Medium |

### Decoupled Surfaces (Safe -- not modified by this worker)

| Surface | Evidence |
|---------|----------|
| `.mcp.json` | Worker C responsibility (plugin scaffold). Worker A specifies env requirements only. |
| `agents/` | Worker C responsibility (orchestration) |
| `skills/` | Worker C responsibility |
| `commands/` | Worker C responsibility |
| `hooks/` | Worker C responsibility |
| `.claude-plugin/plugin.json` | Worker C responsibility |
| `scripts/amplify.sh` (or Python SDK replacement) | Worker D responsibility |
| Calibration engine tools | Worker B responsibility |
| Archetype generation | Worker D responsibility |

---

## Hazards & Mitigations

| H-ID | Hazard | Mitigation | Verification |
|------|--------|------------|--------------|
| H-01 | Position type discrimination failure in `deliberation_record_round()` | Type discrimination via round plan (RoundType enum), NOT hardcoded round number. `deliberation_init()` stores `round_plan` mapping round_n -> RoundType. Record round reads the plan. | Unit test: change round_count to 8. Round 8 = prediction. Verify PredictionPosition accepted, ArgumentPosition rejected. |
| H-02 | Write-through persistence failure (disk full, crash) | Atomic write via temp+rename in `persistence.py`. `os.fsync()` before rename. try/except with temp file cleanup. | Unit test: simulate crash after temp write, before rename. Verify original file intact. |
| H-03 | Cross-engine debiasing interface mismatch | [r2] File-based contract: `domain_corrections.json` with explicit JSON schema (see Task E.1). Worker B writes, Worker A reads. No cross-engine Python imports. Graceful degradation: if file missing or domain absent, skip correction. | Integration test: remove calibration file, verify `amplify_aggregate(apply_debiasing=True)` returns raw results without error. |
| H-04 | Graph temporal queries return expired facts | `as_of` parameter on `graph_query()`. Default is None (all edges). When set, filter by `valid_at`/`invalid_at` bounds. | Unit test: add edge with `invalid_at="round-3"`. Query `as_of="round-4"`. Verify edge excluded. |
| H-05 | Metrics engine format coupling with deliberation | Both engines use shared Pydantic models from `models.py`. No independent serialization formats. | Static analysis: verify metrics_engine imports only from models.py, never reads raw JSON. |
| H-06 | Diversity index threshold sensitivity AND structural weakness at low N | Make clustering threshold configurable (default 0.5 Jaccard). Make premature consensus thresholds configurable (default: cluster_count < 3 AND diversity_index < 0.15). Store thresholds in RunConfig. [r2] Added minimum argument count guard: diversity_index = null when total_unique_arguments < 5, with INSUFFICIENT_DATA flag. | Sensitivity test: run with thresholds 0.3, 0.5, 0.7. Document cluster count variance. Test: verify null diversity with < 5 arguments. |
| H-07 | MCP tool output exceeds 25K token limit | PRIMARY: `detail_level` and `archetype_ids` filter parameters on large-output tools. `max_results` on graph_query. DEFENSE-IN-DEPTH: `MAX_MCP_OUTPUT_TOKENS=50000` env var in .mcp.json (documented at mcp.md:162-163, specified in Task G.4 for Worker C to include). | Unit test: generate 30-archetype position map at detail_level="summary". Count output tokens. Verify < 10,000. |
| H-08 | Concurrent tool calls from multiple agents | MCP stdio is single-threaded (one request at a time). The server processes tool calls sequentially. No concurrent access possible via MCP protocol. (Classification: IMPLICIT assumption A-02, likely correct but not guaranteed.) | Architecture verification: confirm MCP stdio serializes requests. No file-level locking needed. |
| H-09 | ERROR state resume after server restart | `previous_state` stored in run.json alongside current state. `state_resume()` reads from disk (not memory). On startup, if state is ERROR, previous_state is available. | Test: transition to ERROR, kill server, restart, call `state_resume()`. Verify previous_state returned. |
| H-10 | `RoundSummary` references undefined `Position` type | Explicit type alias `Position = Union[ArgumentPosition, PredictionPosition]` in models.py. RoundSummary uses `list[Position]`. | Static analysis: mypy validates RoundSummary.positions type. |
| H-11 | Round 6 evolution delta computed against round 5 which has no numeric fields | Round 6 PredictionEvolution stores absolute values (stance, confidence), NOT deltas. `stance_vs_initial` compares to Archetype.initial_stance (qualitative text for coordinator to interpret). | Unit test: compute round 6 evolution with round 5 ArgumentPosition data. Verify no AttributeError, output contains absolute values. |
| H-12 | Data directory under CLAUDE_PLUGIN_ROOT destroyed on update | [r2] Worker A specifies `${CLAUDE_PLUGIN_DATA}/runs` as required env var for Worker C's `.mcp.json` (Task G.4). Code reads `OATHFISH_DATA_DIR` env var. No hardcoded paths. | Config review: verify Worker C's `.mcp.json` contains `CLAUDE_PLUGIN_DATA`, not `CLAUDE_PLUGIN_ROOT`. |

---

## Test & Validation Plan

### New Tests

| Test | Type | Validates | Command |
|------|------|-----------|---------|
| test_models.py | Unit | All Pydantic models construct and serialize correctly | `pytest engine/tests/test_models.py` |
| test_persistence.py | Unit | Atomic write-through, crash safety, read-back | `pytest engine/tests/test_persistence.py` |
| test_state_machine.py | Unit | 8-state transitions (7 phases + INIT), illegal rejection, ERROR resume | `pytest engine/tests/test_state_machine.py` |
| test_deliberation.py | Unit | Polymorphic positions, Jaccard evolution, diversity index, convergence, [r2] low-N guard | `pytest engine/tests/test_deliberation.py` |
| test_graph.py | Unit | Node/edge CRUD, temporal filtering, centrality | `pytest engine/tests/test_graph.py` |
| test_amplification.py | Unit | Batch recording, aggregation, debiasing integration | `pytest engine/tests/test_amplification.py` |
| test_metrics.py | Unit | Round metrics, sentiment keyword, trends | `pytest engine/tests/test_metrics.py` |
| test_server.py | Integration | MCP stdio server starts, responds to all 21 tools | `pytest engine/tests/test_server.py` |

### Test-to-Hazard-to-Plan Mapping

| H-ID | Test | Task |
|------|------|------|
| H-01 | test_deliberation.py::test_polymorphic_record_round | C.1 |
| H-02 | test_persistence.py::test_atomic_write_crash_safety | A.2 |
| H-03 | test_amplification.py::test_aggregate_without_calibration | E.1 |
| H-04 | test_graph.py::test_temporal_edge_filtering | D.1 |
| H-05 | test_metrics.py::test_reads_shared_models | F.1 |
| H-06 | test_deliberation.py::test_diversity_threshold_sensitivity, [r2] test_deliberation.py::test_diversity_low_n_guard | C.1 |
| H-07 | test_deliberation.py::test_position_map_pagination | C.1 |
| H-08 | (architecture verification -- no test needed) | G.1 |
| H-09 | test_state_machine.py::test_error_resume_after_restart | B.1 |
| H-10 | test_models.py::test_round_summary_position_union | A.1 |
| H-11 | test_deliberation.py::test_round6_evolution_absolute | C.1 |
| H-12 | (config review -- verify Worker C's .mcp.json) | G.4 |

---

## Proof Obligations

| Claim | How to Verify |
|-------|---------------|
| 8-state state machine (7 phases + INIT) includes BASELINE_AMPLIFY | Read engine/state_machine.py LEGAL_TRANSITIONS dict; verify UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE |
| ArgumentPosition has NO stance/confidence fields | Read engine/models.py ArgumentPosition class; verify no float fields |
| PredictionPosition has stance and confidence as mandatory floats, 13 fields total | Read engine/models.py PredictionPosition class; verify `stance: float` and `confidence: float` and `coalition_alignment` |
| Jaccard similarity used for argument evolution rounds 1-5 | Read engine/deliberation_engine.py; find `jaccard_similarity()` function and its usage in `deliberation_track_evolution()` |
| Diversity index computed as clusters/total with low-N guard | Read engine/deliberation_engine.py or engine/metrics_engine.py; find cluster computation, division, and null check for total < 5 |
| INJECT_CONTRARIAN triggered when cluster_count < 3 before round 5 | Read engine/deliberation_engine.py `deliberation_check_convergence()`; find the conditional |
| All mutations use atomic_write_json | Grep engine/*.py for file writes; verify all use `persistence.atomic_write_json()` |
| Worker C's .mcp.json uses CLAUDE_PLUGIN_DATA | Read .mcp.json; verify env block contains `${CLAUDE_PLUGIN_DATA}/runs` (Worker C responsibility, Worker A specifies requirement) |
| deliberation_get_position_map supports detail_level parameter | Read engine/deliberation_engine.py; verify function signature includes `detail_level: str` |
| Graph edges have valid_at/invalid_at fields | Read engine/models.py GraphEdge class; verify optional temporal fields |
| amplify_aggregate outputs both raw and debiased | Read engine/amplification_engine.py; verify return dict contains `raw` and `debiased` keys |
| Keyword sentiment is deterministic | Read engine/sentiment.py; verify no randomness, no LLM calls, no network I/O |
| domain_corrections.json contract is followed | Read engine/amplification_engine.py; verify file-based reads (not CalibrationEngine imports) |

---

## Ambiguities & RFIs

| Question | Decision | Consequence |
|----------|----------|-------------|
| How are argument clusters defined for diversity index? | DECIDED: Word-level Jaccard similarity with single-linkage clustering, threshold 0.5 | Simple, deterministic, but poor semantic understanding. Threshold is configurable. |
| What is the round 6 evolution delta baseline? | DECIDED: Absolute values (not deltas). Stance/confidence from PredictionPosition are reported as-is; `stance_vs_initial` references Archetype.initial_stance qualitatively | Coordinator interprets the qualitative-to-quantitative shift |
| Should graph temporal filtering be mandatory or optional? | DECIDED: Optional parameter (`as_of=None` returns all edges) | Backwards-compatible. Caller opts into temporal filtering. |
| Does debiasing apply to baseline amplification results? | DECIDED: No. Baseline is raw control. Only post-deliberation amplification gets debiased. The `is_baseline` flag on AmplificationConfig distinguishes. | A/B test integrity preserved |
| What happens if `deliberation_record_round()` receives mixed position types? | DECIDED: Reject entire batch with error. All positions in a round must be the same type. | Fail-fast prevents data corruption |
| [r2] SK-05: Feature request places hooks in archetype-agent subagent frontmatter (feature-request.md:646-654). Is this Worker A's concern? | NOTED: This is a SPEC ERROR. Plugin subagent hooks are IGNORED (sub-agents.md:107). Worker C correctly identifies and fixes this via SubagentStop at plugin hooks.json level (Worker C plan Task A.3). Worker A's MCP server is not involved in hook enforcement. | No action for Worker A; Worker C handles. Documented here so implementers do not revert to the broken spec approach. |
| [r2] SK-09: Feature request uses CLAUDE_PLUGIN_ROOT for OATHFISH_DATA_DIR (line 1064). | SPEC CORRECTION: Worker A corrects to CLAUDE_PLUGIN_DATA. This is an intentional correction of the feature request, not an error. Implementers should NOT revert to the spec's CLAUDE_PLUGIN_ROOT. Rationale: mcp-analysis.md:53 establishes that CLAUDE_PLUGIN_DATA is the correct persistent storage location. | OATHFISH_DATA_DIR always uses CLAUDE_PLUGIN_DATA |
| [r2] SK-10: Should Worker A's state machine support SKIP_DELIBERATE transition? | RFI: The research-driven-redesign.md:111 recommends routing simple-binary questions to skip DELIBERATE. Worker B implements the routing recommendation (competence_classifier.py). Currently Worker A's state machine requires BASELINE_AMPLIFY -> DELIBERATE (no skip). If SKIP_DELIBERATE is needed, LEGAL_TRANSITIONS must add `RunPhase.BASELINE_AMPLIFY: {RunPhase.DELIBERATE, RunPhase.AMPLIFY}`. Decision needed from system architect. | Blocked on architecture decision. Question routing is Worker B + Worker C responsibility; state machine extension is Worker A. |

**Blocked until resolved**: SK-10 (SKIP_DELIBERATE transition) requires architecture decision.

---

## Assumption Registry

| A-ID | Assumption | Classification | Evidence | Risk if Wrong |
|------|------------|----------------|----------|---------------|
| A-01 | Python `mcp` PyPI package supports `Server` class with `@app.tool()` decorator and stdio transport | NEEDS_VERIFICATION | feature-request.md:1252 says "mcp PyPI package"; MCP spec describes Python SDK | Server entry point pattern changes. Moderate risk -- would need to adapt to actual SDK API. |
| A-02 | MCP stdio processes tool calls sequentially (single-threaded event loop) | IMPLICIT | stdio is a single-channel protocol; MCP spec does not define concurrent requests over stdio | If concurrent, need file-level locking for persistence (H-08 becomes real) |
| A-03 | `os.replace()` is atomic on macOS (Darwin) filesystem | VERIFIED | POSIX guarantee on rename/replace within same filesystem | If not atomic, write-through could leave corrupted files |
| A-04 | Pydantic v2 `model_dump_json()` handles Union types correctly for serialization/deserialization | VERIFIED | Pydantic v2 docs confirm discriminated unions and model_dump_json | If broken, Position union type fails to serialize in RoundSummary |
| A-05 | Word-level Jaccard is sufficient proxy for argument semantic similarity | IMPLICIT | Only deterministic approach under C-02 + C-19 constraints | If Jaccard produces pathological clustering, diversity index is meaningless. Risk: H-06. |
| A-06 | 30 archetypes x 6 rounds x 300 tokens each = ~54,000 tokens for full position map | IMPLICIT | Estimated from typical LLM response lengths | If actual output is larger, even 50,000 token limit may be insufficient |

---

## Hazard Coverage Check

| H-ID | In Explore? | Mitigation in Plan? | Test for Mitigation? |
|------|-------------|---------------------|----------------------|
| H-01 | Yes | Yes - Task C.1 (type discrimination via round plan) | Yes - test_deliberation::test_polymorphic_record_round |
| H-02 | Yes | Yes - Task A.2 (atomic write-through) | Yes - test_persistence::test_atomic_write_crash_safety |
| H-03 | Yes | Yes - Task E.1 (file-based contract with explicit JSON schema, graceful degradation) [r2 strengthened] | Yes - test_amplification::test_aggregate_without_calibration |
| H-04 | Yes | Yes - Task D.1 (as_of parameter) | Yes - test_graph::test_temporal_edge_filtering |
| H-05 | Yes | Yes - Task F.1 (shared Pydantic models) | Yes - test_metrics::test_reads_shared_models |
| H-06 | Yes | Yes - Task C.1 (configurable thresholds + [r2] low-N guard) | Yes - test_deliberation::test_diversity_threshold_sensitivity, test_diversity_low_n_guard |
| H-07 | Yes | Yes - Tasks C.1, E.1, D.1 (pagination parameters as primary) + Task G.4 (MAX_MCP_OUTPUT_TOKENS as defense-in-depth) | Yes - test_deliberation::test_position_map_pagination |
| H-08 | Yes | Yes - Task G.1 (stdio is sequential, no concurrency -- IMPLICIT assumption) | Architecture verification |
| H-09 | Yes | Yes - Task B.1 (previous_state in run.json) | Yes - test_state_machine::test_error_resume_after_restart |
| H-10 | Yes | Yes - Task A.1 (Position type alias) | Yes - test_models::test_round_summary_position_union |
| H-11 | Yes | Yes - Task C.1 (absolute values, not deltas) | Yes - test_deliberation::test_round6_evolution_absolute |
| H-12 | Yes | Yes - Task G.4 (CLAUDE_PLUGIN_DATA env requirement for Worker C's .mcp.json) | Config review |

All 12 hazards have mitigation and verification.

---

## File Creation Summary

| File | Action | Task | Purpose |
|------|--------|------|---------|
| `engine/__init__.py` | CREATE | G.2 | Package init |
| `engine/models.py` | CREATE | A.1 | All Pydantic models (~30 classes). Worker A OWNS. |
| `engine/persistence.py` | CREATE | A.2 | Atomic write-through layer |
| `engine/state_machine.py` | CREATE | B.1 | 5 state machine tools |
| `engine/deliberation_engine.py` | CREATE | C.1 | 5 deliberation tools |
| `engine/graph_engine.py` | CREATE | D.1 | 5 graph tools |
| `engine/amplification_engine.py` | CREATE | E.1 | 3 amplification tools |
| `engine/metrics_engine.py` | CREATE | F.1 | 3 metrics tools |
| `engine/sentiment.py` | CREATE | F.2 | Keyword sentiment word lists |
| `engine/server.py` | CREATE | G.1 | MCP stdio entry point |
| `engine/requirements.txt` | CREATE | G.3 | Python dependencies |

**Total**: 11 files created by Worker A, 21 MCP tools, ~30 Pydantic models.

**[r2] Note**: `.mcp.json` removed from Worker A's file list. Worker C owns it (Worker C plan Task A.2). Worker A specifies env requirements in Task G.4.

---

## Build Sequence

1. **Phase A** (Foundation): models.py + persistence.py -- no dependencies, enables everything else
2. **Phase B** (State Machine): state_machine.py -- depends on models.py, persistence.py
3. **Phase C** (Deliberation): deliberation_engine.py -- depends on models.py, persistence.py; most complex engine
4. **Phase D** (Graph): graph_engine.py -- depends on models.py, persistence.py; independent of deliberation
5. **Phase E** (Amplification): amplification_engine.py -- depends on models.py, persistence.py; reads calibration data via file interface
6. **Phase F** (Metrics): metrics_engine.py + sentiment.py -- depends on models.py, deliberation data
7. **Phase G** (Server): server.py, __init__.py, requirements.txt -- wires everything together. Env requirements communicated to Worker C for .mcp.json.

Phases D, E, F can be built in parallel after A+B+C are complete.

---

## Handoff

Ready for Skeptic re-audit (revision r2).

Proof Obligations: 13 (added domain_corrections.json contract verification)
Hazards Mitigated: 12/12 (H-03, H-06, H-07 strengthened in r2)
Tasks Defined: 12 (A.1, A.2, B.1, C.1, D.1, E.1, F.1, F.2, G.1, G.2, G.3, G.4)
Assumptions: 6 (0 USER DECISION, 2 NEEDS_VERIFICATION, 2 IMPLICIT, 2 VERIFIED)
Cross-Worker Contracts: 5 files with explicit ownership
RFIs: 1 (SK-10 SKIP_DELIBERATE transition)
