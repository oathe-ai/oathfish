# Skeptic Critique - Worker A: MCP Server Core Engines

---
verdict: UNSOUND
issues_critical: 2
issues_high: 4
issues_medium: 5
---

### Executive Verdict

**Status**: UNSOUND

**Top 3 Blockers**:
1. [SK-01] Cross-worker interface mismatch: Worker A defines `domain_corrections.json` file-based contract; Worker B defines `CalibrationEngine` object parameter. These are incompatible integration models.
2. [SK-02] State machine phase count claim is inconsistent: plan says "7-phase" but lists 8 phases (INIT, UNDERSTAND, BASELINE_AMPLIFY, DELIBERATE, AMPLIFY, SYNTHESIZE, INTERACT, COMPLETE). Feature request C-07 says "7 phases" and lists 7 (excluding INIT). The plan and explore both count differently.
3. [SK-03] Worker D defines PredictionPosition with `coalition_alignment: list[str]` (default_factory) field that Worker A's spec model at feature-request.md:546-561 does not include. Both workers claim to own `engine/models.py`. File ownership collision.

---

### Claim Ledger

| Claim-ID | Type | Statement | Source |
|----------|------|-----------|--------|
| C-01 | Hard | 7-phase state machine: INIT->UNDERSTAND->BASELINE_AMPLIFY->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT->COMPLETE | plan.md:17 |
| C-02 | Hard | 21 MCP tools total | plan.md:10 |
| C-03 | Hard | ArgumentPosition has NO stance/confidence fields | plan.md Proof Obligations |
| C-04 | Hard | PredictionPosition has stance and confidence as mandatory floats | plan.md Proof Obligations |
| C-05 | Semantic | Diversity index = distinct_clusters / total_unique_arguments | plan.md Phase C, explore.md:427 |
| C-06 | Hard | domain_corrections.json is the cross-engine interface for debiasing | plan.md Phase E, explore.md:189-191 |
| C-07 | Hard | All 12 hazards mitigated with tests | plan.md Hazard Coverage Check |
| C-08 | Semantic | MCP stdio processes tool calls sequentially (A-02) | plan.md Assumption Registry |
| C-09 | Hard | .mcp.json uses CLAUDE_PLUGIN_DATA | plan.md Task G.4 |
| C-10 | Hard | Round 6 evolution uses absolute values not deltas | plan.md H-11 mitigation |
| C-11 | Hard | Position = Union[ArgumentPosition, PredictionPosition] resolves H-10 | plan.md H-10 mitigation |
| C-12 | Semantic | Type discrimination via round plan, not hardcoded round 6 | plan.md Phase C H-01 mitigation |
| C-13 | Hard | Worker A creates engine/models.py with ~30 classes | plan.md File Creation Summary |
| C-14 | Negative | No file ownership conflict with other workers on engine/models.py | Implied |
| C-15 | Semantic | Jaccard clustering threshold 0.5 is configurable | plan.md H-06 mitigation |
| C-16 | Semantic | amplify_aggregate returns both raw and debiased distributions | plan.md Proof Obligations |
| C-17 | Semantic | MAX_MCP_OUTPUT_TOKENS=50000 mitigates H-07 | plan.md Task G.4 |

---

### Kill List (Falsified Claims & Omissions)

