# Defense Report - Worker D: Archetype Generation, Grounding, Amplification SDK

---
verdict: SOUND (after repairs)
repairs_made: 10
contests_made: 1
unresolved: 1
---

## Issue Disposition Table

| SK-ID | Status | Fix/Defense |
|-------|--------|-------------|
| SK-01 | RESOLVED | Worker D no longer CREATEs engine/models.py. Imports PredictionPosition from Worker A's models. Proposes coalition_alignment + grounding_sources as additions to Worker A's schema. |
| SK-02 | RESOLVED | Replaced `options.append_system_prompt = delta` with string concatenation fallback. Primary: CLI `--append-system-prompt`. SDK fallback: concatenate base + delta into single `system_prompt`. |
| SK-03 | RESOLVED | Task A.1 changed from CREATE to IMPORT. Worker D no longer defines PredictionPosition; imports from engine.models (owned by Worker A). Task E.1 fields proposed as ADDITIONS to Worker A's Archetype model. |
| SK-04 | RESOLVED | Adopted `list[str]` for grounding_sources on the Archetype model (matching Worker A). GroundingSource rich model retained only for internal Task C.2 processing; serialized to `list[str]` for storage in Archetype. |
| SK-05 | RESOLVED | Added `allowed_tools=[]` to AmplificationConfig and ClaudeAgentOptions construction. Amplification calls are now tool-free. |
| SK-06 | RESOLVED | A-D05 reclassified from USER DECISION to VERIFIED. Task C.2 redesigned to use WebSearch directly. Fallback chain: WebSearch -> WebFetch -> manual. |
| SK-07 | RESOLVED | A-D07 reclassified from WORKER CONSENSUS to IMPLICIT. |
| SK-08 | RESOLVED | Added deliberation digest approach as primary strategy for INFORMED mode. --resume reserved for INTERACT phase only. Digest is 500-1000 token summary injected via concatenated system_prompt. |
| SK-09 | CONTESTED | The aliasing is real but impact is low for n=50. Unique strings confirmed by design. |
| SK-10 | RESOLVED | Merged with SK-05 fix. `allowed_tools=[]` added to both AmplificationConfig and _do_call(). |
| SK-11 | RESOLVED | Added explicit data directory convention referencing Worker A's `${CLAUDE_PLUGIN_DATA}/runs`. |
| SK-12 | UNVERIFIED | Runtime token counting requires SDK features not yet confirmed. Added word count validation as best-effort mitigation. |

---

## Verification Evidence

### SK-01: PredictionPosition Schema Conflict (CRITICAL)

**Skeptic's claim**: Worker A and Worker D both CREATE engine/models.py with different PredictionPosition schemas. Worker A uses defaults on most fields; Worker D makes them all required.

My Verification:

Command: Read Worker A plan.md lines 159-173
```
class PredictionPosition(BaseModel):
    archetype_id: str
    round_n: int
    prediction: str
    decision: str  # adopt | wait | reject | mixed
    stance: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    timeframe: str = ""
    base_rate_anchor: str = ""
    key_uncertainties: list[str] = Field(default_factory=list)
    ... (with defaults on most fields)
    coalition_alignment: list[str] = Field(default_factory=list)
```

Command: Read Worker D plan.md lines 74-92
```
class PredictionPosition(BaseModel):
    archetype_id: str = Field(description="...")
    ...
    timeframe: str = Field(description="...")  # REQUIRED (no default)
    base_rate_anchor: str = Field(description="...")  # REQUIRED (no default)
    ...
```

Disposition: RESOLVED - Skeptic correct. Worker A's schema has defaults (optional fields), Worker D's makes everything required. These produce different JSON schemas via model_json_schema(). Worker D's Task A.1 is changed from CREATE to IMPORT. Worker A OWNS engine/models.py and PredictionPosition. Worker D imports from there.

