# Discover Report - Worker D
## Run: 0001-oathfish-swarm-engine
## Keywords: archetype_generation, structural_archetypes, grounding_ladder, runtime_source_discovery, superforecaster_methodology, amplification_sdk, json_schema, persona_variation, base_rate_anchor, falsification_criteria
## Lens: domain-logic
## Entry Point: feature-request.md 4.3.2 (understand/SKILL.md), 4.3.4 (amplify/SKILL.md)

---

## Project Intelligence (from Serena Memory) - VERIFIED

### Project Status
OathFish is a greenfield project -- no application code exists yet. The project root (`/Users/shezmalik/Projects/Oathe/oathfish/`) contains only `package.json` (name: "oathfish", version: 0.1.0), documentation directories, and reference materials. Verified: `package.json:1-5`.

### Related Codebase: MiroFish
MiroFish (`/Users/shezmalik/Projects/Oathe/MiroFish/`) is an existing sibling project with a working persona generation pipeline in `backend/app/services/oasis_profile_generator.py`. Verified at `:1-947`. This is the closest existing code reference for OathFish archetype generation.

### Research Foundation
Five research papers debated across 3 adversarial rounds inform the design. Final synthesis at `docs/oathe/runs/run_20260318_140000/synthesis/final-synthesis.md`. Verified.

---

## Search Strategy

| Type | Keywords | Source |
|------|----------|--------|
| Literal | archetype_generation, structural_archetypes, grounding_ladder | Feature request C-29, C-36, C-37 |
| Literal | superforecaster_methodology, base_rate_anchor, falsification_criteria | Feature request C-30 |
| Literal | amplification_sdk, json_schema, persona_variation | Feature request 4.3.4, headless SDK |
| Project Terms | OasisAgentProfile, OasisProfileGenerator, persona, bio | MiroFish codebase |
| Synonyms | archetype_prompt, persona_prompt, system_prompt | Claude Code headless CLI |
| Synonyms | PredictionPosition, AmplificationResult, structured_output | Pydantic models in feature spec |
| Anti-seeds | acquiescence, false_consensus, correlated_failure, overfitting | Research warnings |
| Framework | claude -p, --json-schema, --system-prompt, --append-system-prompt, --resume | Claude Code Agent SDK |
| Framework | asyncio.Semaphore, query(), ClaudeSDKClient, ResultMessage | Python SDK patterns |
| Integration | deliberation_record_round, amplify_init, amplify_record_batch, amplify_aggregate | MCP server tools |

---

## Mandatory Anchors

### Package Manifest
- `package.json:1-5` -- Name "oathfish", version 0.1.0. No dependencies, no scripts. Greenfield.

### Application Entry (Planned)
- No code exists. Planned entry: `engine/server.py` (MCP stdio server) per `feature-request.md:509`.
- Skills entry: `skills/understand/SKILL.md` for archetype generation, `skills/amplify/SKILL.md` for amplification. Per `feature-request.md:1036-1038`.

### Type Definitions (Planned)
- `Archetype` model defined at `feature-request.md:523-534` -- 10 fields: id, name, segment, demographics, values, incentives, blind_spots, communication_style, initial_stance, persona_prompt.
- `PredictionPosition` model defined at `feature-request.md:546-561` -- 12 fields including base_rate_anchor, falsification_criteria, second_order_effects.
- `AmplificationResult` model defined at `feature-request.md:571-577` -- 6 fields.
- `ArgumentPosition` model defined at `feature-request.md:535-544` -- 8 fields, rounds 1-5 only.

---

## Surface Inventory

### HIGH Relevance

