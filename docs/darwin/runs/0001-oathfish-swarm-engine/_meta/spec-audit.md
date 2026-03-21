# Spec Audit Report (v3.0 — Post-Research Revision)
## Run: 0001-oathfish-swarm-engine

---

## Verdict

**Status**: BLOCKED

**Blocking Issues**: 5 (3 CRITICAL contradictions, 2 unresolved ambiguities)

- SPEC-01: Position data model requires numeric stance/confidence every round, but C-33 forbids numbers until round 6
- SPEC-02: C-26 (baseline amplification BEFORE deliberation) contradicts the state machine flow (UNDERSTAND -> DELIBERATE -> AMPLIFY)
- SPEC-03: `--resume SESSION_ID` used in amplification contradicts C-21 (claude -p is stateless)
- AMB-01: C-14 says "argument evolution tracked rounds 1-5" but the MCP tool `deliberation_track_evolution()` computes stance deltas (numeric) -- how does evolution tracking work without numbers?
- AMB-02: C-29 (ground in 3-5 real sources) + C-09 (archetypes customized per topic) -- who curates sources for arbitrary topics at runtime?

**Non-Blocking Issues**: 6 warnings

---

## Phase 1: Constraint Ledger (All 35 Constraints)

### 6.1 Functional Requirements (C-01 through C-14)

| C-ID | Type | Constraint | Feasibility | Evidence |
|------|------|------------|-------------|----------|
| C-01 | REQUIREMENT | Claude Code plugin structure | FEASIBLE | Plugin scaffold pattern exists in oathe-research |
| C-02 | REQUIREMENT | Deterministic ops in Python MCP server | FEASIBLE | Python stdlib + Pydantic sufficient |
| C-03 | REQUIREMENT | Creative ops by Claude agents | FEASIBLE | Proven in oathe-research debate skill |
| C-04 | REQUIREMENT | Claude Teams with 30 archetypes via SendMessage | FEASIBLE with WARNING | Max tested ~10; 32 is untested |
| C-05 | REQUIREMENT | Mass amplification via `claude -p`, not Teams | FEASIBLE | CLI piped mode documented |
| C-06 | REQUIREMENT | MCP stdio transport via .mcp.json | FEASIBLE | Standard pattern |
| C-07 | REQUIREMENT | 5-phase state machine: UNDERSTAND->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT | FEASIBLE | oathe-research has identical pattern |
| C-08 | REQUIREMENT | 30 archetypes with persistent identity and memory across rounds | FEASIBLE | memory:project in subagent config |
| C-09 | REQUIREMENT | Archetypes customized per topic | FEASIBLE | LLM generates personas dynamically |
| C-10 | REQUIREMENT | 4 round types + INDEPENDENT_PREDICTION | FEASIBLE | Coordinator prompt templates |
| C-11 | REQUIREMENT | Report combines qualitative reasoning + quantitative stats | FEASIBLE | ReACT report pattern proven |
| C-12 | REQUIREMENT | All state mutations through MCP server | FEASIBLE | Archetype agents lack Write tool |
| C-13 | REQUIREMENT | Hybrid sentiment: 0.7 keyword + 0.3 LLM | FEASIBLE with WARNING | LLM component is non-deterministic; see WARNING-03 |
| C-14 | REQUIREMENT | Argument evolution tracked rounds 1-5; numeric positions only round 6 | CONFLICT | See SPEC-01, AMB-01 |

### 6.1b Research-Mandated Requirements (C-26 through C-35)

| C-ID | Type | Constraint | Feasibility | Evidence |
|------|------|------------|-------------|----------|
| C-26 | REQUIREMENT | A/B test: baseline amplification BEFORE deliberation every run | CONFLICT | See SPEC-02 |
| C-27 | REQUIREMENT | Per-domain acquiescence tracking from run 1; corrections from run 3+ | FEASIBLE | Domain-keyed storage in calibration engine |
| C-28 | REQUIREMENT | Report both corrected AND raw Brier scores | FEASIBLE | Two parallel metric paths |
| C-29 | REQUIREMENT | Ground each archetype in 3-5 real public sources | CONFLICT | See AMB-02 |
| C-30 | REQUIREMENT | Superforecaster methodology in every archetype prompt | FEASIBLE | Prompt template addition |
| C-31 | REQUIREMENT | Question competence classifier before UNDERSTAND | FEASIBLE with WARNING | See WARNING-05 |
| C-32 | REQUIREMENT | Diversity index per round; premature consensus triggers contrarian injection | FEASIBLE | Std dev of argument themes computable |
| C-33 | REQUIREMENT | No numeric predictions shared until final independent round | CONFLICT | See SPEC-01 |
| C-34 | REQUIREMENT | Holdout 20% of resolved predictions from calibration loop | FEASIBLE | Random partition at recording time |
| C-35 | REQUIREMENT | Submit to ForecastBench before public accuracy claims | FEASIBLE | External API submission |

