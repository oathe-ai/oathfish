---
spec_version: "3.0"
run_id: "0001-oathfish-swarm-engine"
feature: "OathFish: Claude-Native Predictive Intelligence Engine"
created_at: "2026-03-17T20:00:00Z"
revised_at: "2026-03-18T16:00:00Z"
status: "UNDER_REVIEW"
blocked_by: []

constraint_count: 37
contradiction_count: 0
ambiguity_count: 0
assumption_count: 9

research_grounding:
  papers:
    - "2305.14325 — Improving Factuality and Reasoning through Multiagent Debate"
    - "2402.19379 — Wisdom of the Silicon Crowd: LLM Ensemble Prediction"
    - "2409.19839 — ForecastBench: Can LLMs Forecast? (ICLR 2025)"
    - "2411.10109 — Generative Agent Simulations of 1,000 People (Stanford)"
    - "2602.19520 — Decomposing Crowd Wisdom: Calibration Dynamics in Prediction Markets"
  debate_rounds: 3
  debate_agents: 5
  synthesis: "docs/oathe/runs/run_20260318_140000/synthesis/final-synthesis.md"
  redesign: "docs/darwin/runs/0001-oathfish-swarm-engine/_meta/research-driven-redesign.md"

boundaries:
  always:
    - "Use Claude Teams for coordination; archetypes as persistent subagents with memory:project"
    - "Use claude -p with --json-schema for mass amplification (structured, parallel, cheap)"
    - "Persist state to disk after every mutation via MCP server"
    - "Compute aggregation metrics deterministically via MCP server"
    - "Customize archetypes per topic, grounded in 3-5 real public sources each"
    - "Separate deterministic work (MCP) from creative work (Claude)"
    - "Run baseline amplification BEFORE deliberation for A/B comparison every run"
    - "Track per-domain acquiescence rates and apply debiasing corrections from run 3+"
    - "Report BOTH calibration-corrected and raw uncorrected Brier scores"
    - "Exchange arguments only (no numbers) during deliberation rounds 1-5; independent predictions in round 6"
    - "Encode superforecaster methodology (decompose, base rate, falsify) in every archetype prompt"
    - "Track diversity index per deliberation round; flag premature consensus as failure"
  ask_first:
    - "Team size exceeding 30 archetypes: may hit Claude Teams limits"
    - "Mass amplification batch size > 1000: cost implications"
    - "Injecting events mid-deliberation: could disrupt convergence"
    - "Using opus model for mass amplification: expensive at scale"
    - "Skipping DELIBERATE phase on simple binary questions (may improve accuracy)"
  never:
    - "Let Claude agents compute aggregation metrics (deterministic work)"
    - "Use Teams for mass amplification (too expensive, use claude -p)"
    - "Skip DELIBERATE on multi-factor questions requiring joint-probability reasoning"
    - "Run without MCP server for state management"
    - "Let archetypes write to state files directly"
    - "Share numeric predictions between archetypes before final independent prediction round"
    - "Claim 'population prediction' — use 'structured ensemble estimates' until calibration validates"
    - "Skip ForecastBench submission before making public accuracy claims"
---

# Feature Specification: OathFish — Claude-Native Swarm Intelligence Engine

## 1. Intent & Vision

### 1.1 Problem Statement

> Predicting social dynamics — how researchers, enterprises, VCs, startups, and ordinary people will react to events, policies, or market shifts — currently requires either expensive focus groups, unreliable surveys, or gut instinct. MiroFish demonstrated that multi-agent simulation on social platforms can produce useful predictions, but it uses shallow agents (text-generation-level reasoning) at mass scale, locked to simulated Twitter/Reddit via OASIS.
>
> Claude Code offers something fundamentally different: **genuine multi-round reasoning between persistent persona agents**. A Claude Team member can form opinions, remember previous discussions, notice contradictions, change their mind, form coalitions, and produce genuine insights — not just generate tweets from a persona prompt.
>
> The 10x outcome is a **RESEARCH-GROUNDED TWO-LAYER system**:
> 1. **Deep Deliberation** via Claude Teams + persistent archetype subagents — 30 population archetype agents with genuine reasoning, cross-run memory, and superforecaster methodology. Arguments exchanged across 5 rounds; independent structured predictions in round 6. Value is CONDITIONAL: highest on multi-factor questions requiring joint-probability reasoning (arxiv 2409.19839), potentially harmful on simple binary forecasts where averaging suffices (arxiv 2402.19379).
> 2. **Mass Amplification** via `claude -p` with `--json-schema` enforcement — hundreds/thousands of structured persona variations for statistical breadth. Session continuity from deliberation via `--resume`. Domain-specific debiasing applied at aggregation.
>
> Together they produce **structured ensemble estimates from archetypal stakeholder perspectives** — combining qualitative depth (why each segment reasons as it does) with quantitative breadth (statistical distributions across persona variations), calibrated against resolved outcomes over time. The honest framing: these are "ensemble estimates calibrated over time," not "predictions of how real populations will respond." The stronger claim is earned through calibration data, not assumed at launch (consensus from 5-paper adversarial debate).

### 1.2 Why Two Layers?

| Capability | Deep Deliberation (Teams) | Mass Amplification (claude -p) |
|-----------|---------------------------|-------------------------------|
| **Agent reasoning** | Genuine multi-turn reasoning with memory | Stateless single-turn response |
| **Scale** | 30 agents (one per population segment) | 500-5000 agents (variations within segments) |
| **Cost per agent** | High (persistent Team member) | Low (single CLI call) |
| **Memory** | Full — remembers all previous rounds | None — fresh context each call |
| **Output type** | Reasoning chains, coalitions, surprising insights | Statistical distributions, adoption curves |
| **Model** | Opus/Sonnet (deep reasoning) | Haiku/Sonnet (fast, cheap) |
| **Purpose** | Understand WHY each segment reacts | Predict HOW MANY react each way |
| **Mechanism** | Claude Teams + SendMessage | `claude -p` CLI piped calls |
| **Unique to Claude** | YES — no other system does this | Achievable with any LLM API |

### 1.3 Target Users

| User Type | Description | Primary Need |
|-----------|-------------|--------------|
| Startup founders | Testing market positioning, finding wedge | Predict how different population segments react to their value proposition |
| Researchers | Studying social phenomena, opinion dynamics | Simulate how diverse archetypes reason about and respond to scenarios |
| Enterprise strategists | Planning product launches, policy changes | Rehearse outcomes with deep stakeholder reasoning before committing |
| VCs / Investors | Evaluating market dynamics, competitive landscapes | Understand how ecosystem segments think, not just what they'd tweet |
| Policy makers | Testing regulation, public health measures | See how different populations reason about and respond to policy |
| General users | Exploring "what if" scenarios | Get genuine multi-perspective analysis of any scenario |

### 1.4 Success Criteria

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| SC-01 | MCP server starts and responds to all tool calls | 100% of ~20 tools return valid JSON |
| SC-02 | Deep deliberation completes with diversity preservation | 6+ rounds with diversity index tracked per round. Final diversity > 0 (NOT full convergence). Arguments-only rounds 1-5, independent structured predictions round 6. Premature consensus triggers contrarian injection. [Research: 2305.14325 warns false consensus; 2402.19379 shows acquiescence drives premature agreement] |
| SC-03 | Archetypes produce genuine reasoning | Internal monologues show real analysis, not generic responses. Position changes are justified by prior discussion. Surprising cross-archetype insights emerge. |
| SC-04 | Mass amplification scales | 500+ `claude -p` calls complete, results aggregate into coherent distributions |
| SC-05 | Report combines depth + breadth | Report cites BOTH specific archetype reasoning chains AND statistical distributions from mass simulation |
| SC-06 | Archetypes are topic-customized | Running on "AI regulation" produces different archetypes than running on "healthcare reform" |
| SC-07 | State persistence and resume | Run can be interrupted at any phase and resumed from last checkpoint |
| SC-08 | Post-run interaction | User can chat with any of the 30 archetypes who respond in-character with memory of the full deliberation |
| SC-09 | Position evolution is trackable | MCP tools show how each archetype's position shifted round-by-round with specific reasoning |
| SC-10 | Coalition dynamics emerge | Report identifies which archetype segments align/oppose and why, with evidence from deliberation transcripts |
| SC-11 | External benchmark validation | Submit 100+ predictions to ForecastBench. Target Brier < 0.122 (beating best individual LLM) within first 3 runs. [Research: 2409.19839 — superforecasters 0.096, best LLM 0.122] |
| SC-12 | Debiasing measurably improves accuracy | After 5 runs, domain-level acquiescence correction improves ensemble Brier by >= 0.01 absolute vs uncorrected predictions. [Research: 2402.19379 — 57% acquiescence; 2602.19520 — domain bias detectable at n=90] |
| SC-13 | A/B test validates deliberation value | Deliberation-informed predictions outperform baseline median aggregation on at least one question type (multi-factor). Measured across first 5 runs. [Research: 2305.14325 — debate 81.8% vs majority 69.0%; 2402.19379 — updating may degrade] |
| SC-14 | Calibration tracking produces actionable corrections | After 5 runs, at least 2/6 domains show statistically significant (p<0.10) directional bias. Additive corrections applied. [Research: 2602.19520 — 80% power at n=90 for d=0.3] |

---

## 2. Architecture

### 2.1 Two-Layer System Overview

