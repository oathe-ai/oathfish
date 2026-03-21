# Explore Report - Worker D
## Run: 0001-oathfish-swarm-engine
## Worker: D
## Lens: domain-logic

---

## Dependency Map

### Archetype Generation Pipeline (UNDERSTAND Phase)

The archetype generation pipeline transforms a user topic into 30 rich archetype definitions (4 structural + 26 topic-customized). No code exists yet; all dependencies are design-level.

**Inbound (what feeds archetype generation):**

| Source | Evidence | Purpose |
|--------|----------|---------|
| User topic string | feature-request.md:766 (`/oathfish "topic"`) | Topic analysis input |
| Seed documents (optional) | feature-request.md:773 (`--documents FILE...`) | Entity extraction for graph-based segment identification |
| Graph centrality results | feature-request.md:452 (`graph_compute_centrality()`) | Rank entities for archetype selection priority |
| Structural archetype templates (4 fixed) | feature-request.md:800-805 | Pre-defined Historian, Systems Thinker, Contrarian, Probabilist |
| Runtime web search results | feature-request.md:1144 (C-29) | 3-5 public sources per archetype for grounding |

**Outbound (what consumes archetype definitions):**

| Consumer | Evidence | Purpose |
|----------|----------|---------|
| archetypes.json | feature-request.md:1081 | Persistent archetype definitions for all downstream phases |
| Deliberation coordinator | feature-request.md:614-621 | Spawns 30 archetype agents with persona prompts |
| BASELINE_AMPLIFY phase | feature-request.md:1128 (C-07) | Uses archetype identities for stateless amplification |
| AMPLIFY phase | feature-request.md:862-875 | Uses archetypes with evolved positions for post-deliberation amplification |
| Persona variation generator | feature-request.md:866-867 | Generates N variations per archetype for mass amplification |

### Python SDK Amplification Engine (AMPLIFY Phase)

**Inbound:**

| Source | Evidence | Purpose |
|--------|----------|---------|
| archetypes.json (with evolved positions) | feature-request.md:864 | Base identity for --system-prompt |
| Persona variation templates | feature-request.md:866-867 | Variation delta for --append-system-prompt |
| PredictionPosition JSON schema | feature-request.md:546-561 | Schema for --json-schema enforcement |
| Deliberation session ID | headless-analysis.md:112 | --resume SESSION_ID for post-deliberation calls |
| Run config (model, variations_per) | feature-request.md:579-586 (RunConfig) | Batch parameters |
| MCP amplify_init() output | feature-request.md:459-465 | Initialization config |

**Outbound:**

| Consumer | Evidence | Purpose |
|----------|----------|---------|
| MCP amplify_record_batch() | feature-request.md:467-470 | Stores batched results |
| MCP amplify_aggregate() | feature-request.md:472-481 | Computes distributions with debiasing |
| Calibration engine | research-driven-redesign.md:253-276 | Records predictions for outcome comparison |
| Synthesis phase | feature-request.md:901-918 | Report analyst reads amplification results |

### Superforecaster Methodology

**Dependency on every archetype prompt:**

| Injection Point | Evidence | Mechanism |
|-----------------|----------|-----------|
| Structural archetype system prompts | feature-request.md:800-805 + research-driven-redesign.md:305 | Baked into pre-defined prompt templates |
| Topic-customized archetype prompts | feature-request.md:1145 (C-30) | Injected during UNDERSTAND generation |
| Amplification calls | headless-analysis.md:169 | --system-prompt carries full persona including methodology |
| PredictionPosition schema | feature-request.md:555-558 | base_rate_anchor, falsification_criteria as REQUIRED fields |
| archetype-reasoning skill | sub-agents-analysis.md:74 | skills: [oathfish:archetype-reasoning] at subagent boot |

---

## Coupling Analysis

### Coupled Components

