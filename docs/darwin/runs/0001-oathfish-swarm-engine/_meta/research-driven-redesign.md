# Research-Driven Feature Request Redesign

## Scope

This document critically reviews every element of `feature-request.md` against evidence from 5 research papers (debated across 3 adversarial rounds by 5 paper agents), 6 Claude Code documentation pages, and the comprehensive MiroFish deep dive. Each section either **SUPPORTS**, **REFUTES**, or **REDESIGNS** a specific feature request element, with cited reasoning.

---

## 1. Intent & Vision (feature-request.md §1)

### §1.1 Problem Statement — SUPPORT with revision

**Current claim**: "The 10x outcome is a TWO-LAYER system: deep deliberation + mass amplification"

**Research verdict**: SUPPORTED but the mechanism is narrower than claimed.

- The ensemble paper (2402.19379) validates that LLM ensembles match human crowd accuracy (Brier 0.20 vs 0.19, p=0.850). The two-layer architecture IS the right structure.
- BUT the debate paper (2305.14325) shows debate improves reasoning tasks 8-15pp while the ensemble paper shows deliberative UPDATING degrades forecasting accuracy (GPT-4: p=0.011; Claude 2: p=0.001).
- The debate team's Round 2 evolution resolved this: **deliberation's value is conditional on question complexity**. Multi-factor questions benefit; simple binary questions may not.

**REDESIGN**: Revise §1.1 to honestly state: "The deep layer adds value specifically on multi-stakeholder, multi-factor prediction questions where joint-probability reasoning across perspectives produces insights that independent predictions cannot. For simple binary forecasts, the mass layer alone may suffice."

**Citation**: paper-debate Round 2 H1 (correlated error regimes); paper-forecast Round 2 H2 (combination questions); paper-ensemble Round 3 final (task-type dependent value).

### §1.2 Why Two Layers — SUPPORT

**Current claim**: Table comparing deep vs mass layers

**Research verdict**: VALIDATED. The calibration paper (2602.19520) independently confirms that different prediction mechanisms have different error structures (markets compress toward 50%, LLMs shift toward positive). The two-layer design creates complementary error structures that can partially cancel.

**Citation**: paper-calibration Round 2 H2 (complementary error structure); paper-ensemble Round 3 (acquiescence is correctable).

### §1.3 Target Users — REDESIGN

**Current claim**: Startup founders, researchers, strategists, VCs, policymakers, general users

**Research verdict**: NEEDS HONESTY about what OathFish actually delivers.

The persona paper (2411.10109) showed 85% fidelity WITH real interview data; OathFish uses synthetic archetypes with unknown fidelity. The forecaster paper (2409.19839) showed LLMs significantly underperform superforecasters (p<0.001). Paper-forecast and paper-persona converged on an honest reframing in Round 3.

**REDESIGN**: OathFish should position as: **"Structured ensemble estimates from archetypal stakeholder perspectives, calibrated against resolved outcomes over time."** NOT "predictions of how real populations will respond." The stronger claim is earned through calibration data over many runs, not assumed at launch.

**Citation**: paper-forecast + paper-persona Round 3 convergence on honest framing.

### §1.4 Success Criteria — REDESIGN

**Current SC-02**: "6+ rounds with 30 archetypes showing measurable position evolution"

**REFUTED as written**. The debate paper (2305.14325) warns that convergence can be false consensus: "debates typically converged into single final answers [that] were not necessarily correct." Position evolution (stance changes) is NOT evidence of accuracy improvement. An archetype that changes its mind 5 times and ends wrong has "evolved" but not improved.

**REDESIGN SC-02**: "6+ rounds with diversity index tracked per round. Final diversity > 0 (NOT full convergence). A/B comparison showing deliberated predictions outperform baseline median on at least one question type."

**NEW SC-11**: "Submit 100+ predictions to ForecastBench. Achieve Brier < 0.122 (beating best individual LLM) within first 3 runs."