```
User
  │
  ▼
/oathfish "How will AI regulation affect the startup ecosystem?"
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│ Phase 1: UNDERSTAND                                            │
│   Single Claude call analyzes topic → identifies ~30 relevant  │
│   population segments → generates archetype personas            │
│   Output: archetypes.json + topic-analysis.md                  │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│ Phase 2: DELIBERATE (Claude Teams — DEEP LAYER)                │
│   [Research-grounded: 2305.14325, 2402.19379]                  │
│                                                                │
│   TeamCreate("oathfish-{RUN_ID}")                              │
│   Spawn coordinator + 30 archetype persistent subagents        │
│   (memory:project for cross-run learning)                      │
│                                                                │
│   *** ARGUMENTS ONLY — NO NUMBERS ROUNDS 1-5 ***              │
│   [Evidence: LLM updating degrades accuracy vs averaging       │
│    (GPT-4 p=0.011, Claude 2 p=0.001) — 2402.19379]            │
│                                                                │
│   Round 1-2: FREE_FORM (arguments only)                        │
│     Each archetype shares qualitative reasoning                │
│     Must state base rate anchor + key uncertainties            │
│     NO stance numbers, NO confidence numbers                   │
│     Coordinator tracks argument themes, not positions          │
│                                                                │
│   Round 3-4: STRUCTURED_DEBATE (arguments only)                │
│     Coordinator pairs opposing archetypes                      │
│     2-3 exchange cycles per debate                             │
│     Must address opponent's STRONGEST argument                 │
│     "Structured stubbornness" — each archetype resists         │
│     on their domain expertise [2305.14325: stubborn > agreeable]│
│                                                                │
│   Round 5: SCENARIO_INJECTION (arguments only)                 │
│     Coordinator injects counterfactual scenarios               │
│     Each archetype reasons about second-order effects          │
│     Tests robustness of reasoning chains                       │
│                                                                │
│   Round 6: INDEPENDENT_PREDICTION (silent, structured)         │
│     Each archetype INDEPENDENTLY produces --json-schema output │
│     NO visibility into others' numbers                         │
│     Schema: {prediction, decision, confidence, base_rate,      │
│       timeframe, key_uncertainties, falsification_criteria,    │
│       second_order_effects, cascade_susceptibility}            │
│     Aggregate via median of independent predictions            │
│                                                                │
│   DIVERSITY MONITORING (every round):                          │
│     Track diversity index (argument theme spread)              │
│     If premature consensus before round 5:                     │
│       → Inject contrarian scenario                             │
│       → Activate "red team" archetype subset                   │
│       → Flag as acquiescence-contaminated                      │
│                                                                │
│   Output: Argument evolution map, coalition dynamics,          │
│           reasoning chains, independent predictions,           │
│           diversity trajectory                                 │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│ Phase 3: AMPLIFY (Python SDK + claude -p — MASS LAYER)         │
│   [Research-grounded: 2402.19379, 2602.19520]                  │
│                                                                │
│   *** BASELINE RUN FIRST (A/B test) ***                        │
│   Run 1500 amplification calls BEFORE deliberation context     │
│   → Establishes simple-averaging baseline                      │
│   [Evidence: simple averaging beats LLM updating — 2402.19379] │
│                                                                │
│   For each of 30 archetypes:                                   │
│     Generate N persona variations (default 50 per archetype)   │
│     Python SDK async engine (replaces bash script):            │
│       --json-schema $PREDICTION_SCHEMA (guaranteed structure)  │
│       --system-prompt $ARCHETYPE_IDENTITY                      │
│       --append-system-prompt $VARIATION_DELTA                  │
│       --resume $DELIBERATE_SESSION_ID (carries context)        │
│       --model haiku (cheap, fast)                              │
│     asyncio.Semaphore for rate limiting + retry with backoff   │
│                                                                │
│   MCP server aggregates WITH DEBIASING:                        │
│     Per-domain acquiescence correction (from run 3+)           │
│     Action distributions per archetype segment                 │
│     Confidence distributions                                   │
│     Reports BOTH raw and debiased distributions                │
│     Cross-segment adoption/rejection curves                    │
│                                                                │
│   Compare: baseline (pre-deliberation) vs informed             │
│   (post-deliberation) predictions. Report delta.               │
│                                                                │
│   Output: Statistical distributions, adoption predictions,     │
│           baseline vs informed comparison, debiasing report    │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│ Phase 4: SYNTHESIZE                                            │
│                                                                │
│   Report analyst agent (ReACT pattern):                        │
│     - Reads deliberation transcripts (qualitative)             │
│     - Reads amplification distributions (quantitative)         │
│     - Can interview archetypes via SendMessage (follow-up)     │
│     - Produces prediction report with reasoning + statistics   │
│                                                                │
│   Output: report.md, reasoning-chains.md, statistics.md        │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│ Phase 5: INTERACT                                              │
│                                                                │
│   All 30 archetype agents remain alive in the Team             │
│   User can:                                                    │
│     /oathfish-chat --archetype "The Cautious VC"               │
│     /oathfish-inject "Breaking: Major competitor just pivoted" │
│     Ask follow-up questions to report analyst                  │
│                                                                │
│   Archetypes respond in-character with full deliberation memory│
└────────────────────────────────────────────────────────────────┘
```

### 2.2 What We DON'T Build (and why)

| MiroFish Had | OathFish Doesn't Need | Reason |
|-------------|----------------------|--------|
| Simulated Twitter/Reddit platform | No platform simulation | Archetypes don't tweet — they reason. We're simulating minds, not social media. |
| Feed generation algorithm (recency * w_r + ...) | No feed algorithm | There's no "feed." Archetypes receive deliberation prompts, not ranked posts. |
| Platform state CRUD (posts, comments, likes) | No platform state | No simulated social media platform to manage. |
| Action validation (post length, rate limits) | No action validation | Archetypes express positions, not constrained platform actions. |
| OASIS agent action space (POST, LIKE, FOLLOW) | No action space | Unconstrained reasoning — archetypes can say anything, form any opinion. |
| Crowd simulator agent | No crowd agent | Mass layer uses `claude -p` instead — cheaper, more scalable, truly parallel. |
| Platform definition files (twitter.json) | No platform configs | Interaction modes are simpler: free-form, debate, scenario, prediction. |
| Zep knowledge graph with GraphRAG | Simpler JSON graph | Just needs entity/relationship tracking, not semantic search. |

### 2.3 Deterministic vs Creative Split

| Deterministic (MCP Server — Python) | Creative (Claude Agents/CLI) |
|--------------------------------------|------------------------------|
| State machine transitions | Archetype persona generation |
| Deliberation round tracking | Archetype reasoning and position formation |
| Position evolution computation | Cross-archetype debate responses |
| Convergence detection (metric deltas) | Internal monologues |
| Graph operations (add/query nodes/edges) | Ontology design (entity types from documents) |
| Mass simulation batch management | Individual persona responses (claude -p) |
| Statistical aggregation of mass results | Report writing (ReACT synthesis) |
| Sentiment keyword scoring (0.7 weight) | Sentiment LLM scoring (0.3 weight) |
| Node centrality computation | Topic analysis and archetype selection |
| Checkpoint persistence | Coalition identification |
| Round metrics computation | Event interpretation |

---

## 3. Scope & Boundaries

### 3.1 In Scope (WILL DO)

- [ ] Python MCP server (stdio transport) with ~20 deterministic tools
- [ ] State Machine: run lifecycle (5 phases), checkpoints, resume
- [ ] Deliberation Engine: round management, position tracking, convergence detection
- [ ] Graph Engine: entity/relationship CRUD, queries, centrality
- [ ] Amplification Engine: batch management, result aggregation, distribution computation
- [ ] Metrics Engine: round metrics, sentiment (keyword), trend computation
- [ ] 3 Claude agent definitions (deliberation-coordinator, archetype-agent, report-analyst)
- [ ] 6 skills (oathfish dispatcher, understand, deliberate, amplify, synthesize, interact)
- [ ] 3 commands (/oathfish, /oathfish-chat, /oathfish-inject)
- [ ] Mass amplification script (amplify.sh — parallel claude -p calls)
- [ ] Pydantic models for all data structures
- [ ] Plugin scaffold (plugin.json, .mcp.json, hooks)
- [ ] File-based artifact persistence per run
- [ ] 4 deliberation round types (free-form, structured debate, scenario reaction, prediction)
- [ ] Archetype generation system (topic → relevant population segments → rich personas)
- [ ] Argument evolution tracking across rounds (qualitative rounds 1-5, numeric round 6)
- [ ] Coalition/alliance detection
- [ ] Post-deliberation interview capability
- [ ] Calibration engine (5 MCP tools: record_prediction, record_outcome, get_domain_bias, get_archetype_bias, get_ensemble_metrics)
- [ ] Debiasing infrastructure (per-domain acquiescence tracking, additive corrections from run 3+)
- [ ] A/B test infrastructure (baseline amplification before deliberation every run)
- [ ] Diversity index tracking per deliberation round with premature consensus detection
- [ ] Question competence classifier (pre-UNDERSTAND gate)
- [ ] Python SDK amplification engine (replaces bash script; --json-schema, --resume, async)
- [ ] Superforecaster methodology in archetype prompt template (decompose, base rate, falsify)
- [ ] Archetype grounding protocol (3-5 real public sources per archetype)
- [ ] Holdout validation set (20% of resolved predictions reserved from calibration loop)
- [ ] Short-horizon bootstrap questions (1-4 week resolution for fast calibration data)
- [ ] Dual-metric reporting (corrected + uncorrected Brier in all quantitative outputs)
- [ ] ForecastBench submission pipeline

