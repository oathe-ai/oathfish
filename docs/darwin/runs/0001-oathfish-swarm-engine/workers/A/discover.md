# Discover Report - Worker A
## Run: 0001-oathfish-swarm-engine
## Keywords: state_machine, deliberation_engine, graph_engine, amplification_engine, metrics_engine, Pydantic models, ArgumentPosition, PredictionPosition, write-through persistence
## Lens: mcp-core
## Entry Point: docs/darwin/runs/0001-oathfish-swarm-engine/_meta/feature-request.md S4.1 (MCP Server)

---

## Memory-Informed Context (Verified Claims)

### From Serena Memory (`project_oathfish_vision.md`)
- OathFish is a two-layer swarm intelligence engine: Claude Teams for deep deliberation + `claude -p` for mass amplification. **VERIFIED**: feature-request.md:69-72 confirms this architecture.
- Python MCP server (~20 tools) for deterministic operations: state machine, deliberation tracking, graph, amplification aggregation, metrics. **VERIFIED**: feature-request.md:284-290 enumerates these five engines.
- 5-phase pipeline: UNDERSTAND -> DELIBERATE -> AMPLIFY -> SYNTHESIZE -> INTERACT. **STALE**: feature-request.md:376 now specifies a 7-phase pipeline: INIT -> UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE -> AMPLIFY -> SYNTHESIZE -> INTERACT -> COMPLETE. The BASELINE_AMPLIFY phase was added per SPEC-02 resolution (spec-audit.md:107-125); INIT and COMPLETE bookend phases were formalized.
- D-01 through D-04 user decisions. **VERIFIED**: feature-request.md:1236-1241.

### Memory Staleness Flags
- Memory says "5-phase pipeline" but code says 7-phase (with INIT, BASELINE_AMPLIFY, COMPLETE added). Must update.
- Memory says "~20 tools" but spec now has 26+ tools across 6 engines (including calibration). Worker B handles calibration engine; this worker covers the core 5 engines (~21 tools).

---

## Search Strategy

| Type | Keywords | Source |
|------|----------|--------|
| Literal | state_machine, deliberation_engine, graph_engine, amplification_engine, metrics_engine | Worker config |
| Literal | ArgumentPosition, PredictionPosition, write-through persistence | Worker config (SPEC-01 resolution) |
| Project Terms | state_init, state_transition, state_get, state_checkpoint, state_resume | feature-request.md:369-391 |
| Project Terms | deliberation_init, deliberation_record_round, deliberation_track_evolution, deliberation_check_convergence, deliberation_get_position_map | feature-request.md:396-425 |
| Project Terms | graph_init, graph_add_node, graph_add_edge, graph_query, graph_compute_centrality | feature-request.md:430-454 |
| Project Terms | amplify_init, amplify_record_batch, amplify_aggregate | feature-request.md:459-481 |
| Project Terms | metrics_compute_round, metrics_sentiment_keyword, metrics_get_trend | feature-request.md:486-502 |
| Synonyms | convergence, diversity_index, Jaccard, Brier, sentiment_keyword | Research papers + AMB-01 resolution |
| Anti-seeds | PREMATURE_CONSENSUS, INJECT_CONTRARIAN, ERROR state, resume | feature-request.md:419, spec-audit.md:210-219 |
| Framework | Pydantic, BaseModel, mcp, FastMCP, stdio, tool decorator | Python MCP SDK patterns |
| Integration | RunConfig, Archetype, RoundSummary, AmplificationResult | feature-request.md:522-587 |

---

## Mandatory Anchors

### Package Manifest
- `package.json` at project root: `oathfish@0.1.0` (package.json:1-5)
- No `requirements.txt` exists yet. Spec calls for `engine/requirements.txt` with `mcp`, `pydantic` dependencies (feature-request.md:517).
- No Python code exists. This is a greenfield project.