### 6.2 Non-Functional (C-15 through C-17)

| C-ID | Type | Constraint | Feasibility |
|------|------|------------|-------------|
| C-15 | REQUIREMENT | Disk persistence after every mutation | FEASIBLE | Write-through caching |
| C-16 | REQUIREMENT | Any phase resumable from checkpoint | FEASIBLE | State machine + checkpoint data |
| C-17 | REQUIREMENT | Mass amplification handles 500-5000 calls | FEASIBLE | Parallel execution via Python SDK |

### 6.3 Limitations (C-18 through C-21)

| C-ID | Type | Constraint | Feasibility |
|------|------|------------|-------------|
| C-18 | LIMITATION | Claude Teams ~30 concurrent agents max | ACKNOWLEDGED |
| C-19 | LIMITATION | Python MCP server, no heavy deps | ACKNOWLEDGED |
| C-20 | LIMITATION | Archetype agents have Read + SendMessage only | ACKNOWLEDGED |
| C-21 | LIMITATION | `claude -p` calls are stateless | CONFLICT | See SPEC-03 |

### 6.4 Invariants (C-22 through C-25)

| C-ID | Type | Constraint | Feasibility |
|------|------|------------|-------------|
| C-22 | INVARIANT | Coordinator never computes metrics | GUARDED |
| C-23 | INVARIANT | All state changes flush to disk immediately | GUARDED |
| C-24 | INVARIANT | User checkpoints every 3 rounds | GUARDED |
| C-25 | INVARIANT | Archetypes never told what position to take | GUARDED |

---

## Phase 2: Contradictions Detected

### SPEC-01: Position Data Model vs Arguments-Only Deliberation [CRITICAL]

**Pattern**: Internal structural contradiction (no impossibility-patterns.md match -- this is novel)

**Constraint A**: C-33 (REQUIREMENT) -- "No numeric predictions shared between archetypes until final independent round." C-14 (REQUIREMENT, revised) -- "Argument evolution tracked rounds 1-5; numeric position tracked only in round 6."

**Constraint B (implicit)**: The Position Pydantic model (feature-request.md line 531-539) requires `stance: float` and `confidence: float` as mandatory fields for EVERY round. The `deliberation_record_round()` MCP tool (line 401-405) takes `positions array [{archetype_id, position_text, stance, confidence, key_arguments}]` -- again requiring numeric stance and confidence every round. The archetype persona prompt template (lines 696-702) instructs: "STANCE: [number from -1.0 to 1.0]" and "CONFIDENCE: [0-100%]" as part of EVERY response format.

**The contradiction**: Three separate components of the spec (data model, MCP API, persona prompt) assume archetypes produce numeric stances every round. But C-33 and C-14 (as revised) mandate no numbers until round 6. The data model, tool API, and prompt template are UNREVISED artifacts from v2 that directly contradict the v3 research-mandated constraints.

**Severity**: CRITICAL -- This is a structural data model conflict. Workers implementing the MCP server will build Position with mandatory float fields. Workers implementing deliberation will enforce C-33 (no numbers). These two implementations are incompatible.

**Resolution options**:
1. Split Position into ArgumentPosition (rounds 1-5: text-only fields) and PredictionPosition (round 6: full structured JSON with numeric fields)
2. Make stance and confidence Optional[float] with None for rounds 1-5
3. Revise the archetype prompt template to have two response formats: argument format (rounds 1-5) and prediction format (round 6)

---

### SPEC-02: Baseline Amplification Timing vs State Machine [CRITICAL]

**Pattern**: Temporal impossibility (novel)