### 3.2 Out of Scope (WON'T DO)

- Frontend/UI (CLI plugin only)
- Zep integration (graph is JSON-file-based)
- OASIS integration (replaced entirely)
- Simulated social media platforms (Twitter/Reddit simulation)
- Feed algorithms or recommendation engines
- Platform action spaces or action validation
- Production deployment (Docker, scaling)
- Authentication or multi-user support
- Real social media API integration
- External NLP libraries (sentiment is keyword-based + LLM hybrid)
- Real-time streaming of deliberation (batch round-by-round)

### 3.3 Boundary Definitions

#### Always Do (Safe Actions)
- Track all state mutations through MCP server tools
- Persist to disk after every state-changing operation
- Customize archetype selection per topic (never use a generic fixed set)
- Use `claude -p` (not Teams) for mass amplification
- Compute aggregation metrics deterministically
- Let archetypes reason freely without constraining their action space

#### Ask First (High-Impact)
- Team size exceeding 30 archetypes: may hit Claude Teams practical limits
- Mass amplification batch > 1000 instances: significant cost
- Injecting events mid-deliberation: may disrupt convergence tracking
- Using opus/sonnet for mass amplification: expensive at scale (prefer haiku)
- Adding round types beyond the initial 4: needs coordinator prompt updates

#### Never Do (Hard Stops)
- Let Claude agents compute aggregation metrics or statistics (deterministic MCP work)
- Use Teams for mass simulation (too expensive — `claude -p` is the right tool)
- Skip the DELIBERATE phase on multi-factor questions requiring joint-probability reasoning [Research: 2409.19839 — this is where deliberation adds most value]
- Let archetype agents write to state/artifact files directly (all through MCP or coordinator)
- Run any phase without the MCP server active
- Hard-code archetype personas (must be generated per topic, grounded in real sources)
- Share numeric predictions between archetypes before the final independent prediction round [Research: 2402.19379 — social updating degrades accuracy, p=0.011]
- Claim "population prediction" accuracy without ForecastBench validation [Research: 2409.19839]
- Feed calibration corrections from holdout set back into the correction model [Research: paper-persona Round 3 — overfitting risk]

---

## 4. Component Design

### 4.1 Component 1: MCP Server (`oathfish-engine`)

Python MCP server, stdio transport. Maintains in-memory state with write-through disk persistence. ~20 tools organized into 5 engines.

#### 4.1.1 State Machine Engine (~5 tools)

```
state_init(run_id, config)
  → Creates run directory structure and run.json
  → Input: run_id string, config object (archetype_count, round_count, amplify_count, topic)
  → Output: { run_id, run_dir, state: "INIT", created_at }

state_transition(new_state)
  → Validates transition is legal, records in run.json with timestamp
  → Legal transitions: INIT→UNDERSTAND→BASELINE_AMPLIFY→DELIBERATE→AMPLIFY→SYNTHESIZE→INTERACT→COMPLETE
  → Also: any→ERROR, ERROR→{previous_state} (resume)
  → Output: { previous_state, new_state, timestamp }

state_get()
  → Returns current run state, config, and full state history
  → Output: { run_id, state, config, state_history: [{state, timestamp}...] }

state_checkpoint(phase, data)
  → Saves checkpoint data for the current phase (enables resume)
  → Output: { checkpoint_id, phase, timestamp }

state_resume()
  → Returns last valid state and checkpoint data
  → Output: { state, checkpoint, resume_instructions }
```

#### 4.1.2 Deliberation Engine (~5 tools)

```
deliberation_init(archetypes, round_count, round_types)
  → Initializes deliberation state with archetype registry and round plan
  → Input: archetypes array (from understand phase), round_count int, round_types array
  → Output: { deliberation_id, archetype_count, round_plan }

deliberation_record_round(round_n, positions)
  → Saves each archetype's position for round N
  → Input: round_n int, positions array
    Rounds 1-5: [{archetype_id, position_text, key_arguments, concerns, influenced_by, base_rate_anchor, key_uncertainties}] (ArgumentPosition — NO numeric stance/confidence)
    Round 6: [{archetype_id, prediction, decision, stance, confidence, timeframe, base_rate_anchor, falsification_criteria, ...}] (PredictionPosition — full structured prediction)
  → Persists to: deliberation/round-{N}/positions.json
  → Output: { round_n, positions_recorded, round_type: "argument"|"prediction", timestamp }

deliberation_track_evolution(round_n)
  → Computes argument evolution between round N and N-1 for each archetype
  → Rounds 1-5 (ArgumentPosition): Detects new arguments introduced, arguments abandoned, influence chains, base rate changes, concern shifts. Uses text comparison (Jaccard similarity on argument sets).
  → Round 6 (PredictionPosition): Computes numeric stance/confidence deltas vs round 5's qualitative signals.
  → Output: { round_n, evolutions: [{archetype_id, new_arguments, dropped_arguments, influence_chain, shift_summary}...] }

deliberation_check_convergence(window_size)
  → Checks if archetype arguments are stabilizing across the last `window_size` rounds
  → Rounds 1-5: Metric is argument set Jaccard stability (% of arguments unchanged between rounds). Convergence threshold: Jaccard > 0.8 for `window_size` consecutive rounds.
  → Round 6: Uses numeric stance deltas (traditional). BUT early convergence (rounds 1-3) triggers WARNING not success.
  → Also computes DIVERSITY INDEX: number of distinct argument clusters. If diversity < 3 clusters before round 5: triggers PREMATURE_CONSENSUS warning.
  → Output: { converged: bool, stability_metric, diversity_index, recommendation: "CONTINUE"|"CONVERGE"|"INJECT_CONTRARIAN" }

deliberation_get_position_map()
  → Returns current position map: all archetypes with latest stance, confidence, key arguments, evolution history
  → Output: { archetypes: [{id, name, segment, current_stance, confidence, key_arguments, evolution: [{round, stance}...]}...] }
```

#### 4.1.3 Graph Engine (~5 tools)

```
graph_init(ontology)
  → Creates graph with entity type and relationship type definitions
  → Input: ontology object { entity_types: [{name, description}], edge_types: [{name, description}] }
  → Output: { graph_id, entity_types_count, edge_types_count }

graph_add_node(name, type, summary, attributes)
  → Adds an entity node to the graph
  → Input: name string, type string (must match ontology), summary string, attributes dict
  → Output: { node_id, name, type }

graph_add_edge(from_node, to_node, type, facts, metadata)
  → Adds a relationship edge between two nodes
  → Input: from_node id/name, to_node id/name, type string, facts string, metadata dict (optional)
  → Output: { edge_id, from, to, type }

graph_query(name_or_id, depth)
  → Returns a node with its edges and neighbors up to specified depth
  → Input: name_or_id string, depth int (default 1)
  → Output: { node, edges: [...], neighbors: [...] }

graph_compute_centrality()
  → Ranks all nodes by degree centrality (connection count)
  → Used in UNDERSTAND phase to identify most important entities for archetype selection
  → Output: { rankings: [{node_id, name, type, degree, rank}...] }
```

#### 4.1.4 Amplification Engine (~3 tools)

```
amplify_init(archetypes, variations_per_archetype, model, scenario)
  → Initializes mass amplification config
  → Input: archetypes array (with evolved positions from deliberation),
           variations_per int (default 50), model string (default "haiku"),
           scenario string (the prompt each variation receives)
  → Generates persona variation templates for each archetype
  → Output: { total_calls: archetypes * variations_per, estimated_cost, config_id }

amplify_record_batch(batch_id, results)
  → Records a batch of claude -p results
  → Input: batch_id string, results array [{persona_id, archetype_id, action, reasoning, confidence}]
  → Output: { batch_id, results_recorded, running_total }

amplify_aggregate()
  → Computes statistical distributions across all recorded results
  → Per archetype: action distribution, confidence distribution, reasoning theme clusters
  → Cross-archetype: overall adoption/rejection curve, sentiment distribution, consensus vs polarization
  → Output: {
      per_archetype: [{archetype_id, action_dist: {adopt: 0.6, wait: 0.25, reject: 0.15}, avg_confidence, top_themes}...],
      overall: {adoption_rate, rejection_rate, polarization_index, consensus_topics, contested_topics},
      network_effects: {viral_potential, resistance_clusters, bridge_archetypes}
    }
```

#### 4.1.5 Metrics Engine (~3 tools)

```
metrics_compute_round(round_n)
  → Aggregate metrics for a deliberation round
  → Computes: position diversity (how spread out stances are), engagement depth (avg argument count),
              stance stability (how much positions changed), coalition count (groups of aligned archetypes)
  → Output: { round_n, diversity, engagement, stability, coalitions, timestamp }

metrics_sentiment_keyword(text)
  → Deterministic keyword-based sentiment score
  → Uses simple positive/negative/neutral word lists
  → Output: { score: float (-1.0 to 1.0), label: "positive"|"neutral"|"negative", confidence: float }
  → Note: This is the 0.7-weight component. Coordinator calls Claude for 0.3-weight LLM sentiment.

metrics_get_trend(metric_name, last_n_rounds)
  → Returns time series of a named metric across rounds
  → Input: metric_name string (diversity, engagement, stability, etc.), last_n_rounds int
  → Output: { metric, values: [{round, value}...], trend: "increasing"|"decreasing"|"stable" }
```

#### 4.1.6 MCP Server Implementation Structure