### Application Entry
- Spec entry point: `engine/server.py` -- MCP stdio server (feature-request.md:509)
- `.mcp.json` configures the server launch: `python ${CLAUDE_PLUGIN_ROOT}/engine/server.py` (feature-request.md:1057-1069)
- Data directory: `${CLAUDE_PLUGIN_DATA}/runs` (corrected from `${CLAUDE_PLUGIN_ROOT}/docs/runs` per mcp-analysis.md:53)

### Type Definitions
- Spec defines 7 Pydantic models in feature-request.md:522-587:
  - `Archetype` (feature-request.md:523-534)
  - `ArgumentPosition` (feature-request.md:535-545) -- rounds 1-5, text-only
  - `PredictionPosition` (feature-request.md:546-561) -- round 6, full numeric + JSON schema
  - `RoundSummary` (feature-request.md:562-569)
  - `AmplificationResult` (feature-request.md:571-578)
  - `RunConfig` (feature-request.md:579-587)
  - `Position` -- referenced in RoundSummary:565 as `list[Position]` but should be `list[ArgumentPosition | PredictionPosition]` per SPEC-01 resolution

---

## Surface Inventory

### HIGH Relevance

| File/Section | Relevance | Anchor |
|------|-----------|--------|
| feature-request.md S4.1 (MCP Server) | PRIMARY -- complete tool specification for all 5 core engines | feature-request.md:362-518 |
| feature-request.md S4.1.7 (Pydantic Models) | PRIMARY -- all data model definitions | feature-request.md:520-587 |
| feature-request.md S4.1.6 (Server Structure) | PRIMARY -- file layout for engine/ directory | feature-request.md:504-518 |
| mcp-analysis.md (full) | PRIMARY -- MCP architecture analysis, Plugin MCP lifecycle, output limits, tool search | references/analysis/mcp-analysis.md:1-249 |
| mcp.md (raw) | PRIMARY -- Claude Code MCP protocol reference | references/raw/mcp.md:1-267 |
| spec-audit.md SPEC-01 | CRITICAL -- Position data model split (ArgumentPosition vs PredictionPosition) | spec-audit.md:88-104 |
| spec-audit.md SPEC-02 | CRITICAL -- BASELINE_AMPLIFY phase addition to state machine | spec-audit.md:107-125 |
| spec-audit.md SPEC-03 | CRITICAL -- `--resume` vs stateless contradiction, resolved as dual-mode | spec-audit.md:128-146 |
| spec-audit.md AMB-01 | CRITICAL -- Evolution tracking without numbers, resolved as Jaccard similarity | spec-audit.md:151-167 |
| research-driven-redesign.md S4.1.2 | HIGH -- Deliberation engine redesign (diversity-tracking convergence) | research-driven-redesign.md:207-225 |
| research-driven-redesign.md S4.1.4 | HIGH -- Amplification engine additions (baseline, debiasing) | research-driven-redesign.md:227-247 |
| 2305.14325-multiagent-debate.md | HIGH -- Convergence dynamics, false consensus warning, stubborn prompts | papers/2305.14325:16-19 |
| 2602.19520-calibration-decomposition.md | HIGH -- Brier score computation, domain bias structure (87.3% R-squared) | papers/2602.19520:9-42 |
| final-synthesis.md | HIGH -- Ranked recommendations, consensus points, open questions | synthesis/final-synthesis.md:117-169 |

### MEDIUM Relevance

| File/Section | Relevance | Anchor |
|------|-----------|--------|
| feature-request.md S5 (Artifact Directory) | MEDIUM -- persistence directory structure per run | feature-request.md:1073-1112 |
| feature-request.md S6 (Constraints) | MEDIUM -- all 37 constraints that engines must satisfy | feature-request.md:1116-1179 |
| feature-request.md S9.1 (Technology Stack) | MEDIUM -- Python 3.11+, Pydantic v2+, mcp PyPI | feature-request.md:1249-1258 |
| feature-request.md S10 (Implementation Sequence) | MEDIUM -- Phase 1 is MCP server foundation | feature-request.md:1285-1299 |
| research-driven-redesign.md S2.2 | MEDIUM -- Graph engine temporal tracking addition (valid_at/invalid_at) | research-driven-redesign.md:137-153 |
| mcp-analysis.md "10x" section | MEDIUM -- PLUGIN_DATA correction, pagination, list_changed | mcp-analysis.md:164-230 |

