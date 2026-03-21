# Explore Report - Worker A
## Run: 0001-oathfish-swarm-engine
## Worker: A
## Lens: mcp-core
## Keywords: state_machine, deliberation_engine, graph_engine, amplification_engine, metrics_engine, Pydantic models, ArgumentPosition, PredictionPosition, write-through persistence

---

## Dependency Map

### 1. State Machine Engine (engine/state_machine.py)

This engine has NO inbound dependencies from other engines -- it is the foundation. All other engines depend on the run context it creates.

**Outbound Dependencies:**

| Dependency | Type | Purpose |
|------------|------|---------|
| `RunConfig` (engine/models.py) | Pydantic model | Validated run configuration |
| `RunState` (engine/models.py) | Pydantic model (NEW -- not in spec) | State + history + checkpoints container |
| Filesystem (`${OATHFISH_DATA_DIR}`) | I/O | Write-through persistence of run.json |
| `datetime` (stdlib) | Library | Timestamps for state history |
| `uuid` (stdlib) | Library | Checkpoint IDs |
| `pathlib` (stdlib) | Library | Directory creation and path management |
| `json` (stdlib) | Library | Serialization |

**State Transition Graph (from feature-request.md:376-378):**

```
INIT -> UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE -> AMPLIFY -> SYNTHESIZE -> INTERACT -> COMPLETE
  \                                                                                              /
   \--> ERROR <--(from any state)                                                               /
          \--> {previous_state} (resume)  <----------------------------------------------------/
```

Legal transitions (encoded as adjacency set):
- `INIT` -> `UNDERSTAND`
- `UNDERSTAND` -> `BASELINE_AMPLIFY`
- `BASELINE_AMPLIFY` -> `DELIBERATE`
- `DELIBERATE` -> `AMPLIFY`
- `AMPLIFY` -> `SYNTHESIZE`
- `SYNTHESIZE` -> `INTERACT`
- `INTERACT` -> `COMPLETE`
- `{any}` -> `ERROR`
- `ERROR` -> `{previous_state}` (resume from error)

**Design Decision**: The transition validator must store `previous_state` in run.json so that ERROR -> resume knows where to go. This requires a `previous_state` field on the state model.

---

### 2. Deliberation Engine (engine/deliberation_engine.py)

**Inbound Dependencies (callers):**

| Caller | Purpose | Evidence |
|--------|---------|----------|
| deliberation-coordinator agent | Records positions, checks convergence, gets position map | feature-request.md:617-621 |
| report-analyst agent | Gets position map for synthesis | feature-request.md:750-751 |

**Outbound Dependencies:**

| Dependency | Type | Purpose |
|------------|------|---------|
| `ArgumentPosition` (engine/models.py) | Pydantic model | Rounds 1-5 position data (feature-request.md:535-545) |
| `PredictionPosition` (engine/models.py) | Pydantic model | Round 6 position data (feature-request.md:546-561) |
| `RoundSummary` (engine/models.py) | Pydantic model | Per-round aggregation |
| `Archetype` (engine/models.py) | Pydantic model | Archetype registry |
| Filesystem | I/O | `deliberation/round-{N}/positions.json` per round |
| State Machine Engine | Cross-engine | Reads current state to validate operations |
| Metrics Engine | Cross-engine | `metrics_compute_round()` called after each round by coordinator (but this is coordinator logic, not engine dependency) |

**Critical Data Flows:**

1. **Record Round (polymorphic)**:
   ```
   Input: round_n, positions[]
   IF round_n <= 5: validate each position as ArgumentPosition
   IF round_n == 6: validate each position as PredictionPosition
   Persist to: deliberation/round-{N}/positions.json
   Output: { round_n, positions_recorded, round_type }
   ```