| From | To | Type | Risk |
|------|-----|------|------|
| Archetype persona_prompt | --system-prompt flag | Data | H-01: prompt length > context limit |
| PredictionPosition schema | --json-schema flag | Contract | H-02: schema mismatch crashes all calls |
| Grounding sources[] | Runtime web search | Runtime dependency | H-03: web search failure degrades grounding |
| Structural archetype definitions | understand/SKILL.md | Hard-coded | H-04: changes require skill file edit |
| Persona variation delta | --append-system-prompt | Composition | H-05: delta + base > context limit |
| Deliberation session_id | --resume flag | Session coupling | H-06: stale/corrupted session crashes calls |
| amplify_aggregate() | PredictionPosition fields | Schema contract | H-07: schema changes break aggregation |
| Superforecaster methodology | archetype-reasoning skill | Skill injection | H-08: methodology inconsistency across archetypes |
| Cost tracking | ResultMessage.total_cost_usd | SDK contract | None -- read-only |

### Decoupled Components (safe to modify independently)

| A | B | Evidence | Implication |
|---|---|----------|-------------|
| Structural archetypes | Topic-customized archetypes | Different generation paths (pre-defined vs LLM-generated) per feature-request.md:796-808 | Can iterate on structural prompts without affecting topic generation |
| BASELINE_AMPLIFY | AMPLIFY | Different state (no --resume vs --resume) per feature-request.md:1169 (C-21) | Baseline engine is a subset of AMPLIFY engine |
| Archetype generation | Amplification SDK | archetypes.json is the clean interface | Can change generation without touching amplification |
| Persona variation algorithm | Core archetype identity | --append-system-prompt is additive per headless-analysis.md:93 | Variations never modify base identity |
| MCP aggregation | SDK execution | batch JSON files are the interface per feature-request.md:1103 | Can change SDK without touching MCP |

---

## Hazard Registry

