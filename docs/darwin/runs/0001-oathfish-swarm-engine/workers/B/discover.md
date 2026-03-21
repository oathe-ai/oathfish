# Discover Report - Worker B
## Run: 0001-oathfish-swarm-engine
## Keywords: calibration_engine, debiasing, acquiescence, domain_bias, Brier score, competence_classifier, baseline_amplify, holdout_validation
## Lens: mcp-research
## Entry Point: feature-request.md section 6.1b (Research-Mandated Requirements)

---

## Phase 0: Memory-Informed Context

### Project Intelligence (from Serena Memory) - VERIFIED

**Source**: `~/.claude/projects/-Users-shezmalik-Projects-Oathe-oathfish/memory/project_oathfish_vision.md`

The project memory describes OathFish as a two-layer swarm intelligence engine with a 5-phase pipeline (UNDERSTAND, DELIBERATE, AMPLIFY, SYNTHESIZE, INTERACT) and a Python MCP server with ~20 tools.

**Verification against code**: The project is greenfield. No engine/ directory exists, no Python files exist, no MCP server code exists yet. The project root at `/Users/shezmalik/Projects/Oathe/oathfish/` contains only `package.json`, `docs/`, `references/`, and `.claude/`. (Verified: `ls` of project root.)

**Memory staleness**: The memory says "~20 tools" and "5-phase pipeline." The research-driven redesign (research-driven-redesign.md:435-442) expanded this to ~28 tools and a 7-phase pipeline (adding BASELINE_AMPLIFY before DELIBERATE). The Calibration Engine (5 tools) is entirely absent from the project memory. Memory is stale on scope.

---

## Phase 1: Search Strategy

| Type | Keywords | Source |
|------|----------|--------|
| Literal | calibration_engine, calibration_record_prediction, calibration_record_outcome, calibration_get_domain_bias, calibration_get_archetype_bias, calibration_get_ensemble_metrics | feature-request.md:303, research-driven-redesign.md:253-276 |
| Literal | debiasing, acquiescence, domain_bias, per-domain correction | feature-request.md:304, C-27:1142, C-28:1143 |
| Literal | competence_classifier, question routing, in-domain, out-of-domain | C-31:1146, research-driven-redesign.md:102-115 |
| Literal | baseline_amplify, A/B test, baseline amplification | C-26:1141, research-driven-redesign.md:228-236 |
| Literal | holdout_validation, holdout set, overfitting detection | C-34:1149, final-synthesis.md:143 |
| Literal | Brier score, mean signed error, calibration index | 2402.19379-silicon-crowd.md:13-14, 2602.19520-calibration-decomposition.md:26-31 |
| Literal | ForecastBench, submission pipeline | C-35:1150, 2409.19839-forecastbench.md:5 |
| Literal | short-horizon bootstrap, resolution latency | research-driven-redesign.md:428, A-09:1232 |
| Synonym | scoring rule, proper scoring, probability calibration | Domain: forecasting statistics |
| Anti-seed | overfitting, correction_error, insufficient_sample, cold_start | Research risks |
| Framework | Pydantic, mcp, stdio, write-through persistence | package.json, feature-request.md:1019-1029 |

---

## Phase 2: Mandatory Anchors

### Package Manifest

**File**: `package.json` (project root)
```json
{
  "name": "oathfish",
  "version": "0.1.0",
  "description": "Claude-Native Swarm Intelligence Engine"
}
```
No dependencies declared. No Python requirements.txt exists. This is a greenfield project.

### Application Entry Point

No code exists. The planned entry point is `engine/server.py` per feature-request.md:1021. The MCP server will be a Python stdio process configured via `.mcp.json` (feature-request.md:1056-1069).

### Type Definitions

No type definitions exist. Planned Pydantic models at `engine/models.py` per feature-request.md:1027. The feature request defines the following models relevant to Worker B's scope:

- `PredictionPosition` (feature-request.md:547-561) -- the round 6 structured prediction format
- `RunConfig` (feature-request.md:579-587) -- run configuration
- `AmplificationResult` (feature-request.md:571-577) -- per-persona amplification output