```
engine/
  __init__.py
  server.py                  # MCP stdio entry point, tool registration
  state_machine.py           # State lifecycle, transitions, persistence
  deliberation_engine.py     # Round management, position tracking, convergence
  graph_engine.py            # Entity/relationship CRUD, centrality
  amplification_engine.py    # Batch management, aggregation, distributions
  metrics_engine.py          # Round metrics, keyword sentiment, trends
  models.py                  # Pydantic models for all data structures
  sentiment.py               # Keyword-based sentiment word lists and scoring
  requirements.txt           # mcp, pydantic
```

#### 4.1.7 Key Pydantic Models

```python
class Archetype(BaseModel):
    id: str                          # e.g., "cautious-vc"
    name: str                        # e.g., "The Cautious VC"
    segment: str                     # e.g., "Institutional Investors"
    demographics: dict               # age_range, education, income, location
    values: list[str]                # e.g., ["capital preservation", "deal flow", "portfolio returns"]
    incentives: list[str]            # e.g., ["LP returns", "fund reputation", "co-investment"]
    blind_spots: list[str]           # e.g., ["founder burnout", "regulatory capture"]
    communication_style: str         # e.g., "Data-driven, risk-focused, speaks in terms of multiples"
    initial_stance: str              # Starting position on the topic
    persona_prompt: str              # Full system prompt for this archetype

class ArgumentPosition(BaseModel):
    """Used in rounds 1-5 (qualitative arguments only, no numbers shared)"""
    archetype_id: str
    round_n: int
    position_text: str               # Natural language position statement
    key_arguments: list[str]         # Top 3 supporting arguments
    concerns: list[str]              # Top concerns/risks identified
    influenced_by: list[str]         # Which other archetypes influenced this reasoning
    base_rate_anchor: str            # Historical base rate cited (superforecaster methodology)
    key_uncertainties: list[str]     # Explicit unknowns acknowledged

class PredictionPosition(BaseModel):
    """Used in round 6 (independent structured prediction, --json-schema enforced)"""
    archetype_id: str
    round_n: int
    prediction: str                  # Specific prediction statement
    decision: str                    # adopt | wait | reject | mixed
    stance: float                    # -1.0 (strongly oppose) to 1.0 (strongly support)
    confidence: float                # 0.0 to 1.0
    timeframe: str                   # When this prediction resolves
    base_rate_anchor: str            # Historical frequency anchor
    key_uncertainties: list[str]     # Top uncertainties with probability ranges
    falsification_criteria: str      # What would prove this prediction wrong
    second_order_effects: list[str]  # Cascade effects on other segments
    cascade_susceptibility: float    # 0.0 to 1.0 — how much this segment is affected by others
    coalition_alignment: list[str]   # Which other archetypes this aligns with

class RoundSummary(BaseModel):
    round_n: int
    round_type: str                  # FREE_FORM, STRUCTURED_DEBATE, SCENARIO_REACTION, PREDICTION
    positions: list[Position]
    key_themes: list[str]
    notable_exchanges: list[str]     # Most impactful archetype-to-archetype interactions
    position_shifts: list[dict]      # Who changed position and why
    coalitions: list[list[str]]      # Groups of aligned archetypes

class AmplificationResult(BaseModel):
    persona_id: str
    archetype_id: str
    action: str                      # e.g., "adopt", "wait", "reject", "modify"
    reasoning: str                   # Brief explanation
    confidence: float
    demographic_variation: dict      # How this persona differs from archetype prototype

class RunConfig(BaseModel):
    topic: str
    archetype_count: int             # Default 30
    deliberation_rounds: int         # Default 6
    amplification_per_archetype: int # Default 50
    amplification_model: str         # Default "haiku"
    checkpoint_interval: int         # Default 3 rounds
    seed_documents: list[str]        # Optional file paths
```

### 4.2 Component 2: Claude Agents (3 definitions)

#### 4.2.1 deliberation-coordinator

```yaml
name: deliberation-coordinator
description: >
  Orchestrates multi-round deliberation between 30 archetype agents.
  Manages round types, facilitates debates, tracks positions via MCP tools.
  Never computes metrics or aggregates — delegates all deterministic work to MCP server.
permissionMode: bypassPermissions
tools:
  - Read
  - Write
  - SendMessage
  - Bash
  - all oathfish-engine MCP tools
skills:
  - deliberate/SKILL.md
```

**Responsibilities:**
- Selects round type for each round based on deliberation stage
- Crafts round prompts tailored to the round type
- Sends prompts to all archetypes via SendMessage
- Collects responses
- For STRUCTURED_DEBATE: pairs opposing archetypes, routes challenges
- Calls MCP tools for all tracking/metrics:
  - `deliberation_record_round()` after collecting positions
  - `deliberation_track_evolution()` to compute changes
  - `deliberation_check_convergence()` to check if positions are stabilizing
  - `metrics_compute_round()` for aggregate metrics
- Presents checkpoint summaries to user every 3 rounds
- Handles event injection from user

**What this agent NEVER does:**
- Compute metrics or statistics (MCP does this)
- Write to artifact files directly (MCP persists)
- Decide archetype positions (archetypes decide for themselves)
- Override archetype reasoning

#### 4.2.2 archetype-agent (persistent subagent — instantiated 30 times)

```yaml
name: archetype-{id}
description: >
  Embodies a population segment archetype as a persistent subagent.
  Receives deliberation prompts, reasons from segment perspective,
  exchanges arguments (not numbers) across rounds, produces independent
  structured prediction in final round. Has cross-run memory for
  calibration learning.
memory: project              # Cross-run learning (calibration, past predictions)
model: opus|sonnet|haiku     # Tiered by archetype centrality/importance
maxTurns: 3-5                # Varies by round type (deeper for debate)
skills:
  - oathfish:archetype-reasoning  # Superforecaster methodology
hooks:
  PreToolUse:
    - matcher: "SendMessage"
      hooks:
        - type: command
          command: "${CLAUDE_SKILL_DIR}/scripts/validate-no-numbers.sh"
          # Blocks numeric predictions in rounds 1-5 [C-33]
tools:
  - Read
  - SendMessage
```

**Research grounding for archetype design:**
- **Persistent memory** (memory:project): Cross-run calibration learning. Each archetype accumulates prediction history and bias corrections. [Claude Code subagent docs; paper-calibration Round 2]
- **Tiered models**: Opus for high-centrality "thought leader" archetypes (5-8), Sonnet for standard (15-20), Haiku for "follower" archetypes (5-8). [Claude Code subagent docs — model override per agent]
- **Superforecaster methodology**: Every archetype prompt includes mandatory forecasting protocol: state base rate, decompose into sub-components, list uncertainties, state falsification criteria. Stakeholder perspective provides INPUTS; methodology provides REASONING METHOD. [2409.19839 — superforecaster gap p<0.001; 2411.10109 — behavioral transfer]
- **Structured stubbornness**: Each archetype stubborn on their domain expertise. The Cautious VC resists on downside risks; the Tech Optimist resists on adoption curves. [2305.14325 — stubborn prompts produce better outcomes]
- **Grounding in real sources**: Before production, each archetype grounded in 3-5 curated real-world sources (public interviews, published decision frameworks, hearing transcripts). [2411.10109 — 85% fidelity with real data; step-function improvement from even modest grounding]
- **No numbers until round 6**: Rounds 1-5 exchange qualitative arguments only. Enforced by PreToolUse hook. [2402.19379 — social updating of numbers degrades accuracy]

**How each archetype instance is created:**

At Team creation, each archetype agent receives a system prompt injected with:
1. Full archetype persona (from `archetypes.json`)
2. Topic context and seed document summaries
3. Deliberation rules and response format
4. Their assigned population segment description

**Per-round behavior:**
1. Receives round prompt from coordinator via SendMessage (includes round type, previous round summary, any events)
2. **Internal monologue**: Reasons privately about the topic from their segment's perspective
3. **Position formation**: Articulates a clear position with supporting arguments
4. **Responds** to coordinator via SendMessage with structured position
5. For STRUCTURED_DEBATE: Receives opponent's position, formulates challenges, responds
6. For SCENARIO_REACTION: Reasons about second-order effects on their segment
7. For PREDICTION: Makes specific, falsifiable predictions with confidence levels

**What makes archetypes different from MiroFish agents:**
- They REASON, not just generate social media posts
- They have genuine MEMORY across rounds — can reference "as I argued in round 2..."
- They can CHANGE THEIR MIND when presented with compelling arguments
- They can NOTICE PATTERNS across the discussion — "I see a concerning trend where..."
- They have INTERNAL MONOLOGUES — private reasoning before public positions
- They can send DIRECT MESSAGES to specific other archetypes (coalition formation)
- They are NOT constrained to an action space — they can express nuance

**Archetype persona structure:**
```
You are "{archetype_name}", representing the {segment} population segment.

## Who You Are
{demographics, background, context}

## Your Values & Incentives
{what drives your decisions, what you optimize for}

## Your Blind Spots
{things you tend to overlook or underweight}

## How You Communicate
{tone, vocabulary, reasoning style}

## Your Starting Position on "{topic}"
{initial stance before deliberation begins}

## Rules
- Reason genuinely from your segment's perspective
- You MAY change your position if presented with compelling arguments
- Reference specific points from other archetypes when they influence your thinking
- Be honest about your uncertainties and concerns
- When making predictions, assign confidence levels (0-100%)
- Format your response as:
  INTERNAL MONOLOGUE: [private reasoning]
  POSITION: [public stance]
  STANCE: [number from -1.0 to 1.0]
  CONFIDENCE: [0-100%]
  KEY ARGUMENTS: [top 3]
  CONCERNS: [worries/risks]
  INFLUENCED BY: [which other archetypes and how]
```