| SK-ID | Type | Claim/Omission | Evidence | Confidence |
|-------|------|----------------|----------|------------|
| SK-01 | Cross-Worker Conflict | Worker A defines file-based debiasing interface (`domain_corrections.json`) but Worker B defines object-parameter interface (`calibration_engine: Optional[CalibrationEngine]`) | Worker A plan.md Phase E lines 807-823 defines the file contract. Worker B plan.md lines 1033-1037 passes `CalibrationEngine` object as parameter to `amplify_aggregate()`. These are fundamentally incompatible -- one reads a file, the other receives an in-memory object. | 95% |
| SK-02 | Empirical | Plan claims "7-phase state machine" but lists 8 phases | plan.md line 17 lists: INIT->UNDERSTAND->BASELINE_AMPLIFY->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT->COMPLETE (8 nodes). Feature request C-07 (line 1128) says "7 phases: UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE -> AMPLIFY -> SYNTHESIZE -> INTERACT -> COMPLETE" (excluding INIT from the count). The plan's own transition graph in explore.md:30-34 shows 8 nodes including INIT. The plan and feature request count differently and the plan's claim of "7-phase" while listing 8 is a factual error. | 90% |
| SK-03 | Cross-Worker Conflict | Both Worker A and Worker D claim to CREATE `engine/models.py` | Worker A plan.md File Creation Summary: "CREATE engine/models.py" with ~30 classes. Worker D plan.md Task A.1 line 62: "CREATE engine/models.py (extends planned file)". Worker D's PredictionPosition includes `coalition_alignment: list[str] = Field(default_factory=list)` which is not in the feature-request.md:546-561 spec and not in Worker A's plan. Additionally Worker D's model has 13 fields (including coalition_alignment) while feature request specifies 12. | 90% |
| SK-04 | Cross-Worker Conflict | Worker C's .mcp.json uses `${CLAUDE_PLUGIN_DATA}` correctly, but Worker A's plan Task G.4 ALSO creates `.mcp.json`. Two workers creating the same file. | Worker A plan.md Task G.4 lines 1000-1020: CREATE `.mcp.json`. Worker C plan.md Task A.2 lines 82-105: CREATE `.mcp.json`. Both workers produce this file. The content is slightly different -- Worker A sets `MAX_MCP_OUTPUT_TOKENS=50000` in env, Worker C does not. Worker C uses `python3`, Worker A uses `python`. | 85% |
| SK-05 | Omission | Feature request Section 4.1.7 archetype-agent spec (lines 630-664) places hooks in subagent frontmatter for C-33 enforcement, but Worker A's plan does not address or flag that this WILL NOT WORK. | The feature request at lines 646-654 puts PreToolUse hooks in archetype-agent frontmatter. Worker C's explore correctly identifies this is broken (sub-agents.md:107 says plugin subagent hooks are IGNORED) and provides the fix (SubagentStop at plugin hooks.json). Worker A's plan does not mention this at all, even though the feature request's MCP server section references the archetype-agent definition. Not directly Worker A's scope, but the plan should at minimum note the spec error. | 60% |
| SK-06 | Semantic | Worker A's `amplify_aggregate` signature differs from Worker B's modified version | Worker A plan.md lines 777-800: `amplify_aggregate(apply_debiasing: bool = False, archetype_ids: list[str] | None = None)`. Worker B plan.md lines 1033-1037: `amplify_aggregate(apply_debiasing: bool = True, calibration_engine: Optional[CalibrationEngine] = None)`. Different default for `apply_debiasing` (False vs True). Worker B adds `calibration_engine` parameter. Worker A has `archetype_ids` filter that Worker B drops. These are conflicting signatures. | 95% |
| SK-07 | Semantic | H-08 mitigation claims MCP stdio is single-threaded and "no concurrent access possible" but this is not guaranteed by the MCP spec | The plan states (H-08 mitigation): "MCP stdio is single-threaded (one request at a time). The server processes tool calls sequentially. No concurrent access possible via MCP protocol." The MCP spec supports request batching, and the Python SDK's asyncio event loop could in theory handle concurrent requests even over stdio. The plan's own A-02 acknowledges this is an assumption (IMPLICIT). Marking this as medium risk rather than falsified -- the claim is likely correct for the current Python MCP SDK but not guaranteed. | 55% |
| SK-08 | Semantic | Plan claims MAX_MCP_OUTPUT_TOKENS=50000 in env mitigates H-07 but this is not a standard MCP configuration parameter | The plan (Task G.4 lines 1014-1024) sets `MAX_MCP_OUTPUT_TOKENS: 50000` as an env var in `.mcp.json`. This is not a recognized MCP protocol parameter or Claude Code MCP configuration key. The MCP protocol has a default 25,000 token output limit (referenced in explore.md H-07) but there is no documented mechanism to override it via an environment variable. The actual mitigation for H-07 should rely solely on the pagination parameters (`detail_level`, `archetype_ids`, `max_results`), not this potentially non-functional env var. | 80% |
| SK-09 | Semantic | Feature request at line 1064 uses CLAUDE_PLUGIN_ROOT for OATHFISH_DATA_DIR (the OLD version) but Worker A's plan correctly uses CLAUDE_PLUGIN_DATA -- however the plan does not flag this as a CORRECTION to the spec | Feature request line 1064: `"OATHFISH_DATA_DIR": "${CLAUDE_PLUGIN_ROOT}/docs/runs"` -- this is the UNCORRECTED version that H-12 warns about. Worker A's plan correctly uses `CLAUDE_PLUGIN_DATA` but does not explicitly note it is correcting the spec. This means an implementer who checks the spec might revert Worker A's correction. | 65% |
| SK-10 | Omission | Research synthesis mandates "question routing: classify simple-binary vs multi-factor, route simple to direct amplification" but Worker A's plan does not address question routing in the MCP server | final-synthesis.md Architecture Change #2: "Question routing: Classify questions as simple-binary vs multi-factor. Route simple to direct amplification, multi-factor through full deliberation." This routing is not present in Worker A's MCP server tools. Worker B's plan includes a competence classifier (Phase C) but it routes based on domain competence, not question complexity for deliberation skipping. Neither plan fully implements the synthesis recommendation for deliberation-skip routing. | 70% |
| SK-11 | Semantic | Diversity index formula `distinct_clusters / total_unique_arguments` can produce misleading results at extremes | If every argument is in its own cluster (maximum diversity), diversity_index = N/N = 1.0. If all arguments merge into 1 cluster, diversity_index = 1/N (approaches 0). But if there are 3 clusters with 3 total arguments, diversity = 1.0 (identical to maximum diversity). The formula does not distinguish "3 unique arguments" from "30 unique arguments with 30 clusters." The threshold (< 0.15) and cluster_count (< 3) are complementary but the index itself has poor information content at low argument counts. H-06 in explore.md acknowledges threshold sensitivity but the plan's mitigation (configurable thresholds) does not address the formula's structural weakness. | 65% |

