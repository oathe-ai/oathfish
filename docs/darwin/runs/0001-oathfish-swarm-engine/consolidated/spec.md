# Golden Specification - OathFish Swarm Intelligence Engine
## Run: 0001-oathfish-swarm-engine
## Consolidated from: Workers A (MCP Core), B (Calibration/Research), C (Orchestration), D (Domain Logic)

---

## Table of Contents

1. [Scope Anchor](#1-scope-anchor)
2. [Constraint Analysis](#2-constraint-analysis)
3. [Architecture Overview](#3-architecture-overview)
4. [Cross-Worker Integration Points](#4-cross-worker-integration-points)
5. [File Manifest](#5-file-manifest)
6. [Implementation Ledger](#6-implementation-ledger)
7. [Build Sequence](#7-build-sequence)
8. [Hazard Registry](#8-hazard-registry)
9. [Spec Corrections & Deviations](#9-spec-corrections--deviations)
10. [Open RFIs](#10-open-rfis)
11. [Resolution Log](#11-resolution-log)

---

## 1. Scope Anchor

**Goal**: Build the complete OathFish Claude Code plugin -- a swarm intelligence engine that runs multi-round deliberation between 30 archetype subagents, mass-amplifies predictions via the Claude SDK, tracks calibration across runs, and submits to ForecastBench. The system is a Claude Code plugin with an MCP server for deterministic computation and Claude agents/skills for creative orchestration.

### Success Criteria

- [ ] SC-01: MCP server starts via stdio and responds to all 27 tool calls (21 core + 6 calibration) with valid JSON
- [ ] SC-02: Plugin loads and /oathfish command appears in skill menu
- [ ] SC-03: Coordinator spawns 30 archetype subagents per round via Agent tool
- [ ] SC-04: C-33 enforcement prevents numeric predictions in rounds 1-5
- [ ] SC-05: Each archetype has memory:project for cross-run learning
- [ ] SC-06: State machine correctly enforces 8-state transitions (7 pipeline phases + INIT)
- [ ] SC-07: PredictionPosition schema is single source of truth (Worker A's engine/models.py)
- [ ] SC-08: Amplification engine handles 1500 calls with rate limiting, retry, cost tracking
- [ ] SC-09: Dual-mode amplification (baseline vs informed via digest) produces comparable results
- [ ] SC-10: Write-through persistence after every mutation
- [ ] SC-11: Submit 100+ predictions to ForecastBench; target Brier < 0.122
- [ ] SC-12: After 5 runs, domain-level correction improves Brier by >= 0.01
- [ ] SC-13: Deliberation outperforms baseline on multi-factor questions
- [ ] SC-14: 2/6 domains show significant directional bias p<0.10 after 5 runs

### Hard Constraints

| ID | Constraint | Type | Source |
|----|-----------|------|--------|
| C-02 | All MCP computation deterministic -- same inputs = same outputs | REQUIREMENT | feature-request.md |
| C-05 | No Teams for archetype deliberation | LIMITATION | sub-agents.md (C-L02) |
| C-06 | Python 3.11+, Pydantic v2+, mcp PyPI package, stdio transport | REQUIREMENT | feature-request.md |
| C-07 | 8-state state machine: INIT->UNDERSTAND->BASELINE_AMPLIFY->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT->COMPLETE (+ ERROR) | REQUIREMENT | feature-request.md:1128 |
| C-14 | Split position types: ArgumentPosition (rounds 1-5) + PredictionPosition (round 6, numeric) | REQUIREMENT | feature-request.md, SPEC-01 |
| C-15 | Write-through disk persistence after every mutation | REQUIREMENT | feature-request.md (C-23) |
| C-19 | No heavy external dependencies -- stdlib + mcp + pydantic only | REQUIREMENT | feature-request.md |
| C-21 | Deliberation digest (500-1000 tokens) for post-deliberation amplification (NOT --resume) | DESIGN_DECISION | Workers C+D, headless-analysis.md:281 |
| C-26 | Baseline amplification before deliberation every run for A/B comparison | REQUIREMENT | feature-request.md:1141 |
| C-27 | Per-domain acquiescence tracking from run 1; corrections from run 3+ | REQUIREMENT | feature-request.md:1142 |
| C-28 | Report both corrected and uncorrected Brier scores | REQUIREMENT | feature-request.md:1143 |
| C-29 | Ground each archetype in 3-5 real public sources via WebSearch | REQUIREMENT | feature-request.md |
| C-30 | Superforecaster methodology in every archetype prompt | REQUIREMENT | feature-request.md:1145 |
| C-31 | Question competence classifier before UNDERSTAND | REQUIREMENT | research-driven-redesign.md |
| C-32 | Diversity index tracking with premature consensus detection | REQUIREMENT | feature-request.md |
| C-33 | No numeric predictions shared before round 6 | REQUIREMENT | feature-request.md |
| C-34 | Holdout 20% of resolved predictions from calibration feedback | REQUIREMENT | feature-request.md:356 |
| C-35 | ForecastBench submission pipeline | REQUIREMENT | feature-request.md:1150 |
| C-36 | 4 structural archetypes (Historian, Systems Thinker, Contrarian, Probabilist) in every run | REQUIREMENT | feature-request.md:800-805 |
| C-37 | Structural archetypes are epistemic lenses, NOT stakeholder personas | REQUIREMENT | feature-request.md |
| C-L01 | Plugin subagent hooks, mcpServers, permissionMode IGNORED | LIMITATION | sub-agents.md:107 |
| C-L02 | Subagents CANNOT spawn other subagents | LIMITATION | sub-agents.md:188 |

---

## 2. Constraint Analysis

### Constraint Cross-Reference

Constraint analysis was performed across all 4 workers' explore and plan documents. The following potential contradictions were identified and resolved during the skeptic/revise cycle:

| REQUIREMENT | LIMITATION | Conflict? | Resolution |
|-------------|-----------|-----------|------------|
| C-33 (no numbers rounds 1-5) | C-L01 (subagent hooks IGNORED) | YES | RESOLVED: C-33 enforced via coordinator-level validation + PreToolUse on Agent tool in plugin hooks.json (Worker C defense SK-01) |
| C-07 (7-phase pipeline) | C-L02 (subagents cannot spawn subagents) | YES | RESOLVED: deliberate skill runs inline (no context:fork) so coordinator IS the main thread (Worker C defense SK-02) |
| C-21 (--resume for post-deliberation) | Cost explosion at 1500 calls | YES | RESOLVED: Deliberation DIGEST approach (500-1000 tokens) replaces --resume. ~40x cheaper. (Workers C+D) |
| C-29 (ground in real sources) | C-19 (no heavy deps) | NO | WebSearch is a built-in Claude Code tool (tools-reference.md:40), no dependency needed |

**No unresolved contradictions remain.** All conflicts were resolved during the skeptic-revise cycle with code evidence.

---

## 3. Architecture Overview

### System Layers

```
User Interface Layer
  /oathfish command -> oathfish/SKILL.md (dispatcher, inline)
  /oathfish-chat, /oathfish-inject, /oathfish-calibrate commands

Orchestration Layer (Worker C)
  skills/: 7 phase skills + 1 shared methodology skill (Worker D)
  agents/: deliberation-coordinator, archetype-agent, report-analyst
  hooks/: PreToolUse on Agent (C-33), SessionStart (compaction recovery)

Computation Layer (Workers A + B)
  engine/server.py: MCP stdio server, 27 tools total
    - 5 state machine tools (Worker A)
    - 5 deliberation tools (Worker A)
    - 5 graph tools (Worker A)
    - 3 amplification tools (Worker A)
    - 3 metrics tools (Worker A)
    - 5 calibration tools (Worker B)
    - 1 competence classifier tool (Worker B)

Amplification Layer (Worker D)
  engine/amplification_sdk.py: Python SDK, async, 1500-call batches
  PersonaVariationGenerator: 50 variations per archetype
  Dual-mode: BASELINE (stateless) + INFORMED (deliberation digest)

Domain Layer (Worker D)
  4 structural archetypes (agents/archetypes/structural/*.md)
  26 topic-customized archetypes (generated per run via WebSearch grounding)
  skills/archetype-reasoning/SKILL.md: superforecaster methodology
```

### Data Flow

```
INIT -> UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE -> AMPLIFY -> SYNTHESIZE -> INTERACT -> COMPLETE
                                                                                    |
                                                                                    v
                                                                              ERROR (recovery)

Phase                What Happens                              Owner
-----                -----------                               -----
UNDERSTAND           Generate 30 archetypes + WebSearch         D (logic), C (skill)
                     grounding; run competence classifier
BASELINE_AMPLIFY     1500 stateless calls, record baseline      D (SDK), A (MCP record)
DELIBERATE           6 rounds x 30 archetypes via coordinator   C (coordinator), A (MCP state)
AMPLIFY              1500 digest-informed calls, record results D (SDK), A (MCP record)
SYNTHESIZE           Aggregate, debias, compare baseline/       A (MCP aggregate), B (calibration)
                     informed, produce report
INTERACT             Interactive follow-up with archetypes      C (skill), A (MCP state)
COMPLETE             Archive run data                           A (MCP state)
```

### Plugin Architecture Decision: Inline Deliberation

The deliberate skill runs INLINE (no `context: fork`) because the coordinator must spawn archetype subagents, which requires main-thread context (sub-agents.md:188-190). Two usage modes are supported:

1. `/oathfish "topic"` -- oathfish skill dispatches phases, deliberate runs inline
2. `claude --agent deliberation-coordinator` -- direct coordinator launch

### C-33 Enforcement: Three-Layer Defense

1. **Primary**: Coordinator refuses to relay numeric predictions between archetypes in rounds 1-5
2. **Secondary**: PreToolUse hook on Agent tool validates prompts contain no other archetypes' numbers
3. **Tertiary**: Archetype system prompt explicitly forbids numeric predictions in rounds 1-5

---

## 4. Cross-Worker Integration Points

### Ownership Table

| Resource | Owner | Consumers | Contract |
|----------|-------|-----------|----------|
| `engine/models.py` (all Pydantic models) | **Worker A** | B, C, D | D imports PredictionPosition + Archetype; B imports for calibration data; D proposes field additions |
| `.mcp.json` | **Worker C** | A (env requirements) | C creates; A specifies OATHFISH_DATA_DIR + MAX_MCP_OUTPUT_TOKENS env vars |
| `engine/server.py` | **Worker A** (base) | B (registers 6 tools) | A creates base with 21 tools; B adds 6 via register_tools() pattern |
| `engine/amplification_engine.py` | **Worker A** (base) | B (adds debiasing) | A creates base; B adds file-based debiasing integration |
| `skills/archetype-reasoning/SKILL.md` | **Worker D** | C (references in archetype-agent.md) | D creates methodology content; C references it |
| `domain_corrections.json` (runtime) | **Worker B** (writes) | A (reads) | JSON file-based contract at ${OATHFISH_DATA_DIR}/calibration/ |
| `understanding/archetypes.json` (runtime) | **Worker D** (generates) | C (coordinator uses), A (MCP stores) | Generated per run during UNDERSTAND phase |

### Cross-Engine File Contract: domain_corrections.json

**Path**: `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json`
**Writer**: Worker B's CalibrationEngine.write_domain_corrections()
**Reader**: Worker A's amplify_aggregate._load_domain_corrections()

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

**Rules**:
- If file does not exist: no debiasing applied (expected for runs 1-2)
- If domain not in corrections: no correction for that domain
- If `correction_active` is false: skip correction even if offset is non-zero
- Correction: `adjusted = clamp(raw - offset, 0.0, 1.0)` (offset > 0 = overconfident, reduce)
- Worker B writes after every record_outcome() and ensemble metrics computation
- Worker A NEVER writes to this file

### Stance-to-Probability Mapping

Worker A's PredictionPosition.stance is [-1, 1]. Worker B's CalibrationPrediction.forecast_probability is [0, 1].

**Mapping function** (in Worker B's domain_classifier.py):
```python
def stance_to_probability(stance: float) -> float:
    """Convert stance [-1, 1] to forecast probability [0, 1]."""
    return (stance + 1) / 2
```

### PredictionPosition Field Proposals

Worker D proposes adding `description=` Field annotations to Worker A's PredictionPosition for better --json-schema guidance. This is a non-breaking change (adds descriptions, preserves all defaults). Worker A retains ownership and approval authority.

Worker D also proposes these additions to the Archetype model (all with defaults, non-breaking):
- `is_structural: bool = False`
- `archetype_type: str = "topic"`
- `stubbornness_domain: str = ""`
- `grounding_search_queries: list[str] = Field(default_factory=list)`

---

## 5. File Manifest

### All Files by Owner

#### Worker A: MCP Server Core (11 files)

| File | Action | Task | Purpose |
|------|--------|------|---------|
| `engine/__init__.py` | CREATE | A-G.2 | Package init |
| `engine/models.py` | CREATE | A-A.1 | All Pydantic models (~30 classes). CANONICAL source. |
| `engine/persistence.py` | CREATE | A-A.2 | Atomic write-through layer (temp+rename) |
| `engine/state_machine.py` | CREATE | A-B.1 | 8-state machine, 5 MCP tools |
| `engine/deliberation_engine.py` | CREATE | A-C.1 | Polymorphic positions, Jaccard evolution, diversity index, 5 MCP tools |
| `engine/graph_engine.py` | CREATE | A-D.1 | Entity/relationship storage, temporal tracking, 5 MCP tools |
| `engine/amplification_engine.py` | CREATE | A-E.1 | Batch recording, aggregation, file-based debiasing, 3 MCP tools |
| `engine/metrics_engine.py` | CREATE | A-F.1 | Round metrics, keyword sentiment, trends, 3 MCP tools |
| `engine/sentiment.py` | CREATE | A-F.2 | Deterministic word-list-based sentiment scoring |
| `engine/server.py` | CREATE | A-G.1 | MCP stdio entry point, registers all tools |
| `engine/requirements.txt` | CREATE | A-G.3 | Python dependencies (mcp>=1.0.0, pydantic>=2.0.0) |

#### Worker B: Calibration & Research (10 files created + 3 modified)

| File | Action | Task | Purpose |
|------|--------|------|---------|
| `engine/calibration_models.py` | CREATE | B-A.1 | Calibration Pydantic models |
| `engine/config/domain_taxonomy.json` | CREATE | B-A.2 | Configurable 6-domain taxonomy |
| `engine/domain_classifier.py` | CREATE | B-A.3 | Deterministic domain/horizon/complexity classifier + stance_to_probability() |
| `engine/calibration_engine.py` | CREATE | B-B.1 | CalibrationEngine class, 5 MCP tools + write_domain_corrections() |
| `engine/competence_classifier.py` | CREATE | B-C.1 | Question competence classifier, 1 MCP tool |
| `engine/forecastbench.py` | CREATE | B-F.1 | ForecastBench export pipeline |
| `tests/test_calibration.py` | CREATE | B-* | Unit tests for calibration engine |
| `tests/test_domain_classifier.py` | CREATE | B-A.3 | Tests for domain classification + stance mapping |
| `tests/test_competence.py` | CREATE | B-C.1 | Tests for competence classifier |
| `tests/test_forecastbench.py` | CREATE | B-F.1 | Tests for ForecastBench export |
| `engine/server.py` | MODIFY | B-B.2 | Register 6 new MCP tools alongside Worker A's 21 |
| `engine/amplification_engine.py` | MODIFY | B-D.1 | Add file-based debiasing to amplify_aggregate() |

Note: Worker B no longer creates or modifies .mcp.json directly. Worker C owns that file.

#### Worker C: Orchestration (19 files)

| File | Action | Task | Purpose |
|------|--------|------|---------|
| `.claude-plugin/plugin.json` | CREATE | C-A.1 | Plugin manifest |
| `.mcp.json` | CREATE | C-A.2 | MCP server config (includes env vars from Worker A) |
| `hooks/hooks.json` | CREATE | C-A.3 | PreToolUse on Agent (C-33), SessionStart hooks |
| `scripts/validate-no-numbers.sh` | CREATE | C-A.4 | C-33 enforcement hook script |
| `scripts/oathfish-init.sh` | CREATE | C-A.5 | Session init hook |
| `scripts/oathfish-reinject-state.sh` | CREATE | C-A.6 | Compaction recovery hook |
| `agents/deliberation-coordinator.md` | CREATE | C-B.1 | Coordinator agent definition |
| `agents/archetype-agent.md` | CREATE | C-B.2 | Archetype subagent template |
| `agents/report-analyst.md` | CREATE | C-B.3 | Report generation agent |
| `skills/oathfish/SKILL.md` | CREATE | C-C.1 | Dispatcher (inline) |
| `skills/understand/SKILL.md` | CREATE | C-C.2 | UNDERSTAND phase (context:fork) |
| `skills/baseline-amplify/SKILL.md` | CREATE | C-C.3 | BASELINE_AMPLIFY phase (context:fork) |
| `skills/deliberate/SKILL.md` | CREATE | C-C.4 | DELIBERATE phase (INLINE -- NO fork) |
| `skills/amplify/SKILL.md` | CREATE | C-C.5 | AMPLIFY phase (context:fork) |
| `skills/synthesize/SKILL.md` | CREATE | C-C.6 | SYNTHESIZE phase (context:fork) |
| `skills/interact/SKILL.md` | CREATE | C-C.7 | INTERACT phase (inline for resume) |
| `commands/oathfish.md` | CREATE | C-D.1 | /oathfish command |
| `commands/oathfish-chat.md` | CREATE | C-D.2 | /oathfish-chat command |
| `commands/oathfish-inject.md` | CREATE | C-D.3 | /oathfish-inject command |
| `commands/oathfish-calibrate.md` | CREATE | C-D.4 | /oathfish-calibrate command |
| `scripts/get-state.sh` | CREATE | C-E.1 | Dynamic context injection for skills |
| `scripts/setup.sh` | CREATE | C-E.2 | Plugin setup script |

#### Worker D: Domain Logic (8 files + proposed additions)

| File | Action | Task | Purpose |
|------|--------|------|---------|
| `skills/archetype-reasoning/SKILL.md` | CREATE | D-A.2 | Superforecaster methodology protocol (Worker D OWNS) |
| `agents/archetypes/structural/historian.md` | CREATE | D-B.1 | Structural archetype: Historian |
| `agents/archetypes/structural/systems-thinker.md` | CREATE | D-B.2 | Structural archetype: Systems Thinker |
| `agents/archetypes/structural/contrarian.md` | CREATE | D-B.3 | Structural archetype: Contrarian |
| `agents/archetypes/structural/probabilist.md` | CREATE | D-B.4 | Structural archetype: Probabilist |
| `engine/amplification_sdk.py` | CREATE | D-D.1 | Python SDK amplification engine (async, tool-free, digest-based) |
| `engine/models.py` | IMPORT | D-A.1 | Imports PredictionPosition + Archetype from Worker A (does NOT create) |
| `engine/models.py` | PROPOSE | D-E.1 | Propose additions to Worker A's Archetype model (non-breaking) |

### Ownership Collision Check

| File | Claimed By | Resolution |
|------|-----------|------------|
| `engine/models.py` | A (CREATE), D (was CREATE) | **Worker A owns.** Worker D imports. Resolved in D defense SK-01/SK-03. |
| `.mcp.json` | A (was CREATE), C (CREATE) | **Worker C owns.** Worker A specifies env requirements. Resolved in A defense SK-04. |
| `engine/server.py` | A (CREATE), B (MODIFY) | **Worker A creates base.** Worker B registers additional tools. No conflict. |
| `engine/amplification_engine.py` | A (CREATE), B (MODIFY) | **Worker A creates base.** Worker B adds debiasing. No conflict. |
| `skills/archetype-reasoning/SKILL.md` | C (was CREATE), D (CREATE) | **Worker D owns.** Worker C references only. Resolved in C defense SK-03. |

**No ownership collisions remain.** All were resolved during skeptic-revise.

---

## 6. Implementation Ledger

### Phase 1: Foundation (Worker A)

#### Task A-A.1: Create engine/models.py -- All Pydantic Models
- **Objective**: Define ~30 Pydantic v2 models: RunPhase, RoundType, ArgumentPosition, PredictionPosition (13 fields including coalition_alignment), Archetype (with proposed extensions from Worker D), RunConfig, RoundSummary, Position union type, GraphNode, GraphEdge, AmplificationResult, ConvergenceResult, etc.
- **Files**: CREATE `engine/models.py`
- **Key details**:
  - PredictionPosition has 13 fields (archetype_id, round_n, prediction, decision, stance, confidence, timeframe, base_rate_anchor, key_uncertainties, falsification_criteria, second_order_effects, cascade_susceptibility, coalition_alignment)
  - Worker A's schema uses defaults on optional fields (Worker D's "all required" approach was rejected -- Worker A is authoritative)
  - `Position = Union[ArgumentPosition, PredictionPosition]` resolves H-10
  - RunPhase enum: INIT, UNDERSTAND, BASELINE_AMPLIFY, DELIBERATE, AMPLIFY, SYNTHESIZE, INTERACT, COMPLETE, ERROR (9 values)
  - RoundType enum: FREE_FORM, STRUCTURED_DEBATE, SCENARIO_REACTION, PREDICTION (4 values, NOT "INDEPENDENT_PREDICTION")
  - Archetype.grounding_sources is `list[str]` (not list[GroundingSource] per Worker D compromise)
  - Diversity index returns null with INSUFFICIENT_DATA flag when total_unique_arguments < 5
- **Evidence**: feature-request.md:535-561, feature-request.md:523-534
- **DoD**: All models construct, serialize, and round-trip via model_dump_json/model_validate_json
- **Risks**: H-10 (Position union type)

#### Task A-A.2: Create engine/persistence.py -- Write-Through Layer
- **Objective**: Atomic JSON persistence via temp file + os.replace()
- **Files**: CREATE `engine/persistence.py`
- **Key details**: os.fsync() before rename; try/except with temp file cleanup
- **DoD**: Atomic write verified; crash during write leaves original intact
- **Risks**: H-02

#### Task A-B.1: Create engine/state_machine.py -- 5 MCP Tools
- **Objective**: state_create_run, state_transition, state_get, state_checkpoint, state_resume
- **Files**: CREATE `engine/state_machine.py`
- **Key details**: 8-state machine (7 phases + INIT + ERROR). LEGAL_TRANSITIONS enforced. previous_state stored for ERROR recovery.
- **DoD**: Illegal transitions rejected; history recorded; ERROR resume works after server restart
- **Risks**: H-09

#### Task A-C.1: Create engine/deliberation_engine.py -- 5 MCP Tools
- **Objective**: deliberation_init, deliberation_record_round, deliberation_track_evolution, deliberation_get_position_map, deliberation_check_convergence
- **Files**: CREATE `engine/deliberation_engine.py`
- **Key details**:
  - Polymorphic position recording: ArgumentPosition for rounds 1-5, PredictionPosition for round 6, via round plan (not hardcoded round number)
  - Jaccard similarity for argument evolution (word-level, single-linkage clustering, threshold 0.5 configurable)
  - Diversity index = distinct_clusters / total_unique_arguments (null when < 5 arguments)
  - Premature consensus: cluster_count < 3 AND diversity_index < 0.15 -> INJECT_CONTRARIAN
  - detail_level and archetype_ids pagination parameters on position_map
  - Round 6 evolution stores absolute values (not deltas vs round 5)
- **DoD**: Polymorphic recording works; convergence detection triggers correctly
- **Risks**: H-01, H-06, H-07, H-11

#### Task A-D.1: Create engine/graph_engine.py -- 5 MCP Tools
- **Objective**: graph_add_entity, graph_add_relationship, graph_query, graph_update, graph_compute_centrality
- **Files**: CREATE `engine/graph_engine.py`
- **Key details**: Temporal filtering via as_of parameter; max_results pagination
- **DoD**: CRUD operations work; temporal queries exclude expired edges
- **Risks**: H-04

#### Task A-E.1: Create engine/amplification_engine.py -- 3 MCP Tools
- **Objective**: amplify_init, amplify_record_batch, amplify_aggregate
- **Files**: CREATE `engine/amplification_engine.py`
- **Key details**:
  - amplify_aggregate signature: `(apply_debiasing: bool = False, archetype_ids: list[str] | None = None)`
  - Debiasing reads from domain_corrections.json (file-based, no CalibrationEngine import)
  - Returns BOTH raw and debiased distributions (C-28)
  - Graceful degradation when calibration file absent
  - Baseline results stored separately from informed results
- **DoD**: Aggregation works; debiasing applies when data exists, skips gracefully when absent
- **Risks**: H-03, H-07

#### Task A-F.1: Create engine/metrics_engine.py -- 3 MCP Tools
- **Objective**: metrics_compute_round, metrics_sentiment_keyword, metrics_get_trend
- **Files**: CREATE `engine/metrics_engine.py`
- **DoD**: Deterministic computation; same text = same sentiment score
- **Risks**: H-05

#### Task A-F.2: Create engine/sentiment.py
- **Objective**: Deterministic word-list-based sentiment scoring (~200 positive, ~200 negative keywords)
- **Files**: CREATE `engine/sentiment.py`
- **DoD**: Pure function, no randomness, no LLM, no network I/O

#### Task A-G.1: Create engine/server.py -- MCP stdio Server
- **Objective**: Register all 21 core tools + accept Worker B's 6 additional tools
- **Files**: CREATE `engine/server.py`
- **Key details**: Server instructions for Tool Search discoverability; DATA_DIR from OATHFISH_DATA_DIR env var
- **DoD**: Server starts, responds to all tools via stdio JSON-RPC
- **Risks**: H-08, H-12

#### Task A-G.2: Create engine/__init__.py
- **Files**: CREATE `engine/__init__.py`

#### Task A-G.3: Create engine/requirements.txt
- **Files**: CREATE `engine/requirements.txt`
- **Content**: mcp>=1.0.0, pydantic>=2.0.0

#### Task A-G.4: MCP Environment Requirements (spec for Worker C)
- **Objective**: Document env vars Worker C must include in .mcp.json
- **Key details**:
  - `OATHFISH_DATA_DIR`: `${CLAUDE_PLUGIN_DATA}/runs` (SPEC CORRECTION from feature-request.md:1064 which incorrectly uses CLAUDE_PLUGIN_ROOT)
  - `MAX_MCP_OUTPUT_TOKENS`: `50000` (documented at mcp.md:162-163, defense-in-depth for H-07)
  - Command should use `python3` (not `python`)
- **No file created** -- specification for Worker C

---

### Phase 2: Calibration Engine (Worker B)

#### Task B-A.1: Define Calibration Pydantic Models
- **Objective**: CalibrationPrediction, CalibrationOutcome, DomainBias, ArchetypeBias, EnsembleMetrics, HoldoutReport, CompetenceAssessment
- **Files**: CREATE `engine/calibration_models.py`
- **Key details**:
  - PredictionDomain enum: POLICY, ECONOMICS, TECHNOLOGY, SCIENCE, ENVIRONMENT, SOCIAL, UNCLASSIFIED
  - PredictionHorizon: SHORT, MEDIUM, LONG, EXTENDED
  - QuestionComplexity: SIMPLE_BINARY, MULTI_FACTOR
  - EnsembleMetrics uses unified delta convention: POSITIVE = IMPROVEMENT (brier_gap = raw - corrected; deliberation_delta = baseline - informed)
  - Holdout: deterministic via `int(prediction_id, 16) % 5 == 0` (direct hex parsing, no double-hashing)
  - All datetimes use `datetime.now(datetime.UTC)` (not deprecated utcnow())
- **DoD**: All models validate and serialize

#### Task B-A.2: Create Domain Taxonomy Config
- **Files**: CREATE `engine/config/domain_taxonomy.json`
- **Key details**: 6 domains with keyword lists; user-overridable via OATHFISH_DATA_DIR/config/

#### Task B-A.3: Create Domain Classifier
- **Files**: CREATE `engine/domain_classifier.py`
- **Key details**:
  - Deterministic keyword matching (no LLM)
  - classify_domain(), classify_horizon() (order: extended -> long -> short -> medium to avoid "1 month" misclassification), classify_complexity()
  - stance_to_probability(): `forecast_probability = (stance + 1) / 2`
  - compute_holdout_flag(): `int(prediction_id, 16) % 5 == 0` (direct hex, no double-hash)
- **DoD**: Deterministic; same input = same domain/horizon/complexity

#### Task B-B.1: Create Calibration Engine -- 5 MCP Tools
- **Objective**: calibration_record_prediction, calibration_record_outcome, calibration_get_domain_bias, calibration_get_archetype_bias, calibration_get_ensemble_metrics
- **Files**: CREATE `engine/calibration_engine.py`
- **Key details**:
  - t-distribution p-values (not normal CDF -- anti-conservative at small n, SK-03 fix)
  - Tiered correction threshold: n>=15 at run 3+ (|MSE|>0.10 large biases only), n>=45 at run 10+ (|MSE|>0.05), n>=90 at run 18+ (p<0.10). **SPEC DEVIATION from C-27 verification (n>=90)** -- explicitly documented
  - write_domain_corrections() method writes domain_corrections.json matching Worker A's schema
  - Overfitting detection: `overfitting_gap > 0.02` (simplified, SK-11 fix)
  - Correction schedule: RECORD_ONLY -> DOMAIN_ADDITIVE -> ARCHETYPE_ADDITIVE -> LOGISTIC (at run 50+)
  - Bootstrap questions: is_bootstrap=True included in calibration corrections, excluded from user-facing Brier
  - A/B comparison: get_deliberation_comparison() stratified by QuestionComplexity
- **DoD**: All 5 tools work; corrections improve synthetic biased data; holdout excluded
- **Risks**: H-01 (noise at small n), H-04 (holdout contamination), H-07 (domain-varying acquiescence)

#### Task B-B.2: Register Calibration Tools in server.py
- **Files**: MODIFY `engine/server.py`
- **Key details**: Add `from .calibration_engine import register_tools as register_calibration_tools`

#### Task B-C.1: Create Competence Classifier -- 1 MCP Tool
- **Objective**: classify_question (pre-UNDERSTAND routing)
- **Files**: CREATE `engine/competence_classifier.py`
- **Key details**:
  - Two-stage design: Stage 1 (text-only, pre-UNDERSTAND) classifies SIMPLE_BINARY vs MULTI_FACTOR; Stage 2 (post-UNDERSTAND) assesses archetype relevance
  - routing_recommendation: "FULL_PIPELINE" | "SKIP_DELIBERATE" | "LOW_CONFIDENCE"
- **DoD**: Works with no archetype data (Stage 1 only)
- **Risks**: H-08 (timing paradox)

#### Task B-C.2: Register Competence Classifier in server.py
- **Files**: MODIFY `engine/server.py`

#### Task B-D.1: Add Debiasing to amplify_aggregate
- **Files**: MODIFY `engine/amplification_engine.py`
- **Key details**:
  - Reads from domain_corrections.json (file-based, no CalibrationEngine parameter)
  - Matches Worker A's signature: `amplify_aggregate(apply_debiasing: bool = False, archetype_ids: list[str] | None = None)`
  - Correction formula: `f_corrected = clamp(f_raw - offset, 0, 1)`
- **DoD**: Returns both raw and debiased distributions

#### Task B-E.1: Baseline Storage in Amplification Engine
- **Files**: MODIFY `engine/amplification_engine.py`
- **Key details**: Separate directories for baseline/ and informed/ results

#### Task B-E.2: A/B Comparison in Ensemble Metrics
- **Key details**: deliberation_delta stratified by QuestionComplexity; _ab_recommendation() generates routing advice

#### Task B-F.1: ForecastBench Pipeline
- **Files**: CREATE `engine/forecastbench.py`
- **Key details**: Modular export; median aggregation; format configurable (ForecastBench format assumed)
- **Risks**: H-09 (format unknown)

#### Task B-F.2: Bootstrap Question Support
- **Key details**: is_bootstrap field on CalibrationPrediction; included in calibration, excluded from primary Brier

#### Task B-CFG.1: Domain Taxonomy Config
- **Files**: CREATE `engine/config/domain_taxonomy.json`

---

### Phase 3: Plugin Scaffold (Worker C)

#### Task C-A.1: Create plugin.json
- **Files**: CREATE `.claude-plugin/plugin.json`
- **Content**: name="oathfish", version="0.1.0", description, author="Oathe"

#### Task C-A.2: Create .mcp.json
- **Files**: CREATE `.mcp.json`
- **Key details**:
  - command: "python3" (not "python")
  - args: ["${CLAUDE_PLUGIN_ROOT}/engine/server.py"]
  - env: OATHFISH_DATA_DIR="${CLAUDE_PLUGIN_DATA}/runs", MAX_MCP_OUTPUT_TOKENS="50000" (per Worker A Task G.4 spec)
- **Risks**: H-04 (server must start)

#### Task C-A.3: Create hooks/hooks.json
- **Files**: CREATE `hooks/hooks.json`
- **Key details**:
  - SessionStart "startup" -> oathfish-init.sh
  - SessionStart "compact" -> oathfish-reinject-state.sh
  - PreToolUse on Agent -> validate-no-numbers.sh (C-33 secondary enforcement)
  - All hook scripts use `${CLAUDE_PLUGIN_DATA:-/tmp}` fallback for env var availability
- **Risks**: H-03 (C-33 enforcement), H-06 (round number via file bridge)

#### Task C-A.4: Create scripts/validate-no-numbers.sh
- **Files**: CREATE `scripts/validate-no-numbers.sh`
- **Key details**: Parses `tool_input.prompt` from Agent tool PreToolUse stdin JSON. Reads `.current_round` file for round-6 exception. Exits 2 (block) if numeric predictions detected in rounds 1-5.

#### Task C-A.5: Create scripts/oathfish-init.sh
- **Files**: CREATE `scripts/oathfish-init.sh`

#### Task C-A.6: Create scripts/oathfish-reinject-state.sh
- **Files**: CREATE `scripts/oathfish-reinject-state.sh`
- **Key details**: Recovers run state from MCP after compaction

#### Task C-B.1: Create agents/deliberation-coordinator.md
- **Files**: CREATE `agents/deliberation-coordinator.md`
- **Key details**:
  - Coordinator system prompt with round management protocol
  - Verbatim relay (no summarization) of arguments between archetypes
  - C-33 enforcement in system prompt (primary layer)
  - Round types: FREE_FORM, STRUCTURED_DEBATE, SCENARIO_REACTION, PREDICTION (not INDEPENDENT_PREDICTION)
  - Generates deliberation digest (500-1000 tokens) for AMPLIFY phase
  - Writes `.current_round` file (transient coordination signal, not run state)

#### Task C-B.2: Create agents/archetype-agent.md
- **Files**: CREATE `agents/archetype-agent.md`
- **Key details**: Frontmatter references `skills: [oathfish:archetype-reasoning]`; memory:project for cross-run learning; tiered models (structural=opus, priority-topics=sonnet, rest=haiku)

#### Task C-B.3: Create agents/report-analyst.md
- **Files**: CREATE `agents/report-analyst.md`

#### Task C-C.1: Create skills/oathfish/SKILL.md (Dispatcher)
- **Files**: CREATE `skills/oathfish/SKILL.md`
- **Key details**: Runs INLINE (no context:fork); dispatches to phase skills; two entry modes documented

#### Task C-C.2 through C-C.7: Phase Skills
- understand (context:fork), baseline-amplify (context:fork), deliberate (INLINE), amplify (context:fork), synthesize (context:fork), interact (inline for resume)

#### Task C-D.1 through C-D.4: Commands
- /oathfish, /oathfish-chat, /oathfish-inject, /oathfish-calibrate

#### Task C-E.1: Create scripts/get-state.sh (Dynamic Context Injection)
- **Files**: CREATE `scripts/get-state.sh`

#### Task C-E.2: Create scripts/setup.sh
- **Files**: CREATE `scripts/setup.sh`
- **Key details**: pip3 install, verify MCP server, create data directory

---

### Phase 4: Domain Logic (Worker D)

#### Task D-A.1: Import PredictionPosition from Worker A
- **Files**: IMPORT from `engine/models.py`
- **Key details**: Worker D's amplification_sdk.py imports PredictionPosition and Archetype from engine.models. Does NOT redefine.
- **DoD**: model_json_schema() produces valid schema; model_validate() round-trips

#### Task D-A.2: Create Superforecaster Methodology Protocol
- **Files**: CREATE `skills/archetype-reasoning/SKILL.md`
- **Key details**: 6-step methodology (State Base Rate, Decompose, List Uncertainties, Falsification Criteria, Second-Order Effects, Calibrate Confidence). Output format section for round 6.
- **Note**: Worker C references this file but does NOT create it.

#### Task D-A.3: Grounding Rung Rubric
- **Key details**: 4-rung rubric (Rung 1: synthetic, Rung 2: 3-5 real sources, Rung 3: methodology grounding, Rung 4: expert interviews/primary data)

#### Task D-B.1 through D-B.4: Structural Archetype Prompts
- **Files**: CREATE `agents/archetypes/structural/{historian,systems-thinker,contrarian,probabilist}.md`
- **Key details**: Epistemic lenses (NOT stakeholder personas); "You are NOT a stakeholder. You are an EPISTEMIC LENS" language; pre-curated Rung 3 grounding (Tetlock, Meadows, Perez, etc.); 5+ reference works each

#### Task D-C.1: Topic-Customized Archetype Generation Pipeline
- **Key details**: Generate 26 archetypes per topic; exclude structural roles; use WebSearch for runtime source discovery (VERIFIED as built-in tool)

#### Task D-C.2: Runtime Source Grounding Protocol
- **Key details**: WebSearch primary -> WebFetch fallback -> manual. GroundingSourceInternal model for processing; serialized to `list[str]` for Archetype.grounding_sources storage.

#### Task D-C.3: Persona Prompt Assembly
- **Key details**: 1000-1500 word target; sections: Who You Are, Values/Incentives, Blind Spots, Communication Style, Stubbornness Domain, Grounding, Superforecaster Protocol, Starting Position, Rules. Word count validation logs warning > 1500.

#### Task D-D.1: Core Amplification Engine Module
- **Files**: CREATE `engine/amplification_sdk.py`
- **Key details**:
  - AmplificationMode: BASELINE (stateless) or INFORMED (digest-injected)
  - AmplificationConfig with allowed_tools=[] (tool-free), max_turns=1 (single-turn), deliberation_digest field
  - PersonaVariationGenerator: deterministic spread across 7 ages x 12 locations x 4 experience x 5 education x 5 personality axes. Known aliasing (edu_idx == axis1_idx) produces 50 unique strings.
  - System prompt = base persona + variation delta + (optional) digest -- all concatenated (NO append_system_prompt field in SDK)
  - asyncio.Semaphore(10) default concurrency; exponential backoff + retry
  - Cost tracking via ResultMessage.total_cost_usd
  - Digest validation: INFORMED mode requires non-empty digest; warns if > 1500 words
- **DoD**: 1500 calls with rate limiting, retry, cost tracking, dual-mode
- **Risks**: H-05 (cost -- mitigated by digest), H-09 (rate limits), H-10 (variation diversity)

#### Task D-D.2: Amplification Orchestrator (Skill Integration)
- **Key details**: Orchestration flow for both BASELINE_AMPLIFY and AMPLIFY phases; digest generation via single claude -p call; cost comparison showing digest is ~40x cheaper than --resume

#### Task D-E.1: Propose Archetype Model Extensions to Worker A
- **Files**: PROPOSE additions to `engine/models.py`
- **Key details**: is_structural, archetype_type, stubbornness_domain, grounding_search_queries (all with defaults, non-breaking)

#### Task D-CFG.1: Deliberation Digest Validation
- **Files**: Part of `engine/amplification_sdk.py`
- **Key details**: Validates digest presence for INFORMED mode; warns on length

---

## 7. Build Sequence

### Dependency Graph

```
Phase 1 (Foundation -- Worker A):
  A-A.1 (models.py) -----+
  A-A.2 (persistence.py) -+---> Phase 2A (Worker A engines, parallel)
                           |
                           +--> A-B.1 (state_machine) -> Phase 3 (Worker C scaffold)
                           +--> A-C.1 (deliberation_engine)
                           +--> A-D.1 (graph_engine)
                           +--> A-E.1 (amplification_engine) -> Phase 2B (Worker B calibration)
                           +--> A-F.1 + A-F.2 (metrics + sentiment)
                           +--> A-G.1 (server.py) -> Phase 2B, Phase 3

Phase 2A (Calibration -- Worker B, after A-A.1 + A-E.1 + A-G.1):
  B-A.1 (calibration_models) -> B-A.2 + B-A.3 (taxonomy + classifier)
  B-B.1 (calibration_engine) -> B-B.2 (register in server.py)
  B-C.1 (competence_classifier) -> B-C.2 (register)
  B-D.1 (debiasing integration) -- depends on A-E.1
  B-F.1 (forecastbench)

Phase 2B (Domain Logic -- Worker D, after A-A.1):
  D-A.1 (import models) -> D-A.2 (methodology skill)
  D-B.1-B.4 (structural archetypes)
  D-C.1-C.3 (generation pipeline)
  D-D.1 (amplification SDK) -> D-D.2 (orchestrator)
  D-E.1 (model extensions proposal)

Phase 3 (Orchestration -- Worker C, after A-B.1 + A-G.1):
  C-A.1 + C-A.2 (plugin.json + .mcp.json) -- can start immediately
  C-A.3-A.6 (hooks + scripts)
  C-B.1-B.3 (agents) -- depends on D-A.2 for archetype-reasoning reference
  C-C.1-C.7 (skills) -- depends on D-D.1 for amplification orchestration
  C-D.1-D.4 (commands)
  C-E.1-E.2 (utility scripts)

Integration Testing:
  Full pipeline test -- depends on ALL phases complete
```

### Recommended Build Order

1. **Week 1**: Worker A Phase 1 (models.py, persistence.py, state_machine.py)
2. **Week 1-2**: Worker A engines in parallel (deliberation, graph, amplification, metrics, server)
3. **Week 2**: Worker B calibration models + engine + classifier (depends on A's models + server)
4. **Week 2**: Worker D structural archetypes + methodology skill (parallel with B)
5. **Week 2-3**: Worker D amplification SDK (depends on A's models)
6. **Week 3**: Worker C scaffold (depends on A's server + D's methodology skill)
7. **Week 3**: Worker B debiasing integration + ForecastBench
8. **Week 4**: Integration testing, full pipeline runs

---

## 8. Hazard Registry

### Consolidated from All Workers (deduplicated)

| H-ID | Hazard | Owner | Mitigation | Confidence |
|------|--------|-------|------------|------------|
| A-H01 | Position type discrimination failure | A | Type discrimination via round plan (RoundType enum), not hardcoded round 6 | HIGH (A,C,D agree) |
| A-H02 | Write-through persistence failure | A | Atomic write via temp+rename, os.fsync() | HIGH |
| A-H03 | Cross-engine debiasing interface mismatch | A+B | File-based contract: domain_corrections.json with explicit JSON schema. Worker B writes, Worker A reads. Graceful degradation. | HIGH (resolved SK-01) |
| A-H04 | Graph temporal queries return expired facts | A | as_of parameter on graph_query() | HIGH |
| A-H05 | Metrics engine format coupling | A | Shared Pydantic models from models.py | HIGH |
| A-H06 | Diversity index threshold sensitivity + low-N weakness | A | Configurable thresholds; null diversity when total_unique_arguments < 5 with INSUFFICIENT_DATA flag | HIGH (improved in r2) |
| A-H07 | MCP output exceeds 25K token limit | A | PRIMARY: pagination parameters. DEFENSE-IN-DEPTH: MAX_MCP_OUTPUT_TOKENS=50000 | HIGH |
| A-H08 | Concurrent tool calls race condition | A | stdio sequential assumption (IMPLICIT, likely correct) | MEDIUM |
| A-H09 | ERROR state resume after restart | A | previous_state stored in run.json | HIGH |
| A-H10 | RoundSummary references undefined Position type | A | Position = Union[ArgumentPosition, PredictionPosition] | HIGH |
| A-H11 | Round 6 evolution delta against round 5 (no numeric fields) | A | Absolute values, not deltas | HIGH |
| A-H12 | Data directory under CLAUDE_PLUGIN_ROOT | A+C | CLAUDE_PLUGIN_DATA in .mcp.json (spec correction) | HIGH |
| B-H01 | Noise corrections at small n | B | Tiered thresholds: n>=15/|MSE|>0.10, n>=45/|MSE|>0.05, n>=90/p<0.10. t-distribution p-values. | HIGH (SPEC DEVIATION documented) |
| B-H02 | Domain taxonomy undefined | B | 6-domain taxonomy with keyword classifier, configurable JSON | HIGH |
| B-H03 | Calibration data lost on plugin update | B+C | CLAUDE_PLUGIN_DATA in .mcp.json | HIGH |
| B-H04 | Holdout set contamination | B | Hash-based deterministic partition; exclude_holdout=True default | HIGH |
| B-H05 | A/B temporal confound | B | Timestamps recorded; stratification by complexity | MEDIUM (documentation mitigation) |
| B-H06 | Cold-start / resolution latency | B | Bootstrap questions (1-4 week resolution) | MEDIUM |
| B-H07 | Domain-varying acquiescence | B | Per-domain corrections, not global | HIGH |
| B-H08 | Competence classifier timing paradox | B | Two-stage design: text-only pre-UNDERSTAND, archetype-aware post-UNDERSTAND | HIGH |
| B-H09 | ForecastBench format unknown | B | Modular export, assumed binary probability JSON | MEDIUM |
| B-H10 | Logistic recalibration unstable at small n | B | Deferred to run 50+ | HIGH |
| B-H11 | Gap > 0.05 triggers undefined action | B+D | Report recommendation; re-grounding is Worker D concern | MEDIUM |
| C-H01 | Coordinator context pressure (180 payloads / 6 rounds) | C | MCP-as-external-memory; compact hook re-injects state | HIGH |
| C-H02 | MCP output exceeds 25K (position map with 30 archetypes) | C | Paginated queries | HIGH |
| C-H03 | Plugin subagent hooks IGNORED -- C-33 broken in frontmatter | C | Three-layer defense: coordinator enforcement + PreToolUse on Agent + archetype prompt prohibition | HIGH |
| C-H04 | MCP server must be alive for state transitions | C | setup.sh verification; oathfish skill checks state_get() | HIGH |
| C-H05 | allowed-tools MCP namespacing syntax unverified | C | Test with one skill first; fallback to permissive | MEDIUM |
| C-H06 | Round number unavailable to hooks | C | File-based bridge: coordinator writes .current_round | HIGH |
| C-H07 | STRUCTURED_DEBATE rounds serial bottleneck | C | Reduce to 2 exchange cycles; parallel pairs | MEDIUM |
| C-H08 | Teams experimental flag may not be needed | C | Eliminated Teams dependency (subagent architecture) | HIGH (eliminated) |
| C-H09 | Subagent concurrency limit unknown | C | Batch by priority tier; background=true | MEDIUM |
| C-H10 | Skills preloading context inflation | C+D | archetype-reasoning skill under 100 lines | HIGH |
| C-H11 | INTERACT phase subagent resume | C | Store subagent IDs; resume via Agent tool | MEDIUM |
| C-H12 | Argument relay fidelity degradation | C | System prompt: "Pass FULL text, do NOT summarize" | HIGH |
| C-H13 | context:fork file persistence unverified | C | Fork likely shares FS (not isolation:worktree); fallback: MCP for artifacts | MEDIUM |
| C-H14 | Nesting problem: dispatcher cannot launch coordinator | C | RESOLVED: deliberate skill runs inline | HIGH (eliminated) |
| D-H01 | Persona prompt exceeds context limit | D | 1000-1500 word target; word count validation warning | HIGH |
| D-H02 | PredictionPosition schema mismatch MCP vs SDK | D | Single import from Worker A's engine/models.py | HIGH (resolved) |
| D-H03 | Web search failure for grounding | D | Graceful degradation to Rung 1; WebSearch VERIFIED as built-in | HIGH |
| D-H04 | Structural archetype drift between skill and model | D | Single authoritative source per concern | HIGH |
| D-H05 | Context overflow with --resume at 1500 calls | D | ELIMINATED: Digest approach, NOT --resume. ~40x cheaper. | HIGH (eliminated) |
| D-H08 | Superforecaster methodology inconsistency | D | Single skill file; all archetypes reference it | HIGH |
| D-H09 | 1500 calls overwhelm rate limits | D | asyncio.Semaphore(10); exponential backoff; fallback model | HIGH |
| D-H10 | Persona variation insufficient diversity | D | PersonaVariationGenerator; 50 unique strings per archetype (aliasing noted) | MEDIUM |
| D-H13 | Topic archetypes overlap structural archetypes | D | Exclusion instruction in generation prompt | HIGH |

**Total hazards**: 45 (after deduplication)
**All have mitigations documented.** No unmitigated hazards.

---

## 9. Spec Corrections & Deviations

### Corrections to Feature Request

| Issue | Feature Request Says | Spec Corrects To | Rationale | Workers |
|-------|---------------------|-----------------|-----------|---------|
| OATHFISH_DATA_DIR path | `${CLAUDE_PLUGIN_ROOT}/docs/runs` (line 1064) | `${CLAUDE_PLUGIN_DATA}/runs` | CLAUDE_PLUGIN_ROOT wiped on plugin update; CLAUDE_PLUGIN_DATA persists. Per mcp-analysis.md:53. | A, B, C |
| Hooks in subagent frontmatter | Hooks in archetype-agent frontmatter (lines 646-654) | Hooks in plugin hooks/hooks.json + coordinator enforcement | sub-agents.md:107: plugin subagent hooks IGNORED | C |
| INDEPENDENT_PREDICTION round type | "INDEPENDENT_PREDICTION" (line 169 descriptive label) | "PREDICTION" (formal enum value) | Must match RoundType.PREDICTION enum for MCP validation. feature-request.md:1131 uses PREDICTION formally. | A, C |

### Spec Deviations (Intentional)

| Deviation | Spec Says | Plan Does | Rationale | Worker |
|-----------|----------|-----------|-----------|--------|
| Correction threshold | n>=90/domain (C-27 verification) | Tiered: n>=15 at run 3+ (large biases), n>=45 at run 10+, n>=90 at run 18+ | C-27 says "corrections from run 3+" but verification says n>=90. At run 3, only ~15/domain. Tiered approach catches only large biases early, progressively increases sensitivity. Statistical caveats documented. | B |
| Post-deliberation context | --resume SESSION_ID (C-21) | Deliberation digest (500-1000 tokens) injected into system_prompt | --resume at 1500 calls with 100K+ token context = 150M input tokens, ~$50-100x cost explosion. Digest is ~40x cheaper. Context injected via prompt, not session resumption. | C, D |
| append_system_prompt usage | Feature request implies append capability | Concatenate base + delta into single system_prompt string | ClaudeAgentOptions does NOT include append_system_prompt field (headless-analysis.md:55). CLI --append-system-prompt exists but SDK equivalent absent. | D |

---

## 10. Open RFIs

| RFI-ID | Question | Impact | Workers | Needed |
|--------|----------|--------|---------|--------|
| RFI-01 | Should Worker A's state machine support SKIP_DELIBERATE transition (BASELINE_AMPLIFY -> AMPLIFY)? | Worker B's competence_classifier routes SIMPLE_BINARY to SKIP_DELIBERATE, but state machine currently requires BASELINE_AMPLIFY -> DELIBERATE. Need LEGAL_TRANSITIONS extension. | A, B, C | Architecture decision from system architect |
| RFI-02 | Does MCP Python SDK guarantee sequential processing over stdio? | If concurrent requests possible, need file-level locking in persistence layer. | A | Runtime testing |
| RFI-03 | Is CLAUDE_PLUGIN_DATA available in hook script environment? | Hook scripts use `${CLAUDE_PLUGIN_DATA:-/tmp}` fallback. If absent, round file bridge uses /tmp. | C | Runtime testing |
| RFI-04 | Is there a lightweight token counting mechanism in SDK or stdlib? | Would improve H-01 (persona prompt length) mitigation beyond word count heuristic. | D | SDK docs |
| RFI-05 | Can 30 background subagents run concurrently? | If not, must batch 5-10 at a time, 3-6x slower rounds. | C | Runtime testing |
| RFI-06 | Does context:fork preserve file writes to parent filesystem? | If not, phase skills must use MCP for artifact storage. Fork likely shares FS (not isolation:worktree). | C | Runtime testing |

**Recommendation for RFI-01**: Add the SKIP_DELIBERATE transition. This enables the question routing pipeline that Workers B and C have designed. The state machine change is minimal: add `RunPhase.AMPLIFY` to `LEGAL_TRANSITIONS[RunPhase.BASELINE_AMPLIFY]`.

---

## 11. Resolution Log

### Cross-Worker Conflicts Resolved

| Conflict | Workers | Resolution | Method |
|----------|---------|------------|--------|
| Debiasing interface (object vs file) | A vs B | File-based contract: domain_corrections.json. Worker B writes, Worker A reads. No cross-engine Python imports. | Skeptic critique + defense (SK-01 both workers) |
| amplify_aggregate signature | A vs B | Worker A's signature canonical: `(apply_debiasing=False, archetype_ids=None)`. Worker B's modification uses file reads, keeps archetype_ids filter. | Skeptic critique (SK-06) |
| apply_debiasing default (False vs True) | A vs B | Worker A's `False` is correct (conservative for early runs with no calibration data). | Analysis |
| engine/models.py ownership | A vs D | Worker A OWNS. Worker D IMPORTS. D proposes additions via cross-worker specification. | Skeptic critique + defense (SK-03 both workers) |
| PredictionPosition field optionality (defaults vs required) | A vs D | Worker A's schema (with defaults) is authoritative. Worker D's "all required" rejected -- Worker A owns. | Skeptic critique (D-SK-01) |
| grounding_sources type (list[str] vs list[GroundingSource]) | A vs D | Worker A's `list[str]` adopted. Worker D uses GroundingSourceInternal for processing, serializes to `list[str]`. | Skeptic critique (D-SK-04) |
| .mcp.json ownership | A vs C | Worker C OWNS (scaffold/plugin config). Worker A specifies env requirements. | Skeptic critique (A-SK-04) |
| archetype-reasoning/SKILL.md ownership | C vs D | Worker D OWNS (domain logic content). Worker C REFERENCES. | Skeptic critique (C-SK-03) |
| INDEPENDENT_PREDICTION vs PREDICTION | C vs A | PREDICTION (matching Worker A's RoundType enum). | Skeptic critique (C-SK-06) |
| PredictionPosition field count (12 vs 13) | A vs D | 13 fields (coalition_alignment IS in feature-request.md:560). Worker D's "12 fields" was wrong. | Code verification |
| append_system_prompt existence | D | Does NOT exist in ClaudeAgentOptions. Replaced with string concatenation. | Skeptic critique (D-SK-02) |
| WebSearch availability | D | EXISTS as built-in tool (tools-reference.md:40). A-D05 reclassified from USER_DECISION to VERIFIED. | Skeptic critique (D-SK-06) |
| --resume cost explosion | D | Replaced with deliberation digest approach (~40x cheaper). --resume reserved for INTERACT only. | Skeptic critique (D-SK-08) |
| Normal CDF vs t-distribution | B | t-distribution adopted (normal is anti-conservative at small n). | Skeptic critique (B-SK-03) |
| brier_gap sign convention | B | Unified: POSITIVE = IMPROVEMENT. brier_gap = raw - corrected. | Skeptic critique (B-SK-05) |
| classify_horizon "1 month" bug | B | Fixed: check short before medium in ordering. | Skeptic critique (B-SK-07) |
| SubagentStop blocking undocumented | C | Replaced with PreToolUse on Agent + coordinator enforcement. | Skeptic critique (C-SK-01) |
| Coordinator nesting problem | C | deliberate skill runs inline (no context:fork). | Skeptic critique (C-SK-02) |

### Conflicts Resolved by Consensus (no user input needed)

All 18 conflicts above were resolved through code verification and skeptic-driven analysis. No architectural conflicts required user decision -- all had clear resolutions based on primary documentation evidence or safety-first defaults.

---

## Appendix A: MCP Tool Registry (27 tools)

### Worker A Core Tools (21)

**State Machine (5)**:
1. state_create_run
2. state_transition
3. state_get
4. state_checkpoint
5. state_resume

**Deliberation (5)**:
6. deliberation_init
7. deliberation_record_round
8. deliberation_track_evolution
9. deliberation_get_position_map
10. deliberation_check_convergence

**Graph (5)**:
11. graph_add_entity
12. graph_add_relationship
13. graph_query
14. graph_update
15. graph_compute_centrality

**Amplification (3)**:
16. amplify_init
17. amplify_record_batch
18. amplify_aggregate

**Metrics (3)**:
19. metrics_compute_round
20. metrics_sentiment_keyword
21. metrics_get_trend

### Worker B Calibration Tools (6)

22. calibration_record_prediction
23. calibration_record_outcome
24. calibration_get_domain_bias
25. calibration_get_archetype_bias
26. calibration_get_ensemble_metrics
27. classify_question (competence classifier)

---

## Appendix B: Test Coverage Summary

| Worker | Unit Tests | Integration Tests | Total Test Files |
|--------|-----------|-------------------|-----------------|
| A | 7 (models, persistence, state_machine, deliberation, graph, amplification, metrics) | 1 (server) | 8 |
| B | 4 (calibration, domain_classifier, competence, forecastbench) | - | 4 |
| C | 3 (C-33 enforcement, hook firing, plugin load) | 4 (inline deliberate, compaction, context:fork, MCP start) | 7 |
| D | 5 (models import, variation, archetypes, amplification, grounding) | 3 (superforecaster integration, schema contract, websearch) | 8 |

---

## Appendix C: Data Directory Structure

```
${CLAUDE_PLUGIN_DATA}/
  runs/
    {run_id}/
      _meta/
        run.json              # RunConfig + state (Worker A state machine)
      understanding/
        archetypes.json       # 30 archetype definitions (Worker D generates)
      deliberation/
        round-{n}/
          positions.json      # ArgumentPosition (1-5) or PredictionPosition (6)
          summary.json        # Round summary + metrics
        convergence.json      # Convergence tracking
      amplification/
        baseline/
          config.json
          results/
            batch-{N}.json
          distributions.json
        informed/
          config.json
          results/
            batch-{N}.json
          distributions.json
      graph/
        entities.json
        relationships.json
      synthesis/
        report.json
  calibration/
    predictions.json          # All CalibrationPrediction records (Worker B)
    outcomes.json             # All CalibrationOutcome records (Worker B)
    domain_corrections.json   # Cross-engine contract (Worker B writes, Worker A reads)
  config/
    domain_taxonomy.json      # User-overridable domain taxonomy (Worker B)
  .active_run                 # Current active run ID (transient)
  .current_round              # Current round number for hook bridge (transient)
```

---

## Handoff

Golden specification saved to: `docs/darwin/runs/0001-oathfish-swarm-engine/consolidated/spec.md`
Ready for Execute phase (Darwin:execute).

**Summary**:
- Workers synthesized: A (MCP Core), B (Calibration), C (Orchestration), D (Domain Logic)
- Total files: 48 (11 Worker A + 13 Worker B + 19 Worker C + 8 Worker D, with 3 shared MODIFYs)
- MCP tools: 27
- Hazards consolidated: 45 (all mitigated)
- Cross-worker conflicts resolved: 18
- Open RFIs: 6 (none blocking; RFI-01 has recommendation)
- Spec corrections: 3 (OATHFISH_DATA_DIR path, hooks placement, round type name)
- Spec deviations: 3 (correction threshold, digest vs resume, append_system_prompt)
