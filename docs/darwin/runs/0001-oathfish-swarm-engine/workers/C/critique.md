# Skeptic Critique - Worker C (Orchestration)

## Run: 0001-oathfish-swarm-engine
## Worker: C
## Iteration: 0

---

```yaml
---
verdict: UNSOUND
issues_critical: 3
issues_high: 4
issues_medium: 5
---
```

---

### Executive Verdict

**Status**: UNSOUND

**Top 3 Blockers**:
1. [SK-01] SubagentStop blocking behavior is not documented in the primary reference -- the entire C-33 enforcement mechanism rests on an inference from an analysis doc, not verified API behavior
2. [SK-02] The /oathfish dispatcher-to-coordinator architecture has a fatal nesting problem -- the coordinator spawned via Agent tool becomes a subagent and CANNOT spawn archetype subagents per C-L02
3. [SK-03] Cross-worker file collision: Worker C Task C.8 and Worker D Task A.2 both CREATE `skills/archetype-reasoning/SKILL.md` with different content

---

### Claim Ledger

| Claim-ID | Type | Statement | Source |
|----------|------|-----------|--------|
| C-01 | Hard | Plugin subagent hooks, mcpServers, permissionMode IGNORED | plan.md:39 |
| C-02 | Hard | SubagentStop can block via exit 2, forcing continuation | plan.md:48, plan.md:162 |
| C-03 | Semantic | SubagentStop stdin JSON contains `last_assistant_message` | plan.md:205 |
| C-04 | Hard | memory field is NOT ignored for plugin subagents | plan.md:25 (implicit) |
| C-05 | Hard | SubagentStop matcher matches agent type regex `archetype-.*` | plan.md:145 |
| C-06 | Assumption | Coordinator as main thread can be launched from /oathfish skill | plan.md:715 |
| C-07 | Hard | Skills 500-line limit | plan.md:43 |
| C-08 | Semantic | context:fork file writes persist to parent filesystem | plan.md (implicit in understand, baseline-amplify, amplify, synthesize skills) |
| C-09 | Hard | Plan specifies "7 skills" | plan.md:16 |
| C-10 | Semantic | INDEPENDENT_PREDICTION is a valid RoundType | plan.md:385 |
| C-11 | Semantic | Post-deliberation amplify uses --no-session-persistence | plan.md:1082 |
| C-12 | Hard | CLAUDE_PLUGIN_DATA available in hook script environment | plan.md:191 |
| C-13 | Negative | Plan has no cross-worker file conflicts | plan.md (implicit) |
| C-14 | Semantic | A-06 VERIFIED: stopped subagent auto-resumes on SendMessage | plan.md:1579 |
| C-15 | Hard | SessionStart compact matcher fires after compaction | plan.md:134 |
| C-16 | Hard | All 12 hazards have mitigations | plan.md:1603 |

---

### Kill List (Falsified Claims & Omissions)

