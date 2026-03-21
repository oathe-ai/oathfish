# Defense Report - Worker A: MCP Server Core Engines

---
verdict: SOUND
repairs_made: 6
contests_made: 3
unresolved: 2
---

## Issue Disposition Table

| SK-ID | Status | Fix/Defense |
|-------|--------|-------------|
| SK-01 | RESOLVED | Adopted file-based contract (domain_corrections.json) as the explicit integration point. Documented JSON schema. Worker B writes the file; Worker A reads it. No cross-engine Python imports. |
| SK-02 | RESOLVED | Clarified to "8-state machine (7 phases + INIT start state)" to match feature request C-07 which lists 7 phases excluding INIT. |
| SK-03 | CONTESTED | Worker A's PredictionPosition already includes `coalition_alignment: list[str]` at plan line 173. Feature request at line 560 includes this field (13 fields total, not 12). Worker D says "extends planned file" -- Worker A OWNS, Worker D imports. Confirmed with explicit ownership statement in revised plan. |
| SK-04 | RESOLVED | Worker A no longer claims to CREATE .mcp.json. Worker C owns .mcp.json (Task A.2 in Worker C's plan). Worker A documents env requirements that Worker C includes. Removed Task G.4 as a file creation task; replaced with env requirement specification. |
| SK-05 | RESOLVED | Added note in plan acknowledging that feature request places hooks in subagent frontmatter, which is broken per sub-agents.md:107. Worker C handles the fix via SubagentStop. |
| SK-06 | RESOLVED | Adopted file-based interface definitively. Worker B's CalibrationEngine writes domain_corrections.json; Worker A's amplify_aggregate reads it. Signature keeps `apply_debiasing: bool = False` and `archetype_ids` filter. No CalibrationEngine parameter. Worker B MODIFIES amplify_aggregate (per Worker B's plan Task D.1) but must use the file-based pattern. |
| SK-07 | CONTESTED | Plan already classifies A-02 as IMPLICIT and acknowledges the assumption. MCP Python SDK uses asyncio but stdio is single-channel. Practical risk is low. No change needed. |
| SK-08 | CONTESTED | MAX_MCP_OUTPUT_TOKENS IS a documented Claude Code env var. references/raw/mcp.md:162-166 explicitly documents it: "Configure via MAX_MCP_OUTPUT_TOKENS env var" with example "export MAX_MCP_OUTPUT_TOKENS=50000". Skeptic's claim at 80% confidence is wrong. However, since Worker A no longer owns .mcp.json, this env var requirement is documented as a spec for Worker C. |
| SK-09 | RESOLVED | Added explicit note that plan CORRECTS the feature request spec error (CLAUDE_PLUGIN_ROOT -> CLAUDE_PLUGIN_DATA). Marked as spec correction. |
| SK-10 | CONTESTED | Question routing is Worker B's responsibility (competence_classifier.py produces routing_recommendation: "FULL_PIPELINE" | "SKIP_DELIBERATE" | "LOW_CONFIDENCE"). Worker C's coordinator acts on the recommendation. Worker A's MCP server provides the state machine phases but does NOT make routing decisions. This is correct separation of concerns. |
| SK-11 | RESOLVED | Added minimum argument count guard to diversity index. When total_unique_arguments < 5, diversity_index reports as null with flag "INSUFFICIENT_DATA". |

---

## Verification Evidence

### SK-01: Cross-worker debiasing interface mismatch

**Skeptic claim**: Worker A defines file-based interface (domain_corrections.json); Worker B defines object-parameter interface (CalibrationEngine). These are incompatible.

My Verification:
Command: Search Worker B plan for amplify_aggregate signature
```
Worker B plan.md lines 1033-1037:
def amplify_aggregate(
    self,
    apply_debiasing: bool = True,
    calibration_engine: Optional[CalibrationEngine] = None,
) -> dict:
```

Worker A plan.md lines 777-780:
```
async def amplify_aggregate(
    apply_debiasing: bool = False,
    archetype_ids: list[str] | None = None
) -> dict:
```

Disposition: RESOLVED
Reason: Skeptic is correct that the interfaces are incompatible. Worker A's file-based approach (domain_corrections.json) is more decoupled and appropriate for cross-engine integration since it requires no Python import of Worker B's CalibrationEngine class. Worker B's plan at line 1024 says "Worker A creates base; Worker B adds debiasing" -- so Worker B MODIFIES Worker A's file. The contract must be: Worker B writes domain_corrections.json as a materialized view of CalibrationEngine state; Worker A reads it.

Fix: Plan revised to make the file-based contract the canonical integration point with explicit JSON schema. Worker B's modification of amplify_aggregate must use file reads, not CalibrationEngine parameter injection. Added cross-worker contract section.

---

### SK-02: Phase count mismatch (7 vs 8)

**Skeptic claim**: Plan says "7-phase" but lists 8 phases including INIT.

My Verification:
Command: Read feature request C-07
```
feature-request.md:1128:
C-07 | REQUIREMENT | State machine with 7 phases: UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE -> AMPLIFY -> SYNTHESIZE -> INTERACT -> COMPLETE
```

Worker A plan line 17:
```
MUST: 7-phase state machine: INIT->UNDERSTAND->BASELINE_AMPLIFY->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT->COMPLETE (C-07)
```

Disposition: RESOLVED
Reason: Skeptic is correct. C-07 lists 7 phases excluding INIT. INIT is the start state, not a "phase" in the pipeline. The plan lists 8 states (including INIT + ERROR) but calls it "7-phase." This is confusing.

Fix: Changed to "8-state state machine (7 pipeline phases + INIT start state)" with explicit note that C-07 counts 7 phases excluding INIT.

---

### SK-03: models.py ownership collision with Worker D

**Skeptic claim**: Both Workers A and D claim to CREATE engine/models.py. Worker D's PredictionPosition includes coalition_alignment which "is not in the feature-request.md:546-561 spec."

My Verification:
Command: Read feature request PredictionPosition definition
```
feature-request.md lines 546-561:
class PredictionPosition(BaseModel):
    archetype_id: str
    round_n: int
    prediction: str
    decision: str
    stance: float
    confidence: float
    timeframe: str
    base_rate_anchor: str
    key_uncertainties: list[str]
    falsification_criteria: str
    second_order_effects: list[str]
    cascade_susceptibility: float
    coalition_alignment: list[str]   # <-- LINE 560, PRESENT IN SPEC
```

Worker A plan line 173:
```
coalition_alignment: list[str] = Field(default_factory=list)
```

Worker D plan line 64:
```
PredictionPosition model with all 12 fields
```

Field count in feature request: 13 fields (archetype_id, round_n, prediction, decision, stance, confidence, timeframe, base_rate_anchor, key_uncertainties, falsification_criteria, second_order_effects, cascade_susceptibility, coalition_alignment).

Disposition: CONTESTED (partially)
Reason: Skeptic is WRONG that coalition_alignment is "not in the feature-request.md:546-561 spec" -- it is clearly present at line 560. Worker D says "12 fields" which is also wrong (the spec has 13). Worker A's plan already includes coalition_alignment correctly. However, the skeptic IS correct that there is a file ownership collision -- Worker D says "CREATE engine/models.py (extends planned file)" at line 62. This needs explicit ownership designation.

Fix: Added explicit ownership statement: Worker A OWNS engine/models.py as the canonical source. Worker D must import from it, not create a parallel definition. Worker D's "extends" language is acknowledged -- Worker D may propose additional fields but Worker A is the authoritative owner.

---

### SK-04: .mcp.json collision with Worker C

**Skeptic claim**: Both Workers A and C create .mcp.json with different content.

My Verification:
```
Worker A plan Task G.4 (lines 1000-1020):
  command: "python"
  env: OATHFISH_DATA_DIR, MAX_MCP_OUTPUT_TOKENS

Worker C plan Task A.2 (lines 81-107):
  command: "python3"
  env: OATHFISH_DATA_DIR, OATHFISH_PLUGIN_ROOT
```

Disposition: RESOLVED
Reason: Skeptic is correct. Two workers creating the same file with different content is a guaranteed build-time conflict. Worker C is the scaffold/plugin worker -- .mcp.json is a plugin configuration file and belongs with the plugin scaffold.

Fix: Worker A no longer creates .mcp.json. Task G.4 is converted to an env requirements specification. Worker C owns .mcp.json. Worker A specifies the env vars that Worker C must include (OATHFISH_DATA_DIR using CLAUDE_PLUGIN_DATA, and MAX_MCP_OUTPUT_TOKENS=50000). Worker C should use `python3` (not `python`).

---

### SK-05: Feature request spec error (hooks in subagent frontmatter) not flagged

**Skeptic claim**: Worker A does not flag that the feature request's hooks placement in archetype-agent frontmatter is broken.

My Verification:
```
feature-request.md:646-654 places PreToolUse hooks in archetype agent frontmatter.
sub-agents.md:107 says plugin subagent hooks are IGNORED.
Worker C plan lines 158-166 identifies and fixes this with SubagentStop at hooks.json.
```

Disposition: RESOLVED
Reason: Skeptic is partially correct. While this is Worker C's scope to fix, Worker A should note the spec error since Worker A references the archetype-agent definition. Added acknowledgment note.

Fix: Added note in plan's Ambiguities section.

---

### SK-06: amplify_aggregate signature conflict with Worker B

**Skeptic claim**: Different signatures, different defaults, incompatible interfaces.

My Verification: Same evidence as SK-01. Worker A has `apply_debiasing=False`, Worker B has `apply_debiasing=True`. Worker A has `archetype_ids` filter, Worker B drops it and adds `CalibrationEngine`.

Disposition: RESOLVED (merged with SK-01)
Reason: The debiasing default and parameter differences are resolved by the file-based contract. Worker A's `apply_debiasing=False` is more conservative (safer for early runs with no calibration data). Worker B's modification of amplify_aggregate must keep the `archetype_ids` filter (it's needed for H-07 pagination mitigation). The `CalibrationEngine` parameter is replaced by file reads.

Fix: Documented in cross-worker contract section. Worker A's base signature is canonical. Worker B adds debiasing logic but uses file-based reads, not object injection.

---

### SK-07: H-08 sequential assumption unverified

**Skeptic claim**: stdio sequential processing is not guaranteed by MCP spec.

My Verification:
```
Worker A plan A-02 already classifies this as IMPLICIT:
"MCP stdio processes tool calls sequentially (single-threaded event loop)"
Classification: IMPLICIT
```

Disposition: CONTESTED
Reason: Worker A already acknowledges this is an implicit assumption (A-02). The plan correctly classifies it as IMPLICIT, not VERIFIED. The risk mitigation (H-08) acknowledges this explicitly. The MCP Python SDK's asyncio event loop over stdio practically serializes requests, but the plan does not claim this is guaranteed. No change needed.

---

### SK-08: MAX_MCP_OUTPUT_TOKENS non-functional

**Skeptic claim at 80% confidence**: MAX_MCP_OUTPUT_TOKENS "is not a recognized MCP protocol parameter or Claude Code MCP configuration key."

My Verification:
Command: Read references/raw/mcp.md around line 160
```
references/raw/mcp.md:158-166:
## MCP Output Limits

- Warning at 10,000 tokens per tool output
- Default max: 25,000 tokens
- Configure via `MAX_MCP_OUTPUT_TOKENS` env var

```bash
export MAX_MCP_OUTPUT_TOKENS=50000
claude
```
```

Disposition: CONTESTED
Reason: Skeptic is WRONG. MAX_MCP_OUTPUT_TOKENS is explicitly documented in the MCP reference documentation at references/raw/mcp.md:162-163. The exact usage pattern ("export MAX_MCP_OUTPUT_TOKENS=50000") matches what Worker A's plan specifies. The env var IS a recognized Claude Code configuration mechanism.

However, since Worker A no longer owns .mcp.json (resolved in SK-04), the env var requirement is documented as a specification for Worker C's .mcp.json.

---

### SK-09: Spec correction not flagged

**Skeptic claim**: Plan corrects CLAUDE_PLUGIN_ROOT to CLAUDE_PLUGIN_DATA but does not mark it as a spec correction.

My Verification:
```
feature-request.md:1064:
  "OATHFISH_DATA_DIR": "${CLAUDE_PLUGIN_ROOT}/docs/runs"

Worker A plan line 1014:
  "OATHFISH_DATA_DIR": "${CLAUDE_PLUGIN_DATA}/runs"
```

Disposition: RESOLVED
Reason: Skeptic is correct. An implementer checking the original spec might revert the correction. The plan should explicitly flag this.

Fix: Added explicit spec correction callout in the plan with rationale.

---

### SK-10: Question routing not implemented in MCP server

**Skeptic claim**: research-driven-redesign.md mandates question routing but Worker A's MCP server does not implement it.

My Verification:
Command: Search Worker B plan for routing logic
```
Worker B plan.md lines 926-987:
  competence_classifier.py implements classify_question()
  routing_recommendation: "FULL_PIPELINE" | "SKIP_DELIBERATE" | "LOW_CONFIDENCE"
  SIMPLE_BINARY -> SKIP_DELIBERATE
  MULTI_FACTOR -> FULL_PIPELINE
```

Command: Search research-driven-redesign.md
```
research-driven-redesign.md:102-115:
  "ADD: A competence classifier before UNDERSTAND that:
  1. Classifies incoming question as simple-binary vs multi-factor
  2. Assesses whether the archetype set has domain-relevant perspectives
  3. Routes simple-binary -> direct AMPLIFY (skip DELIBERATE)
  4. Routes multi-factor -> full DELIBERATE pipeline"
```

Disposition: CONTESTED
Reason: Question routing IS implemented -- by Worker B (competence_classifier.py, Task C.1) and acted upon by Worker C (coordinator). Worker A's MCP server provides the STATE MACHINE (phase transitions) but does not make routing DECISIONS. The state machine allows UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE -> AMPLIFY (full pipeline) or could allow UNDERSTAND -> BASELINE_AMPLIFY -> AMPLIFY (skip deliberation) if the state machine transitions are extended. However, the routing decision is outside Worker A's scope.

Note: Worker A's state machine currently does NOT allow skipping DELIBERATE (BASELINE_AMPLIFY can only transition to DELIBERATE). This may need a future state machine extension to support the SKIP_DELIBERATE route. Added as an RFI.

---

### SK-11: Diversity index formula structural weakness

**Skeptic claim**: Formula `distinct_clusters / total_unique_arguments` has poor information content at low argument counts.

My Verification: The formula produces:
- 3 arguments, 3 clusters -> diversity = 1.0 (same as 30 arguments, 30 clusters)
- 3 arguments, 1 cluster -> diversity = 0.33
- Problem: Cannot distinguish "high diversity with few arguments" from "high diversity with many arguments"

Disposition: RESOLVED
Reason: Skeptic makes a valid point. The formula's information content is poor at low N. The existing H-06 mitigation (configurable thresholds) addresses threshold sensitivity but not the structural weakness.

Fix: Added minimum argument count guard. When `total_unique_arguments < 5`, diversity_index is null and `flag: "INSUFFICIENT_DATA"` is returned. This prevents misleading ratios at low counts. Also added `total_unique_arguments` as a reported field alongside diversity_index to give consumers the full picture.

---

## Plan Deltas

Changes made to the plan:

1. **Scope Anchor line 17**: Changed "7-phase state machine" to "8-state state machine (7 pipeline phases + INIT start state)" with clarification note
2. **Task A.1 (models.py)**: Added explicit ownership statement: "Worker A OWNS this file as the canonical model source. Worker D imports from it."
3. **Task A.1 PredictionPosition**: Added note that `coalition_alignment` is spec-mandated (feature-request.md:560), not a Worker D addition. Field count is 13, not 12.
4. **Task C.1 (diversity index)**: Added minimum argument count guard: when `total_unique_arguments < 5`, diversity_index = null with `INSUFFICIENT_DATA` flag. Added `total_unique_arguments` to ConvergenceResult model.
5. **Task E.1 (amplification)**: Strengthened cross-engine interface contract documentation. Explicit JSON schema for domain_corrections.json. Added note that Worker B writes this file, Worker A reads it.
6. **Task G.4 (.mcp.json)**: Converted from file creation task to env requirements specification. Worker C owns .mcp.json. Worker A specifies required env vars.
7. **Ambiguities section**: Added note about feature request spec error (hooks in subagent frontmatter) per SK-05.
8. **Ambiguities section**: Added explicit spec correction callout for CLAUDE_PLUGIN_ROOT -> CLAUDE_PLUGIN_DATA per SK-09.
9. **File Creation Summary**: Removed `.mcp.json` from Worker A's file list.
10. **Blast Radius Map**: Updated to reflect .mcp.json ownership change.
11. **New section**: Cross-Worker Integration Contracts with explicit ownership table.

---

## RFIs

| SK-ID | Question | Needed Evidence |
|-------|----------|-----------------|
| SK-10 | Should Worker A's state machine support a SKIP_DELIBERATE transition (BASELINE_AMPLIFY -> AMPLIFY) for simple-binary question routing? | Decision from system architect. Currently the state machine requires BASELINE_AMPLIFY -> DELIBERATE. If SKIP_DELIBERATE is needed, the LEGAL_TRANSITIONS dict must be extended. |
| SK-07 | Does the MCP Python SDK guarantee sequential processing over stdio? | Runtime testing with concurrent requests over stdio transport. |
