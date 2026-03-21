# Explore Report - Worker C
## Run: 0001-oathfish-swarm-engine
## Worker: C
## Lens: orchestration

---

## Dependency Map

### Architecture Decision: Coordinator as Main Thread with Subagent Archetypes

After tracing all constraints, the architecture is forced:

**Teams-only (30 archetypes as teammates)** is rejected because:
- Recommended 3-5 teammates (agent-teams.md:109-110), 30 is 6x beyond
- No `memory:project` for teammates -- only subagents get persistent memory (sub-agents.md:70, :78-80)
- No model override per teammate -- only subagents get per-agent model (sub-agents.md:64)
- No maxTurns per teammate -- only subagents get this (sub-agents.md:66)
- Token cost of 32 concurrent sessions is prohibitive (agent-teams-analysis.md:203-209)

**Subagent-only (coordinator as main thread, archetypes as subagents)** is the forced choice because:
- Coordinator MUST be main thread to spawn subagents (sub-agents.md:188-190)
- Subagents get memory:project (sub-agents.md:70), model override (:64), maxTurns (:66), skills preloading (:67)
- True isolation for independent prediction round 6 (sub-agents-analysis.md:223-226)
- All communication mediated through coordinator -- prevents accidental number sharing (sub-agents-analysis.md:226-228)

**Consequence**: No TeamCreate, no SendMessage between archetypes. The coordinator uses the Agent tool to spawn archetypes, collects results, and relays arguments. The coordinator can still use Agent Teams for functional roles (report-analyst as teammate), but archetypes are subagents.

**Evidence chain**:
- sub-agents.md:188-190 "Subagents CANNOT spawn other subagents"
- sub-agents.md:190 "Only agents running as main thread with `claude --agent` can spawn subagents"
- sub-agents-analysis.md:209-217 "the correct statement is: Coordinator as main thread; archetypes as subagents"

### Coordinator Agent (deliberation-coordinator.md)

**Inbound**:
| Caller | Mechanism | Purpose |
|--------|-----------|---------|
| oathfish dispatcher skill | `claude --agent coordinator` | Main thread launch |
| User via /oathfish command | skill -> agent | Entry point |
| Archetype subagent results | Agent tool return | Round responses |

**Outbound**:
| Dependency | Mechanism | Purpose |
|------------|-----------|---------|
| Archetype subagents (30) | Agent tool invocation | Spawn per round |
| oathfish-engine MCP tools | MCP tool calls | deliberation_record_round, deliberation_track_evolution, deliberation_check_convergence, metrics_compute_round |
| Report-analyst subagent | Agent tool invocation | Synthesis phase |
| Filesystem | Read tool | Load archetypes.json, round templates |
| Filesystem | Write tool | Write round summaries, deliberation artifacts |

### Archetype Subagent (archetype-agent.md)

**Inbound**:
| Caller | Mechanism | Purpose |
|--------|-----------|---------|
| Coordinator | Agent tool with prompt injection | Round prompt with previous round summary |
| Coordinator | Resume via agent ID / SendMessage | Continue deliberation across rounds |

**Outbound**:
| Dependency | Mechanism | Purpose |
|------------|-----------|---------|
| Subagent response | Return to coordinator | Position/argument output |
| memory:project | .claude/agent-memory/archetype-{id}/ | Cross-run calibration learning |
| Preloaded skill content | archetype-reasoning skill | Superforecaster methodology |

### Report Analyst (report-analyst.md)

**Inbound**:
| Caller | Mechanism | Purpose |
|--------|-----------|---------|
| Coordinator or synthesize skill | Agent tool invocation | Launch synthesis |
| Archetype subagents | Agent tool (via coordinator relay) | Follow-up interviews |

**Outbound**:
| Dependency | Mechanism | Purpose |
|------------|-----------|---------|
| oathfish-engine MCP tools | MCP tool calls | deliberation_get_position_map, amplify_aggregate, graph_query, metrics_get_trend, calibration tools |
| Filesystem | Read tool | Deliberation artifacts, amplification results |
| Filesystem | Write tool | report.md, reasoning-chains.md, statistics.md, calibration.md, diversity-trajectory.md |