---

### Hazard Audit

| H-ID | Hazard | Mitigation in Plan | Valid |
|------|--------|-------------------|-------|
| H-01 | Position type discrimination failure | Type discrimination via round plan, not hardcoded round 6 (Task C.1) | VALID - sound approach |
| H-02 | Write-through persistence failure | Atomic write via temp+rename in persistence.py (Task A.2) | VALID - standard pattern |
| H-03 | Cross-engine debiasing interface mismatch | File-based contract, graceful degradation (Task E.1) | INVALID - see SK-01, SK-06. Worker B does not use file-based contract. Worker B passes CalibrationEngine as parameter. |
| H-04 | Graph temporal query returns expired facts | as_of parameter on graph_query() (Task D.1) | VALID |
| H-05 | Metrics engine format coupling with deliberation | Shared Pydantic models from models.py (Task F.1) | VALID |
| H-06 | Diversity index threshold sensitivity | Configurable thresholds stored in RunConfig (Task C.1) | PARTIAL - configurable helps but see SK-11 for formula structural weakness |
| H-07 | MCP tool output exceeds 25K token limit | Pagination parameters + MAX_MCP_OUTPUT_TOKENS env var (Tasks C.1, E.1, D.1, G.4) | PARTIAL - pagination is valid; MAX_MCP_OUTPUT_TOKENS is likely non-functional (SK-08) |
| H-08 | Concurrent tool calls race condition | stdio is sequential (Task G.1) | PROVISIONAL - assumption A-02 unverified but likely correct |
| H-09 | ERROR state resume after restart | previous_state stored in run.json (Task B.1) | VALID |
| H-10 | RoundSummary references undefined Position type | Position = Union[ArgumentPosition, PredictionPosition] (Task A.1) | VALID |
| H-11 | Round 6 evolution delta against round 5 (no numeric fields) | Absolute values, not deltas (Task C.1) | VALID |
| H-12 | OATHFISH_DATA_DIR under CLAUDE_PLUGIN_ROOT | Uses CLAUDE_PLUGIN_DATA in .mcp.json (Task G.4) | VALID |