Worker D's contribution is to PROPOSE two additions to Worker A's model:
1. `coalition_alignment` (already present in Worker A's schema)
2. `grounding_sources` on Archetype (type negotiation -- see SK-04)

The `description=` Field annotations from Worker D's version should be proposed as an ENHANCEMENT to Worker A's model via cross-worker PR, not a separate definition.

---

### SK-02: `append_system_prompt` Not in ClaudeAgentOptions (CRITICAL)

**Skeptic's claim**: headless-analysis.md:55 lists all ClaudeAgentOptions fields and `append_system_prompt` is NOT among them. Worker D's code at plan.md:1012 sets `options.append_system_prompt = delta`.

My Verification:

Command: Read headless-analysis.md line 55
```
ClaudeAgentOptions dataclass with all configuration: allowed_tools, disallowed_tools,
system_prompt, max_turns, max_budget_usd, model, fallback_model, output_format,
resume, fork_session, continue_conversation, effort, thinking, hooks, agents,
mcp_servers, cwd, add_dirs, env, sandbox, permission_mode, can_use_tool callback,
plugins, setting_sources, include_partial_messages
```

Confirmed: `append_system_prompt` is NOT listed. Only `system_prompt` exists.

Command: Read headless.md lines 106-117 (raw reference)
```
--system-prompt: FULLY REPLACE default prompt
--append-system-prompt: Append to default prompt
```

Confirmed: `--append-system-prompt` exists as a CLI flag but is NOT a field in ClaudeAgentOptions.

Command: Read headless-analysis.md line 93
```
System prompt control is dual-mode. --system-prompt fully replaces the default.
--append-system-prompt adds to the default. They can be combined: --system-prompt
sets the base, --append-system-prompt layers on top.
```

Confirmed: The combination works at CLI level.

Command: Read headless-analysis.md lines 285-289
```
The docs say the append flags "can be combined with either replacement flag,"
which implies it appends to whatever --system-prompt set. But the wording
"append to the default prompt" is ambiguous.
Mitigation: Test the combination explicitly. If --append-system-prompt does not
append to --system-prompt replacement, concatenate both into a single --system-prompt value.
```

Disposition: RESOLVED - Skeptic correct. The SDK ClaudeAgentOptions does NOT have `append_system_prompt`. Fix: concatenate base persona + variation delta into a single `system_prompt` string. This is the safest approach that works regardless of CLI/SDK mode. The docstring comment notes the CLI alternative for when using subprocess calls.

---

### SK-03: File Collision engine/models.py (CRITICAL)

**Skeptic's claim**: Both Worker A and Worker D CREATE engine/models.py with no merge protocol.

My Verification:

Command: Read Worker A plan.md line 63
```
Files: CREATE engine/models.py
```

Command: Read Worker D plan.md line 62
```
Files: CREATE engine/models.py (extends planned file)
```

Disposition: RESOLVED - Skeptic correct. Worker D's parenthetical "(extends planned file)" acknowledges awareness but the operation is listed as CREATE. Fix: Worker D's Task A.1 is now IMPORT (not CREATE). Worker D imports PredictionPosition and Archetype from engine.models (Worker A's file). Worker D's Task E.1 proposes ADDITIONS to Worker A's Archetype model as a cross-worker specification, not a separate file creation.

**Ownership for archetype-reasoning/SKILL.md**: Worker C's plan (Task C.8) at line 1228-1231 CREATEs `skills/archetype-reasoning/SKILL.md`. Worker D's plan (Task A.2) also CREATEs the same file. Per the user's instruction, Worker D OWNS this file. Worker C should reference it but not create it. This is confirmed: Worker D's Task A.2 contains the complete methodology text; Worker C's Task C.8 provides the frontmatter wrapper. Resolution: Worker D's content is authoritative; Worker C should IMPORT/REFERENCE this content.

---

### SK-04: Archetype Model grounding_sources Type Conflict (HIGH)

**Skeptic's claim**: Worker A uses `grounding_sources: list[str]`, Worker D uses `grounding_sources: list[GroundingSource]` (a full BaseModel). Incompatible types.

My Verification:

Command: Read Worker A plan.md line 143
```
grounding_sources: list[str] = Field(default_factory=list)
```

Command: Read Worker D plan.md lines 1121-1150
```
class GroundingSource(BaseModel):
    title: str
    author: Optional[str] = None
    date: Optional[str] = None
    excerpt: str
    url: Optional[str] = None
    source_type: str

class Archetype(BaseModel):
    ...
    grounding_sources: list[GroundingSource] = []
```

Disposition: RESOLVED - Skeptic correct. Types are incompatible. Per user instruction: adopt `list[str]` for Archetype.grounding_sources (matching Worker A). The GroundingSource model is retained internally for Task C.2 processing only. When assembling the Archetype, grounding sources are serialized as formatted strings: `"{title} by {author} ({date}): {excerpt}"`. This gives both richness in processing and compatibility with Worker A's schema.

---

### SK-05: Missing tools="" in Amplification Calls (HIGH)

**Skeptic's claim**: Worker D's ClaudeAgentOptions at plan.md:1000-1007 does not set tools or allowed_tools. headless-analysis.md:120 recommends `--tools ""` for amplification purity.

My Verification:

Command: Read headless-analysis.md line 120
```
| Tool restriction | --tools "" or omit --allowedTools | Amplification calls need NO tools --
  they produce a prediction, not execute actions. Disabling tools prevents wasted tokens
  on tool-use reasoning. |
```

Command: Read headless-analysis.md lines 229-233
```
--max-turns 1 + --tools "" for mass amplification purity

Amplification calls should be single-turn, tool-free predictions. --max-turns 1 prevents
the agent from entering an agentic loop. Combined with --tools "" (disable all tools),
each call becomes: prompt in -> structured JSON out.
```

Disposition: RESOLVED - Skeptic correct. The plan's reference documentation explicitly recommends disabling tools for amplification. Fix: Added `allowed_tools: list[str] = field(default_factory=list)` to AmplificationConfig and `allowed_tools=self.config.allowed_tools` (defaults to `[]`) in ClaudeAgentOptions construction. Empty list disables all tools.

---

### SK-06: WebSearch Tool EXISTS (HIGH)

**Skeptic's claim**: tools-reference.md lists WebSearch as a built-in tool. Worker D claims "no web search infrastructure exists."

My Verification:

Command: Read tools-reference-analysis.md line 33
```
| WebSearch | Yes | Performs web searches |
```

Command: Read tools-reference-analysis.md line 60
```
Tools requiring permission (Yes): Bash, Edit, Write, Skill, WebFetch, WebSearch,
NotebookEdit, ExitPlanMode.
```

Disposition: RESOLVED - Skeptic correct. WebSearch is a built-in Claude Code tool requiring permission. A-D05 is reclassified from USER DECISION to VERIFIED. Task C.2 redesigned to use WebSearch as primary source discovery mechanism with `--allowedTools "WebSearch"` on the UNDERSTAND phase coordinator.

---

### SK-07: A-D07 WORKER CONSENSUS Invalid (MEDIUM)

**Skeptic's claim**: A-D07 classified as WORKER CONSENSUS is invalid in population mode where no cross-worker deliberation occurred.

My Verification: This is a population-mode run with Workers A/B/C/D. No inter-worker consensus process occurred for this assumption.

Disposition: RESOLVED - Skeptic correct. Reclassified to IMPLICIT. The deterministic variation spread is a standard approach, not a consensus decision.

---

### SK-08: --resume Cost Explosion (HIGH)

**Skeptic's claim**: H-05 mitigation ($0.05 budget cap) is inadequate. 100K tokens per call at 1500 calls = 150M input tokens. $0.05 may be too low for resumed context.

My Verification:

Command: Read headless-analysis.md lines 275-281
```
A 6-round deliberation with 30 archetypes can generate 100K-500K tokens of conversation
history. Loading this via --resume means every amplification call pays input token costs
for the full deliberation transcript. At 1500 calls: 1500 x 100K tokens = 150M input tokens.
...
Mitigation: The deliberation digest approach (SPEC-03 option 3) may be more cost-effective:
summarize deliberation insights into a 2K-5K token digest, inject via --append-system-prompt.
```

Disposition: RESOLVED - Skeptic correct. The cost explosion is real and the budget cap alone is insufficient. Fix: Replaced --resume with deliberation digest approach for post-deliberation AMPLIFY. The coordinator generates a 500-1000 token digest of deliberation findings. This digest is concatenated into the system_prompt for informed amplification calls. --resume is reserved exclusively for INTERACT phase (interactive follow-up) where cost is acceptable (few calls, not 1500).

---

### SK-09: PersonaVariationGenerator Aliasing (MEDIUM)

**Skeptic's claim**: `edu_idx = n % 5` and `axis1_idx = n % 5` are identical, creating correlation between education and personality axis selection.

My Verification:

Analysis of the code:
```python
edu_idx = n % len(self.EDUCATION_MODIFIERS)  # len = 5, so n % 5
axis1_idx = n % len(self.PERSONALITY_AXES)   # len = 5, so n % 5
```

Both use `n % 5`. This means variation 0 always gets education[0] + personality_axis[0], variation 5 always gets education[0] + personality_axis[0], etc. Perfect correlation.

However, the skeptic also acknowledges: "For 50 variations, this is adequate" and "The plan's diversity claim is PARTIALLY correct: unique strings yes, maximally diverse coverage no."

Disposition: CONTESTED - The aliasing is real as a code observation, but the impact is low. The plan claims 50 unique delta strings, which is TRUE (different combinations of age, location, experience, education, and personality produce unique strings even with aliasing). The aliasing reduces maximum diversity but does not produce duplicate deltas. For 50 variations per archetype, the unique string count is correct. An improvement using prime-based stepping would be nice but is not a plan-breaking issue.

The revised plan adds a comment noting the aliasing and suggesting prime-based stepping as a future optimization, but does not change the core algorithm since 50 unique strings is the requirement and it is met.

---

### SK-10: AmplificationConfig Lacks tools Field (HIGH)

**Skeptic's claim**: AmplificationConfig has no `tools` field and code does not set `allowed_tools=[]`.

Disposition: RESOLVED - Merged with SK-05. Fix applied: added `allowed_tools` field to AmplificationConfig and set it in ClaudeAgentOptions construction.

---

### SK-11: No Data Directory Convention (MEDIUM)

**Skeptic's claim**: Worker D does not reference Worker A's `${CLAUDE_PLUGIN_DATA}/runs` data directory convention.

My Verification:

Command: Read Worker A plan.md line 22
```
MUST NOT: Store run data under ${CLAUDE_PLUGIN_ROOT} (use ${CLAUDE_PLUGIN_DATA} per mcp-analysis.md:53)
```

Worker D's plan has no reference to CLAUDE_PLUGIN_DATA.

Disposition: RESOLVED - Skeptic correct. Added explicit reference to Worker A's data directory convention. AmplificationConfig.output_dir now defaults to the run directory under `${CLAUDE_PLUGIN_DATA}/runs/{run_id}/`.

---

### SK-12: H-01 Prompt Length Mitigation Weak (MEDIUM)

**Skeptic's claim**: H-01 mitigation is word count target only with no runtime enforcement or token counting.

Disposition: UNVERIFIED - Runtime token counting would require either a tokenizer library (adds dependency, violates C-19) or SDK features (unconfirmed). The word count target (1000-1500 words) is a reasonable design-time constraint. Added a word count validation step in Task C.3 that logs a warning if any assembled persona_prompt exceeds 1500 words. Full token counting is deferred as it requires runtime infrastructure not yet specified.

---

## Plan Deltas

Changes made to the plan:

1. **Task A.1**: Changed from CREATE to IMPORT. Worker D imports PredictionPosition from engine.models (Worker A's file). Removed duplicate model definition. Added cross-worker field proposal for `description=` annotations.

2. **Task E.1**: Changed GroundingSource from Archetype field type to internal processing model. Archetype.grounding_sources now uses `list[str]` matching Worker A. Added explicit note that Worker D PROPOSES additions to Worker A's Archetype model (is_structural, archetype_type, stubbornness_domain, grounding_rung, grounding_search_queries).

3. **Task D.1 (_do_call)**: Replaced `options.append_system_prompt = delta` with string concatenation: `system_prompt = archetype.persona_prompt + "\n\n" + delta`. Added `allowed_tools=[]` to ClaudeAgentOptions. Added `allowed_tools` field to AmplificationConfig.

4. **Task D.1 (INFORMED mode)**: Replaced `--resume` with deliberation digest injection. New `deliberation_digest` field on AmplificationConfig. Digest (500-1000 tokens) concatenated into system_prompt. --resume removed from AMPLIFY phase entirely.

5. **Task C.2**: Redesigned to use WebSearch as primary source discovery tool. Fallback chain: WebSearch -> WebFetch -> manual operator step.

6. **A-D05**: Reclassified from USER DECISION to VERIFIED.

7. **A-D07**: Reclassified from WORKER CONSENSUS to IMPLICIT.

8. **H-05**: Updated mitigation to reference deliberation digest approach. Removed reliance on --max-budget-usd as sole cost control for informed mode.

9. **Ambiguities section**: Removed "How is web search performed" (resolved: WebSearch). Updated --resume question to note digest approach is primary.

10. **Data directory**: Added explicit reference to `${CLAUDE_PLUGIN_DATA}/runs` convention from Worker A.

---

## RFIs (if any)

| SK-ID | Question | Needed Evidence |
|-------|----------|-----------------|
| SK-12 | Is there a lightweight token counting mechanism available in the SDK or stdlib? | Runtime testing or SDK docs beyond current references |