---

## Coupling Analysis

### Coupled Components

| From | To | Type | Evidence | Risk |
|------|-----|------|----------|------|
| Coordinator | Archetype subagents | Spawn/Resume | sub-agents.md:167-169 (resume via SendMessage) | H-01 |
| Coordinator | MCP deliberation engine | Data | feature-request.md:617-621 (record/track/convergence) | H-02 |
| Archetype hooks | Plugin hooks.json | Config | sub-agents.md:107 (plugin subagent hooks IGNORED) | H-03 |
| Skills | MCP state machine | Control flow | feature-request.md:764-767 (state transitions) | H-04 |
| Archetype memory:project | .claude/agent-memory/ | Persistence | sub-agents.md:78-80 | None |
| Phase skills | allowed-tools | Security | skills.md:61 | H-05 |
| validate-no-numbers hook | Current round number | Data | hooks-analysis.md:196-202 | H-06 |
| Coordinator context window | 30 archetype responses x 6 rounds | Capacity | sub-agents-analysis.md:261-263 | H-07 |
| Agent Teams env flag | Teams availability | Config | agent-teams.md:8 | H-08 |

### Decoupled (Safe to modify independently)

| Component A | Component B | Evidence | Implication |
|-------------|-------------|----------|-------------|
| MCP server (engine/) | Claude agent definitions | Separate processes, stdio interface | Can develop MCP and agents in parallel |
| Phase skills | Each other | context:fork isolation (skills.md:95-104) | Phase changes do not cascade |
| Archetype subagents | Each other | Isolated context windows (sub-agents.md:8) | True independence for round 6 |
| Commands (*.md) | Skills (SKILL.md) | Commands route to skills | Command UX independent of orchestration |

---

## Hazard Registry

| H-ID | Category | Hazard | Evidence | Failure Mode | Severity |
|------|----------|--------|----------|--------------|----------|
| H-01 | Architecture | Coordinator context pressure: 30 responses x 6 rounds fills context | sub-agents-analysis.md:261-263 "30 archetype responses per round x 6 rounds = 180 result payloads" | Compaction fires mid-deliberation, coordinator loses argument history | High |
| H-02 | Integration | MCP tools return up to 25,000 tokens per call; deliberation_get_position_map with 30 archetypes may exceed limit | mcp.md:158-162 "Default max: 25,000 tokens" | Position map truncated silently | Medium |
| H-03 | Configuration | Plugin subagent hooks IGNORED -- C-33 enforcement hooks in archetype-agent.md frontmatter will not fire | sub-agents.md:107 "hooks, mcpServers, permissionMode fields IGNORED for plugin subagents" | Numeric predictions leak in rounds 1-5, destroying independence (2402.19379 p=0.011) | Critical |
| H-04 | State | State machine transition validation depends on MCP server being alive | feature-request.md:351 "Run any phase without the MCP server active" is a never-do | Phase proceeds without state tracking, artifacts not persisted | High |
| H-05 | Security | allowed-tools in skill frontmatter may not support MCP tool namespacing correctly | skills-analysis.md:329 "The exact syntax for MCP tools in allowed-tools must be tested" | Phase skills either too permissive (all tools) or too restrictive (MCP tools blocked) | Medium |
| H-06 | State | validate-no-numbers hook needs current round number but SendMessage tool_input may not contain it | hooks-analysis.md:196-202 "The round number is not in the default SendMessage tool_input schema" | Hook cannot distinguish round 6 (numbers required) from rounds 1-5 (numbers blocked) | High |
| H-07 | Performance | Debate topology is serial: each archetype pair exchange requires 3 sequential subagent calls | sub-agents-analysis.md:237-240 "15 pairs, 45 sequential calls per debate round" | STRUCTURED_DEBATE rounds take 3-5x longer than FREE_FORM | Medium |
| H-08 | Configuration | Agent Teams is experimental and disabled by default | agent-teams.md:8 "experimental and disabled by default" | If architecture depends on Teams features, a single env flag change breaks everything | Medium |
| H-09 | Compatibility | Subagent concurrency limit unknown -- docs do not specify max concurrent background subagents | sub-agents-analysis.md:265-267 "The docs do not specify how many background subagents can run concurrently" | If limit is low (3-5), each round requires 6+ batches of archetypes | Medium |
| H-10 | Integration | Skills preloaded into subagents consume context -- 30 subagents x archetype-reasoning skill | skills-analysis.md:317 "200 lines x 30 subagents = 6,000 lines of duplicated methodology" | Each archetype starts with less available context for deliberation | Low |
| H-11 | Architecture | INTERACT phase: subagents complete and return, they do not "remain alive" like Team members | sub-agents-analysis.md:272-275 "subagents complete and return results" | /oathfish-chat requires resume mechanism; archetype may lose context on compaction | Medium |
| H-12 | Data | Debate mediation fidelity: coordinator must faithfully relay arguments without summarizing or filtering | sub-agents-analysis.md:235-236 "coordinator must faithfully relay arguments" | Coordinator inadvertently distorts or summarizes arguments, degrading debate quality | Medium |