**Constraint A**: C-26 (REQUIREMENT) -- "A/B test: run baseline amplification BEFORE deliberation every run." The boundaries section (line 35) says: "Run baseline amplification BEFORE deliberation for A/B comparison every run." The architecture diagram (line 194-197) shows "BASELINE RUN FIRST" inside the AMPLIFY phase, stating "Run 1500 amplification calls BEFORE deliberation context."

**Constraint B**: C-07 (REQUIREMENT) -- State machine phases are strictly sequential: UNDERSTAND -> DELIBERATE -> AMPLIFY -> SYNTHESIZE -> INTERACT. The `state_transition()` tool (line 376) enforces: "Legal transitions: INIT->UNDERSTAND->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT->COMPLETE."

**The contradiction**: C-26 requires amplification to run BEFORE deliberation. C-07 requires DELIBERATE to complete before AMPLIFY can begin. These are mutually exclusive under the defined state machine.

The spec tries to resolve this by placing the baseline run inside the AMPLIFY phase (after deliberation), but that misses the point: a baseline must use PRE-deliberation archetype stances (initial positions from UNDERSTAND) without any deliberation context. If the baseline runs inside AMPLIFY (after 6 rounds of deliberation), the archetypes have already been exposed to all arguments. The `--resume SESSION_ID` flag means the baseline calls would carry deliberation memory, contaminating the baseline.

**Severity**: CRITICAL -- The A/B test infrastructure is meaningless if the baseline is contaminated by deliberation exposure. This is the core scientific control for validating whether deliberation adds value (the single most important finding from the research debate).

**Resolution options**:
1. Add a BASELINE_AMPLIFY sub-phase between UNDERSTAND and DELIBERATE. Run amplification with initial (pre-deliberation) archetype stances, then proceed to DELIBERATE, then run post-deliberation amplification in AMPLIFY.
2. Allow the state machine to support a branching flow: UNDERSTAND -> [BASELINE_AMPLIFY || DELIBERATE] -> AMPLIFY -> ...
3. Do NOT use `--resume` for baseline calls. Baseline calls use only the UNDERSTAND-phase archetype definitions (no deliberation session to resume from).

---

### SPEC-03: `--resume SESSION_ID` vs `claude -p` Statelessness [CRITICAL]

**Pattern**: SEM-001 (Stateless Memory) from impossibility-patterns.md

**Constraint A**: Feature-request.md line 205 specifies amplification calls use `--resume $DELIBERATE_SESSION_ID` to carry deliberation context. Line 70 states: "Session continuity from deliberation via `--resume`." The in-scope list (line 308) includes: "Python SDK amplification engine (replaces bash script; --json-schema, --resume, async)."

**Constraint B**: C-21 (LIMITATION) -- "`claude -p` calls are stateless. Mass layer cannot remember previous calls -- all context must be in prompt." C-05 verification reads: "500+ parallel stateless calls complete." The architecture table (line 78-81) explicitly contrasts: "Deep layer: Full memory" vs "Mass layer: None -- fresh context each call."

**The contradiction**: `--resume SESSION_ID` makes the call stateful (it loads a prior conversation). C-21 says the calls are stateless. These are mutually exclusive. If `--resume` is used, the calls are no longer stateless, no longer cheap (they load full conversation history), and no longer independent (they share a deliberation session). If C-21 is enforced, `--resume` cannot be used.

Furthermore, if `--resume` loads a shared deliberation session, all 1500 amplification calls share the same session context. This is both a correctness concern (shared state between "independent" predictions) and a cost concern (each call loads the full multi-round deliberation transcript).

**Severity**: CRITICAL -- Directly matches SEM-001 impossibility pattern (stateless + remember).

**Resolution options**:
1. Drop `--resume` entirely. Inject a SUMMARY of deliberation insights into the amplification prompt context (e.g., key argument themes, evolved positions). This preserves statelessness while transferring deliberation value.
2. Use `--resume` but acknowledge that amplification calls are NOT stateless. Update C-21 to: "Mass layer carries deliberation context via --resume but does not accumulate state across amplification calls."
3. Create a "deliberation digest" artifact at the end of DELIBERATE that summarizes key insights, and inject that into amplification prompts as text. No --resume needed.

---