No Pydantic models for the Calibration Engine are defined in the feature request. Worker B must design these.

---

## Phase 3: Surface Inventory - Research Materials

### 3.1 Calibration Engine (5 MCP tools)

**Primary sources**:

| Source | File | Relevance | Key Data |
|--------|------|-----------|----------|
| Calibration tool signatures | research-driven-redesign.md:253-276 | HIGH | 5 tool signatures with input/output specs |
| Feature scope | feature-request.md:303 | HIGH | Calibration engine listed in scope |
| Success criteria SC-14 | feature-request.md:116 | HIGH | "2/6 domains show p<0.10 bias after 5 runs" |
| Power analysis | 2602.19520-calibration-decomposition.md:26-31 | HIGH | 4-component model, 87.3% R-squared, n=90 for d=0.3 |
| Domain bias structure | 2602.19520-calibration-decomposition.md:19-22 | HIGH | theta(d,tau,s) = mu(tau) + alpha_d + beta_d(tau) + gamma_d(s) + epsilon |
| Correction schedule | final-synthesis.md:99 | HIGH | "run 3+ (80% power at n=90/domain)" |
| Implementation approach | mcp-analysis.md:128-135 | HIGH | Deterministic calibration via MCP, persistent via CLAUDE_PLUGIN_DATA |

**Tool specifications from research-driven-redesign.md:253-276**:

1. `calibration_record_prediction(run_id, archetype_id, domain, horizon, prediction)` -- Stores prediction for future comparison
2. `calibration_record_outcome(run_id, actual_outcome)` -- Records outcome, triggers Brier computation
3. `calibration_get_domain_bias(domain, min_n=3)` -- Mean signed error per domain
4. `calibration_get_archetype_bias(archetype_id, domain=None, min_n=5)` -- Per-archetype bias
5. `calibration_get_ensemble_metrics(window=10)` -- Overall Brier, diversity, acquiescence rate

### 3.2 Debiasing Infrastructure

**Primary sources**:

| Source | File | Relevance | Key Data |
|--------|------|-----------|----------|
| Acquiescence bias quantification | 2402.19379-silicon-crowd.md:23 | CRITICAL | M=57.35, t(1006)=86.20, p<0.001 |
| Domain bias as calibration component | 2602.19520-calibration-decomposition.md:29 | HIGH | alpha_d = domain intercept, 14.6% R-squared |
| Domain-by-horizon interaction | 2602.19520-calibration-decomposition.md:30 | HIGH | beta_d(tau) = 26.0% R-squared |
| Correction constraint C-27 | feature-request.md:1142 | HIGH | "Track from run 1; corrections from run 3+" |
| Correction constraint C-28 | feature-request.md:1143 | HIGH | "Report both corrected AND uncorrected Brier" |
| Correction schedule | final-synthesis.md:99 | HIGH | Domain-level at run 3+, archetype-level needs n=50+ |
| Debiasing in aggregation | research-driven-redesign.md:237-247 | HIGH | amplify_aggregate(apply_debiasing=True) |
| Simple averaging beats updating | 2402.19379-silicon-crowd.md:37-40 | HIGH | GPT-4: p=0.011, Claude 2: p=0.001 |

**Correction protocol (from research synthesis, cross-referenced)**:

- Runs 1-2: Record only. Accumulate domain-level acquiescence data.
- Run 3+: Apply additive domain-level corrections where n >= 90/domain and bias is detectable.
- Run 10+: Extend to archetype-level corrections (requires n >= 5/archetype/domain).
- Run 50+: Consider logistic recalibration (requires large samples for curve fitting).

### 3.3 Question Competence Classifier

**Primary sources**:

| Source | File | Relevance | Key Data |
|--------|------|-----------|----------|
| Constraint C-31 | feature-request.md:1146 | HIGH | "Question competence classifier before UNDERSTAND phase" |
| Design rationale | research-driven-redesign.md:102-115 | HIGH | Routes simple-binary to skip DELIBERATE |
| Competence risk | final-synthesis.md:65-66 | HIGH | "No competence boundary detection" |
| Spec audit warning | spec-audit.md:242-248 | CRITICAL | WARNING-05: "Competence classifier is underspecified" |