---

## Constraint Registry

| C-ID | Type | Constraint | Source | Verified | Evidence |
|------|------|------------|--------|----------|----------|
| C-01 | REQUIREMENT | Claude Code plugin (plugin.json, .mcp.json, agents/, skills/, commands/) | feature-request.md:1122 | INHERITED | Spec states |
| C-04 | REQUIREMENT | Deep deliberation with 30 archetypes communicating via SendMessage | feature-request.md:1125 | CONFLICT | sub-agents.md:188-190 (subagents cannot spawn subagents; must use main-thread coordinator instead of Teams) |
| C-07 | REQUIREMENT | 7-phase state machine: INIT->UNDERSTAND->BASELINE_AMPLIFY->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT->COMPLETE | feature-request.md:1128 | INHERITED | Spec states |
| C-08 | REQUIREMENT | 30 archetypes with persistent identity and memory | feature-request.md:1129 | YES | sub-agents.md:70,78-80 (memory:project provides this) |
| C-10 | REQUIREMENT | 4 deliberation round types + INDEPENDENT_PREDICTION | feature-request.md:1131 | INHERITED | Spec states |
| C-12 | REQUIREMENT | All state mutations through MCP server | feature-request.md:1133 | INHERITED | Spec states |
| C-20 | LIMITATION | Archetype agents have Read + SendMessage only | feature-request.md:1168 | REVISED | In subagent architecture, archetypes return results to coordinator; no SendMessage needed |
| C-22 | INVARIANT | Coordinator never computes metrics | feature-request.md:1175 | INHERITED | Spec states |
| C-25 | INVARIANT | Archetypes never told what position to take | feature-request.md:1178 | INHERITED | Spec states |
| C-33 | REQUIREMENT | No numeric predictions shared until round 6 | feature-request.md:1148 | YES | hooks-guide.md:15-17 (PreToolUse can block), but H-03 means enforcement must be at plugin hooks.json level |
| C-L01 | LIMITATION | Plugin subagent hooks IGNORED for security | sub-agents.md:107 | YES | Direct reading of reference doc |
| C-L02 | LIMITATION | Subagents cannot spawn other subagents | sub-agents.md:188-190 | YES | Direct reading of reference doc |
| C-L03 | LIMITATION | Skills must be under 500 lines | skills.md:153-154 | YES | Direct reading of reference doc |
| C-L04 | LIMITATION | Agent Teams is experimental | agent-teams.md:8 | YES | Direct reading of reference doc |
| C-I01 | INVARIANT | Coordinator is main thread via `claude --agent` | sub-agents.md:190 | YES | Forced by C-L02 |

## Constraint Conflicts

| REQUIREMENT | LIMITATION | Evidence | Severity |
|-------------|------------|----------|----------|
| C-04 (Teams with 30 archetypes via SendMessage) | C-L02 (subagents cannot spawn subagents) | sub-agents.md:188-190 vs feature-request.md:1125 | HIGH -- architecture must be redesigned |
| C-33 (PreToolUse hook in archetype frontmatter) | C-L01 (plugin subagent hooks IGNORED) | feature-request.md:646-654 vs sub-agents.md:107 | CRITICAL -- enforcement mechanism invalidated |