| SK-ID | Type | Claim/Omission | Evidence | Confidence |
|-------|------|----------------|----------|------------|
| SK-01 | Empirical | SubagentStop "can block via decision:block, forcing continuation" (plan.md:48) cites hooks-guide.md:23 | hooks-guide.md:22 says only "When subagent finishes." The primary reference doc contains NO documentation of SubagentStop blocking behavior, no `decision: "block"` for SubagentStop, and no `stop_hook_active` for SubagentStop. The claim originates from hooks-analysis.md:23 (an analysis doc, not the primary reference). The general exit code at hooks-guide.md:62 says "Exit 2: action blocked" but what "blocked" means for SubagentStop specifically is undocumented. | 85% |
| SK-02 | Architectural | Coordinator cannot be both main thread AND launched from /oathfish dispatcher | sub-agents.md:188-190: "Subagents CANNOT spawn other subagents. Only agents running as main thread with `claude --agent` can spawn subagents." The oathfish dispatcher skill (Task C.1) routes to DELIBERATE phase which "Launch `claude --agent deliberation-coordinator`" (plan.md:715). But skills cannot launch main-thread agents. If the dispatcher uses the Agent tool, the coordinator becomes a subagent and CANNOT spawn archetypes. If it uses Bash(claude --agent ...), that creates an entirely separate session, not integrated with the current conversation. The plan says "Coordinator runs as main thread via `claude --agent deliberation-coordinator`" (plan.md:13) but provides no mechanism for the /oathfish entry point to achieve this. | 95% |
| SK-03 | Cross-Worker | Worker C Task C.8 and Worker D Task A.2 both CREATE `skills/archetype-reasoning/SKILL.md` | Worker C plan.md:1231 "CREATE skills/archetype-reasoning/SKILL.md". Worker D plan.md:97 "CREATE skills/archetype-reasoning/SKILL.md". Both define different content for the same file. Worker D's version focuses on methodology steps (decompose, outside view, inside view, synthesis, falsification). Worker C's version has different structure (reference class, decompose, key uncertainties, falsification, anchor-and-adjust, anti-acquiescence). | 100% |
| SK-04 | Empirical | SubagentStop stdin contains `last_assistant_message` field (plan.md:205) | hooks-guide.md:45-57 shows the stdin JSON format with `session_id`, `cwd`, `hook_event_name`, `tool_name`, `tool_input`. There is NO documentation of a `last_assistant_message` field in SubagentStop input. The claim comes from hooks-analysis.md:231, not the primary reference. The validate-no-numbers.sh script depends entirely on this field existing. | 80% |
| SK-05 | Inconsistency | Plan says "7 skills" (plan.md:16) but lists 8 SKILL.md files in file manifest | File manifest (plan.md:1633-1640) lists: oathfish, understand, baseline-amplify, deliberate, amplify, synthesize, interact, archetype-reasoning = 8 skills. The constraint line says "MUST: 7 skills (oathfish, understand, baseline-amplify, deliberate, amplify, synthesize, interact)." archetype-reasoning is the 8th, excluded from the count. | 90% |
| SK-06 | Semantic | INDEPENDENT_PREDICTION is used as round type name (plan.md:385) but Worker A defines RoundType.PREDICTION | Worker A plan.md:92 defines `PREDICTION = "PREDICTION"` as the RoundType enum. Worker C's coordinator system prompt (plan.md:385) labels round 6 as "INDEPENDENT_PREDICTION". If the coordinator passes "INDEPENDENT_PREDICTION" to MCP's `deliberation_record_round()`, the type validation will fail because the MCP expects "PREDICTION". | 85% |
| SK-07 | Semantic | C-21 deviation: Post-deliberation amplify uses --no-session-persistence instead of --resume SESSION_ID | Feature request C-21 (feature-request.md:1169) explicitly states post-deliberation calls use "--resume SESSION_ID to carry deliberation context." Plan's amplify skill (plan.md:1082-1086) deliberately uses --no-session-persistence. The plan does not flag this as a constraint deviation, does not add it to the assumption registry, and does not explain the trade-off to the user. | 80% |
| SK-A-01 | Assumption | A-06 classified as VERIFIED but primary reference does not confirm auto-resume | Plan.md:1579 says VERIFIED citing sub-agents.md:167-169. Actual text at sub-agents.md:167: "Each invocation creates fresh instance. Ask Claude to resume via agent ID for continued context." This does NOT say "SendMessage auto-resumes a stopped subagent." The auto-resume claim comes from sub-agents-analysis.md:30,70,314, not the primary reference. Classification should be IMPLICIT, not VERIFIED. | 82% |

---

### Evidence Mirror

**SK-01: SubagentStop blocking behavior**

Steel-Man attempt (primary reference):
```
File: references/raw/hooks-guide.md
Line 22: | `SubagentStop` | When subagent finishes |
Line 62: - **Exit 2**: action blocked. Stderr becomes Claude's feedback.
Line 106: | SubagentStart, SubagentStop | agent type | `Bash`, `Explore`, `Plan`, custom |
```

Search for "decision:block" or "force continuation" in hooks-guide.md:
```
Grep pattern: "decision.*block|block.*subagent|force.*continu"
Path: references/raw/hooks-guide.md
Result: No matches found
```

Search for "last_assistant_message" in hooks-guide.md:
```
Grep pattern: "last_assistant_message"
Path: references/raw/hooks-guide.md
Result: No matches found
```

Analysis doc (secondary source) at hooks-analysis.md:23:
```
10. **SubagentStop** -- subagent finishes. Matcher: agent type.
    Can block (force continuation) via `decision: "block"`.
    Has `stop_hook_active` field.
```

Interpretation: The blocking behavior is asserted in the analysis doc but is NOT documented in the primary hooks-guide.md reference. The general exit code semantics (exit 2 = blocked) provide a reasonable inference, but the specific behavior for SubagentStop (force continuation, stderr becomes feedback to subagent) is not confirmed. The entire C-33 enforcement architecture depends on this undocumented behavior.

**SK-02: Coordinator nesting problem**

```
File: references/raw/sub-agents.md
Line 188: **Subagents CANNOT spawn other subagents.**
Line 190: Only agents running as main thread with `claude --agent` can spawn subagents.
Line 153: **`--agent <name>`**: session-wide, replaces system prompt
```