**NEW SC-12**: "After 5 runs, domain-level acquiescence correction measurably improves Brier scores (>= 0.01 absolute improvement)."

**Citation**: paper-debate Round 3 (convergence is not success); paper-forecast Round 3 (ForecastBench benchmark); paper-calibration Round 3 (domain correction feasibility).

---

## 2. Architecture (feature-request.md §2)

### §2.1 Phase 2: DELIBERATE — MAJOR REDESIGN

**Current design**: 6 rounds exchanging full positions (stance, confidence, key arguments, concerns, influenced_by). Numbers shared throughout.

**REFUTED by research**. This is the single most important redesign.

Paper-debate's Round 3 final statement identified the core architectural insight: **separate arguments from predictions**. The ensemble paper proved that when LLMs see others' numeric predictions, they anchor-and-adjust badly (p=0.011). The debate paper proved that slower convergence (stubborn prompts) produces better outcomes.

**REDESIGN**:

```
Rounds 1-2 (FREE_FORM): Exchange qualitative arguments ONLY
  - No stance numbers, no confidence numbers
  - Share reasoning, concerns, scenarios, evidence
  - Archetypes respond with INTERNAL MONOLOGUE + POSITION TEXT only

Rounds 3-4 (STRUCTURED_DEBATE): Adversarial argument exchange
  - Pairs challenge each other's REASONING, not numbers
  - Must address opponent's strongest argument
  - "Structured stubbornness" — each archetype stubborn on their domain expertise

Round 5 (SCENARIO_INJECTION): Stress test reasoning
  - Inject counterfactual scenarios
  - Each archetype reasons about second-order effects
  - Still NO numbers exchanged

Round 6 (INDEPENDENT PREDICTION): Silent structured JSON
  - Each archetype INDEPENDENTLY produces structured prediction
  - No visibility into others' numbers
  - --json-schema enforced: {prediction, decision, confidence,
    base_rate_anchor, timeframe, key_uncertainties,
    falsification_criteria, second_order_effects}
  - Aggregate via median
```

**Rationale**: This design respects BOTH the debate paper (deliberation improves reasoning quality) AND the ensemble paper (independent prediction aggregation beats social updating). Arguments without numbers until the final round is the optimal architecture.

**Citation**: paper-debate Round 3 §1 (most architecturally actionable recommendation, scored 34/40); paper-ensemble Round 2 concession + H1 evolution; final-synthesis.md Tier 1 recommendation #2.

### §2.1 NEW: Question Routing (pre-UNDERSTAND)

**Not in current feature request.**

Paper-forecast identified that deliberation's highest-value target is **combination questions** requiring joint-probability reasoning. Paper-ensemble agreed that deliberation hurts on simple binary questions. Both converged on question routing.

**ADD**: A competence classifier before UNDERSTAND that:
1. Classifies incoming question as simple-binary vs multi-factor
2. Assesses whether the archetype set has domain-relevant perspectives
3. Routes simple-binary → direct AMPLIFY (skip DELIBERATE)
4. Routes multi-factor → full DELIBERATE pipeline
5. Flags out-of-domain questions as "low-confidence, outside core competence"

**Citation**: paper-forecast Round 2 H2 (combination questions); paper-forecast Round 3 §4 (competence boundary detection, highest-scoring risk); paper-ensemble Round 3 §2 (deliberation hurts simple binaries).

### §2.1 Phase 3: AMPLIFY — REDESIGN

**Current design**: `amplify.sh` bash script with `xargs -P`, free-text responses

**REFUTED as implementation** (not concept). The Claude Code headless docs (references/headless-agent-sdk.md) reveal capabilities the current design ignores:

1. `--json-schema` guarantees structured output — eliminates free-text parsing entirely
2. `--resume SESSION_ID` carries deliberation context into amplification calls
3. `--system-prompt` + `--append-system-prompt` separates archetype identity from variation delta
4. Python SDK provides async/await, structured output via Pydantic, retry logic