---

## Configuration Hazard Detection

### H-CFG-01: Plugin Subagent Hook Restriction

| Check | Answer | Hazard? |
|-------|--------|---------|
| Scoping | hooks in subagent frontmatter apply only when subagent is NOT a plugin subagent | YES |
| Activation | Plugin agents auto-strip hooks, mcpServers, permissionMode | YES |
| Failure Mode | Silent -- hooks are ignored, no error raised | YES -- CRITICAL silent failure |
| Environment | Same in dev and prod (plugin context) | N/A |

**Resolution**: Define all archetype-scoped hooks at the plugin `hooks/hooks.json` level using `PreToolUse` with tool name matcher. The hook script must detect which agent type is making the call (from stdin JSON `tool_input` or environment) and apply C-33 logic only for archetype agents.

### H-CFG-02: Teams Experimental Flag

| Check | Answer | Hazard? |
|-------|--------|---------|
| Scoping | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` must be set for ANY Teams usage | YES if architecture uses Teams |
| Activation | Feature is disabled by default; user must opt in | YES |
| Failure Mode | TeamCreate/SendMessage tools not available; error on invocation | Observable failure |
| Environment | Must be set in user's settings.json or environment | YES -- setup dependency |

**Resolution**: Since the decided architecture uses subagents (not Teams) for archetypes, Teams dependency is reduced. If the report-analyst is also a subagent (not a teammate), the Teams dependency is eliminated entirely. The setup.sh script should validate the env flag only if Teams features are used.

### H-CFG-03: Round Number Availability for Hook Scripts

| Check | Answer | Hazard? |
|-------|--------|---------|
| Scoping | validate-no-numbers.sh needs current round from MCP state | File-based bridge needed |
| Activation | Hook fires on every tool invocation matching the matcher | YES |
| Failure Mode | Hook blocks round 6 predictions (false positive) or allows round 1-5 numbers (false negative) | YES -- both modes are dangerous |
| Environment | Same dev/prod | N/A |

**Resolution**: The MCP state machine writes the current round number to a known file path (e.g., `${CLAUDE_PLUGIN_DATA}/.current_round`). The hook script reads this file. The MCP server updates it at the start of each round via `deliberation_record_round()`. This creates a file-based bridge between the MCP server and the hook script.

---

## Lens-Specific Findings: Orchestration

### Finding 1: The Deliberation Loop Is Hub-and-Spoke, Not Mesh

In the subagent architecture, all communication flows through the coordinator:

```
Coordinator (main thread)
    |
    |-- spawn Archetype A --> collect response
    |-- spawn Archetype B --> collect response
    |-- ... (30 total, potentially parallel as background)
    |
    Coordinator assembles round summary
    |
    |-- resume Archetype A with summary + round 2 prompt
    |-- resume Archetype B with summary + round 2 prompt
    |-- ...