2. **Track Evolution (Jaccard for arguments, numeric for predictions)**:
   ```
   Input: round_n
   Load: round N positions + round N-1 positions
   IF round_n <= 5 (ArgumentPosition):
     For each archetype:
       prev_args = set(round[N-1].key_arguments)
       curr_args = set(round[N].key_arguments)
       jaccard = |prev_args & curr_args| / |prev_args | curr_args|
       new_args = curr_args - prev_args
       dropped_args = prev_args - curr_args
       influence_chain = round[N].influenced_by
   IF round_n == 6 (PredictionPosition):
     For each archetype:
       stance_delta = round[6].stance - (inferred from round 5 qualitative signals)
       confidence_delta = round[6].confidence - baseline
   Output: { evolutions: [...] }
   ```
   Note: Round 6 deltas are computed against baseline (not round 5's numeric fields, since round 5 has no numeric fields). The delta is between round 6's prediction and the archetype's initial stance from `Archetype.initial_stance`. This is a design choice -- documented in AMB-01 resolution.

3. **Check Convergence (diversity-preserving)**:
   ```
   Input: window_size
   Load: last window_size rounds of positions
   IF rounds 1-5:
     jaccard_stability = avg Jaccard similarity across window for all archetypes
     diversity_index = count of distinct argument clusters / total unique arguments
     IF jaccard_stability > 0.8 for window_size consecutive rounds: converged = true
     IF diversity_index < 3 clusters before round 5: recommendation = INJECT_CONTRARIAN
   IF round 6:
     stance_deltas = numeric deltas
     IF early convergence (rounds 1-3): WARNING (not success)
   Output: { converged, stability_metric, diversity_index, recommendation }
   ```

---

### 3. Graph Engine (engine/graph_engine.py)

**Inbound Dependencies:**

| Caller | Purpose | Evidence |
|--------|---------|----------|
| understand/SKILL.md | Graph construction from seed documents | feature-request.md:780-782 |
| report-analyst agent | Graph queries for entity context | feature-request.md:752 |

**Outbound Dependencies:**

| Dependency | Type | Purpose |
|------------|------|---------|
| Filesystem | I/O | `graph/ontology.json`, `graph/nodes.json`, `graph/edges.json` |
| `uuid` (stdlib) | Library | Node and edge IDs |

**Temporal Extension (from research-driven-redesign.md:148-152):**

Graph edges gain `valid_at` and `invalid_at` optional fields for temporal fact tracking. This enables "past truth != present truth" queries. Example: "The Cautious VC supported AI regulation in round 1 but opposed it by round 4."

Edge model extension:
```python
class GraphEdge(BaseModel):
    edge_id: str
    from_node: str
    to_node: str
    type: str
    facts: str
    metadata: dict = {}
    valid_at: str | None = None      # ISO timestamp or round number
    invalid_at: str | None = None    # ISO timestamp or round number
```

**Centrality Computation:**

`graph_compute_centrality()` uses degree centrality (connection count). This is O(N+E) where N is nodes and E is edges. For OathFish's scale (30 archetypes + ~100 entities from seed docs), this is trivially fast. No external graph library needed.

---

### 4. Amplification Engine (engine/amplification_engine.py)

**Inbound Dependencies:**

| Caller | Purpose | Evidence |
|--------|---------|----------|
| amplify/SKILL.md | Initializes amplification, records batches, gets aggregate | feature-request.md:863-875 |
| report-analyst agent | Gets aggregate distributions | feature-request.md:753 |

**Outbound Dependencies:**

| Dependency | Type | Purpose |
|------------|------|---------|
| `AmplificationResult` (engine/models.py) | Pydantic model | Individual result validation |
| `Archetype` (engine/models.py) | Pydantic model | Archetype identity for aggregation |
| Filesystem | I/O | `amplification/config.json`, `amplification/results/batch-{N}.json`, `amplification/distributions.json` |
| Calibration Engine (Worker B) | Cross-engine interface | `amplify_aggregate()` reads domain bias corrections IF they exist |

**Debiasing Integration Point (cross-worker boundary):**

`amplify_aggregate()` (feature-request.md:473-480, research-driven-redesign.md:237-246) has an `apply_debiasing` parameter. When `True` and calibration data exists (run >= 3), it loads domain-level bias corrections and applies additive correction per domain. The interface contract:

```
amplify_aggregate(apply_debiasing=True) ->
  1. Load calibration corrections from ${OATHFISH_DATA_DIR}/calibration/domain_corrections.json
  2. For each prediction in each domain: adjusted = raw - domain_offset
  3. Output includes BOTH raw and debiased distributions
```

This crosses the boundary into Worker B's calibration engine. The contract must be:
- File: `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json`
- Format: `{ "domain_name": { "offset": float, "n": int, "direction": "over"|"under" }, ... }`
- If file does not exist or domain not in file: no correction applied for that domain

---

### 5. Metrics Engine (engine/metrics_engine.py)

**Inbound Dependencies:**

| Caller | Purpose | Evidence |
|--------|---------|----------|
| deliberation-coordinator | Computes round metrics after each round | feature-request.md:620 |
| report-analyst | Gets trend data for synthesis | feature-request.md:753 |

**Outbound Dependencies:**

| Dependency | Type | Purpose |
|------------|------|---------|
| Deliberation Engine | Cross-engine | Reads round position data to compute metrics |
| `sentiment.py` (engine/sentiment.py) | Module | Keyword-based sentiment word lists and scoring |
| Filesystem | I/O | Metrics stored per-round in run data |

**Sentiment Module (engine/sentiment.py):**

The keyword-based sentiment scorer (feature-request.md:492-496) is the 0.7-weight component of hybrid sentiment (D-01). It uses positive/negative/neutral word lists and produces a float score from -1.0 to 1.0. This is pure Python, no external NLP libraries (C-19).

**Diversity Index Computation (C-32, AMB-01 resolution):**

`metrics_compute_round()` must compute:
- `diversity`: For rounds 1-5, this is the number of distinct argument clusters divided by total unique arguments across all archetypes. A cluster is a group of semantically similar arguments. Since we cannot use LLM-based clustering (C-02 requires determinism), clustering must be keyword-based or Jaccard-based.

  **Design decision**: Use Jaccard similarity to cluster arguments. Two arguments are in the same cluster if their word-level Jaccard similarity > 0.5. This is deterministic and requires no external libraries.

- `engagement`: Average argument count per archetype per round.
- `stability`: Average Jaccard similarity of argument sets between consecutive rounds.
- `coalitions`: Groups of archetypes with pairwise argument Jaccard > 0.6. Computed via simple transitive closure.

---

### 6. Write-Through Persistence Layer (cross-cutting)

**Design**: Every engine method that mutates state MUST:
1. Update in-memory state
2. Serialize to JSON via Pydantic `.model_dump_json()`
3. Write to disk atomically (write to temp file, then rename)
4. Only THEN return success

**Atomic Write Pattern:**
```python
import tempfile
import os

def atomic_write(path: Path, data: str) -> None:
    """Write data atomically to prevent corruption on crash."""
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(data)
        os.replace(tmp_path, str(path))  # atomic on POSIX
    except:
        os.unlink(tmp_path)
        raise
```

This pattern is used by ALL engines for ALL disk writes. It satisfies:
- C-15: State persists to disk after every mutation
- C-23: All state changes flush to disk immediately
- Crash safety: Partial writes never corrupt the primary file

---

## Coupling Analysis

### Coupled Components

| From | To | Type | Evidence | Risk |
|------|-----|------|----------|------|
| Deliberation Engine | engine/models.py (ArgumentPosition, PredictionPosition) | Data | feature-request.md:401-407 | H-01 |
| Deliberation Engine | Filesystem (round-{N}/positions.json) | I/O | feature-request.md:406 | H-02 |
| State Machine Engine | Filesystem (run.json) | I/O | feature-request.md:371, C-23 | H-02 |
| Amplification Engine | Calibration Engine (Worker B) | Cross-engine | research-driven-redesign.md:237-246 | H-03 |
| All Engines | Write-through persistence | Pattern | C-23 | H-02 |
| Graph Engine | Temporal edge metadata | Data | research-driven-redesign.md:148 | H-04 |
| Metrics Engine | Deliberation Engine (position data) | Cross-engine | feature-request.md:488-490 | H-05 |
| `deliberation_check_convergence` | Diversity index computation | Algorithmic | AMB-01 resolution, C-32 | H-06 |
| `deliberation_record_round` | Position type discrimination | Type safety | SPEC-01 resolution | H-01 |
| MCP Server | Tool output size | Output | mcp-analysis.md:59 | H-07 |

### Decoupled Components (Safe to modify independently)

| Component A | Component B | Evidence | Implication |
|-------------|-------------|----------|-------------|
| Graph Engine | Deliberation Engine | No shared state; graph is for UNDERSTAND phase, deliberation for DELIBERATE | Can implement independently |
| Metrics Engine (sentiment) | Graph Engine | Sentiment operates on text; graph operates on entities | No interaction |
| State Machine | Graph Engine | State machine tracks phases; graph tracks entities | Interface only at transition validation |
| Amplification Engine | Deliberation Engine | Different phases; amplification reads deliberation OUTPUT but does not call deliberation tools | Sequential dependency, no bidirectional coupling |

---

## Hazard Registry

| H-ID | Category | Hazard | Evidence | Failure Mode | Severity |
|------|----------|--------|----------|--------------|----------|
| H-01 | Data | Position type discrimination failure: `deliberation_record_round()` receives positions for round N but cannot determine whether they should be ArgumentPosition or PredictionPosition | SPEC-01 resolution at feature-request.md:401-407 specifies round_type discriminator; but what if round_count is changed from 6? The boundary is "round 6 = prediction" which is hardcoded. | Wrong Pydantic model validation applied; numeric fields rejected in prediction round or accepted in argument round | High |
| H-02 | State | Write-through persistence failure: disk full, permission error, or crash during write leaves corrupted JSON | C-23 at feature-request.md:1177 mandates immediate flush; no error handling specified in tool signatures | State data lost or corrupted; run cannot resume (violates C-16) | High |
| H-03 | Integration | Cross-engine debiasing interface: `amplify_aggregate()` depends on calibration data format that Worker B defines. If format changes, amplification breaks silently. | research-driven-redesign.md:237-246 specifies debiasing in aggregate but calibration engine is separate worker | Debiasing silently applies wrong corrections; predictions are worse than uncorrected | Medium |
| H-04 | Data | Graph temporal tracking adds complexity: `valid_at`/`invalid_at` on edges require query-time filtering. `graph_query()` must respect temporal bounds or return stale/future facts. | research-driven-redesign.md:148-150 adds temporal tracking | Query returns facts that are no longer valid; synthesis report cites expired relationships | Medium |
| H-05 | Integration | Metrics Engine reads position data from Deliberation Engine's filesystem. If file format changes (e.g., new fields in ArgumentPosition), metrics computation breaks. | feature-request.md:488-490; both engines write/read from deliberation/ directory | Metrics computation fails or produces wrong diversity index | Medium |
| H-06 | Algorithmic | Diversity index computation uses keyword-based Jaccard clustering with a threshold (0.5). This threshold is arbitrary and may produce pathological results: two similar arguments with slightly different wording may be counted as separate clusters (over-counting diversity) or two genuinely different arguments sharing common words may be merged (under-counting). | AMB-01 resolution: Jaccard similarity on argument sets; C-32 requires diversity index | Premature consensus detection either triggers too aggressively (halting productive convergence) or not aggressively enough (allowing false consensus) | High |
| H-07 | Performance | MCP tool output exceeds 25,000 token limit for `deliberation_get_position_map()` (30 archetypes x 6 rounds x ~300 tokens = ~54,000 tokens) and potentially `amplify_aggregate()` (30 archetypes x distributions). | mcp-analysis.md:59, 193-204 | Tool output truncated silently; agent receives incomplete data; synthesis report misses archetypes | High |
| H-08 | State | Concurrent tool calls from multiple agents: coordinator and report-analyst both call MCP tools. If both call tools that read/write the same file simultaneously, race condition on filesystem. | feature-request.md:617-621 (coordinator), 750-754 (report-analyst); both active during SYNTHESIZE phase | File corruption or stale reads; inconsistent state between in-memory and disk | Medium |
| H-09 | State | State machine allows any -> ERROR but ERROR -> {previous_state} requires remembering previous_state. If the server crashes in ERROR state and restarts, how is previous_state recovered? | feature-request.md:377-378; state_resume() at feature-request.md:389-391 | Cannot resume from ERROR after server restart; run is stuck | Medium |
| H-10 | Data | `RoundSummary` model (feature-request.md:562-569) references `list[Position]` but `Position` is not defined as a type. It should be `list[ArgumentPosition] | list[PredictionPosition]` after SPEC-01 split. | feature-request.md:565 uses `Position` (undefined); SPEC-01 resolution splits into two types | Pydantic validation error at runtime; round summary cannot be constructed | Medium |
| H-11 | Algorithmic | `deliberation_track_evolution()` for round 6 (PredictionPosition) computes "numeric stance/confidence deltas vs round 5's qualitative signals" (feature-request.md:412). But round 5 is ArgumentPosition with NO numeric fields. Delta against what baseline? | feature-request.md:412-413; ArgumentPosition has no stance/confidence fields | Evolution tracking produces meaningless deltas or crashes with AttributeError | High |
| H-12 | Configuration | `OATHFISH_DATA_DIR` env var in `.mcp.json` must use `${CLAUDE_PLUGIN_DATA}` not `${CLAUDE_PLUGIN_ROOT}`. Feature request v3 shows corrected version at feature-request.md:1063-1065, but the spec-audit originally flagged this (mcp-analysis.md:53). If an implementer copies from an older version, run data is destroyed on plugin update. | mcp-analysis.md:53, 166-170 | All run data, calibration history, and cross-run state destroyed on plugin update; violates C-15, C-27 | Critical |

---

## Constraint Registry

| C-ID | Type | Constraint | Source | Verified | Evidence |
|------|------|------------|--------|----------|----------|
| C-02 | REQUIREMENT | Deterministic operations in Python MCP server | feature-request.md:1123 | INHERITED | Spec mandates; no code to verify yet |
| C-06 | REQUIREMENT | MCP stdio transport via .mcp.json | feature-request.md:1127 | INHERITED | Spec mandates |
| C-07 | REQUIREMENT | 7-phase state machine: INIT->UNDERSTAND->BASELINE_AMPLIFY->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT->COMPLETE | feature-request.md:1128 | INHERITED | Spec v3 includes BASELINE_AMPLIFY |
| C-12 | REQUIREMENT | All state mutations through MCP server tools | feature-request.md:1133 | INHERITED | Archetype agents lack Write tool (C-20) |
| C-14 | REQUIREMENT | Argument evolution tracked rounds 1-5; numeric round 6 | feature-request.md:1135 | INHERITED | AMB-01 resolved: Jaccard for arguments |
| C-15 | REQUIREMENT | Disk persistence after every mutation | feature-request.md:1159 | INHERITED | Write-through pattern |
| C-16 | REQUIREMENT | Any phase resumable from checkpoint | feature-request.md:1160 | INHERITED | State machine + checkpoint |
| C-19 | LIMITATION | Python MCP server, no heavy deps | feature-request.md:1167 | INHERITED | stdlib + mcp + pydantic only |
| C-23 | INVARIANT | All state changes flush to disk immediately | feature-request.md:1177 | INHERITED | Write-through caching |
| C-32 | REQUIREMENT | Diversity index per round; premature consensus triggers contrarian injection | feature-request.md:1147 | INHERITED | AMB-01 resolution specifies Jaccard clustering |
| C-33 | REQUIREMENT | No numeric predictions shared until round 6 | feature-request.md:1148 | INHERITED | ArgumentPosition has no numeric fields |

### Constraint Conflicts

| REQUIREMENT | LIMITATION | Evidence | Severity |
|-------------|------------|----------|----------|
| C-32 (diversity index) | C-02 (deterministic) + C-19 (no heavy deps) | Diversity index via argument clustering must be deterministic without NLP libraries. Jaccard on word sets is the only feasible approach under these constraints, but it is a poor proxy for semantic similarity. | Medium |

This conflict generates H-06 (diversity index threshold sensitivity).

---

## Lens-Specific Findings (mcp-core)

### MCP Server Architecture

**Server Entry Point (`engine/server.py`):**

The MCP Python SDK (PyPI `mcp` package) provides a `Server` class with decorator-based tool registration. The server runs in stdio mode, reading JSON-RPC messages from stdin and writing responses to stdout.

Key architectural decisions:

1. **Single server instance** hosting all engines. Tools are namespaced by prefix (`state_`, `deliberation_`, `graph_`, `amplify_`, `metrics_`). No per-engine servers.

2. **In-memory state with write-through**: The server loads state from disk at startup (or on first tool call for a run). All mutations update in-memory state AND flush to disk before returning.

3. **No async I/O needed for core engines**: All operations are synchronous filesystem reads/writes + in-memory computation. The MCP Python SDK may require async handlers, but the actual work is synchronous. Wrap with `async def` for SDK compatibility.

4. **Server-level instructions** for Tool Search discoverability (mcp-analysis.md:174-189):
   ```
   OathFish Engine: Deterministic computation core for swarm-based predictive intelligence.
   Use these tools for: state management, deliberation tracking, graph operations,
   mass amplification aggregation, metrics computation, and calibration.
   NEVER compute these deterministically yourself -- always delegate to oathfish-engine tools.
   ```

### Tool Output Size Management (H-07 mitigation)

Large-output tools need pagination parameters:

| Tool | Default Output Size | Mitigation |
|------|-------------------|------------|
| `deliberation_get_position_map()` | ~54,000 tokens (30 archetypes x 6 rounds) | Add `detail_level: "summary" | "full"`, `archetype_ids: list[str] | None` |
| `amplify_aggregate()` | ~15,000-30,000 tokens | Add `archetype_ids` filter; default returns summary only |
| `graph_query(depth=2)` | Unbounded (depends on connectivity) | Add `max_results: int = 50` parameter |
| `metrics_get_trend()` | Small (time series) | No mitigation needed |

### Pydantic Model Architecture

**Model Hierarchy (engine/models.py):**

```python
# Run-level
class RunConfig(BaseModel): ...
class StateHistoryEntry(BaseModel): ...  # NEW: {state, timestamp}
class CheckpointData(BaseModel): ...     # NEW: {checkpoint_id, phase, data, timestamp}
class RunState(BaseModel): ...           # NEW: {run_id, state, config, state_history, checkpoints, previous_state}

# Archetype
class Archetype(BaseModel): ...

# Deliberation positions (SPEC-01 split)
class ArgumentPosition(BaseModel): ...   # Rounds 1-5, text-only
class PredictionPosition(BaseModel): ... # Round 6, full numeric

# Round aggregation
class ArgumentEvolution(BaseModel): ...  # NEW: per-archetype evolution for rounds 1-5
class PredictionEvolution(BaseModel): ... # NEW: per-archetype evolution for round 6
class RoundSummary(BaseModel): ...       # Uses Union[list[ArgumentPosition], list[PredictionPosition]]

# Graph
class GraphNode(BaseModel): ...
class GraphEdge(BaseModel): ...          # Includes valid_at/invalid_at
class GraphOntology(BaseModel): ...

# Amplification
class AmplificationResult(BaseModel): ...
class AmplificationConfig(BaseModel): ... # NEW: batch config
class AggregateDistribution(BaseModel): ... # NEW: per-archetype distribution

# Metrics
class RoundMetrics(BaseModel): ...       # NEW: diversity, engagement, stability, coalitions
class SentimentResult(BaseModel): ...    # NEW: score, label, confidence
class TrendResult(BaseModel): ...        # NEW: metric, values, trend direction
```

Models NOT in the spec that must be created:
- `StateHistoryEntry`: Tracks state transitions with timestamps
- `CheckpointData`: Encapsulates checkpoint information for resume
- `RunState`: Full run state container (spec describes it but does not formalize as Pydantic)
- `ArgumentEvolution` / `PredictionEvolution`: Evolution tracking output types
- `GraphNode` / `GraphEdge` / `GraphOntology`: Graph data structures (spec describes but does not formalize)
- `AmplificationConfig`: Batch configuration
- `AggregateDistribution`: Per-archetype statistical distribution
- `RoundMetrics`: Round-level metric container
- `SentimentResult` / `TrendResult`: Metric engine output types

### Diversity Index Design (C-32 deep dive)

The spec says "number of distinct argument clusters" (feature-request.md:419). Given constraints C-02 (deterministic) and C-19 (no heavy deps), the approach is:

1. Tokenize each argument string into a set of lowercase words (strip stop words using a hardcoded list).
2. Compute pairwise Jaccard similarity between all argument sets across all archetypes for that round.
3. Cluster using single-linkage clustering with threshold 0.5: if Jaccard(A,B) > 0.5, they are in the same cluster.
4. `diversity_index = num_clusters / total_unique_arguments`
5. If `diversity_index < 0.15` before round 5 and `num_clusters < 3`: recommendation = `INJECT_CONTRARIAN` (C-32, feature-request.md:419).

The threshold 0.15 comes from the spec (research-driven-redesign.md:218: "diversity drops below 0.15 before penultimate round"). The cluster count threshold of 3 comes from feature-request.md:419: "If diversity < 3 clusters before round 5."

**Critical note**: These two thresholds (0.15 index AND < 3 clusters) are both specified. They are complementary -- the index is a normalized measure, the cluster count is an absolute floor. Both should trigger INJECT_CONTRARIAN.

---

## Handoff to Plan

### Key constraints for implementation:

1. **MUST** implement atomic write-through persistence for ALL engines (H-02 mitigation)
2. **MUST** implement polymorphic position handling in `deliberation_record_round()` with explicit round-type discrimination (H-01 mitigation)
3. **MUST** add pagination parameters to large-output tools (H-07 mitigation)
4. **MUST** resolve round 6 evolution baseline problem: define that PredictionPosition deltas are computed against `Archetype.initial_stance` parsed as float, not against round 5 (H-11 mitigation)
5. **MUST** define `Position` type alias as `Union[ArgumentPosition, PredictionPosition]` for RoundSummary (H-10 mitigation)
6. **MUST** persist `previous_state` in run.json for ERROR -> resume recovery (H-09 mitigation)
7. **MUST** use `${CLAUDE_PLUGIN_DATA}` for data directory (H-12 mitigation)
8. **SHOULD** define calibration data interface contract (JSON schema for domain_corrections.json) for Worker B cross-engine integration (H-03 mitigation)
9. **SHOULD** implement graph edge temporal filtering in `graph_query()` (H-04 mitigation)
10. **SHOULD** document diversity index threshold sensitivity and make thresholds configurable (H-06 mitigation)