### LOW Relevance (for this worker)

| File/Section | Relevance | Anchor |
|------|-----------|--------|
| feature-request.md S4.2-4.6 (Agents, Skills, Commands) | LOW -- Worker C's responsibility | feature-request.md:589-1052 |
| feature-request.md S6.1b C-26 through C-35 (Research-mandated) | LOW -- Worker B's calibration engine responsibility | feature-request.md:1137-1151 |
| 2402.19379-silicon-crowd.md | LOW -- Acquiescence bias details (Worker B focus) | -- |
| 2411.10109-generative-agents-1000.md | LOW -- Persona fidelity (Worker D focus) | -- |

---

## Symbol Inventory

| Symbol | Type | Specified Location | Purpose |
|--------|------|----------|-----------|
| `state_init` | MCP tool | engine/state_machine.py | Create run directory + run.json |
| `state_transition` | MCP tool | engine/state_machine.py | Validate and record phase transitions (7-phase + ERROR) |
| `state_get` | MCP tool | engine/state_machine.py | Return current run state, config, history |
| `state_checkpoint` | MCP tool | engine/state_machine.py | Save phase checkpoint for resume |
| `state_resume` | MCP tool | engine/state_machine.py | Return last valid state and checkpoint |
| `deliberation_init` | MCP tool | engine/deliberation_engine.py | Initialize deliberation with archetype registry |
| `deliberation_record_round` | MCP tool | engine/deliberation_engine.py | Save positions per round (polymorphic: Argument or Prediction) |
| `deliberation_track_evolution` | MCP tool | engine/deliberation_engine.py | Compute argument evolution (Jaccard for rounds 1-5, numeric deltas for round 6) |
| `deliberation_check_convergence` | MCP tool | engine/deliberation_engine.py | Argument stability + diversity index; INJECT_CONTRARIAN trigger |
| `deliberation_get_position_map` | MCP tool | engine/deliberation_engine.py | All archetypes with latest positions and evolution history |
| `graph_init` | MCP tool | engine/graph_engine.py | Create graph with ontology |
| `graph_add_node` | MCP tool | engine/graph_engine.py | Add entity node |
| `graph_add_edge` | MCP tool | engine/graph_engine.py | Add relationship edge (with temporal tracking) |
| `graph_query` | MCP tool | engine/graph_engine.py | Query node with edges and neighbors |
| `graph_compute_centrality` | MCP tool | engine/graph_engine.py | Degree centrality ranking |
| `amplify_init` | MCP tool | engine/amplification_engine.py | Initialize mass amplification config |
| `amplify_record_batch` | MCP tool | engine/amplification_engine.py | Record batch of claude -p results |
| `amplify_aggregate` | MCP tool | engine/amplification_engine.py | Compute statistical distributions with debiasing |
| `metrics_compute_round` | MCP tool | engine/metrics_engine.py | Aggregate round metrics (diversity, engagement, stability, coalitions) |
| `metrics_sentiment_keyword` | MCP tool | engine/metrics_engine.py | Deterministic keyword-based sentiment score |
| `metrics_get_trend` | MCP tool | engine/metrics_engine.py | Time series of named metric |
| `Archetype` | Pydantic model | engine/models.py | Archetype definition (id, name, segment, demographics, values, ...) |
| `ArgumentPosition` | Pydantic model | engine/models.py | Rounds 1-5 position (text-only, no numbers) |
| `PredictionPosition` | Pydantic model | engine/models.py | Round 6 position (full numeric + JSON schema) |
| `RoundSummary` | Pydantic model | engine/models.py | Round-level aggregation |
| `AmplificationResult` | Pydantic model | engine/models.py | Single amplification response |
| `RunConfig` | Pydantic model | engine/models.py | Run-level configuration |