**REDESIGN**:
- Replace `amplify.sh` bash with Python SDK async engine
- Every amplification call uses `--json-schema` for guaranteed structured responses
- Use `--system-prompt` for archetype identity, `--append-system-prompt` for variation delta
- Consider `--resume SESSION_ID` from deliberation (carries context without re-prompting)
- Semaphore-based rate limiting, exponential backoff retry, progress callbacks

**Citation**: references/headless-agent-sdk.md §§1-5; paper-ensemble analysis (structured output eliminates parsing); v3 plan §Architecture.

### §2.2 What We DON'T Build — PARTIAL REFUTATION

**Current claim**: "Simpler JSON graph" instead of Zep knowledge graph

**CHALLENGED by MiroFish deep dive**. The MiroFish exploration revealed that Zep's temporal fact tracking (`valid_at`/`invalid_at`) enables "past truth ≠ present truth" modeling. The report agent's InsightForge tool auto-decomposes queries into sub-questions and runs parallel semantic search. PanoramaSearch shows how positions/facts expired over time.

OathFish's "simpler JSON graph" loses:
- Temporal fact modeling (when did a position become valid/invalid?)
- Multi-dimensional retrieval (InsightForge-style decomposition)
- Historical fact tracking (how has the graph evolved?)

**REDESIGN**: Keep JSON-based persistence (no Zep dependency) but ADD:
- `valid_at`/`invalid_at` fields on graph edges for temporal tracking
- A `graph_decompose_query(query)` MCP tool that breaks complex queries into sub-questions and runs parallel searches (InsightForge pattern)
- Position timeline visualization in synthesis output

**Citation**: MiroFish deep dive agent 2 (InsightForge, PanoramaSearch, temporal facts); paper-persona Round 2 H2 (calibration + temporal tracking).

### §2.3 Deterministic vs Creative Split — SUPPORT

**Research verdict**: VALIDATED. The calibration paper's 4-component decomposition model is deterministic math. The debate paper's reasoning improvement is creative. The split is correct.

One nuance from WARNING-03 in spec-audit.md: hybrid sentiment's 0.3 LLM component introduces non-determinism into what should be deterministic metrics. The spec audit already flagged this. Research reinforces it.

**Citation**: spec-audit.md WARNING-03; paper-calibration Round 2 (statistical rigor requires deterministic metrics).

---

## 3. Scope & Boundaries (feature-request.md §3)

### §3.1 In Scope — ADD items

**Missing from current scope** (research-mandated additions):

1. **Debiasing engine** — Per-domain acquiescence tracking and additive correction. Paper-ensemble showed 57% positive prediction rate (p<0.001). Paper-calibration showed domain-level bias detectable at n=90 (3 runs). This is the #1 known error source and the cheapest fix.

2. **A/B test infrastructure** — Run amplification BEFORE and AFTER deliberation every run. Compare. This is non-negotiable per the synthesis consensus.

3. **Diversity index tracking** — Per-round diversity metric (std dev of archetype predictions). Paper-debate showed early convergence = failure mode.

4. **Competence classifier** — Pre-UNDERSTAND gate. Paper-forecast's highest-scoring risk.

5. **Calibration MCP tools** — `calibration_record_prediction()`, `calibration_record_outcome()`, `calibration_get_domain_bias()`, `calibration_get_archetype_bias()`

6. **Short-horizon bootstrap questions** — Include fast-resolving questions (1-4 week) for early calibration data. Paper-calibration's resolution latency risk.

7. **Holdout validation set** — Reserve 20% of resolved predictions from calibration loop. Paper-persona's overfitting risk.

**Citation**: final-synthesis.md ranked recommendations; paper-calibration Round 3 (resolution latency); paper-persona Round 3 (overfitting risk).

### §3.3 Boundary Definitions — REDESIGN

**Current "Never Do"**: "Skip the DELIBERATE phase (it's the core differentiator)"

**REFUTED**. The research debate reached consensus that deliberation's value is question-type-dependent. Skipping DELIBERATE on simple binary questions may IMPROVE accuracy.