## Phase 3: Ambiguities Detected

### AMB-01: How Does Evolution Tracking Work Without Numbers? [BLOCKING]

**Statement**: C-14 says "Argument evolution tracked round-by-round per archetype (qualitative rounds 1-5); numeric position tracked only in round 6." But the MCP tool `deliberation_track_evolution(round_n)` (line 407-410) is defined as: "Computes position deltas between round N and N-1 for each archetype. Detects: stance changes, confidence shifts, new arguments introduced, arguments abandoned. Output: {evolutions: [{previous_stance, new_stance, delta, shift_reason}]}"

**Problem**: The tool output schema includes `previous_stance`, `new_stance`, and `delta` -- all numeric fields. If no numbers exist in rounds 1-5, what do these fields contain? The tool literally cannot compute "position deltas" without numeric positions.

Similarly, `deliberation_check_convergence(window_size)` (line 413-416) uses "average absolute stance delta across all archetypes" with "Convergence threshold: avg_delta < 0.1." This metric requires numeric stances every round.

The diversity monitoring (line 177-183) says "track diversity index" but uses "argument theme spread" -- a qualitative measure. Meanwhile, C-32 says "Diversity index tracked per deliberation round; premature consensus triggers contrarian injection." What is the diversity index computed from if there are no numeric stances in rounds 1-5?

**Clarification needed**: What EXACTLY does "argument evolution tracking" mean for qualitative rounds? Options:
1. Track argument THEMES (new arguments introduced, arguments abandoned, influence chains) -- purely qualitative. The `deliberation_track_evolution()` tool needs a redesigned output schema without numeric deltas.
2. Archetypes DO produce internal numeric stances (private, not shared with other archetypes) that feed into evolution tracking. The "no numbers" rule means no SHARING of numbers, not no PRODUCTION of numbers.
3. Use NLP-based or LLM-based stance classification on the qualitative text to infer approximate stances (but this violates C-02: deterministic MCP).

**Why this blocks**: Workers implementing the deliberation engine will need to choose between incompatible approaches. Option 1 requires redesigning the MCP API. Option 2 is an important nuance that must be specified. Option 3 introduces non-determinism.

---

### AMB-02: Source Curation for Arbitrary Topics at Runtime [BLOCKING]

**Statement**: C-29 requires "Ground each archetype in 3-5 curated real public sources before production." C-09 requires "Archetypes are customized per topic, not a fixed generic set."

**Problem**: If archetypes are generated dynamically per topic, they do not exist before runtime. Who curates 3-5 real public sources for 30 archetypes (90-150 sources total) generated on-the-fly for an arbitrary user query?

The research-driven-redesign.md (line 307) says "Before production, each archetype grounded in 3-5 curated real-world sources (public interviews, published decision frameworks, hearing transcripts)." This implies MANUAL curation before the system is used. But C-09 requires archetypes to be topic-specific (dynamically generated), which means the sources would need to be found and curated at runtime.

**Clarification needed**: Which of these is intended?
1. **Pre-curated archetype library**: Build a library of ~100 pre-grounded archetypes, and SELECT 30 per topic from this library. This satisfies C-29 (pre-curated sources) but weakens C-09 (not truly "customized per topic" -- selected from fixed set).
2. **Runtime source discovery**: During UNDERSTAND phase, the system finds and evaluates public sources for each generated archetype. This satisfies C-09 but makes C-29 dependent on source discovery quality at runtime (may find poor or no sources for niche archetypes).
3. **Hybrid**: Pre-curated core archetypes (VCs, founders, regulators) + dynamically generated niche archetypes that start at "Rung 1" (synthetic) and can be grounded later. Report honestly discloses which archetypes are grounded vs ungrounded.

**Why this blocks**: The grounding protocol is a Tier 2 research recommendation (scored 33/40). If it cannot be operationalized for dynamic topic-based archetypes, the spec needs to honestly acknowledge that limitation rather than listing it as a MUST requirement.

---

## Phase 4: Research Citation Accuracy Check

### Accurately Represented Citations