#### 4.2.3 report-analyst

```yaml
name: report-analyst
description: >
  Synthesizes deliberation transcripts and amplification statistics into
  a prediction report. Uses ReACT pattern with MCP tools for data retrieval
  and SendMessage for archetype interviews.
permissionMode: bypassPermissions
tools:
  - Read
  - Write
  - Grep
  - Glob
  - SendMessage
  - all oathfish-engine MCP tools
skills:
  - synthesize/SKILL.md
```

**Capabilities:**
- Reads deliberation artifacts (position maps, debate transcripts, evolution data)
- Reads amplification results (distributions, adoption curves)
- Calls MCP tools:
  - `deliberation_get_position_map()` for current archetype positions
  - `amplify_aggregate()` for statistical distributions
  - `graph_query()` for entity relationship context
  - `metrics_get_trend()` for trend data
- SendMessage to archetypes for follow-up interviews ("Why did you shift your position in round 4?")
- Produces:
  1. `report.md` — Main prediction report (executive summary, per-segment analysis, cross-segment dynamics, predictions with confidence)
  2. `reasoning-chains.md` — Key reasoning threads from deliberation
  3. `statistics.md` — Mass amplification statistical summary

### 4.3 Component 3: Skills (6 skills)

#### 4.3.1 oathfish/SKILL.md — Main Dispatcher

State machine orchestrator. Reads `run.json`, determines current phase, dispatches to appropriate phase skill. Handles resume.

Entry: `/oathfish "topic" --archetypes 30 --rounds 6 --amplify 50 --model haiku`

Options:
- `--archetypes N` — Number of population segment archetypes (default 30)
- `--rounds N` — Deliberation rounds (default 6)
- `--amplify N` — Persona variations per archetype for mass simulation (default 50)
- `--model MODEL` — Model for mass amplification (default haiku)
- `--documents FILE...` — Seed documents to analyze
- `--inject "event"` — Initial event/scenario to seed deliberation

#### 4.3.2 understand/SKILL.md — Phase 1

1. If seed documents provided:
   - Read and analyze documents
   - Dispatch graph-builder subagent to extract entities and relationships
   - Call MCP `graph_init()`, `graph_add_node()`, `graph_add_edge()`
   - Call MCP `graph_compute_centrality()` to identify key entities
2. Analyze topic to identify ~30 relevant population segments
3. Dispatch archetype-generator subagent (creative) to generate rich personas
   - Each archetype gets: name, segment, demographics, values, incentives, blind spots, communication style, initial stance
   - Output: `understanding/archetypes.json`
4. Call MCP `state_transition(DELIBERATE)`

**Archetype Selection Principles:**
- Cover the full spectrum of perspectives (not just "for" and "against")
- Include segments that are typically overlooked (the "quiet majority")
- Ensure economic, social, geographic, and generational diversity
- Include both powerful (VCs, executives) and less powerful (consumers, employees) segments
- Include contrarian/unexpected archetypes (the segment everyone forgets)

**Structural Archetypes (4 fixed, present in EVERY run regardless of topic):**

These provide cross-cutting analytical frameworks that improve ensemble accuracy on ALL topics. They are NOT stakeholder perspectives — they are epistemic lenses grounded in specific methodologies.

| # | Archetype | Role | Grounding Sources | Research Rationale |
|---|-----------|------|-------------------|-------------------|
| 1 | **The Historian** | Base rate authority. Anchors every prediction to historical precedent. "Of the N similar events since year X, Y% played out this way." Curates centuries of social dynamics, technology adoption curves, regulatory cycles, market patterns. The single most powerful anti-acquiescence force in the ensemble. | Published historical analysis, technology adoption databases (Gartner hype cycles, Carlota Perez), regulatory history datasets, economic cycle research | 2409.19839: superforecasters anchor to base rates; 2402.19379: acquiescence bias (57% positive) needs historical counterweight; 2602.19520: universal horizon effect (30.2% R²) is fundamentally historical |
| 2 | **The Systems Thinker** | Second-order effects, feedback loops, unintended consequences. "If segment A adopts, what happens to segment B's cost structure, and how does that cascade to segment C?" Maps causal chains that linear thinkers miss. | Donella Meadows' systems dynamics, complexity science literature, network effect research, Nassim Taleb's antifragility framework | 2409.19839: superforecaster gap widest on combination questions requiring joint-probability reasoning; paper-forecast Round 2 H2: multi-factor questions are deliberation's highest-value target |
| 3 | **The Contrarian** | Explicit incentive to argue AGAINST emerging consensus. When 28/30 archetypes converge, the Contrarian's job is to find the strongest case for the opposite. Not randomly oppositional — structurally adversarial with reasoned dissent. | Published contrarian analysis (short-seller reports, regulatory dissents, technology criticism), prediction market anomalies, "Why Most Things Fail" literature | 2305.14325: "stubborn" prompts produce better outcomes; 2402.19379: acquiescence (57%) drives false consensus; debate Round 3: premature consensus is the #1 failure mode |
| 4 | **The Probabilist** | Formal calibration, uncertainty quantification, Bayesian updating. Tracks prediction confidence intervals, flags overconfidence, computes joint probabilities. The ensemble's internal auditor. Loads calibration history from persistent memory. | Tetlock's superforecasting methodology, Bayesian reasoning frameworks, proper scoring rule literature, calibration research | 2602.19520: calibration is structured (4 components, 87.3% R²); 2409.19839: superforecaster methodology (decompose, update, calibrate); paper-calibration Round 2: directional bias tracking |

**Topic-Customized Archetypes (26 generated per topic):**
The remaining 26 archetypes are generated per topic by the UNDERSTAND phase, representing specific population segments relevant to the question. Each grounded in 3-5 real public sources [C-29].

#### 4.3.3 deliberate/SKILL.md — Phase 2

1. Call MCP `deliberation_init(archetypes, round_count, round_types)`
2. `TeamCreate("oathfish-{RUN_ID}")`
3. Spawn deliberation-coordinator agent
4. Spawn 30 archetype agents (each loaded with their persona from archetypes.json)
5. Coordinator runs the deliberation loop:

```
DELIBERATION LOOP:

  Round N:
  ┌─────────────────────────────────────────────────────────┐
  │ 1. SELECT ROUND TYPE                                     │
  │    Round 1-2: FREE_FORM (explore the space)              │
  │    Round 3-4: STRUCTURED_DEBATE (deepen tensions)        │
  │    Round 5:   SCENARIO_REACTION (test with events)       │
  │    Round 6:   PREDICTION (converge on predictions)       │
  │    (Adjustable via config or coordinator judgment)        │
  ├─────────────────────────────────────────────────────────┤
  │ 2. CRAFT ROUND PROMPT                                    │
  │    Include: round type, instructions, previous round     │
  │    summary, any injected events, specific questions      │
  │    For STRUCTURED_DEBATE: include opponent assignment     │
  ├─────────────────────────────────────────────────────────┤
  │ 3. BROADCAST TO ARCHETYPES (creative)                    │
  │    SendMessage(to: each_archetype, msg: round_prompt)    │
  │    Each archetype reasons and responds                   │
  │    For STRUCTURED_DEBATE:                                │
  │      Route challenges between paired archetypes          │
  │      2-3 exchange cycles                                 │
  ├─────────────────────────────────────────────────────────┤
  │ 4. COLLECT & RECORD (deterministic)                      │
  │    MCP: deliberation_record_round(N, positions)          │
  │    MCP: deliberation_track_evolution(N)                  │
  │    MCP: metrics_compute_round(N)                         │
  ├─────────────────────────────────────────────────────────┤
  │ 5. CHECK CONVERGENCE (deterministic)                     │
  │    MCP: deliberation_check_convergence(window=3)         │
  │    If converged → exit loop early                        │
  │    If max rounds → exit loop                             │
  ├─────────────────────────────────────────────────────────┤
  │ 6. USER CHECKPOINT (every 3 rounds)                      │
  │    Present: position map, key shifts, notable exchanges  │
  │    User can: inject event, skip to prediction, stop      │
  │    MCP: state_checkpoint(deliberation, {round_n, ...})   │
  └─────────────────────────────────────────────────────────┘
```

6. After loop: Call MCP `state_transition(AMPLIFY)`
7. Keep Team alive (archetypes needed for interviews in SYNTHESIZE and INTERACT)

#### 4.3.4 amplify/SKILL.md — Phase 3

1. Call MCP `amplify_init(archetypes_with_positions, variations_per, model, scenario)`
2. For each archetype, generate persona variation prompts:
   - Same core archetype but with demographic variation (age, location, education, experience level)
   - Same evolved position but with personality variation (enthusiasm, skepticism, caution, boldness)
3. Run `amplify.sh` script which:
   - Creates a temporary directory of prompt files
   - Runs parallel `claude -p` calls (GNU parallel or xargs)
   - Collects JSON responses
   - Pipes results back
4. Record results in batches: MCP `amplify_record_batch(batch_id, results)`
5. Aggregate: MCP `amplify_aggregate()`
6. Call MCP `state_transition(SYNTHESIZE)`