**The spec audit flagged (spec-audit.md:242-248) that the competence classifier has unresolved design questions**:
- What model/method performs classification? (LLM call? rule-based?)
- What is the domain taxonomy? (how many categories? what defines "in-domain"?)
- How is archetype relevance assessed BEFORE archetypes are generated?
- What does "base-rate-only" mode mean for out-of-domain questions?

### 3.4 Baseline Amplification (A/B Test Infrastructure)

**Primary sources**:

| Source | File | Relevance | Key Data |
|--------|------|-----------|----------|
| Constraint C-26 | feature-request.md:1141 | HIGH | "Run baseline amplification BEFORE deliberation every run" |
| State machine phase | feature-request.md:1128 | HIGH | C-07: 7 phases including BASELINE_AMPLIFY |
| Baseline tool spec | research-driven-redesign.md:228-236 | HIGH | amplify_baseline() tool signature |
| Evidence: averaging beats updating | 2402.19379-silicon-crowd.md:37-40 | CRITICAL | Simple avg beats LLM updating at p=0.011 |
| Stateless constraint | feature-request.md:1169 | HIGH | C-21: baseline calls are fully stateless |
| Success criteria SC-13 | feature-request.md:115 | HIGH | "Deliberation outperforms baseline on multi-factor questions" |

### 3.5 Holdout Validation Set

**Primary sources**:

| Source | File | Relevance | Key Data |
|--------|------|-----------|----------|
| Constraint C-34 | feature-request.md:1149 | HIGH | "Holdout 20% of resolved predictions from calibration feedback" |
| Overfitting risk | final-synthesis.md:85-86 | HIGH | "Calibration-persona overfitting feedback loop" |
| Never-do boundary | feature-request.md:356 | HIGH | "NEVER feed calibration corrections from holdout set back into correction model" |
| Implementation hint | mcp-analysis.md:134 | MEDIUM | "Every 5th resolved prediction flagged as holdout" |

### 3.6 ForecastBench Submission Pipeline

**Primary sources**:

| Source | File | Relevance | Key Data |
|--------|------|-----------|----------|
| Constraint C-35 | feature-request.md:1150 | HIGH | "Submit to ForecastBench before making public accuracy claims" |
| Brier thresholds | 2409.19839-forecastbench.md:19-25 | HIGH | Superforecasters 0.096, o3 (best LLM) 0.1352, human crowd 0.149 |
| Success criteria SC-11 | feature-request.md:113 | HIGH | "Target Brier < 0.122 within first 3 runs" |
| Feature-request target | final-synthesis.md:59 | HIGH | "below 0.122 = architecture adds value, below 0.10 = genuinely novel" |

### 3.7 Short-Horizon Bootstrap Questions

**Primary sources**:

| Source | File | Relevance | Key Data |
|--------|------|-----------|----------|
| Resolution latency risk A-09 | feature-request.md:1232 | HIGH | "3-12 months for primary questions" |
| Mitigation | research-driven-redesign.md:428 | HIGH | "Short-horizon bootstrap questions (1-4 week resolution)" |
| Research warning | final-synthesis.md:105 | HIGH | "Resolution latency starves calibration for 6-12 months" |
| Scope item | feature-request.md:312 | HIGH | "Short-horizon bootstrap questions (1-4 week resolution for fast calibration data)" |

### 3.8 Data Volume Reality Check

**From research debate round 1** (round-1-ffa.md:116):
> "30 archetypes and perhaps 10-20 runs over the first year, that's 300-600 data points total -- before any stratification by domain or horizon."

**From calibration paper** (2602.19520-calibration-decomposition.md:63):
> "CRITICAL CHALLENGE: Paper uses 292M data points. OathFish will have ~300-600 predictions."

**From synthesis** (synthesis-report.md:61):
> "With 6 domains and 4 time horizons, most (archetype, domain, horizon) cells will have 0-1 observations."