```

For STRUCTURED_DEBATE (rounds 3-4), the coordinator must:
1. Spawn Archetype A with debate prompt
2. Collect A's argument
3. Spawn/Resume Archetype B with A's argument injected
4. Collect B's challenge
5. Resume Archetype A with B's challenge
6. Collect A's rebuttal

This is 3 sequential subagent calls per debate pair. With 15 pairs and 2 exchange cycles, that is 90 sequential calls minimum.

**Evidence**: sub-agents-analysis.md:237-240

**Impact on design**: The coordinator's system prompt must include explicit debate mediation protocol. The coordinator must NOT summarize arguments when relaying -- it must pass them verbatim or risk degrading debate quality (H-12).

### Finding 2: The 7-Skill Architecture

Based on the 7-phase state machine (C-07) and the workers.yaml:91:

| Skill | Phase | context:fork? | Key Tools |
|-------|-------|---------------|-----------|
| oathfish/SKILL.md | Dispatcher | No (inline) | State machine MCP tools, Agent |
| understand/SKILL.md | UNDERSTAND | Yes | Read, Grep, WebSearch, graph MCP tools |
| baseline-amplify/SKILL.md | BASELINE_AMPLIFY | Yes | Bash (claude -p), amplify MCP tools |
| deliberate/SKILL.md | DELIBERATE | No (stays in coordinator context) | Agent, deliberation MCP tools |
| amplify/SKILL.md | AMPLIFY | Yes | Bash (claude -p), amplify MCP tools |
| synthesize/SKILL.md | SYNTHESIZE | Yes | Read, Write, Agent (report-analyst), all MCP query tools |
| interact/SKILL.md | INTERACT | No (interactive) | Agent (resume archetypes), Read |

**Design decision**: The deliberate skill should NOT use context:fork because the coordinator needs to maintain conversation history across rounds. Forking would create a fresh context per round, losing deliberation continuity.

The baseline-amplify skill is structurally identical to the amplify skill but with two differences: (1) no deliberation context injected (stateless), (2) uses pre-deliberation archetype stances only.

### Finding 3: Command Architecture (3 + 1)

| Command | Skill Route | argument-hint |
|---------|------------|---------------|
| /oathfish | oathfish/SKILL.md | `"topic" --archetypes 30 --rounds 6 --amplify 50 --documents file.pdf` |
| /oathfish-chat | interact/SKILL.md | `--archetype "The Cautious VC" OR --report` |
| /oathfish-inject | deliberate/SKILL.md (scenario injection mode) | `"Breaking: New regulation announced" --run RUN_ID` |
| /oathfish-calibrate | calibrate/SKILL.md (new) | `--run RUN_ID --outcomes outcomes.json` |

The /oathfish-calibrate command is new (per task assignment) and routes to calibration MCP tools (record_outcome, get_domain_bias, get_ensemble_metrics).

### Finding 4: Hook Architecture Must Be Layered

Due to H-03 (plugin subagent hooks IGNORED), the hook architecture must be:

**Layer 1: Plugin hooks/hooks.json** (always active when plugin enabled)
- SessionStart (startup): detect active runs, offer resume
- SessionStart (compact): re-inject deliberation state
- PreToolUse (SendMessage): C-33 no-numbers enforcement -- but this needs careful scoping since the coordinator also uses SendMessage

**Layer 2: Project .claude/settings.json** (active for this project)
- SubagentStart (archetype-.*): inject round-specific context
- TeammateIdle: force continued deliberation if unresolved challenges exist

**Problem with Layer 1 PreToolUse on SendMessage**: In the subagent architecture, archetypes do NOT use SendMessage -- they return results via Agent tool completion. The coordinator uses SendMessage if Teams are used for functional roles. So the PreToolUse hook on SendMessage may not be the right enforcement point.

**Revised C-33 enforcement**: If archetypes are subagents, their "output" is the Agent tool return value, not a SendMessage call. The numbers enforcement must happen either:
(a) In the archetype's system prompt (prompt-level, probabilistic)
(b) In a SubagentStop hook that checks the archetype's last message for numeric content (deterministic, post-hoc)
(c) In the coordinator's logic that strips numbers before relaying to other archetypes (coordinator-level)

Option (b) is the best fit: a SubagentStop hook with matcher `archetype-.*` that parses the last_assistant_message for numeric patterns. If detected, the hook returns `decision: "block"` (forcing the subagent to continue without numbers) or logs a warning.

However, SubagentStop cannot modify the subagent's output -- it can only block completion or allow it. If it blocks, the subagent continues working but may produce numbers again. The hook needs to inject feedback: "Your response contained numeric predictions. Remove all numbers and restate your arguments qualitatively."

**Actually**: Re-reading hooks-guide.md:23, SubagentStop can block via `decision: "block"` which "forces continuation." The stderr becomes feedback to the subagent. So the flow is:

1. Archetype subagent completes with a response
2. SubagentStop hook fires, parses response for numbers
3. If numbers detected: exit 2, stderr = "Remove numeric predictions. Exchange arguments only."
4. Subagent receives feedback and continues, producing a cleaned response
5. SubagentStop fires again on the new completion
6. If clean: exit 0, subagent completes

This is a retry loop. It will terminate because the archetype's system prompt instructs it to not include numbers, and the hook feedback is explicit.

**Round 6 exception**: The SubagentStop hook script reads `${CLAUDE_PLUGIN_DATA}/.current_round`. If round >= 6, exit 0 immediately (allow numbers).

### Finding 5: Structured Stubbornness Encoding

Per the task assignment, each archetype must be stubborn on their domain expertise. This is encoded in the system prompt body of archetype-agent.md, NOT in hooks or skills.

The stubbornness pattern:
```
## Your Expertise and Stubbornness Protocol