| Claim | Source | Verdict |
|-------|--------|---------|
| Simple averaging beats LLM updating (p=0.011 GPT-4, p=0.001 Claude 2) | 2402.19379 Study 2 | ACCURATE -- paper says exactly this |
| 57% positive prediction rate (acquiescence bias, p<0.001) | 2402.19379 acquiescence finding | ACCURATE -- M=57.35, t(1006)=86.20, p<0.001 |
| 85% fidelity with real interview data | 2411.10109 abstract | ACCURATE -- "85% as accurately as participants replicate their own answers" |
| Superforecasters significantly outperform LLMs (p<0.001) | 2409.19839 finding #1 | ACCURATE |
| Stubborn prompts produce better outcomes | 2305.14325 finding #2 | ACCURATE -- "more stubborn led to LONGER debates and BETTER final solutions" |
| 87.3% calibration variance explained by 4 components | 2602.19520 table | ACCURATE |
| Domain-level bias detectable at n=90 | Research debate extrapolation | SEE BELOW |

### Potentially Misleading Citation

| Claim | Issue | Severity |
|-------|-------|----------|
| SC-11: "Target Brier < 0.122 (beating best individual LLM)" | The 0.122 figure does not appear in the ForecastBench paper (2409.19839). The paper reports o3 at 0.1352 as the best LLM. The ensemble paper (2402.19379) reports GPT-4 at 0.15 on 31 questions. Where does 0.122 come from? | MEDIUM |
| SC-11: "within first 3 runs" | No research basis for this timeline. The papers tested single-shot predictions, not iterative improvement across runs. | LOW |
| C-27: "corrections from run 3+ where n>=90/domain" | The n=90 power analysis (2602.19520) is for prediction MARKET calibration with 292 million trades. Extrapolating to 30 archetypes x 3 runs = 90 predictions assumes comparable statistical properties. LLM predictions may have very different error structures than market prices. | MEDIUM |
| A-07: "80% power at d=0.3 with n=90" | The d=0.3 effect size is the calibration paper's finding for prediction markets. LLM acquiescence bias is much larger (12pp per 2402.19379), so d=0.3 may be conservative -- but the sample composition is fundamentally different (market trades vs LLM predictions). | LOW |

---

## Phase 5: Success Criteria Threshold Analysis (SC-11 through SC-14)

### SC-11: "Submit 100+ predictions to ForecastBench. Achieve Brier < 0.122 within first 3 runs."

**Assessment**: AMBITIOUS. The best individual LLM (o3) achieves 0.1352 per ForecastBench. No ensemble of a SINGLE model family has been tested. The 0.122 threshold would require OathFish to beat every individual LLM on the leaderboard within 3 runs. This is possible in theory (ensemble effect) but the paper-ensemble consensus was "effective ensemble size may be 3-5, not 30" due to single-model correlation (WARNING-07). A more honest threshold would be "Brier < 0.135 (matching best individual LLM)" for the first 3 runs, with < 0.122 as a stretch goal.

### SC-12: "Debiasing improves Brier by >= 0.01 after 5 runs."

**Assessment**: REASONABLE. The acquiescence bias is quantified at 12pp (2402.19379), so a 0.01 Brier improvement from correcting it is plausible. However, the 5-run timeline assumes sufficient outcome resolution. Per paper-calibration (resolution latency risk, A-09), most primary predictions resolve in 3-12 months. After 5 runs (at what cadence?), the system may have very few resolved outcomes. The success criterion should specify that the 5 runs include short-horizon bootstrap questions (per C-34 mitigation).

### SC-13: "Deliberation outperforms baseline on at least one question type."

**Assessment**: REASONABLE but UNFALSIFIABLE as written. "At least one question type" sets a very low bar -- the spec only defines two types (simple binary, multi-factor). Outperforming on one of two categories is a coin flip if the effect is noise. Should specify: "statistically significant improvement (p < 0.10) on multi-factor questions."

### SC-14: "At least 2/6 domains show significant directional bias (p<0.10) after 5 runs."

**Assessment**: REASONABLE. Per paper-calibration, domain-level bias is detectable with moderate sample sizes. However, the "6 domains" are not defined anywhere in the spec. What are the six domains? If the system handles arbitrary topics, how are domains categorized? This is an implicit dependency.

---

## Phase 6: Additional Warnings (Non-Blocking)

### WARNING-01: Claude Teams Scale at 32 Members (HIGH)