---

## Framework Patterns

### MCP Python SDK (from references/raw/mcp.md and references/analysis/mcp-analysis.md)

| Pattern | Detail | Reference |
|---------|--------|-----------|
| stdio transport | Plugin MCP server as child process of Claude Code | mcp.md:28-36, mcp-analysis.md:49 |
| Plugin MCP auto-start | `.mcp.json` at plugin root, auto-connect on session startup | mcp.md:120-157 |
| `${CLAUDE_PLUGIN_ROOT}` | References bundled plugin code (immutable across updates) | mcp.md:124 |
| `${CLAUDE_PLUGIN_DATA}` | References persistent state surviving updates (for run data, calibration) | mcp.md:125, mcp-analysis.md:53 |
| Tool output limits | Warning at 10,000 tokens, max 25,000 default, configurable via `MAX_MCP_OUTPUT_TOKENS` | mcp.md:158-167 |
| Tool search | Auto-enabled when tool descriptions exceed 10% of context window | mcp.md:169-191 |
| Dynamic tool updates | `list_changed` notifications for runtime tool registration changes | mcp.md:49-51 |
| Env var expansion | `${VAR}` and `${VAR:-default}` in `.mcp.json` fields | mcp.md:100-118 |

### Python MCP SDK Patterns (inferred from spec + MCP documentation)

The Python `mcp` PyPI package (feature-request.md:1252) uses a decorator-based tool registration pattern. The standard approach:

```python
from mcp.server import Server
from mcp.types import Tool

app = Server("oathfish-engine")

@app.tool()
async def state_init(run_id: str, config: dict) -> dict:
    ...
```

Key constraints from spec:
- Python 3.11+ (feature-request.md:1251)
- Pydantic v2+ for all models (feature-request.md:1253)
- No heavy external dependencies (C-19, feature-request.md:1167)
- stdio transport only (C-06, feature-request.md:1127)

---

## Configuration Systems

| System | Config Location | Governs What |
|--------|-----------------|--------------|
| `.mcp.json` | Plugin root | MCP server lifecycle (command, args, env) |
| `run.json` | `${OATHFISH_DATA_DIR}/{RUN_ID}/_meta/run.json` | Per-run state, config, phase history |
| `OATHFISH_DATA_DIR` env var | `.mcp.json` env block | Root path for all persistent data |
| `MAX_MCP_OUTPUT_TOKENS` env var | Process environment | MCP tool output size limit |
| `MCP_TIMEOUT` env var | Process environment | Server startup timeout |

### Configuration Hazard Flags (for Explore phase)
- `OATHFISH_DATA_DIR` must use `${CLAUDE_PLUGIN_DATA}` not `${CLAUDE_PLUGIN_ROOT}` -- data must survive plugin updates (mcp-analysis.md:53, C-15, C-27)
- Tool output limits may truncate large responses from `deliberation_get_position_map()` and `amplify_aggregate()` (mcp-analysis.md:59, 193-204)
- Tool search may defer tool loading if many MCP servers are active -- server instructions must be rich for discoverability (mcp-analysis.md:29, 174-189)

---

## Research Findings Relevant to MCP Core Engines

### From 2305.14325 (Multi-Agent Debate)
- Convergence is NOT a success metric: "debates typically converged into single final answers [that] were not necessarily correct" (papers/2305.14325:16)
- Stubborn prompts produce better outcomes: longer debates + better final solutions (papers/2305.14325:18)
- Agents are "relatively agreeable" due to RLHF -- converge TOO QUICKLY (papers/2305.14325:18)
- **MCP Impact**: `deliberation_check_convergence()` must track diversity, not just stability. Premature consensus = FAILURE not SUCCESS.