**Implication**: Formal variance decomposition is impossible at OathFish's data scale. The design must use simpler statistical methods (directional bias tracking, mean signed error) that work at small n.

---

## Phase 3.5: Domain Taxonomy Gap

The spec-audit (spec-audit.md:226-228) flagged that "6 domains" is referenced in SC-14 but never defined. The calibration paper (2602.19520-calibration-decomposition.md:20) uses domain categories like Politics and Weather from prediction market data. OathFish handles arbitrary topics.

**Worker B must define**: The domain taxonomy for calibration tracking. This is a design decision that affects every calibration tool.

The calibration paper's domain structure from prediction markets suggests a starting taxonomy adapted for OathFish's use cases:

| Prediction Market Domain | OathFish Equivalent | Rationale |
|-------------------------|---------------------|-----------|
| Politics / Policy | POLICY | Regulation, government action, political outcomes |
| Finance / Economics | ECONOMICS | Markets, business, financial outcomes |
| Technology | TECHNOLOGY | Tech adoption, product launches, innovation |
| Science | SCIENCE | Scientific outcomes, medical trials |
| Weather / Environment | ENVIRONMENT | Climate, environmental, natural events |
| Sports / Entertainment | SOCIAL | Social dynamics, cultural shifts, consumer behavior |

This taxonomy must be auto-classified at prediction recording time by the MCP tool, not manually tagged.

---

## Phase 4: Framework Patterns

### MCP Server Patterns (from mcp-analysis.md)

| Pattern | Evidence | Relevance |
|---------|----------|-----------|
| stdio transport for local process | mcp-analysis.md:49 | Direct -- calibration engine runs as part of MCP stdio server |
| CLAUDE_PLUGIN_DATA for persistent state | mcp-analysis.md:53, 128-135 | CRITICAL -- calibration history must survive plugin updates |
| Write-through caching | mcp-analysis.md:92 | Direct -- every calibration mutation flushes to disk |
| 25,000 token output limit | mcp-analysis.md:31, 59 | Constraint on calibration_get_ensemble_metrics output |
| Deterministic computation boundary | mcp-analysis.md:96-100 | CRITICAL -- calibration corrections must be deterministic (no LLM in correction loop) |

### Statistical Methodology

All formulas from research papers, to be implemented in MCP server:

**Brier Score** (2402.19379-silicon-crowd.md:13):
```
BS = (1/N) * SUM(f_i - o_i)^2
```
Where f_i = forecast probability, o_i = binary outcome (0 or 1). Lower is better. Range [0, 1].

**Mean Signed Error** (2602.19520-calibration-decomposition.md, implied):
```
MSE_d = (1/N_d) * SUM(f_i - o_i) for all i in domain d
```
Positive MSE = overconfident (predicted too high). Negative = underconfident.

**Acquiescence Rate** (2402.19379-silicon-crowd.md:23):
```
ACQ = mean(f_i) across all predictions
```
If ACQ > 0.50, ensemble exhibits positive acquiescence. Paper found M=57.35% (t(1006)=86.20, p<0.001).

**Additive Domain Correction** (simplified from 2602.19520-calibration-decomposition.md:14-22):
```
f_corrected_i = f_i - alpha_d
```
Where alpha_d = MSE_d computed from historical resolved predictions in domain d.

**Power Analysis Threshold** (2602.19520-calibration-decomposition.md:OathFish Relevance):
80% power to detect d=0.3 effect size requires n=90 per domain. At 30 archetypes/run, n=90 requires 3 runs (90/30 = 3).

---

## Phase 4.5: Configuration System Intelligence

### Calibration Data Persistence Configuration

| System | Config Location | Governs What |
|--------|-----------------|--------------|
| OATHFISH_DATA_DIR | .mcp.json env block (feature-request.md:1063) | Root for all persistent run and calibration data |
| CLAUDE_PLUGIN_DATA | MCP infrastructure variable (mcp-analysis.md:53) | Persistent state surviving plugin updates |
| Holdout partition ratio | Hardcoded 20% (C-34:1149) | Proportion of resolved predictions excluded from correction model |
| Correction activation threshold | Run 3+ (C-27:1142) | When domain corrections begin |
| Domain taxonomy | Not yet configured (spec-audit.md:228) | How topics map to calibration domains |