The /oathfish skill (plan.md lines 700-719) runs inline and dispatches to phases. For DELIBERATE, it says "Launch `claude --agent deliberation-coordinator`". But `--agent` is a session launch parameter (sub-agents.md:153), not an in-session tool. The skill's allowed-tools include Agent and Bash, suggesting two options:
- Agent tool: coordinator becomes subagent, CANNOT spawn archetypes (C-L02 violated)
- Bash(claude --agent ...): creates separate session, not integrated with current conversation

Neither option achieves "coordinator as main thread" when launched from /oathfish.

**SK-03: Cross-worker file collision**

```
Worker C plan.md:1231: CREATE `skills/archetype-reasoning/SKILL.md`
Worker D plan.md:97:   CREATE `skills/archetype-reasoning/SKILL.md`
```

Worker C's version (plan.md lines 1239-1296): Sections are "State Reference Class", "Decompose Into Sub-Questions", "List Key Uncertainties", "State Falsification Criteria", "Anchor and Adjust", "Anti-Acquiescence Protocol"

Worker D's version (plan.md lines 106-118 and beyond): Sections are "Outside View", "Inside View", "Synthesis", "Falsification Criteria", "Calibration Memory"

Different structure, different content. Second worker to execute will overwrite the first.

**SK-04: last_assistant_message field**

```
File: references/raw/hooks-guide.md
Lines 47-57: Stdin JSON example shows:
{
  "session_id": "abc123",
  "cwd": "/Users/sarah/myproject",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": { "command": "npm test" }
}
```

No `last_assistant_message` field documented. The hooks-analysis.md:231 mentions it in passing ("available in last_assistant_message for SubagentStop") but provides no evidence from the primary docs. The validate-no-numbers.sh script at plan.md:205 extracts this field: `MESSAGE=$(echo "$INPUT" | jq -r '.last_assistant_message // empty')`.

If this field does not exist in SubagentStop stdin JSON, the script silently passes (due to `// empty` fallback), and C-33 enforcement FAILS OPEN -- all archetype responses are allowed, numbers included.

**SK-06: RoundType mismatch**

```
Worker A plan.md:92: PREDICTION = "PREDICTION"
Worker C plan.md:385: Round 6: INDEPENDENT_PREDICTION
```

The coordinator's round type table uses "INDEPENDENT_PREDICTION" which is a descriptive label, not a MCP enum value. If the coordinator passes this string to MCP tools (e.g., `deliberation_record_round()`), it will not match Worker A's `RoundType.PREDICTION` enum. The coordinator must use "PREDICTION" when interfacing with MCP.

---

### Assumption Audit

| A-ID | Classification | Skeptic Finding | Status |
|------|----------------|-----------------|--------|
| A-01 | IMPLICIT | Valid inference -- sub-agents.md:190 confirms main thread can spawn, no documented limit | Valid |
| A-02 | IMPLICIT | INVALID -- primary docs do not document SubagentStop stdin schema with last_assistant_message | SK-04 |
| A-03 | IMPLICIT | Valid concern -- no MCP tool examples in allowed-tools docs | Valid |
| A-04 | IMPLICIT | Reasonable inference from hooks-guide.md:119 | Valid |
| A-05 | IMPLICIT | Valid concern -- skills-analysis.md:331 explicitly flags this as unverified | Valid, understated severity |
| A-06 | VERIFIED | OVERCLASSIFIED -- primary source (sub-agents.md:167) says "Ask Claude to resume via agent ID" not "SendMessage auto-resumes" | SK-A-01 |
| A-07 | IMPLICIT | CONFIRMED FALSE by primary source -- sub-agents.md:107 explicitly says mcpServers IGNORED for plugin subagents. Plan already accounts for this. | Valid |
| A-08 | IMPLICIT | Partially supported -- hooks-analysis.md:48 lists CLAUDE_PLUGIN_DATA as available env var, but this is analysis doc not primary reference | Valid |
| A-09 | NEEDS_VERIFICATION | Correctly classified | Valid |

---

### Hazard Audit