**Carried from v2 audit.** Persistent subagent architecture (v3 change) may mitigate this if archetypes are spawned per-round rather than kept as permanent Team members. However, the spec says "All 30 archetype agents remain alive in the Team" for the INTERACT phase (line 240). This means 30 subagents + coordinator + report analyst = 32 concurrent members for the full run duration.

### WARNING-03: Hybrid Sentiment Non-Determinism (MEDIUM)

**Carried from v2 audit.** Still applies. The 0.3 LLM component of sentiment introduces non-determinism into blended scores. If these scores feed into convergence detection, C-02 is violated. The v3 revision did not address this.

### WARNING-05: Competence Classifier is Underspecified (MEDIUM)

**New.** C-31 requires a "question competence classifier before UNDERSTAND phase." The spec provides no detail on:
- What model/method performs classification (LLM call? rule-based?)
- What the domain taxonomy is (how many categories? what defines "in-domain"?)
- How the archetype set's "domain-relevant perspectives" are assessed before archetypes are generated (they are generated IN the UNDERSTAND phase, but the classifier runs BEFORE UNDERSTAND)
- What "base-rate-only" mode means for out-of-domain questions

### WARNING-06: Deliberation May Destroy Value (CRITICAL per research, HIGH as warning)

**New.** The research consensus is that deliberation may HARM accuracy on simple binary questions (2402.19379). The spec acknowledges this but the state machine still routes ALL questions through DELIBERATE unless the competence classifier (C-31) routes them to skip. Since the competence classifier is underspecified (WARNING-05), the safeguard against deliberation-destroys-value is not operationalized.

### WARNING-07: Single-Model Correlated Failures (HIGH)

**New.** 30 Claude instances share training data, RLHF objectives, and reasoning patterns. The effective ensemble size may be 3-5, not 30 (paper-ensemble Round 3). No mitigation is specified beyond "monitor inter-archetype correlation." The spec should honestly state this as a known limitation of the single-model architecture.

### WARNING-08: Archetype Prompt Template Not Updated for v3 (MEDIUM)

**New.** The archetype persona prompt template (Section 4.2.2, lines 671-703) still instructs archetypes to output "STANCE: [number from -1.0 to 1.0]" and "CONFIDENCE: [0-100%]" in every response. This template was written for v2 (numbers every round) and not updated for v3 (arguments-only rounds 1-5). While this is subsumed by SPEC-01, it is worth noting as a concrete artifact that needs updating.

---

## Phase 7: Specific Conflict Analysis (Per Task Requirements)

### C-33 (no numbers until round 6) vs C-14 (position evolution tracking)

**Verdict**: CONFLICT. Addressed in SPEC-01 and AMB-01 above. The evolution tracking mechanism assumes numeric stances exist every round (computes deltas, convergence thresholds). Without numbers in rounds 1-5, the entire deliberation engine API surface (track_evolution, check_convergence, get_position_map) needs redesign.

### C-26 (baseline BEFORE deliberation) vs state machine flow

**Verdict**: CONFLICT. Addressed in SPEC-02 above. The state machine forbids AMPLIFY before DELIBERATE, but the baseline must run before deliberation to be an uncontaminated control.

### C-29 (ground in real sources) vs C-09 (archetypes per topic)

**Verdict**: AMBIGUOUS. Addressed in AMB-02 above. Cannot pre-curate sources for dynamically generated archetypes on arbitrary topics.

### C-31 (competence classifier) vs C-25 (archetypes never told what position)

**Verdict**: LOW RISK. The competence classifier routes questions to skip or include deliberation, but does not tell archetypes what position to take. Routing decisions do not influence individual archetype predictions -- they only determine whether deliberation occurs. However, if "out-of-domain" questions are routed to "base-rate-only" mode, the archetypes are effectively being told "don't reason deeply about this" which could be seen as constraining their reasoning. This is a philosophical tension, not a hard contradiction.

### Persistent subagent memory (memory:project) vs C-21 (claude -p stateless)

**Verdict**: CONFLICT (subsumed by SPEC-03). The `--resume` flag is the specific mechanism that breaks statelessness. Additionally, the persistent memory of subagents (memory:project) only works within the Team/subagent context, not in `claude -p` calls. So amplification calls cannot access deliberation memory via the subagent's memory:project store. The only mechanisms to transfer deliberation context to amplification are: (a) `--resume` (contradicts C-21), or (b) injecting summary text into prompts (no contradiction, but not specified).