**REDESIGN "Never Do"**: "Skip the DELIBERATE phase on multi-factor questions" (changed from blanket prohibition to conditional)

**ADD "Always Do"**:
- "Run baseline amplification before deliberation for A/B comparison"
- "Track per-domain acquiescence rates from run 1"
- "Report both calibration-corrected and raw uncorrected Brier scores"
- "Ground each archetype in 3-5 real public sources before production"

**Citation**: paper-ensemble Round 2 H1 (task-type dependency); paper-persona Round 3 §1 (dual metrics); paper-persona Round 2 H1 (grounding ladder).

---

## 4. Component Design (feature-request.md §4)

### §4.1.2 Deliberation Engine — REDESIGN

**Current `deliberation_check_convergence`**: "avg stance delta < 0.1 for window_size consecutive rounds → CONVERGE"

**REFUTED**. Convergence-as-success is wrong per all 5 paper agents' consensus.

**REDESIGN**: Replace with diversity-tracking convergence:
```
deliberation_check_diversity(round_n)
  → Computes std dev of archetype stances (diversity index)
  → Tracks trajectory: diversity SHOULD decrease but not collapse
  → If diversity drops below 0.15 before penultimate round:
    → Returns { warning: "PREMATURE_CONSENSUS", trigger: "INJECT_CONTRARIAN" }
  → If diversity stable at round 6+:
    → Returns { status: "HEALTHY_CONVERGENCE" }
  → Output: { diversity_index, trajectory, recommendation }
```

**Citation**: paper-debate Round 3 §3 (convergence is NOT success); paper-ensemble Round 2 (acquiescence drives false convergence); final-synthesis.md recommendation #5 (diversity-preserving deliberation).

### §4.1.4 Amplification Engine — REDESIGN

**ADD new tool**:
```
amplify_baseline(archetypes, variations_per, model, scenario)
  → Runs BEFORE deliberation as A/B baseline
  → Same parameters, same archetypes, but with initial (pre-deliberation) stances
  → Output stored separately for comparison
```

**REDESIGN `amplify_aggregate()`**: Add debiasing step:
```
amplify_aggregate(apply_debiasing=True)
  → If calibration data exists (run >= 3):
    → Load domain-level bias corrections
    → Apply additive correction per domain
  → Report BOTH raw and debiased distributions
  → Output: { raw: {...}, debiased: {...}, corrections_applied: [...] }
```

**Citation**: final-synthesis.md recommendation #1 (A/B test); paper-calibration Round 2 H1 (domain-level corrections at n=3).

### §4.1 NEW: Calibration Engine (~5 tools)

**Not in current feature request.** Research mandates this.

```
calibration_record_prediction(run_id, archetype_id, domain, horizon, prediction)
  → Stores structured prediction for future outcome comparison
  → Fields: decision, confidence, timeframe, base_rate_anchor

calibration_record_outcome(run_id, actual_outcome)
  → Records what actually happened
  → Triggers Brier score computation for all predictions in that run

calibration_get_domain_bias(domain, min_n=3)
  → Returns mean signed error for domain (positive = overconfident)
  → Only returns if n >= min_n observations
  → Output: { domain, mse, direction, n, p_value, correction }

calibration_get_archetype_bias(archetype_id, domain=None, min_n=5)
  → Returns per-archetype directional bias, optionally filtered by domain
  → Output: { archetype, mse, direction, n, domains: [...] }

calibration_get_ensemble_metrics(window=10)
  → Returns overall ensemble Brier, effective diversity, acquiescence rate
  → Compares corrected vs uncorrected accuracy
  → Output: { brier_raw, brier_corrected, gap, acquiescence_rate,
              effective_diversity, n_predictions, n_resolved }
```

**Citation**: paper-calibration Round 2 H1 (domain-level tracking at n=3); paper-persona Round 3 (corrected vs uncorrected gap); paper-ensemble Round 3 (acquiescence rate tracking).