| H-ID | Hazard | Mitigation Found | Valid | Notes |
|------|--------|------------------|-------|-------|
| H-01 | Coordinator context pressure | Yes (MCP persistence + compact hook) | Partially -- compact hook depends on active_run file | Mitigation is reasonable |
| H-02 | MCP output 25K limit | Yes (paginated queries) | Yes but plan mentions "paginate" without specifying the mechanism in MCP tool API | |
| H-03 | Plugin subagent hooks IGNORED | Yes (plugin hooks.json with SubagentStop) | Depends on SK-01 (SubagentStop blocking is undocumented) | CRITICAL dependency |
| H-04 | MCP server must be alive | Yes (setup.sh verification) | Yes | |
| H-05 | allowed-tools MCP namespacing | Yes (test with one skill first) | Punt to empirical testing; acceptable | |
| H-06 | Round number unavailable to hooks | Yes (file bridge) | Depends on SK-04 (does hook actually receive archetype output?) | |
| H-07 | Debate serial bottleneck | Yes (reduce to 2 cycles, parallel pairs) | Yes | |
| H-08 | Teams experimental flag | Yes (eliminate dependency if possible) | Yes -- plan correctly avoids Teams for archetypes | |
| H-09 | Subagent concurrency unknown | Yes (batch by priority) | Yes | |
| H-10 | Skills preloading context inflation | Yes (under 100 lines) | Yes | |
| H-11 | INTERACT phase resume | Yes (store subagent IDs) | Depends on SK-A-01 (resume mechanism not verified from primary source) | |
| H-12 | Argument relay fidelity | Yes (verbatim relay in coordinator prompt) | Yes -- prompt-level mitigation, not deterministic | |

**Missing Hazard**: The plan does not identify the nesting problem (SK-02) as a hazard. The dispatcher -> coordinator -> archetype chain creates a 3-level nesting problem. This is arguably the most critical architectural hazard and it is completely unaddressed in the hazard registry.

**Missing Hazard**: `context: fork` file persistence (A-05/SK-08). Four skills use context:fork and write artifacts to the filesystem. If forked subagent writes don't persist, the entire pipeline breaks. skills-analysis.md:331 explicitly flags this. The plan lists it as assumption A-05 but does not add it to the hazard registry or provide a mitigation.

---

### Ambiguity Register