**Hazard Coverage**: 10/12 fully valid, 1 partial (H-06), 1 invalid (H-03). H-07 mitigation partially depends on a non-functional mechanism.

---

### Assumption Audit

| A-ID | Classification | Skeptic Finding | Status |
|------|----------------|-----------------|--------|
| A-01 | NEEDS_VERIFICATION | MCP Python SDK API (Server, @app.tool, stdio) - reasonable assumption but specific decorator pattern may differ | VALID classification |
| A-02 | IMPLICIT | stdio sequential processing - likely correct but not guaranteed | VALID classification |
| A-03 | VERIFIED | os.replace() atomic on Darwin - this IS a POSIX guarantee | VALID - correctly verified |
| A-04 | VERIFIED | Pydantic v2 Union handling - correct, v2 handles discriminated unions | VALID |
| A-05 | IMPLICIT | Jaccard as semantic similarity proxy - acknowledged weak | VALID - plan is honest about limitation |
| A-06 | IMPLICIT | 54,000 token estimate for full position map - reasonable estimate | VALID |

All assumption classifications appear accurate. No misclassifications found.

---

### Ambiguity Register

| Claim | Strategies Tried | Result |
|-------|------------------|--------|
| MAX_MCP_OUTPUT_TOKENS is a valid env var | Searched MCP documentation references, feature-request, mcp-analysis.md | mcp-analysis.md:59 mentions 25,000 token default but no override mechanism documented. Inconclusive -- may exist in undocumented Claude Code behavior. |
| MCP stdio guarantees sequential processing | Checked MCP spec references, Worker A explore, Python asyncio patterns | No definitive proof either way. MCP protocol allows request pipelining in theory. Python SDK likely processes sequentially but this is implementation, not protocol guarantee. |

---

### Certified Facts

| Claim | Evidence |
|-------|----------|
| ArgumentPosition has no stance/confidence float fields | feature-request.md:535-545 confirms text-only fields: archetype_id, round_n, position_text, key_arguments, concerns, influenced_by, base_rate_anchor, key_uncertainties |
| PredictionPosition has stance: float and confidence: float | feature-request.md:546-561 confirms mandatory float fields |
| 7-phase state machine includes BASELINE_AMPLIFY | feature-request.md:1128 (C-07) includes BASELINE_AMPLIFY in the chain. Though INIT is implicitly the starting state, not counted as a "phase" |
| Jaccard similarity used for argument evolution | AMB-01 resolution referenced in explore.md:83, plan.md Phase C |
| Write-through disk persistence required | C-23 at feature-request.md:1177 mandates immediate flush |
| .mcp.json in plan correctly uses CLAUDE_PLUGIN_DATA | plan.md Task G.4 lines 1014: `"OATHFISH_DATA_DIR": "${CLAUDE_PLUGIN_DATA}/runs"` |
| All 12 hazards from explore.md are addressed in plan | Hazard Coverage Check at plan.md lines 1167-1181 maps all H-01 through H-12 |
| Round 6 evolution correctly avoids delta vs round 5 | plan.md Phase C key detail #4 stores absolute values |
| Type discrimination avoids hardcoded "round 6" | plan.md Phase C key detail #1 uses round_plan from deliberation_init() |

---

### Cross-Worker Conflict Summary