| Item | File | Anchor | Relevance |
|------|------|--------|-----------|
| Archetype persona structure (system prompt template) | feature-request.md | :691-724 | Exact template for archetype system prompts |
| 4 Structural archetypes table (Historian, Systems Thinker, Contrarian, Probabilist) | feature-request.md | :800-805 | Fixed archetypes with grounding sources and research rationale |
| Structural archetypes are NOT stakeholder perspectives | feature-request.md | :798 | C-37 invariant -- epistemic lenses, not personas |
| PredictionPosition Pydantic model | feature-request.md | :546-561 | JSON schema for --json-schema enforcement |
| Archetype model with grounding fields | feature-request.md | :523-534 | Needs extension for grounding_sources[] and grounding_rung |
| Python SDK amplification engine design | research-driven-redesign.md | :117-135 | Replaces amplify.sh with async Python SDK |
| headless CLI --json-schema pattern | headless-analysis.md | :85-86 | Schema-validated structured output is production-ready |
| headless CLI --system-prompt / --append-system-prompt | headless-analysis.md | :93 | Dual-mode: system-prompt for archetype identity, append for variation delta |
| headless CLI --resume SESSION_ID | headless-analysis.md | :87-88 | Session continuity for post-deliberation amplification |
| Python SDK query() async pattern | headless-analysis.md | :89 | asyncio.gather() + Semaphore for parallel execution |
| SDK structured output + Pydantic integration | headless-analysis.md | :56-57 | model_json_schema() generates schema, model_validate() parses response |
| Superforecaster methodology encoding in prompts | research-driven-redesign.md | :305-306 | Mandatory protocol: base rate, decompose, uncertainties, falsification |
| Archetype grounding in real sources (C-29) | feature-request.md | :1144 | Runtime web search for 3-5 public sources per archetype |
| C-21 dual mode amplification | feature-request.md | :1169 | Baseline (stateless) vs post-deliberation (--resume) |
| MiroFish OasisProfileGenerator | oasis_profile_generator.py | :142-210 | Persona generation patterns: entity context building, LLM-based profile gen, retry logic |
| MiroFish OasisAgentProfile dataclass | oasis_profile_generator.py | :28-58 | Profile structure: age, gender, mbti, country, profession, interested_topics |
| MiroFish individual persona prompt | oasis_profile_generator.py | :676-723 | 2000-word persona template with 7 sections |
| MiroFish batch generation with parallel_count | oasis_profile_generator.py | :850-947 | ThreadPoolExecutor, progress callback, fallback profiles |
| MiroFish Zep context enrichment | oasis_profile_generator.py | :285-411 | Parallel edge+node search with retry, context dedup |
| Amplification flag mapping table | headless-analysis.md | :107-120 | Complete mapping of OathFish components to headless flags |

### MEDIUM Relevance

| Item | File | Anchor | Relevance |
|------|------|--------|-----------|
| amplify.sh bash script (to be replaced) | feature-request.md | :878-893 | Current baseline design; Python SDK replaces this |
| Archetype selection principles | feature-request.md | :789-795 | Spectrum coverage, overlooked segments, diversity requirements |
| A/B test infrastructure (C-26) | feature-request.md | :1141 | Baseline amplification before deliberation |
| BASELINE_AMPLIFY state in state machine | feature-request.md | :1128 | C-07: UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE -> AMPLIFY |
| amplify_init MCP tool | feature-request.md | :459-465 | Initializes mass amplification config |
| amplify_record_batch MCP tool | feature-request.md | :467-470 | Records batch of claude -p results |
| amplify_aggregate MCP tool | feature-request.md | :472-481 | Computes distributions with debiasing |
| Tiered model assignment for archetypes | feature-request.md | :659 | Opus (5-8 high centrality), Sonnet (15-20), Haiku (5-8 followers) |
| --effort flag for tiered depth | cli-reference-analysis.md | :364-375 | max/high/medium effort per archetype tier |
| --fallback-model for reliability | cli-reference-analysis.md | :352-362 | sonnet fallback for haiku amplification |
| --max-turns 1 for single-shot | headless-analysis.md | :119 | Prevents agentic wandering in amplification |
| --tools "" to disable tools | headless-analysis.md | :120 | Amplification needs NO tools |
| ResultMessage fields | headless-analysis.md | :58 | total_cost_usd, usage, session_id, is_error, structured_output |
| Paper: 85% fidelity with real interviews | 2411.10109-generative-agents-1000.md | :13 | Stanford benchmark for persona quality |
| Paper: Demographics-only < rich personas | 2411.10109-generative-agents-1000.md | :22 | Depth > breadth for persona generation |
| Paper: Superforecaster gap p<0.001 | 2409.19839-forecastbench.md | :13 | Expert forecasters significantly outperform LLMs |
| Paper: Best LLM Brier 0.1352 vs superforecasters 0.096 | 2409.19839-forecastbench.md | :22-24 | Target gap to close through architecture |

### LOW Relevance