**amplify.sh (core script):**
```bash
#!/bin/bash
# Runs parallel claude -p calls for mass amplification
# Input: directory of prompt files, model name, output directory
# Output: JSON results per prompt
# Uses xargs -P (universally available) instead of GNU parallel

PROMPT_DIR="$1"
MODEL="$2"
OUTPUT_DIR="$3"
PARALLEL_JOBS="${4:-10}"

find "$PROMPT_DIR" -name "*.txt" -print0 | \
  xargs -0 -P "$PARALLEL_JOBS" -I {} sh -c \
    'cat "$1" | claude -p --model '"$MODEL"' --output-format json > '"$OUTPUT_DIR"'/$(basename "$1" .txt).json' _ {}
```

**Canonical `claude -p` invocation pattern (single source of truth):**
```bash
# ALWAYS pipe the full prompt via stdin. Never pass a positional argument alongside stdin.
cat prompt_file.txt | claude -p --model haiku --output-format json > result.json
```

#### 4.3.5 synthesize/SKILL.md — Phase 4

1. Spawn report-analyst agent with context:
   - Topic and scenario
   - Path to deliberation artifacts
   - Path to amplification results
   - Team name for archetype interviews
2. Report analyst uses ReACT loop:
   - **Think**: What aspect of the prediction needs analysis?
   - **Act**: Call MCP tool or SendMessage to archetype
   - **Observe**: Read result
   - **Repeat** until section is well-supported
   - **Write**: Generate section
3. Output artifacts:
   - `synthesis/report.md` — Main prediction report
   - `synthesis/reasoning-chains.md` — Key deliberation threads
   - `synthesis/statistics.md` — Mass simulation statistics
4. Call MCP `state_transition(INTERACT)`

**Report Structure:**
```markdown
# Prediction Report: {topic}

## Executive Summary
{2-3 paragraph overview of key predictions with confidence levels}

## Population Segment Analysis
### {Archetype 1: The Cautious VC}
- **Position**: {final evolved stance}
- **Key reasoning**: {why this segment thinks this way}
- **Position evolution**: {how their view shifted during deliberation and why}
- **Mass amplification**: {X% of this segment would adopt, Y% wait, Z% reject}

### {Archetype 2: The Scrappy Founder}
...
[Repeat for all 30 archetypes]

## Cross-Segment Dynamics
### Coalitions Formed
{Which segments aligned and why}

### Key Tensions
{Where the deepest disagreements lie, with reasoning from both sides}

### Surprising Findings
{Unexpected insights that emerged from the deliberation}

## Quantitative Predictions
### Overall Adoption/Reaction Distribution
{Aggregated mass simulation results with confidence intervals}

### Segment-by-Segment Breakdown
{Per-archetype adoption curves}

### Network Effects & Cascades
{How one segment's reaction might trigger reactions in others}

## Prediction Summary
| Prediction | Confidence | Supporting Archetypes | Opposing Archetypes |
|-----------|-----------|----------------------|-------------------|
| {prediction_1} | {high/medium/low} | {segments} | {segments} |

## Methodology
{How many archetypes, rounds, amplification instances, models used}
```

#### 4.3.6 interact/SKILL.md — Phase 5

Routes user messages to archetype agents or report analyst via SendMessage.

- `/oathfish-chat --archetype "The Cautious VC"` → SendMessage to that archetype, who responds in-character with full deliberation memory
- `/oathfish-chat --report` → SendMessage to report analyst for follow-up questions
- `/oathfish-inject "Breaking: Major competitor raises $500M"` → Triggers a new SCENARIO_REACTION round with all archetypes

### 4.4 Component 4: Commands

#### /oathfish
```yaml
name: oathfish
description: "Run a full swarm intelligence prediction. Analyzes topic, deliberates with 30 population archetypes, amplifies with mass simulation, generates prediction report."
argument-hint: '"topic" --archetypes 30 --rounds 6 --amplify 50 --documents file.pdf'
```

#### /oathfish-chat
```yaml
name: oathfish-chat
description: "Chat with any archetype from a completed deliberation, or with the report analyst."
argument-hint: '--archetype "The Cautious VC" OR --report'
```

#### /oathfish-inject
```yaml
name: oathfish-inject
description: "Inject an event into an active deliberation. Triggers a scenario reaction round."
argument-hint: '"Breaking: New regulation announced" --run RUN_ID'
```

### 4.5 Component 5: Hooks

```json
{
  "hooks": [
    {
      "event": "SessionStart",
      "command": "oathfish-init.sh",
      "description": "Detect active OathFish runs, offer resume"
    }
  ]
}
```

### 4.6 Component 6: Plugin Structure

```
oathfish/
  .claude-plugin/
    plugin.json                       # Plugin manifest
  .mcp.json                           # MCP server config (starts oathfish-engine)
  engine/                             # Python MCP server (deterministic)
    __init__.py
    server.py                         # MCP stdio entry point
    state_machine.py                  # Run lifecycle, transitions, persistence
    deliberation_engine.py            # Round management, position tracking, convergence
    graph_engine.py                   # Entity/relationship CRUD, centrality
    amplification_engine.py           # Batch management, result aggregation
    metrics_engine.py                 # Round metrics, keyword sentiment, trends
    models.py                         # Pydantic data models
    sentiment.py                      # Keyword-based sentiment word lists
    requirements.txt                  # mcp, pydantic
  agents/
    deliberation-coordinator.md       # Orchestrates deliberation rounds
    archetype-agent.md                # Template for population archetype personas
    report-analyst.md                 # ReACT report generator
  skills/
    oathfish/SKILL.md                 # Main state machine dispatcher
    understand/SKILL.md               # Topic analysis + archetype generation
    deliberate/SKILL.md               # Team-based multi-round deliberation
    amplify/SKILL.md                  # Mass claude -p batch orchestration
    synthesize/SKILL.md               # Report generation
    interact/SKILL.md                 # Chat routing
  commands/
    oathfish.md                       # /oathfish entry point
    oathfish-chat.md                  # Chat with archetypes
    oathfish-inject.md                # Inject events
  hooks/
    hooks.json                        # SessionStart resume detection
  scripts/
    amplify.sh                        # Parallel claude -p batch execution
    setup.sh                          # Install Python deps, verify MCP server
  docs/
    runs/                             # Per-run artifacts
```

### 4.7 Component 7: .mcp.json

```json
{
  "mcpServers": {
    "oathfish-engine": {
      "type": "stdio",
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/engine/server.py"],
      "env": {
        "OATHFISH_DATA_DIR": "${CLAUDE_PLUGIN_ROOT}/docs/runs"
      }
    }
  }
}
```

---

## 5. Artifact Directory (per run)

```
docs/runs/{RUN_ID}/
  _meta/
    run.json                          # State + config + history + checkpoints
  understanding/
    topic-analysis.md                 # Topic analysis results
    archetypes.json                   # 30 archetype definitions (full personas)
    archetype-rationale.md            # Why these specific archetypes were chosen
  graph/
    ontology.json                     # Entity/relationship types (if seed docs provided)
    nodes.json                        # Entity nodes
    edges.json                        # Relationship edges
  deliberation/
    round-{N}/
      prompt.md                       # What the coordinator sent to archetypes
      positions.json                  # Each archetype's position for this round
      debates/                        # Structured debate transcripts (rounds 3-4)
        {archetype-a}_vs_{archetype-b}.md
      evolution.json                  # How positions changed from previous round
      summary.md                      # Coordinator's round summary
    convergence.json                  # Convergence metrics across all rounds
    coalition-map.json                # Alliance/opposition patterns
    position-evolution.json           # Full evolution history per archetype
  amplification/
    config.json                       # Batch config
    prompts/                          # Generated persona variation prompts
      {archetype-id}/
        variation-{N}.txt
    results/                          # Raw claude -p results
      batch-{N}.json
    distributions.json                # Aggregated statistical distributions
  synthesis/
    report.md                         # Main prediction report
    reasoning-chains.md               # Key reasoning threads from deliberation
    statistics.md                     # Mass simulation statistical summary
  team/
    team-config.json                  # Team metadata
```

---

## 6. Constraints & Requirements

### 6.1 Functional Requirements

| C-ID | Type | Constraint | Priority | Verification |
|------|------|------------|----------|--------------|
| C-01 | REQUIREMENT | System must be a Claude Code plugin (plugin.json, .mcp.json, agents/, skills/, commands/) | MUST | Plugin loads, /oathfish command appears |
| C-02 | REQUIREMENT | Deterministic operations (metrics, aggregation, convergence, graph, state) handled by Python MCP server | MUST | Same inputs → same outputs, no LLM variance |
| C-03 | REQUIREMENT | Creative operations (archetype reasoning, persona generation, reports) handled by Claude agents | MUST | Outputs show genuine reasoning, personality, creative judgment |
| C-04 | REQUIREMENT | Deep deliberation uses Claude Teams with 30 archetype agents communicating via SendMessage | MUST | TeamCreate succeeds, archetypes exchange messages across 6+ rounds |
| C-05 | REQUIREMENT | Mass amplification uses `claude -p` CLI calls, not Teams | MUST | 500+ parallel stateless calls complete, results aggregate |
| C-06 | REQUIREMENT | MCP server uses stdio transport configured via .mcp.json | MUST | Server starts automatically with plugin |
| C-07 | REQUIREMENT | State machine with 7 phases: UNDERSTAND → BASELINE_AMPLIFY → DELIBERATE → AMPLIFY → SYNTHESIZE → INTERACT → COMPLETE | MUST | Each transition recorded in run.json. BASELINE_AMPLIFY runs stateless amplification before deliberation for A/B comparison. |
| C-08 | REQUIREMENT | 30 archetype agents have persistent identity and memory across all deliberation rounds | MUST | Agent references "as I argued in round 2", tracks position evolution |
| C-09 | REQUIREMENT | Archetypes are customized per topic, not a fixed generic set | MUST | "AI regulation" produces different archetypes than "healthcare reform" |
| C-10 | REQUIREMENT | 4 deliberation round types: FREE_FORM, STRUCTURED_DEBATE, SCENARIO_REACTION, PREDICTION | MUST | Each type produces distinctly structured output |
| C-11 | REQUIREMENT | Report combines qualitative reasoning chains AND quantitative mass simulation statistics | MUST | Report has both archetype quotes/reasoning AND distribution numbers |
| C-12 | REQUIREMENT | All state mutations flow through MCP server tools | MUST | No direct file writes to state by Claude agents |
| C-13 | REQUIREMENT | Hybrid sentiment: 0.7 keyword (MCP) + 0.3 LLM (coordinator) | MUST | Both scores computed and blended |
| C-14 | REQUIREMENT | Argument evolution tracked round-by-round per archetype (qualitative rounds 1-5); numeric position tracked only in round 6 independent predictions | MUST | MCP tool returns argument evolution history (rounds 1-5) and final structured predictions (round 6) |