| Conflict | Workers | Impact | Resolution Required |
|----------|---------|--------|---------------------|
| `.mcp.json` file ownership | A vs C | Both create this file with different content. Worker C uses `python3`, Worker A uses `python`. Worker A adds `MAX_MCP_OUTPUT_TOKENS`. | Designate single owner. Recommend Worker C owns scaffold, Worker A contributes env requirements. |
| `engine/models.py` file ownership | A vs D | Both create this file. Worker D adds `coalition_alignment` field to PredictionPosition not in Worker A's spec. | Designate Worker A as owner of core models, Worker D extends via separate file or coordination. |
| `amplify_aggregate()` signature | A vs B | Worker A: file-based debiasing with archetype_ids filter. Worker B: object-parameter debiasing, no archetype_ids filter. Different defaults. | Must agree on single signature. File-based interface is more decoupled; object-parameter is more type-safe. Decision needed. |
| `amplify_aggregate()` apply_debiasing default | A vs B | Worker A defaults to `False`. Worker B defaults to `True`. | Must agree. Worker A's `False` default is more conservative (safer for early runs with no calibration data). |

---

### Issue Ledger

| SK-ID | Status | Severity | Notes |
|-------|--------|----------|-------|
| SK-01 | OPEN | CRITICAL | Cross-worker interface mismatch blocks integration. Must resolve before implementation. |
| SK-02 | OPEN | MEDIUM | Counting error (7 vs 8 phases). Minor but confusing for implementers. Feature request counts INIT as implicit start state, not a "phase." Plan should clarify. |
| SK-03 | OPEN | CRITICAL | File ownership collision on engine/models.py. Worker D adds fields not in Worker A's spec. Must coordinate. |
| SK-04 | OPEN | HIGH | Two workers creating same .mcp.json with different content. Build-time conflict guaranteed. |
| SK-05 | OPEN | MEDIUM | Feature request spec error (hooks in subagent frontmatter) not flagged by Worker A. Worker C handles it but Worker A should note. |
| SK-06 | OPEN | HIGH | amplify_aggregate signature conflict between Workers A and B. |
| SK-07 | OPEN | MEDIUM | H-08 sequential assumption is unverified but likely correct. Low practical risk. |
| SK-08 | OPEN | HIGH | MAX_MCP_OUTPUT_TOKENS env var is likely non-functional. Plan relies on it as partial H-07 mitigation. |
| SK-09 | OPEN | MEDIUM | Plan corrects spec error (CLAUDE_PLUGIN_ROOT -> CLAUDE_PLUGIN_DATA) but does not explicitly mark it as a spec correction. |
| SK-10 | OPEN | MEDIUM | Question routing for deliberation-skip (simple binary questions) not implemented in MCP server. |
| SK-11 | OPEN | HIGH | Diversity index formula has structural weakness at low argument counts that configurable thresholds do not address. |

---

### Recommendations for Revision

1. **CRITICAL (SK-01, SK-06)**: Resolve the debiasing interface with Worker B. Either:
   - Worker A keeps file-based interface and Worker B writes `domain_corrections.json` as a materialized view of CalibrationEngine state, OR
   - Worker A adopts Worker B's approach and accepts CalibrationEngine as a parameter (tighter coupling but type-safe).
   Both approaches are valid. The current state where they disagree is not.

2. **CRITICAL (SK-03, SK-04)**: Establish file ownership protocol:
   - `engine/models.py`: Worker A owns the file. Worker D's additions (coalition_alignment) must be proposed to Worker A for inclusion, not independently added.
   - `.mcp.json`: Worker C owns the file (it is scaffold/config). Worker A specifies env requirements that Worker C includes.

3. **HIGH (SK-08)**: Remove `MAX_MCP_OUTPUT_TOKENS` from .mcp.json env unless its validity can be verified. Rely entirely on pagination parameters for H-07 mitigation.

4. **HIGH (SK-11)**: Consider adding a minimum argument count threshold to the diversity index computation. If total_unique_arguments < 10, the index should report "INSUFFICIENT_DATA" rather than a potentially misleading ratio.

5. **MEDIUM (SK-02)**: Clarify phase counting. Either call it "8-state machine" (including INIT) or "7-phase machine with INIT as implicit start state." Be consistent with feature-request C-07.

6. **MEDIUM (SK-10)**: Add a `question_type` field to RunConfig (SIMPLE_BINARY | MULTI_FACTOR) that the orchestration layer can use for routing decisions, even if the MCP server itself does not make routing decisions.