### §4.2.2 archetype-agent — MAJOR REDESIGN

**Current design**: Template instantiated 30 times as Team members with Read + SendMessage.

**REFUTED as architecture** (not concept). The Claude Code subagent docs reveal that subagents with `memory: project` provide persistent cross-session learning. Team members don't have this.

**REDESIGN**: Archetypes as persistent subagents:

```yaml
name: archetype-{id}
description: "Embodies {segment} perspective with persistent memory"
memory: project           # Cross-run learning
model: opus|sonnet|haiku  # Tiered by archetype centrality
maxTurns: 3-5            # Varies by round type
skills:
  - oathfish:archetype-reasoning  # Uniform superforecaster methodology
hooks:
  PreToolUse:
    - matcher: "SendMessage"
      hooks:
        - type: command
          command: "validate-position-coherence.sh"
```

**Key additions from research**:
1. **Superforecaster methodology in every archetype** (paper-forecast Round 3 recommendation #4, scored 34/40): Every archetype prompt includes mandatory forecasting protocol — state base rate, decompose into sub-components, list uncertainties, state falsification criteria. Stakeholder perspective provides INPUTS; superforecaster methodology provides REASONING METHOD.

2. **Grounding in real public sources** (paper-persona Round 3 recommendation, scored 33/40): Before production, each archetype grounded in 3-5 curated real-world sources (interviews, blog posts, hearing transcripts). This is Rung 2 of the grounding ladder.

3. **Structured stubbornness** (paper-debate Round 2 H2): Each archetype stubborn on their domain expertise. The Cautious VC resists on downside risks; the Tech Optimist resists on adoption curves. Creates diversity-preserving debate.

4. **No numbers until Round 6** (paper-debate Round 3): Archetypes exchange arguments only (rounds 1-5), then produce independent structured predictions (round 6).

**Citation**: references/sub-agents.md (memory, hooks, model override); paper-forecast Round 3 §1 (superforecaster encoding, 34/40); paper-persona Round 3 §1 (grounding ladder, 33/40); paper-debate Round 2 H2 (structured stubbornness).

### §4.2.1 deliberation-coordinator — REDESIGN

**ADD**: Diversity monitoring responsibility

The coordinator must track diversity index per round and trigger contrarian injection if premature consensus detected. This is a new responsibility not in the current spec.

Also: the coordinator routes simple-binary questions to skip deliberation (question routing).

**Citation**: paper-ensemble Round 2 (acquiescence monitoring); paper-debate Round 3 (diversity > convergence).

### §4.2.3 report-analyst — ADD calibration reporting

**Current design**: Produces report.md, reasoning-chains.md, statistics.md

**ADD**:
- `calibration.md` — Per-archetype and per-domain accuracy metrics (after outcomes resolve)
- `diversity-trajectory.md` — How prediction diversity evolved across rounds (quality indicator)
- Corrected vs uncorrected Brier scores in all quantitative outputs

**Citation**: paper-persona Round 3 (dual-metric reporting); paper-calibration Round 3 (domain bias reporting).

---

## 5. Constraints (feature-request.md §6)

### C-04 — REDESIGN

**Current**: "Deep deliberation uses Claude Teams with 30 archetype agents communicating via SendMessage"

**REDESIGN**: "Deep deliberation uses Claude Teams for coordination. Archetypes are persistent subagents with memory:project for cross-run learning. Coordinator + archetype subagents communicate via SendMessage. Arguments exchanged rounds 1-5; independent structured predictions in round 6."

### C-10 — REDESIGN

**Current**: "4 deliberation round types: FREE_FORM, STRUCTURED_DEBATE, SCENARIO_REACTION, PREDICTION"

**ADD**: INDEPENDENT_PREDICTION as a distinct type — silent, no-sharing, JSON-schema-enforced structured output.

### NEW CONSTRAINTS

| C-ID | Type | Constraint |
|------|------|------------|
| C-26 | REQUIREMENT | A/B test: run baseline amplification before deliberation every run |
| C-27 | REQUIREMENT | Track per-domain acquiescence rate from run 1 |
| C-28 | REQUIREMENT | Report both calibration-corrected and raw uncorrected metrics |
| C-29 | REQUIREMENT | Ground each archetype in 3-5 real public sources |
| C-30 | REQUIREMENT | Superforecaster methodology encoded in every archetype prompt |
| C-31 | REQUIREMENT | Question competence classifier before UNDERSTAND phase |
| C-32 | REQUIREMENT | Diversity index tracked per deliberation round |
| C-33 | REQUIREMENT | No numeric predictions shared between archetypes until final round |
| C-34 | REQUIREMENT | Holdout 20% of resolved predictions from calibration feedback |
| C-35 | REQUIREMENT | Submit to ForecastBench before making public accuracy claims |

**Citation**: final-synthesis.md Tier 1-3 recommendations; all 5 paper agents' Round 3 finals.

---

## 6. Assumptions (feature-request.md §8)

### A-04 — REFUTED

**Current**: "Archetype agents will genuinely reason and evolve positions (not just repeat their initial stance)"

**Research says**: They will evolve, but evolution ≠ accuracy. The debate paper warns of confident false consensus. The ensemble paper warns of acquiescence bias pulling all positions toward agreement. Evolution is measurable; improvement is not (until outcomes resolve).

**REDESIGN A-04**: "Archetype agents will evolve positions, but evolution may be driven by acquiescence bias rather than genuine insight. Position evolution is a necessary but insufficient condition for prediction quality. A/B testing against baseline aggregation is required to verify deliberation adds value."

### NEW ASSUMPTIONS

| A-ID | Assumption | Risk if Wrong |
|------|-----------|---------------|
| A-06 | Synthetic archetypes provide enough diversity for meaningful ensemble (inter-archetype correlation < 0.8) | If correlation > 0.8, effective ensemble size is ~3-5, not 30. Architecture provides no statistical advantage. |
| A-07 | Domain-level acquiescence correction is achievable at n=90 per domain (3 runs) | If acquiescence is not structured by domain, correction requires orders of magnitude more data |
| A-08 | Superforecaster methodology encoded in prompts transfers to LLM reasoning | If encoded methodology is superficial (LLMs generate decompositions without genuine analytical depth), the technique adds token cost without accuracy |
| A-09 | Outcome resolution latency (3-12 months) won't starve calibration loop | If most predictions are long-horizon, calibration feedback is delayed 6-12 months. Year 1 has zero calibration data. |

**Citation**: paper-ensemble Round 3 §4 (correlation risk); paper-calibration Round 2 H1 (n=90 power analysis); paper-forecast Round 3 §2 (methodology transfer); paper-calibration Round 3 §4 (resolution latency).

---

## 7. Spec Audit Warnings — Updated

### WARNING-01 (Teams Scale at 20+) — NOW MITIGATED

Moving archetypes to persistent subagents (not all Team members) reduces Team size. Coordinator in Team; archetypes as subagents spawned per round. This sidesteps the 32-member limit entirely.

**Citation**: references/sub-agents.md (subagent architecture); references/agent-teams.md (team limitations).

### WARNING-05 (NEW): Deliberation May Destroy Value

**Severity**: CRITICAL
**Source**: paper-ensemble Round 1 H2, evolved through 3 rounds of debate
**Evidence**: Simple averaging beats LLM updating (p=0.011 GPT-4, p=0.001 Claude 2)
**Mitigation**: A/B test infrastructure (C-26). Arguments-only deliberation (C-33).

### WARNING-06 (NEW): Acquiescence Bias

**Severity**: HIGH
**Source**: paper-ensemble (57% positive predictions, p<0.001)
**Evidence**: Systematic, cross-model, quantified
**Mitigation**: Per-domain acquiescence tracking (C-27). Structured stubbornness in archetype design.

### WARNING-07 (NEW): Single-Model Correlated Failures

**Severity**: HIGH
**Source**: paper-ensemble Round 3 §4
**Evidence**: 30 Claude instances share training data and RLHF objectives
**Mitigation**: Monitor inter-archetype correlation. Consider multi-model archetypes in future.

### WARNING-08 (NEW): Calibration Resolution Latency

**Severity**: HIGH
**Source**: paper-calibration Round 3 §4
**Evidence**: Most target questions resolve in 3-12 months. Calibration loop is starved for year 1.
**Mitigation**: Include short-horizon bootstrap questions (1-4 week resolution) in every run.

---

## 8. Implementation Sequence — REDESIGN

### Phase 0 (NEW): Foundations
- Calibration engine (5 MCP tools)
- Debiasing infrastructure in amplification engine
- Question competence classifier
- A/B test infrastructure (baseline amplification before deliberation)
- Archetype grounding protocol (Rung 2: curate 3-5 public sources per archetype)

### Phase 1: MCP Server (UPDATED)
- Original 20 tools + 5 calibration tools + `deliberation_check_diversity` + `amplify_baseline`
- ~28 tools total

### Phase 2: Plugin Scaffold (unchanged)

### Phase 3: UNDERSTAND (UPDATED)
- Add question competence classifier
- Add superforecaster methodology to archetype prompt template
- Add grounding requirement (3-5 public sources per archetype)

### Phase 4: DELIBERATE (MAJOR UPDATE)
- Arguments-only rounds 1-5 (no numbers)
- Independent prediction round 6 (JSON schema enforced)
- Diversity index tracking per round
- Premature consensus detection and contrarian injection
- Structured stubbornness per archetype

### Phase 5: AMPLIFY (MAJOR UPDATE)
- Python SDK replaces bash script
- `--json-schema` for guaranteed structured output
- Baseline amplification run before deliberation (A/B)
- Debiasing applied in aggregation
- Dual metrics: raw + corrected

### Phase 6: SYNTHESIZE + INTERACT + CALIBRATE (UPDATED)
- Report includes calibration metrics, diversity trajectory
- New `/oathfish-calibrate` command for recording outcomes
- Holdout validation set (20%)

---

## Summary: What Changes

| Element | Before (v2) | After (v3 research-grounded) | Evidence |
|---------|-------------|------------------------------|----------|
| Deliberation | Numbers shared all rounds | Arguments rounds 1-5, independent prediction round 6 | 2305.14325 + 2402.19379 |
| Convergence | "stance delta < 0.1 = success" | Diversity tracking, premature consensus = failure | 2305.14325 (false consensus) |
| Question routing | All questions through full pipeline | Simple → skip deliberation; multi-factor → full pipeline | 2409.19839 + 2402.19379 |
| Amplification | Bash script, free-text | Python SDK, --json-schema, --resume, debiased | Claude Code docs |
| Archetypes | Team members, session-only | Persistent subagents with memory:project | Claude Code docs |
| Archetype prompts | Persona + reasoning rules | + Superforecaster methodology + grounding in real sources | 2409.19839 + 2411.10109 |
| Calibration | Not in spec | 5 MCP tools, domain-level bias tracking, holdout set | 2602.19520 + 2402.19379 |
| Debiasing | Not in spec | Per-domain acquiescence correction from run 3+ | 2402.19379 + 2602.19520 |
| A/B testing | Not in spec | Baseline amplification before deliberation every run | 2402.19379 (p=0.011) |
| Validation | Not in spec | ForecastBench submission, Brier < 0.122 target | 2409.19839 |
| Positioning | "Predict how populations respond" | "Structured ensemble estimates, calibrated over time" | All 5 papers |
| Success metric | Position evolution | A/B improvement + ForecastBench score + diversity preservation | Debate consensus |
| MCP tools | ~20 | ~28 (+ calibration, diversity, baseline, debiasing) | Research additions |
| Constraints | 25 | 35 (+ 10 research-mandated) | All 5 papers |