| Item | File | Anchor | Relevance |
|------|------|--------|-----------|
| MiroFish MBTI_TYPES constant | oasis_profile_generator.py | :155-160 | Demographic variation dimension (not primary for OathFish) |
| MiroFish COUNTRIES constant | oasis_profile_generator.py | :163-166 | Geographic variation dimension |
| MiroFish rule-based fallback | oasis_profile_generator.py | :773-844 | Backup when LLM fails -- pattern to follow |
| MiroFish truncated JSON repair | oasis_profile_generator.py | :582-668 | Robust JSON handling -- less needed with --json-schema |
| Report analyst agent | feature-request.md | :726-758 | Downstream of amplification, not core to Worker D |
| Graph engine tools | feature-request.md | :428-454 | Used in UNDERSTAND for centrality, not archetype generation |

---

## Framework Patterns (from Reference Analysis)

### Claude Code Agent SDK (Python)

| Pattern | Reference | OathFish Usage |
|---------|-----------|----------------|
| `query()` async generator | headless-analysis.md:53-54 | Each amplification call is an independent `query()` |
| `ClaudeSDKClient` persistent client | headless-analysis.md:54 | NOT used for amplification (each call is stateless) |
| `ClaudeAgentOptions` dataclass | headless-analysis.md:55 | Full config per call: model, system_prompt, output_format, resume |
| `output_format={"type": "json_schema", "schema": {...}}` | headless-analysis.md:56 | Forces PredictionPosition schema validation |
| `ResultMessage.structured_output` | headless-analysis.md:58 | Validated prediction data, no parsing needed |
| `ResultMessage.total_cost_usd` | headless-analysis.md:58 | Per-call cost tracking for budget management |
| `asyncio.Semaphore(N)` for rate limiting | headless-analysis.md:89 | Cap concurrent calls to prevent overload |
| `ProcessError` with exit_code | headless-analysis.md:65 | Crash detection in amplification calls |

### CLI Flags (for amplification)

| Flag | Reference | Usage |
|------|-----------|-------|
| `--json-schema` | headless.md:42-48 | Enforces PredictionPosition schema |
| `--system-prompt` | headless.md:113-115 | Full replacement with archetype persona |
| `--append-system-prompt` | headless.md:116-117 | Adds variation delta on top of persona |
| `--resume SESSION_ID` | headless.md:132-134 | Post-deliberation context (AMPLIFY only, not BASELINE_AMPLIFY) |
| `--model haiku` | headless.md:28 | Cheap/fast for mass amplification |
| `--fallback-model sonnet` | headless.md:27 | Automatic retry on overload |
| `--max-turns 1` | headless.md:25 | Prevent agentic wandering |
| `--max-budget-usd N.NN` | headless.md:26 | Per-call cost cap |
| `--tools ""` | headless.md:24 | Disable all tools for amplification |
| `--effort` | headless.md:29 | Tiered reasoning depth per archetype tier |
| `--output-format json` | headless.md:36 | Required with --json-schema |
| `--no-session-persistence` | headless.md:32 | Prevents disk writes for stateless calls |

---

## Configuration Systems

### Amplification Configuration

| System | Config Location | Governs What |
|--------|-----------------|--------------|
| Amplification batch config | `docs/runs/{RUN_ID}/amplification/config.json` (planned) | Total calls, model, variations_per_archetype |
| Per-call config via CLI flags | CLI invocation args | --json-schema, --system-prompt, --model, --resume |
| Run config | `docs/runs/{RUN_ID}/_meta/run.json` (planned) | Global: archetype_count, amplification_per_archetype, amplification_model |
| Python SDK ClaudeAgentOptions | In-memory per call | All call-level settings |

### Archetype Generation Configuration

| System | Config Location | Governs What |
|--------|-----------------|--------------|
| Structural archetype definitions | Hard-coded in understand/SKILL.md | 4 fixed archetypes: Historian, Systems Thinker, Contrarian, Probabilist |
| Topic-customized archetype generation | LLM-generated per run | 26 variable archetypes based on topic analysis |
| Grounding source registry | Per-archetype in archetypes.json | grounding_sources[] and grounding_rung per archetype |

---

## Initial Observations