**Handoff to Explore**: Flag for H-CFG hazard analysis:
- OATHFISH_DATA_DIR currently points to CLAUDE_PLUGIN_ROOT (wrong per mcp-analysis.md:53)
- Domain taxonomy is undefined
- Correction activation threshold is a static rule but may need dynamic adjustment
- Holdout partition ratio is fixed at 20% but at small n this reduces already-sparse training data

### Correction Schedule Configuration

The correction schedule is a cascading system of increasingly aggressive corrections:

| Run Range | Correction Level | Min n per Cell | Activation |
|-----------|-----------------|----------------|------------|
| 1-2 | Record only | 0 | Always |
| 3-9 | Domain additive | 90/domain | Auto when n threshold met |
| 10-49 | Archetype-within-domain | 5/archetype/domain | Auto when n threshold met |
| 50+ | Logistic recalibration | 50+ total per domain | Manual review recommended |

This schedule needs to be configurable but with safe defaults.

---

## Phase 5: Initial Observations

### Observation 1: The "6 Domains" Gap is Critical

SC-14 (feature-request.md:116) targets "2/6 domains show significant directional bias" but the domain taxonomy is never defined. Every calibration tool depends on domain classification. This is not a nice-to-have -- it is the primary organizational dimension for the entire calibration engine.

### Observation 2: Greenfield Advantage and Risk

No code exists. This means Worker B can design the calibration engine from scratch with optimal data structures, but there are no existing patterns to follow or break. Every Pydantic model, persistence format, and statistical computation is new.

### Observation 3: Data Volume is the Dominant Constraint

The calibration paper used 292 million data points (2602.19520-calibration-decomposition.md:7). OathFish will have 300-600 predictions after a year (round-1-ffa.md:116). The 4-component decomposition model is aspirational, not achievable at launch. The design must be robust at small n (n=30 per run, n=90 per domain after 3 runs).

### Observation 4: Dual Purpose of Calibration Data

Calibration data serves two distinct purposes that must not contaminate each other:
1. **Correction model training** -- feeds back into future predictions (80% of resolved data)
2. **Holdout validation** -- detects overfitting (20% of resolved data, never fed back per C-34/feature-request.md:356)

### Observation 5: ForecastBench is the External Anchor

Without ForecastBench submission (C-35), all calibration metrics are self-referential. The pipeline must produce predictions in ForecastBench-compatible format. The paper (2409.19839-forecastbench.md:5) describes a dynamic benchmark with ~1,000 questions, no data leakage, and a public leaderboard.

### Observation 6: Competence Classifier Runs Before Archetypes Exist

The spec-audit (spec-audit.md:247) flags a timing paradox: C-31 requires assessing "archetype set's domain-relevant perspectives" before UNDERSTAND, but archetypes are generated IN the UNDERSTAND phase. The classifier must work with topic metadata alone, not archetype information.

---

## Handoff to Explore

### Priority 1: Calibration Engine Architecture
Design 5 MCP tools with complete Pydantic models, persistence format, and statistical methodology. Define the domain taxonomy. Specify the correction schedule with precise activation conditions and formulas.

### Priority 2: Debiasing Infrastructure
Design the per-domain acquiescence correction algorithm. Define how corrections integrate into amplify_aggregate(). Specify dual-metric reporting format (C-28).

### Priority 3: Question Competence Classifier
Resolve the timing paradox (runs before archetypes exist). Define classification method, domain taxonomy mapping, routing rules, and "base-rate-only" fallback mode.

### Priority 4: Holdout Validation and Overfitting Detection
Design the holdout partition mechanism. Define overfitting detection criteria. Specify never-feed-back invariant enforcement.

### Priority 5: ForecastBench Pipeline and Bootstrap Questions
Design the submission pipeline. Define short-horizon bootstrap question management. Address resolution latency risk.

---