### From 2602.19520 (Calibration Decomposition)
- 87.3% of calibration variance explained by 4 structured components (papers/2602.19520:36)
- Domain-specific biases are persistent and predictable (papers/2602.19520:39)
- **MCP Impact**: `metrics_compute_round()` must compute diversity index. `amplify_aggregate()` must support debiasing corrections.

### From final-synthesis.md
- Recommendation #2 (34/40): Separate arguments from predictions in DELIBERATE (synthesis/final-synthesis.md:123)
- Recommendation #3 (34/40): Domain-level debiasing from run 1 (synthesis/final-synthesis.md:125)
- Consensus: Acquiescence bias is #1 known error source (synthesis/final-synthesis.md:150)
- Risk: Single-model correlated failures (synthesis/final-synthesis.md:152)

---

## Initial Observations

1. **Greenfield project**: No existing Python code. All engine files must be created from scratch. The spec provides complete tool signatures and Pydantic model definitions -- this is a well-specified build.

2. **SPEC-01 is resolved in the v3 spec**: feature-request.md:535-561 already defines split `ArgumentPosition` (rounds 1-5, text-only) and `PredictionPosition` (round 6, full numeric). The `deliberation_record_round()` tool (feature-request.md:401-407) explicitly documents the polymorphic behavior with `round_type: "argument"|"prediction"`.

3. **SPEC-02 is resolved**: The 7-phase state machine (feature-request.md:376) includes BASELINE_AMPLIFY between UNDERSTAND and DELIBERATE. C-07 (feature-request.md:1128) now reads: `INIT->UNDERSTAND->BASELINE_AMPLIFY->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT->COMPLETE`.

4. **SPEC-03 is resolved**: C-21 (feature-request.md:1169) now defines dual modes: "(1) BASELINE_AMPLIFY calls are fully stateless; (2) AMPLIFY (post-deliberation) calls use `--resume SESSION_ID`."

5. **AMB-01 is resolved**: `deliberation_track_evolution()` (feature-request.md:409-413) uses Jaccard similarity on argument sets for rounds 1-5. `deliberation_check_convergence()` (feature-request.md:415-420) uses argument set Jaccard stability + diversity index (distinct argument clusters).

6. **Write-through persistence is an invariant**: C-23 (feature-request.md:1177) mandates every state change flushes to disk immediately. The MCP server's in-memory state is a cache; JSON files on disk are the source of truth.

7. **Output size management needed**: `deliberation_get_position_map()` for 30 archetypes x 6 rounds at ~300 tokens each = ~54,000 tokens uncompressed. This exceeds the 25,000 token default limit. Need `detail_level` and `archetype_ids` filter parameters per mcp-analysis.md:193-204.

8. **Graph engine needs temporal tracking**: research-driven-redesign.md:148-150 adds `valid_at`/`invalid_at` fields on graph edges for temporal fact tracking (inspired by MiroFish's Zep integration).

---

## Handoff to Explore

### Priority Areas for Depth-First Exploration

1. **State Machine Engine**: Trace the 7-phase + ERROR transition graph. Map legal transitions, checkpoint logic, resume protocol. Identify hazards around state corruption, partial writes, concurrent access.

2. **Deliberation Engine with Split Position Models**: Deep dive into the polymorphic `deliberation_record_round()` API. Trace how ArgumentPosition (Jaccard-based evolution) and PredictionPosition (numeric deltas) flow through all 5 deliberation tools. Identify hazards around type discrimination, diversity index computation, premature consensus detection thresholds.

3. **Write-Through Persistence Layer**: Design the persistence abstraction that underlies ALL engines. Every mutation must flush to disk. Identify failure modes: partial writes, disk full, concurrent tool calls from multiple agents, JSON corruption.

4. **Graph Engine Temporal Extensions**: Assess the `valid_at`/`invalid_at` addition from MiroFish patterns. Design the edge metadata model and query semantics for temporal facts.

5. **Amplification Engine Debiasing Integration**: Trace how `amplify_aggregate()` integrates with the calibration engine (Worker B's domain) to apply per-domain corrections. Identify the interface contract between engines.