| H-ID | Category | Hazard | Evidence | Failure Mode | Severity |
|------|----------|--------|----------|--------------|----------|
| H-01 | Integration | Archetype persona_prompt exceeds --system-prompt context limit. Rich personas (2000+ words per MiroFish pattern at oasis_profile_generator.py:702) + grounding sources + superforecaster methodology could exceed model's context budget for system prompts. | oasis_profile_generator.py:702 (2000-word persona), feature-request.md:691-724 (persona structure), headless.md:113-115 (--system-prompt replaces default) | Persona truncated silently; archetype loses identity/methodology | High |
| H-02 | Contract | PredictionPosition JSON schema mismatch between Pydantic model definition and --json-schema parameter. Schema must be identical in SDK code and MCP server models.py. | feature-request.md:546-561 (schema definition), headless-analysis.md:57 (model_json_schema() generates schema) | All 1500 amplification calls fail with error_max_structured_output_retries | Critical |
| H-03 | Integration | Runtime web search for archetype grounding sources may fail, timeout, or return low-quality results. No existing search infrastructure in the project. | feature-request.md:1144 (C-29 requires web search), no search code exists | Archetypes fall to Rung 1 (synthetic, ungrounded); fidelity degrades per 2411.10109 findings | Medium |
| H-04 | Data | Structural archetype definitions hard-coded in understand/SKILL.md but also referenced by MCP models.py for schema validation. Dual source of truth. | feature-request.md:800-805 (definitions), feature-request.md:523-534 (Archetype model) | Structural archetype drift between skill definition and MCP validation | Medium |
| H-05 | Performance | --system-prompt (archetype identity) + --append-system-prompt (variation delta) combined may exceed the input context budget, especially with --resume loading deliberation history. | headless-analysis.md:93 (dual system prompts), headless-analysis.md:227 (resume loads 100K+ tokens) | Post-deliberation amplification calls fail or truncate; cost spikes 10-50x per call | High |
| H-06 | State | --resume SESSION_ID for post-deliberation amplification loads the full deliberation transcript. If session file is corrupted, deleted, or cwd mismatches, all post-deliberation calls fail. | headless-analysis.md:87-88 (session mechanics), headless-analysis.md:77-78 (cwd must match) | Post-deliberation amplification completely fails; only baseline results available | High |
| H-07 | Contract | MCP amplify_aggregate() depends on specific field names in PredictionPosition (decision, confidence, stance, etc.). If schema evolves without matching aggregation logic, distributions are wrong. | feature-request.md:546-561 (schema), feature-request.md:472-481 (aggregate logic) | Silent incorrect distributions; calibration data poisoned | Critical |
| H-08 | Consistency | Superforecaster methodology must be identical across: (1) structural archetype prompts, (2) topic-customized archetype prompts, (3) archetype-reasoning skill, (4) PredictionPosition schema required fields. Four sources of truth for one protocol. | feature-request.md:1145 (C-30), sub-agents-analysis.md:74 (skill injection), feature-request.md:555 (schema fields) | Inconsistent methodology across archetypes violates C-30; some archetypes skip base rates or falsification | High |
| H-09 | Performance | 1500 concurrent amplification calls (30 archetypes x 50 variations) overwhelm rate limits. Even with Semaphore, burst patterns cause cascading retries. | feature-request.md:1160 (C-17: 500-5000 calls), headless-analysis.md:243 (rate limits near-certain at 1500) | Amplification batch stalls; partial results; inconsistent batch completion | Medium |
| H-10 | Data | Persona variation algorithm may produce variations too similar to each other (low inter-variation diversity) or too different from base archetype (identity loss). No diversity metric defined. | feature-request.md:866-867 (variation described), no variation diversity metric exists | Effective amplification sample size much smaller than 50 per archetype; or variations no longer represent the archetype | Medium |
| H-11 | Domain | Grounding ladder rung assessment is subjective. No formal criteria for distinguishing Rung 1 from Rung 2 from Rung 3. Report says "grounding_rung per archetype" but no scoring rubric defined. | feature-request.md:1144 (C-29 mentions rung 1-4), no rubric exists in any doc | Inconsistent rung reporting; grounding quality claims are unverifiable | Medium |
| H-12 | Integration | The 4 structural archetypes claim pre-curated grounding sources (Gartner hype cycles, Carlota Perez, Donella Meadows, Tetlock, etc.) but no actual URLs or document references exist in the codebase. | feature-request.md:802-805 (claims sources), no URLs or files exist | Structural archetypes ship as Rung 1 (synthetic) despite claiming Rung 3; contradicts C-36 | High |
| H-13 | Domain | Topic-customized archetype generation by LLM may produce archetypes that overlap with structural archetypes (e.g., generating a "Risk Analyst" that duplicates the Probabilist's role). | feature-request.md:789-795 (selection principles), feature-request.md:807-808 (26 topic-customized) | Effective ensemble diversity reduced; 30 archetypes act like 26 or fewer | Medium |
| H-14 | Contract | --resume SESSION_ID for post-deliberation amplification: documentation says "cwd must match" (headless-analysis.md:78). If amplification SDK runs from a different working directory than deliberation, resume fails silently. | headless-analysis.md:77-78 (cwd must match) | All post-deliberation amplification calls silently start fresh sessions instead of resuming | High |

---

## Constraint Registry

| C-ID | Type | Constraint | Source | Verified | Evidence |
|------|------|------------|--------|----------|----------|
| C-29 | REQUIREMENT | Ground each archetype in 3-5 real public sources via runtime web search during UNDERSTAND | feature-request.md:1144 | INHERITED | User stated; no implementation exists |
| C-30 | REQUIREMENT | Superforecaster methodology in every archetype prompt (decompose, base rate, falsify) | feature-request.md:1145 | INHERITED | User stated; no implementation exists |
| C-36 | REQUIREMENT | 4 structural archetypes (Historian, Systems Thinker, Contrarian, Probabilist) in every run | feature-request.md:1151 | INHERITED | User stated; definitions exist at feature-request.md:800-805 |
| C-37 | INVARIANT | Structural archetypes are epistemic lenses, not stakeholder personas | feature-request.md:1152 | INHERITED | User stated |
| C-21 | LIMITATION | claude -p has two modes: baseline (stateless) and post-deliberation (--resume) | feature-request.md:1169 | YES | headless.md:132-134 confirms --resume mechanics |
| C-05 | REQUIREMENT | Mass amplification uses claude -p CLI, not Teams | feature-request.md:1126 | YES | headless.md:14-16 confirms -p mode |
| C-09 | REQUIREMENT | Archetypes customized per topic | feature-request.md:1130 | INHERITED | No generation code exists yet |
| C-17 | SCALABILITY | Mass amplification handles 500-5000 calls | feature-request.md:1160 | INHERITED | SDK supports async parallel per headless-analysis.md:89 |
| C-26 | REQUIREMENT | A/B test: baseline amplification BEFORE deliberation | feature-request.md:1141 | INHERITED | User stated |
| C-33 | REQUIREMENT | No numeric predictions shared until final round | feature-request.md:1148 | INHERITED | PreToolUse hook per feature-request.md:646-651 |

### Constraint Conflicts

| REQUIREMENT | LIMITATION | Evidence | Severity |
|-------------|------------|----------|----------|
| C-29 (ground in 3-5 real sources) | No web search infrastructure exists | No search tool or API in project | HIGH -- grounding is a MUST but mechanism undefined |
| C-30 (superforecaster in every prompt) | System prompt length limited | Rich persona + methodology + sources may exceed limits | MEDIUM -- may need prompt compression |

---

## Lens-Specific Findings: Domain Logic

### 1. Structural Archetype Design Logic

The 4 structural archetypes serve fundamentally different roles from topic-customized archetypes. Per C-37 (`feature-request.md:1152`), they are epistemic lenses -- methodological frameworks, not stakeholder personas. This creates a critical design distinction:

**Topic-customized archetype prompt structure** (feature-request.md:691-724):
- "You are {archetype_name}, representing the {segment} population segment"
- Demographics, values, incentives, blind spots, communication style
- Stakeholder-centered: "What does YOUR segment think about this?"

**Structural archetype prompt structure** (must be DIFFERENT):
- "You are The Historian, an epistemic lens applied to any topic"
- Methodology, analytical framework, canonical references
- Method-centered: "What does HISTORY say about this pattern?"

The feature request's persona template at `:691-724` is designed for topic-customized archetypes. The 4 structural archetypes need a SEPARATE prompt template that foregrounds methodology over identity.

Evidence: The table at `feature-request.md:800-805` explicitly specifies "Role" and "Grounding Sources" per structural archetype, with research rationale. The "Role" column describes analytical methods (base rate authority, second-order effects, adversarial dissent, formal calibration), NOT stakeholder perspectives.

### 2. Superforecaster Methodology is Double-Layered

C-30 (`feature-request.md:1145`) requires superforecaster methodology in EVERY archetype prompt. But the 4 structural archetypes each embody a DIFFERENT aspect of the superforecaster methodology:

| Structural Archetype | Superforecaster Component | Evidence |
|---------------------|---------------------------|----------|
| The Historian | Base rate anchoring | feature-request.md:802 ("base rate authority, pattern matching across eras") |
| The Systems Thinker | Decomposition into sub-components | feature-request.md:803 ("second-order effects, feedback loops") |
| The Contrarian | Falsification and adversarial challenge | feature-request.md:804 ("explicit incentive to argue AGAINST emerging consensus") |
| The Probabilist | Formal calibration and uncertainty quantification | feature-request.md:805 ("formal calibration, uncertainty quantification, Bayesian updating") |

This means:
- Topic-customized archetypes get the FULL superforecaster protocol as an overlay (all 4 components)
- Each structural archetype SPECIALIZES in one component but still performs all 4
- The structural archetypes together form a complete superforecaster methodology team

### 3. Runtime Source Discovery Architecture

C-29 (`feature-request.md:1144`) requires "web search to find interviews, hearing transcripts, published frameworks, or public statements." The feature request does not specify HOW web search is performed.

Design decision needed: The Claude Code Agent SDK does not include a built-in web search tool. Options:
1. Use `Bash` tool to run `curl` against a search API (Google Custom Search, Brave Search API)
2. Use an MCP server that provides web search (e.g., a search MCP)
3. Use Claude Code's built-in web browsing capability (if available in the target Claude Code version)
4. Use the `WebFetch` tool documented in Claude Code for fetching known URLs

The grounding protocol should:
- Generate search queries based on each archetype's domain and the topic
- Fetch 3-5 results per archetype
- Extract relevant excerpts
- Inject excerpts into the archetype's persona_prompt
- Report grounding_rung based on source quality

### 4. Persona Variation Algorithm Design

The feature request describes two variation axes (`feature-request.md:866-867`):
- **Demographic variation**: age, location, education, experience level
- **Personality variation**: enthusiasm, skepticism, caution, boldness

MiroFish's approach at `oasis_profile_generator.py:28-58` uses fixed fields (age, gender, mbti, country, profession, interested_topics) with random sampling. OathFish needs STRUCTURED variation that preserves archetype core identity.

The --append-system-prompt mechanism (`headless-analysis.md:93`) enables compositional variation:
- Base: `--system-prompt $ARCHETYPE_IDENTITY` (fixed per archetype)
- Delta: `--append-system-prompt $VARIATION_DELTA` (varies per call)

The variation delta must be a SHORT modifier, not a full persona rewrite. Example:
```
VARIATION: You are a version of this archetype who is 25 years old (instead of the
typical 45), based in Austin TX (instead of SF), with 3 years industry experience.
You are more optimistic than the prototype and slightly less risk-averse.
Apply the same analytical framework but from this demographic position.
```

This keeps the core archetype identity intact while shifting demographic and personality parameters.

### 5. Python SDK Amplification Engine Data Flow

Complete data flow trace for a single amplification call:

```
1. Load archetype from archetypes.json
   → Extract persona_prompt (includes grounding sources + superforecaster methodology)

2. Generate variation delta
   → Demographic params: sample from demographic ranges for this archetype
   → Personality params: sample from personality spectrum
   → Format as --append-system-prompt text

3. Construct ClaudeAgentOptions:
   → system_prompt = archetype.persona_prompt
   → append_system_prompt = variation_delta
   → output_format = {"type": "json_schema", "schema": PredictionPosition.model_json_schema()}
   → model = "haiku"
   → fallback_model = "sonnet"
   → max_turns = 1
   → max_budget_usd = 0.05
   → tools = "" (disabled)
   → resume = None (BASELINE) or session_id (AMPLIFY)

4. Execute: async for msg in query(prompt=scenario_text, options=options)

5. Collect ResultMessage:
   → structured_output → PredictionPosition.model_validate()
   → total_cost_usd → accumulate
   → is_error → retry with backoff
   → session_id → log for traceability

6. Batch results → MCP amplify_record_batch()
7. After all calls → MCP amplify_aggregate()
```

### 6. Dual-Mode Amplification Logic

The two amplification modes have distinct data flow patterns:

**BASELINE_AMPLIFY (C-26, C-21):**
- Runs BEFORE deliberation
- No --resume flag
- No deliberation context
- Pure archetype identity + variation
- Produces uncontaminated control predictions
- State transition: UNDERSTAND -> BASELINE_AMPLIFY

**AMPLIFY (post-deliberation, C-21):**
- Runs AFTER deliberation
- Uses --resume $DELIBERATE_SESSION_ID
- Loads full deliberation transcript into context
- Same archetype identity + variation + deliberation context
- Produces deliberation-informed predictions
- State transition: DELIBERATE -> AMPLIFY

Both use identical: --json-schema, --model, --system-prompt, --append-system-prompt, --max-turns, --tools.
Only difference: presence/absence of --resume.

The Python SDK engine MUST be parameterized to handle both modes with a single code path:
```python
async def run_amplification(
    archetypes: list[Archetype],
    scenario: str,
    mode: Literal["baseline", "informed"],
    session_id: Optional[str] = None,  # Only for "informed" mode
    ...
)
```

---

## Handoff to Plan

Key constraints for implementation:

1. MUST design two distinct prompt templates: one for structural archetypes (methodology-first, C-37) and one for topic-customized archetypes (stakeholder-first, C-09). Both include superforecaster methodology (C-30).

2. MUST define exact PredictionPosition JSON schema as single source of truth shared between MCP models.py and SDK amplification engine (mitigates H-02, H-07).

3. MUST design persona variation algorithm with diversity constraints to prevent both identity loss and insufficient variation (mitigates H-10).

4. MUST specify web search mechanism for runtime source discovery (mitigates H-03) and grounding rung rubric (mitigates H-11).

5. MUST ensure --resume session cwd matches amplification cwd (mitigates H-14) and handle session corruption gracefully (mitigates H-06).

6. MUST create pre-curated grounding source lists for all 4 structural archetypes with actual URLs/references (mitigates H-12).

7. MUST design Python SDK amplification engine with: asyncio.Semaphore rate limiting, exponential backoff retry, progress callbacks, per-call cost tracking, dual-mode support (baseline vs informed).

8. MUST establish superforecaster methodology as a SINGLE source of truth (archetype-reasoning skill) injected into all archetype prompts (mitigates H-08).