---

## Summary of All Issues

### Blocking (Must Resolve Before Worker Dispatch)

| ID | Type | Summary | Severity |
|----|------|---------|----------|
| SPEC-01 | Contradiction | Position model/API/prompt assume numbers every round; C-33/C-14 forbid numbers until round 6 | CRITICAL |
| SPEC-02 | Contradiction | C-26 baseline must run BEFORE deliberation; C-07 state machine forbids AMPLIFY before DELIBERATE | CRITICAL |
| SPEC-03 | Contradiction | `--resume` in amplification contradicts C-21 statelessness; matches SEM-001 impossibility pattern | CRITICAL |
| AMB-01 | Ambiguity | Evolution tracking, convergence detection, and diversity index all require numeric stances that do not exist in rounds 1-5 | BLOCKING |
| AMB-02 | Ambiguity | Cannot pre-curate 3-5 real sources per archetype when archetypes are generated dynamically per topic | BLOCKING |

### Non-Blocking (Warnings for Worker Awareness)

| ID | Type | Summary | Severity |
|----|------|---------|----------|
| WARNING-01 | Scale risk | Claude Teams untested at 32 concurrent members | HIGH |
| WARNING-03 | Determinism | Hybrid sentiment LLM component may contaminate deterministic metrics | MEDIUM |
| WARNING-05 | Underspec | Competence classifier has no defined method, taxonomy, or behavior | MEDIUM |
| WARNING-06 | Research risk | Deliberation may destroy value on simple binaries; safeguard not operationalized | HIGH |
| WARNING-07 | Architecture | Single-model correlation limits effective ensemble to ~3-5 predictors | HIGH |
| WARNING-08 | Stale artifact | Archetype prompt template not updated for v3 arguments-only design | MEDIUM |

### Citation Concerns (Non-Blocking)

| ID | Issue | Severity |
|----|-------|----------|
| CIT-01 | SC-11 Brier threshold 0.122 has no paper source | MEDIUM |
| CIT-02 | n=90 power analysis extrapolated from market data to LLM predictions | LOW |

---

## Recommendations

1. **SPEC-01**: Create two Pydantic models: `ArgumentPosition` (rounds 1-5: archetype_id, round_n, position_text, key_arguments, concerns, influenced_by) and `PredictionPosition` (round 6: all fields including stance, confidence, base_rate, timeframe, falsification_criteria). Update `deliberation_record_round()` to accept either type based on round_type.

2. **SPEC-02**: Add a BASELINE_AMPLIFY step between UNDERSTAND and DELIBERATE. The state machine becomes: UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE -> AMPLIFY -> SYNTHESIZE -> INTERACT. Baseline uses initial archetype stances (no deliberation context, no --resume). Post-deliberation amplification uses evolved context.

3. **SPEC-03**: Drop `--resume` from amplification. Instead, create a "deliberation digest" artifact at the end of DELIBERATE that contains: key argument themes, evolved archetype positions (from round 6 predictions), notable insights. Inject this digest into amplification prompts as text context. This preserves C-21 statelessness while transferring deliberation value.

4. **AMB-01**: Decide between two tracking models:
   - Option A: Qualitative-only tracking (argument themes, influence chains, position text similarity). Redesign `deliberation_track_evolution()` and `deliberation_check_convergence()` to work with text, not numbers. Use LLM-based or keyword-based topic clustering for diversity index.
   - Option B: Private numeric stances. Archetypes produce internal stance numbers that are recorded by MCP but NEVER shared with other archetypes. Numbers are "private" to the tracking system. C-33 means "no numbers shared between archetypes," not "no numbers produced at all."

5. **AMB-02**: Adopt the hybrid approach. Pre-curate sources for ~20 common archetype templates (VCs, founders, regulators, consumers, etc.). For topic-specific archetypes that do not match pre-curated templates, honestly label them as "Rung 1" (synthetic, ungrounded) and disclose this in the report. Change C-29 from MUST to SHOULD, or scope it to: "Ground each archetype in 3-5 real public sources where curated sources exist; label ungrounded archetypes as synthetic."