You are an authority on {domain_expertise}. When other archetypes challenge your
reasoning in this domain, you DO NOT yield easily. You require:
1. Specific evidence that contradicts your domain knowledge
2. A mechanism that explains WHY your expertise-based prediction is wrong
3. Not just "most people disagree" -- that is social pressure, not evidence

You MAY change your position on topics OUTSIDE your domain expertise when presented
with compelling arguments from domain experts.
```

**Evidence for this pattern**: 2305.14325:17-18 "Prompts that encouraged models to be more 'stubborn' led to LONGER debates and BETTER final solutions"

Examples per archetype type:
- The Cautious VC: stubborn on downside risk assessment, capital preservation concerns
- The Tech Optimist: stubborn on technology adoption curves, capability trajectories
- The Regulator: stubborn on compliance requirements, regulatory precedent
- The Historian (structural): stubborn on base rate anchoring, historical precedent

### Finding 6: The Report Analyst Produces 5 Outputs

Per the task assignment, expanding from the feature request's 3 outputs:

| Output | Content | Source Data |
|--------|---------|-------------|
| report.md | Executive summary, per-segment analysis, cross-segment dynamics, predictions | Deliberation transcripts + amplification distributions |
| reasoning-chains.md | Key reasoning threads from deliberation, argument evolution | Deliberation round artifacts |
| statistics.md | Mass simulation statistical summary, per-archetype distributions | Amplification results |
| calibration.md | Dual Brier scores (corrected + uncorrected), domain bias tracking | Calibration engine MCP tools |
| diversity-trajectory.md | Per-round diversity index, premature consensus events, contrarian injections | Deliberation convergence metrics |

### Finding 7: Coordinator Compaction Resilience

The coordinator will process 30 archetype responses per round across 6 rounds = 180 response payloads. Auto-compaction fires at ~95% context capacity (sub-agents.md:173). The coordinator MUST survive compaction.

**Mechanism**: SessionStart hook with `compact` matcher re-injects:
1. Current run_id, phase, round number
2. Active archetype list (names + IDs for resume)
3. Diversity trajectory so far
4. Last round summary
5. MCP server connection state

The MCP server acts as external memory. After compaction, the coordinator queries:
- `state_get()` for current state
- `deliberation_get_position_map()` for latest positions
- `metrics_get_trend("diversity", 6)` for diversity trajectory

---

## Handoff to Plan

Key constraints for implementation:

1. **MUST** use coordinator-as-main-thread architecture, NOT Teams for archetypes (H-03, C-L02)
2. **MUST** enforce C-33 via SubagentStop hook in plugin hooks.json with round-number file bridge (H-03, H-06)
3. **MUST** design compaction-resilient coordinator with MCP-as-external-memory (H-01, H-07)
4. **MUST** design 7 skills staying under 500 lines each (C-L03)
5. **MUST** encode structured stubbornness per archetype domain in system prompts
6. **MUST** have report analyst produce 5 outputs
7. **SHOULD** batch archetypes in background for parallelism within rounds (H-09)
8. **SHOULD** use verbatim argument relay in STRUCTURED_DEBATE to prevent H-12
9. **MUST** account for plugin subagent restriction on hooks, mcpServers, permissionMode (C-L01)
10. **MUST** include round-number file bridge for hook scripts (H-06)