### 6.1b Research-Mandated Requirements (from 5-paper adversarial debate)

| C-ID | Type | Constraint | Priority | Verification | Research Source |
|------|------|------------|----------|--------------|----------------|
| C-26 | REQUIREMENT | A/B test: run baseline amplification BEFORE deliberation every run | MUST | Baseline vs deliberation-informed predictions compared in every report | 2402.19379 (p=0.011 updating degrades) |
| C-27 | REQUIREMENT | Track per-domain acquiescence rate from run 1; apply corrections from run 3+ | MUST | Domain acquiescence rates reported; corrections applied when n>=90/domain | 2402.19379 (57% positive, p<0.001) + 2602.19520 (domain bias 14.6% R²) |
| C-28 | REQUIREMENT | Report both calibration-corrected AND raw uncorrected Brier scores | MUST | Dual metrics in every quantitative output | Paper-persona Round 3 (gap > 0.05 = re-ground) |
| C-29 | REQUIREMENT | Ground each archetype in 3-5 real public sources via runtime discovery during UNDERSTAND phase. After archetypes are generated, use web search to find interviews, hearing transcripts, published frameworks, or public statements relevant to each archetype's domain. Quality varies by archetype — report grounding quality (Rung 1-4) per archetype in output. Structural archetypes (Historian, Systems Thinker, Contrarian, Probabilist) are pre-grounded. | MUST | Each archetype definition includes `grounding_sources[]` and `grounding_rung` (1-4). Sources found via automated search during UNDERSTAND. | 2411.10109 (85% fidelity with real data; step-function improvement from even modest grounding) |
| C-30 | REQUIREMENT | Encode superforecaster methodology in every archetype prompt (decompose, base rate, falsify) | MUST | Every archetype response includes base_rate_anchor and falsification_criteria | 2409.19839 (superforecasters 0.096 vs LLMs 0.122) |
| C-31 | REQUIREMENT | Question competence classifier before UNDERSTAND phase | MUST | Questions flagged as in-domain/out-of-domain; out-of-domain uses base-rate-only | Paper-forecast Round 3 (competence boundary risk) |
| C-32 | REQUIREMENT | Diversity index tracked per deliberation round; premature consensus triggers contrarian injection | MUST | Diversity trajectory in output; injection triggered if diversity < 0.15 before round 5 | 2305.14325 (false consensus) + 2402.19379 (acquiescence) |
| C-33 | REQUIREMENT | No numeric predictions shared between archetypes until final independent round | MUST | Rounds 1-5 contain only qualitative arguments; round 6 is independent structured JSON | 2402.19379 (p=0.011 social updating degrades) + 2305.14325 (stubborn > agreeable) |
| C-34 | REQUIREMENT | Holdout 20% of resolved predictions from calibration feedback loop | MUST | Holdout set accuracy tracked separately; overfitting detected if gap grows | Paper-persona Round 3 (calibration-persona overfitting risk) |
| C-35 | REQUIREMENT | Submit to ForecastBench before making public accuracy claims | MUST | ForecastBench score published; target Brier < 0.122 | 2409.19839 (only standardized benchmark) |
| C-36 | REQUIREMENT | 4 structural archetypes (Historian, Systems Thinker, Contrarian, Probabilist) present in EVERY run regardless of topic | MUST | All 4 structural archetypes appear in archetypes.json for every run | Superforecaster methodology (2409.19839) + anti-acquiescence (2402.19379) + combination reasoning (2305.14325) + calibration (2602.19520) |
| C-37 | INVARIANT | Structural archetypes are NOT stakeholder perspectives — they are epistemic lenses with fixed methodology | MUST | Structural archetype prompts contain analytical framework, not persona/demographic identity | Cross-paper synthesis: methodology > identity for prediction accuracy |

### 6.2 Non-Functional Requirements

| C-ID | Category | Constraint | Target | Verification |
|------|----------|------------|--------|--------------|
| C-15 | Reliability | State persists to disk after every MCP mutation | 0 data loss on restart | Kill MCP, restart, verify state |
| C-16 | Resumability | Any phase resumable from last checkpoint | Resume from round N | Interrupt, resume, correct state |
| C-17 | Scalability | Mass amplification handles 500-5000 calls | 1500 default (30 * 50) | Batch completes, results aggregate |

### 6.3 Technical Constraints (Limitations)

| C-ID | Limitation | Source | Impact |
|------|------------|--------|--------|
| C-18 | LIMITATION | Claude Teams ~30 concurrent agents maximum | Team = 30 archetypes + 1 coordinator + 1 report analyst = 32 |
| C-19 | LIMITATION | MCP server is Python (Pydantic + mcp library) | No external NLP, ML, or heavy dependencies |
| C-20 | LIMITATION | Archetype agents have Read + SendMessage only | All data comes via SendMessage from coordinator |
| C-21 | LIMITATION | `claude -p` calls have two modes: (1) BASELINE_AMPLIFY calls are fully stateless — no --resume, no session context; (2) AMPLIFY (post-deliberation) calls use `--resume SESSION_ID` to carry deliberation context. Baseline captures uncontaminated control; post-deliberation captures informed predictions. Both use `--json-schema` for structured output. | Baseline = stateless (A/B control), Post-deliberation = `--resume` with session_id captured via `claude -p --output-format json \| jq -r '.session_id'` |

### 6.4 Invariants

| C-ID | Invariant | Rationale | Guard |
|------|-----------|-----------|-------|
| C-22 | INVARIANT | Coordinator never computes metrics — only orchestrates | Prevents LLM variance in deterministic ops | Agent def restricts to orchestration |
| C-23 | INVARIANT | All MCP state changes flush to disk immediately | Write-through caching, not periodic | Every mutation → file write |
| C-24 | INVARIANT | User checkpoints every 3 deliberation rounds | User maintains control over deliberation direction | Coordinator checks round % 3 |
| C-25 | INVARIANT | Archetypes are never told what position to take | Genuine reasoning, not scripted outcomes | Prompt only provides persona, not desired stance |

---

## 7. Specification Analysis

### 7.1 Impossibility Check

| Pattern | Matched? | Evidence |
|---------|----------|----------|
| PHYS-001 (Persistence vs Volatility) | NO | Write-through caching: in-memory + immediate disk flush |
| PHYS-002 (Crash-safe vs Stateless) | NO | Explicit checkpointing for all phases |
| CS-001 (CAP) | NO | Single-machine system |
| SEM-001 (Stateless Memory) | NO | Archetypes have persistent Team memory; mass layer is intentionally stateless |
| PERF-001 (Real-time vs Deep) | NO | No real-time claims |
| PERF-002 (Scale vs Single) | NO | Two-tier: Teams for depth (30), claude -p for breadth (1500+) |
| RES-002 (No Deps vs Use Service) | NO | MCP server + Claude Code are internal |
| All others | NO | Not applicable to this architecture |

### 7.2 Novel Contradictions Checked

| Check | Result |
|-------|--------|
| C-18 (30 agent limit) vs C-04 (30 archetypes + coordinator + analyst = 32) | ACCEPTABLE: 32 is within practical limits. If needed, report analyst can be a subagent instead of team member. |
| C-21 (claude -p stateless) vs needing evolved archetype positions | NO CONFLICT: Evolved positions are injected into each claude -p prompt context. Statelessness is a feature, not a bug. |
| C-13 (hybrid sentiment) vs C-02 (deterministic MCP) | NO CONFLICT: MCP provides the 0.7 keyword component (deterministic). Coordinator provides the 0.3 LLM component (creative). Blending is done by coordinator. |
| C-25 (archetypes not told what position to take) vs wanting predictions | NO CONFLICT: Genuine reasoning IS the value. Scripted agents would defeat the purpose. |

### 7.3 Contradictions Detected

None. All constraint pairs are compatible.

### 7.4 Ambiguities Detected

None remaining. D-01 (hybrid sentiment) and D-02 (both broadcast + sequential) resolved by user.

Note: D-02 (sequential-turn platforms) is less relevant in v2 since we're not simulating platforms. The deliberation round types (FREE_FORM, STRUCTURED_DEBATE, etc.) naturally support both broadcast and sequential interaction without platform configs.

---

## 8. Assumptions & Decisions

### 8.1 Explicit Assumptions