### 1. Greenfield Project -- All Design, No Refactoring
No existing code to modify. The entire archetype generation pipeline, amplification SDK, and structural archetype definitions must be designed from scratch. This eliminates refactoring hazards but introduces "blank page" design risk.

### 2. MiroFish Provides Rich Persona Patterns
The `oasis_profile_generator.py` at `:676-723` shows a 2000-word persona template with 7 sections (basic info, background, personality, social media behavior, stances, unique traits, personal memory). OathFish needs an analogous but forecasting-oriented template: demographics, values/incentives, blind spots, communication style, domain expertise, superforecaster methodology protocol, initial stance, grounding sources.

### 3. Two Distinct Archetype Types Require Different Generation Paths
- **Structural archetypes** (4 fixed): Pre-defined with curated grounding sources, methodology-first prompts. They are NOT stakeholders -- they are epistemic lenses (C-37, `feature-request.md:798`).
- **Topic-customized archetypes** (26 per topic): Generated by LLM during UNDERSTAND, then grounded via runtime web search. They ARE stakeholder perspectives.

### 4. Python SDK Replaces Bash -- Complete Rewrite
The `amplify.sh` script (`feature-request.md:878-893`) using `xargs -P` is explicitly replaced by a Python async SDK engine (`research-driven-redesign.md:117-135`). Key capabilities: asyncio.Semaphore, exponential backoff, Pydantic schema validation, per-call cost tracking, progress callbacks.

### 5. Dual-Mode Amplification is Structurally Critical
C-21 (`feature-request.md:1169`) defines two amplification modes:
- BASELINE_AMPLIFY: Fully stateless (no --resume), runs before deliberation. A/B control.
- AMPLIFY: Uses `--resume SESSION_ID` to carry deliberation context. Informed predictions.
Both use --json-schema with PredictionPosition schema.

### 6. Superforecaster Methodology is Structural, Not Optional
C-30 (`feature-request.md:1145`) requires EVERY archetype prompt to include: state base rate, decompose into sub-components, list uncertainties, state falsification criteria. This is the REASONING METHOD overlaid on every archetype's stakeholder perspective. The PredictionPosition schema at `:546-561` structurally enforces base_rate_anchor and falsification_criteria as required fields.

### 7. Grounding Ladder Has 4 Rungs
From cross-referencing `research-driven-redesign.md:307`, `sub-agents-analysis.md:113`, `skills-analysis.md:160`, and `feature-request.md:1144`:
- **Rung 1**: Synthetic persona (LLM-generated, no real sources)
- **Rung 2**: 3-5 real public sources curated per archetype (interviews, hearing transcripts, published frameworks)
- **Rung 3**: Rich grounding with domain-specific databases (Gartner, regulatory databases)
- **Rung 4**: Interview-grounded (real interview transcripts, Stanford paper's gold standard)

C-29 targets Rung 2 minimum for all archetypes. Structural archetypes aim for Rung 3 with pre-curated domain sources.

### 8. JSON Schema is the Scientific Instrument
`headless-analysis.md:193-197` identifies `--json-schema` as "the single most important capability for OathFish's quantitative integrity." It eliminates free-text parsing for all 1500+ amplification calls and structurally enforces calibration-required fields (confidence, timeframe, base_rate_anchor).

---

## Handoff to Explore

Priority areas for depth-first exploration:

1. **Structural Archetype Prompt Design** -- Full prompt templates for all 4 structural archetypes, integrating superforecaster methodology protocol with epistemic lens identity. Must resolve: how does a "Historian" archetype differ from a "historian stakeholder"?

2. **Archetype Generation Pipeline** -- Complete trace from topic input through entity extraction, segment identification, archetype generation, runtime source grounding, to archetypes.json output. What are the exact transformation steps?

3. **Python SDK Amplification Engine Architecture** -- async/await structure, Semaphore rate limiting, retry logic, dual-mode (baseline vs post-deliberation), Pydantic schema enforcement, progress callbacks, cost tracking. Complete module design.

4. **Persona Variation Algorithm** -- How to generate N variations per archetype with demographic diversity (age, location, education) and personality diversity (enthusiasm, skepticism, caution) while preserving core archetype identity. Informed by MiroFish patterns.

5. **Runtime Source Discovery Mechanism** -- How the UNDERSTAND phase performs web search to find 3-5 public sources per archetype at runtime. How to assess and report grounding_rung per archetype.