| Claim | Strategies Tried | Result |
|-------|------------------|--------|
| SubagentStop exit 2 forces continuation | 1. Searched hooks-guide.md for "SubagentStop" -- found only event description. 2. Searched for "decision:block" in hooks-guide.md -- no matches. 3. Found hooks-analysis.md:23 claiming it works. 4. Verified general exit code semantics at hooks-guide.md:62. | The inference is reasonable but unverified. The general exit 2 semantics suggest blocking, and the Stop hook (SubagentStop's parent event) supports it. But specific SubagentStop behavior is undocumented. MEDIUM confidence (60%) that it works as described. |
| CLAUDE_PLUGIN_DATA available in hook script env | 1. Searched hooks-guide.md -- not found. 2. Found in hooks-analysis.md:48 as analysis claim. 3. mcp.md:125 documents it for MCP server env config. | Documented for MCP server env, not explicitly for hook scripts. Hooks-analysis:48 claims it, but analysis docs are derivative. MEDIUM confidence (55%). |

---

### Certified Facts

| Claim | Evidence |
|-------|----------|
| Plugin subagent hooks, mcpServers, permissionMode IGNORED | sub-agents.md:107: "For security: `hooks`, `mcpServers`, `permissionMode` fields IGNORED for plugin subagents." |
| Subagents CANNOT spawn other subagents | sub-agents.md:188: "Subagents CANNOT spawn other subagents." |
| Only main thread can spawn subagents | sub-agents.md:190: "Only agents running as main thread with `claude --agent` can spawn subagents." |
| Skills 500-line limit | skills.md:154: "Keep SKILL.md under 500 lines." |
| memory field NOT listed as ignored for plugin subagents | sub-agents.md:107 lists only hooks, mcpServers, permissionMode. memory is absent. |
| SubagentStop matcher filters on agent type | hooks-guide.md:106 |
| SessionStart compact matcher documented | hooks-guide.md:103 |
| Exit 2 = action blocked (general) | hooks-guide.md:62 |
| TeammateIdle exit 2 = keep working | agent-teams.md:90 |
| TaskCompleted exit 2 = prevent completion | agent-teams.md:91 |
| context:fork runs in isolated subagent, no conversation history | skills.md:97 |

---

### Configuration Validity (Attack E)

**E1: SubagentStop hook in plugin hooks.json**

The plan places the SubagentStop hook in `hooks/hooks.json` (plugin-level). Per hooks-guide.md:119, "Plugin hooks/hooks.json" is a valid location. The hook fires for subagents spawned when the plugin is enabled. This is correctly scoped IF plugin hooks apply to subagents spawned by the plugin's agents.

Unverified: Does a plugin-level SubagentStop hook fire for subagents spawned by the plugin's own coordinator agent? The docs say plugin hooks are active "when plugin enabled" but do not specify the interaction between plugin hooks and plugin agents spawning subagents. This is a scoping question (A-04).

**E2: CLAUDE_PLUGIN_DATA in hook scripts**

The plan's hook scripts use `${CLAUDE_PLUGIN_DATA}` extensively. The mcp.md:125 documents this variable for MCP server env configs. The hooks-analysis.md:48 lists it as available in hook script environment. But the primary hooks-guide.md does not list available environment variables for hook scripts beyond the stdin JSON fields. If CLAUDE_PLUGIN_DATA is not set in the hook script's environment, all file bridge paths resolve to `/tmp/...` due to the fallback in the scripts.

**E3: .current_round file bridge**

The round number file bridge depends on:
1. The coordinator writing to `${CLAUDE_PLUGIN_DATA}/.current_round` (plan.md:425)
2. The SubagentStop hook reading from the same path (plan.md:191-197)
3. The MCP server NOT being the one writing this file (the coordinator does it directly)

The coordinator writes to the filesystem (plan.md:425: "Write current round to state file"), but the coordinator's agent definition (plan.md:450) says "Write to state files directly (MCP persists -- C-12)" as something the coordinator NEVER does. This contradicts itself: the coordinator must write .current_round for the hook bridge, but the coordinator is told it never writes state files.

---

### Issue Ledger

| SK-ID | Status | Severity | Notes |
|-------|--------|----------|-------|
| SK-01 | OPEN | CRITICAL | SubagentStop blocking undocumented -- C-33 enforcement at risk |
| SK-02 | OPEN | CRITICAL | Nesting problem -- dispatcher cannot launch coordinator as main thread |
| SK-03 | OPEN | CRITICAL | Cross-worker file collision on archetype-reasoning/SKILL.md |
| SK-04 | OPEN | HIGH | last_assistant_message field undocumented -- C-33 hook may fail open |
| SK-05 | OPEN | MEDIUM | Internal inconsistency: "7 skills" but 8 listed |
| SK-06 | OPEN | HIGH | RoundType mismatch: INDEPENDENT_PREDICTION vs PREDICTION |
| SK-07 | OPEN | HIGH | C-21 deviation undeclared: --no-session-persistence instead of --resume |
| SK-08 | OPEN | HIGH | context:fork file persistence unverified -- 4 skills depend on this |
| SK-09 | OPEN | MEDIUM | .current_round write contradicts "coordinator never writes state files" |
| SK-10 | OPEN | MEDIUM | CLAUDE_PLUGIN_DATA availability in hook scripts unverified from primary docs |
| SK-11 | OPEN | MEDIUM | Missing hazard: nesting problem not in hazard registry |
| SK-12 | OPEN | MEDIUM | Missing hazard: context:fork file persistence not in hazard registry |
| SK-A-01 | OPEN | MEDIUM | A-06 overclassified as VERIFIED -- should be IMPLICIT |

---

### Recommendations for Revision

1. **SK-02 (CRITICAL)**: Resolve the nesting problem. Options:
   a. Make the coordinator the ONLY entry point (`claude --agent deliberation-coordinator`) and fold the dispatcher logic into the coordinator's own system prompt. Phase skills become inline skill invocations, not a separate dispatch layer.
   b. Use `Bash(claude --agent deliberation-coordinator --print-session-id ...)` to launch a separate session and poll for results. This is fragile but technically avoids nesting.
   c. Redesign the phase architecture so the dispatcher IS the coordinator (single agent handles all phases, including spawning archetypes).

2. **SK-01/SK-04 (CRITICAL)**: Reduce dependency on undocumented SubagentStop behavior. Add a fallback: if SubagentStop blocking does not work, the coordinator itself strips numeric content from archetype responses before recording to MCP (coordinator-level enforcement, option c from explore.md:277). This provides defense-in-depth even if the hook-based enforcement fails.

3. **SK-03 (CRITICAL)**: Coordinate with Worker D on archetype-reasoning/SKILL.md ownership. Either Worker C defers to Worker D's version, or they agree on a canonical version before implementation.

4. **SK-06 (HIGH)**: Use "PREDICTION" (matching Worker A's RoundType enum) instead of "INDEPENDENT_PREDICTION" when interfacing with MCP tools.

5. **SK-07 (HIGH)**: Either use `--resume` per C-21, or explicitly add the deviation to the assumption registry and document the rationale (Worker D's A-D04 flags the same uncertainty).

6. **SK-08 (HIGH)**: Add context:fork file persistence to the hazard registry. Provide a mitigation: if fork isolation prevents persistence, use the MCP server for artifact storage instead of direct filesystem writes.