| A-ID | Assumption | Basis | Risk if Wrong | Classification |
|------|------------|-------|---------------|----------------|
| A-01 | `claude -p` CLI is available and supports `--model` and `--output-format json` flags | Claude Code CLI documentation | Mass amplification won't work; would need to fall back to Anthropic SDK | NEEDS_VERIFICATION |
| A-02 | 30 Team members + coordinator + analyst (~32 total) is within Claude Teams practical limits | oathe-research ran 14 agents successfully | Deliberation phase fails; would need to reduce archetype count or batch | NEEDS_VERIFICATION |
| A-03 | Python `mcp` PyPI package supports stdio server with Pydantic model integration | MCP specification and Python SDK docs | MCP server architecture needs rethinking | NEEDS_VERIFICATION |
| A-04 | Archetype agents will evolve positions, BUT evolution may be driven by acquiescence bias rather than genuine insight. Position evolution is necessary but insufficient for prediction quality. A/B testing against baseline required to verify deliberation adds value. | Claude's reasoning + 2402.19379 (acquiescence bias 57%, p<0.001) + 2305.14325 (false consensus risk) | Deliberation produces confident-but-wrong convergence; A/B test shows baseline beats deliberation | REVISED per research |
| A-05 | xargs -P is available for parallel claude -p execution (backup; primary is Python SDK) | Standard Unix tool (macOS/Linux) | Mass amplification runs sequentially (much slower) | VERIFIED |
| A-06 | Synthetic archetypes provide enough diversity for meaningful ensemble (inter-archetype prediction correlation < 0.8) | 2305.14325 (different prompts improve 3.1pp) + 2411.10109 (deep personas > demographics) | If correlation > 0.8, effective ensemble size is ~3-5 not 30. Architecture provides no statistical advantage. | NEEDS_VERIFICATION |
| A-07 | Domain-level acquiescence correction achievable at n=90 per domain (3 runs × 30 archetypes) | 2602.19520 (power analysis: 80% at d=0.3 with n=90) + 2402.19379 (bias is large, 12pp) | If acquiescence is not structured by domain, correction requires orders of magnitude more data | NEEDS_VERIFICATION |
| A-08 | Superforecaster methodology encoded in prompts transfers to LLM reasoning behavior | 2409.19839 (methodology gap identified) + 2411.10109 (behavioral transfer at 85% with real data) | If methodology is superficial (LLMs generate decompositions without genuine depth), adds token cost without accuracy | NEEDS_VERIFICATION |
| A-09 | Outcome resolution latency (3-12 months for primary questions) won't prevent useful calibration within year 1 | Mitigated by including short-horizon bootstrap questions (1-4 week resolution) in every run | If most predictions are long-horizon, calibration feedback delayed 6-12 months. Year 1 has zero calibration data for primary questions. | RISK — paper-calibration Round 3 flagged this as biggest remaining risk |

### 8.2 Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| D-01: Sentiment approach | Hybrid 0.7 keyword + 0.3 LLM | USER DECIDED. Best of both: deterministic base + nuanced augmentation. |
| D-02: Platform interaction modes | Both broadcast + sequential | USER DECIDED. In v2, this maps to deliberation round types (FREE_FORM = broadcast, STRUCTURED_DEBATE = sequential) rather than platform configs. |
| D-03: Architecture paradigm | Two-layer (Teams + claude -p) instead of MiroFish port | USER DECIDED. Depth > breadth for core value; mass layer for statistical amplification. |
| D-04: Agent count | 30 archetypes as population representatives | USER DECIDED. Each represents a segment, not an individual. |

---

## 9. Technical Context

### 9.1 Technology Stack

| Component | Technology | Version | Notes |
|-----------|------------|---------|-------|
| MCP Server | Python | 3.11+ | stdio transport, Pydantic models, ~20 tools |
| MCP Library | `mcp` PyPI package | Latest | Python MCP SDK |
| Data Models | Pydantic | v2+ | Type-safe JSON serialization |
| Plugin Host | Claude Code | Current | Teams, SendMessage, Agent, Skill tools |
| Mass Amplification | `claude -p` CLI | Current | Piped mode, parallel execution |
| Parallel Execution | xargs -P (POSIX) | System | For mass claude -p calls (universally available) |
| Keyword Sentiment | Custom Python | N/A | Word lists + scoring rules |
| Persistence | JSON files | N/A | Write-through caching |

### 9.2 Integration Points

| System | Interface | Direction | Data |
|--------|-----------|-----------|------|
| Claude Code Plugin | plugin.json + .mcp.json | BOTH | Plugin config, MCP lifecycle |
| Claude Teams | TeamCreate, SendMessage | BOTH | 30 archetypes + coordinator + analyst |
| Claude CLI | `claude -p` via Bash | OUT→IN | Mass amplification prompts → responses |
| MCP Server | stdio tools | BOTH | All deterministic operations |
| Filesystem | JSON in docs/runs/ | BOTH | State, artifacts, results |

### 9.3 Existing Patterns to Follow

| Pattern | Location | What to Reuse |
|---------|----------|---------------|
| State machine dispatcher | oathe-research `skills/research/SKILL.md` | State transitions, resume, checkpoints |
| Team + round orchestration | oathe-research `skills/debate/SKILL.md` | TeamCreate, SendMessage, round loop, convergence |
| Parallel subagent dispatch | DARWIN `skills/dep/SKILL.md` | Parallel batch persona generation |
| MCP server setup | `plugin-dev:mcp-integration` skill | .mcp.json config, stdio server |
| Persona generation | MiroFish `oasis_profile_generator.py` | Demographic variation, persona richness |
| Agent definitions | oathe-research `agents/*.md` | Frontmatter format, tool lists |
| Debate rounds | oathe-research debate orchestration | Exchange cycles, scoring, judge patterns |
| Mass CLI execution | Standard Unix parallel patterns | GNU parallel, xargs -P |

---

## 10. Implementation Sequence

### Phase 1: MCP Server Foundation
- `engine/server.py` — MCP stdio server entry point
- `engine/models.py` — All Pydantic models (Archetype, Position, RoundSummary, etc.)
- `engine/state_machine.py` — 5 state machine tools
- `engine/deliberation_engine.py` — 5 deliberation tools
- `engine/graph_engine.py` — 5 graph tools
- `engine/amplification_engine.py` — 3 amplification tools
- `engine/metrics_engine.py` — 3 metrics tools
- `engine/sentiment.py` — Keyword word lists and scoring
- `requirements.txt` — mcp, pydantic
- `.mcp.json` — Server config
- **Test**: Start server, call every tool, verify JSON responses

### Phase 2: Plugin Scaffold
- `.claude-plugin/plugin.json`
- `commands/oathfish.md`
- `skills/oathfish/SKILL.md` — State machine dispatcher
- `hooks/hooks.json` — SessionStart resume detection
- `scripts/setup.sh` — Install deps, verify server
- **Test**: `/oathfish` command loads, state machine initializes

### Phase 3: UNDERSTAND Phase
- `skills/understand/SKILL.md` — Orchestration
- Archetype generator subagent prompt (topic → 30 population segment personas)
- Graph builder subagent prompt (for seed documents)
- Wire to MCP graph tools
- **Test**: Topic → 30 diverse archetypes in archetypes.json

### Phase 4: DELIBERATE Phase (Core)
- `agents/deliberation-coordinator.md`
- `agents/archetype-agent.md`
- `skills/deliberate/SKILL.md` — Team creation + round loop
- 4 round type prompt templates (free-form, debate, scenario, prediction)
- Wire to MCP deliberation tools
- **Test**: 6 rounds, 30 archetypes, position evolution tracked, convergence detected

### Phase 5: AMPLIFY Phase
- `skills/amplify/SKILL.md` — Batch orchestration
- `scripts/amplify.sh` — Parallel claude -p execution
- Wire to MCP amplification tools
- **Test**: 1500 calls (30 * 50), results aggregate into distributions

### Phase 6: SYNTHESIZE + INTERACT
- `agents/report-analyst.md`
- `skills/synthesize/SKILL.md` — Report generation
- `skills/interact/SKILL.md` — Chat routing
- `commands/oathfish-chat.md`, `commands/oathfish-inject.md`
- **Test**: Report references both deliberation reasoning and amplification stats; archetype responds in-character

---

## 11. Handoff Summary

### Status
| Metric | Value |
|--------|-------|
| Constraints | 25 (REQUIREMENT: 14, LIMITATION: 4, INVARIANT: 4, Non-Functional: 3) |
| Contradictions | 0 |
| Ambiguities | 0 |
| Assumptions | 5 (3 NEEDS_VERIFICATION, 1 IMPLICIT, 1 NEEDS_VERIFICATION) |
| Decisions | 4 (all confirmed by user) |

### Readiness
- [x] All contradictions resolved (none found)
- [x] All ambiguities clarified (D-01, D-02 by user; D-02 remapped to round types in v2)
- [x] All MUST decisions made (D-01 through D-04)
- [x] Success criteria defined (SC-01 through SC-10)
- [x] Boundaries established (always/ask_first/never)
- [x] Architecture redesigned from first principles (two-layer: Teams + claude -p)

**Status**: READY_FOR_SKEPTIC

**Decisions Confirmed:**
- D-01: Hybrid sentiment (0.7 keyword + 0.3 LLM) — USER DECIDED
- D-02: Both broadcast + sequential → maps to round types in v2 — USER DECIDED
- D-03: Two-layer architecture (Teams depth + claude -p breadth) — USER DECIDED
- D-04: 30 archetypes as population segment representatives — USER DECIDED
