# Sub-Agents — OathFish Analysis

**Source**: https://code.claude.com/docs/en/sub-agents
**Date fetched**: 2026-03-18

---

## <reading document>

The Sub-Agents documentation describes a system for creating specialized AI assistants that handle specific types of tasks within Claude Code. Each subagent runs in its own context window with a custom system prompt, specific tool access, and independent permissions. The core primitives are:

**Built-in subagents**: Explore (haiku, read-only), Plan (inherits model, read-only), general-purpose (inherits model, all tools). Also Bash, statusline-setup, and Claude Code Guide as helpers.

**Configuration**: Markdown files with YAML frontmatter. Fields: name, description, tools, disallowedTools, model, permissionMode, maxTurns, skills, mcpServers, hooks, memory, background, isolation.

**Scopes**: CLI `--agents` (session, priority 1), `.claude/agents/` (project, priority 2), `~/.claude/agents/` (user, priority 3), plugin `agents/` (lowest, priority 4).

**Memory**: Three scopes -- `user` (~/.claude/agent-memory/), `project` (.claude/agent-memory/), `local` (.claude/agent-memory-local/). Auto-loads first 200 lines of MEMORY.md. Read/Write/Edit tools auto-enabled when memory is active.

**MCP scoping**: Inline definitions scoped to subagent only (connected on start, disconnected on finish). String references share parent session's connection.

**Permission modes**: default, acceptEdits, dontAsk, bypassPermissions, plan. Parent bypassPermissions takes precedence and cannot be overridden.

**Plugin restrictions**: hooks, mcpServers, permissionMode fields IGNORED for security on plugin subagents.

**Hooks**: PreToolUse, PostToolUse, Stop (auto-converted to SubagentStop). Also SubagentStart and SubagentStop in settings.json for main session hooks.

**Skills**: Full content injected at startup. Subagents do NOT inherit skills from parent -- must list explicitly.

**Invocation**: Natural language, @-mention (guaranteed delegation), `--agent <name>` for session-wide mode. Resume via agent ID using SendMessage tool with agent's ID as `to` field. If a stopped subagent receives SendMessage, it auto-resumes in background.

**Auto-compaction**: ~95% capacity by default. Configurable via CLAUDE_AUTOCOMPACT_PCT_OVERRIDE.

**Isolation**: `worktree` runs in temporary git worktree, auto-cleaned if no changes.

**Background**: `background: true` runs concurrently. Permissions pre-approved before launch. Clarifying questions fail silently.

**The critical constraint**: "Subagents cannot spawn other subagents. If your workflow requires nested delegation, use Skills or chain subagents from the main conversation."

**The spawning mechanism**: "When an agent runs as the main thread with `claude --agent`, it can spawn subagents using the Agent tool. To restrict which subagent types it can spawn, use `Agent(agent_type)` syntax in the `tools` field." And: "If `Agent` is omitted from the `tools` list entirely, the agent cannot spawn any subagents. This restriction only applies to agents running as the main thread with `claude --agent`. Subagents cannot spawn other subagents, so `Agent(agent_type)` has no effect in subagent definitions."

**Resume mechanism**: Each subagent invocation creates a new instance with fresh context. To continue, ask Claude to resume it. Resumed subagents retain full conversation history. Subagent transcripts persist independently of main conversation -- stored in `~/.claude/projects/{project}/{sessionId}/subagents/` as `agent-{agentId}.jsonl`. Transcripts unaffected by main conversation compaction.

**Subagents vs Teams**: "If you need multiple agents working in parallel and communicating with each other, see agent teams instead. Subagents work within a single session; agent teams coordinate across separate sessions."

---

## <what I learned>

### The No-Nesting Rule Is Absolute

The docs are unambiguous: "Subagents cannot spawn other subagents." There is no exception, no workaround, no flag to override this. The text also explicitly states that `Agent(agent_type)` in the tools field "has no effect in subagent definitions." The system actively prevents even configuring the capability.

This is not a soft limitation. It is a hard architectural boundary. The Plan subagent documentation explains the rationale directly: preventing "infinite nesting" of subagents.

### Only `claude --agent` Gets Spawning Power

The spawning mechanism is exclusive to the main thread: "This restriction only applies to agents running as the main thread with `claude --agent`." A main-thread agent running via `claude --agent coordinator` CAN spawn subagents and CAN restrict which types via `Agent(worker, researcher)` syntax. But once spawned, those workers and researchers are subagents and cannot spawn anything further.

### Teams and Subagents Are Separate Systems

The documentation explicitly separates these: "Subagents work within a single session; agent teams coordinate across separate sessions." Teams use SendMessage for inter-agent communication across sessions. Subagents work within a single session. The question is: can a Team member spawn subagents? The docs do not address this directly. But since Team members are "separate Claude Code instances" (per agent-teams.md), each teammate could potentially run as a `claude --agent` instance -- which WOULD have spawning power.

### Memory Is Genuinely Persistent

The memory system is real filesystem persistence, not session-scoped. Project-scope memory lives at `.claude/agent-memory/<name>/`, is version-controllable, and survives across conversations. The auto-load of first 200 lines of MEMORY.md means each subagent boots with accumulated knowledge. This is exactly what the v3 redesign needs for archetype cross-run learning.

### Resume Is Powerful but Scoped

Resume via SendMessage to agent ID preserves full conversation history including all tool calls and reasoning. A stopped subagent auto-resumes on receiving SendMessage. Transcripts persist independently of main conversation compaction. This means an archetype subagent could be resumed across rounds within a session, maintaining its full deliberation history.

### Skills Injection Is Static

Skills are injected at startup -- full content, not lazy-loaded. Subagents do not inherit skills from parent. This is the right mechanism for the superforecaster methodology: inject `oathfish:archetype-reasoning` at archetype boot time, guaranteeing every archetype has the forecasting protocol in context from the start.

---

## <what maps to OathFish>

### Direct Mappings (features that align with OathFish's needs)

| OathFish Need | Sub-Agent Feature | Fit Quality |
|---|---|---|
| Cross-run archetype learning | `memory: project` | EXCELLENT -- .claude/agent-memory/ survives across conversations, version-controllable |
| Superforecaster methodology per archetype | `skills: [oathfish:archetype-reasoning]` | EXCELLENT -- full content injected at startup, uniform across all archetypes |
| No-numbers enforcement rounds 1-5 | `hooks: PreToolUse` on SendMessage | EXCELLENT -- validate-no-numbers.sh blocks numeric predictions before execution |
| Tiered models by centrality | `model: opus\|sonnet\|haiku` | EXCELLENT -- per-subagent model override, exactly as specified in v3 |
| MCP server access for state tracking | `mcpServers` inline or by reference | GOOD -- can scope oathfish-engine MCP to archetype subagents |
| Archetype identity isolation | Separate context window per subagent | EXCELLENT -- each archetype gets its own system prompt and context |
| Round-limit control | `maxTurns` | GOOD -- can limit archetype turns per round to prevent runaway reasoning |
| Permission control | `permissionMode: dontAsk` or `plan` | GOOD -- archetypes should be read-only + SendMessage only |
| Resume across rounds | Resume via agent ID / SendMessage | EXCELLENT -- archetype maintains full deliberation history within session |

### Broken Mappings (features that conflict with OathFish's architecture)

| OathFish Need | Sub-Agent Constraint | Conflict |
|---|---|---|
| Coordinator spawns 30 archetype subagents | Subagents cannot spawn subagents | SHOWSTOPPER if coordinator is a subagent |
| Archetypes communicate via SendMessage | SendMessage is a Teams feature for cross-session communication | MISMATCH -- subagents use Agent tool for delegation, not SendMessage for peer communication |
| 30 persistent archetypes alive for INTERACT phase | Subagent context returns to main conversation on completion | CONTEXT PRESSURE -- 30 subagent results flooding main context |
| Archetypes as peers exchanging arguments | Subagents are hierarchical (parent delegates to child) | STRUCTURAL MISMATCH -- subagents are not peers; they are workers reporting to a parent |

---

## <what maps to the research>

### 2411.10109 (Generative Agent Simulations of 1,000 People)

**Finding**: Persona fidelity improves with persistent data (85% with real interviews).

**Sub-agents mapping**: `memory: project` is the mechanism. Each archetype-{id} accumulates prediction history, bias corrections, and domain-specific learnings in `.claude/agent-memory/archetype-{id}/MEMORY.md`. The auto-load of first 200 lines means the archetype boots with its accumulated persona knowledge. Over multiple OathFish runs, each archetype's memory becomes richer -- analogous to the Stanford paper's real interview data grounding each simulated person.

**Gap**: The Stanford paper used real interview data. OathFish's memory is self-generated (the archetype's own past predictions and reasoning). This is Rung 1 grounding (synthetic), not Rung 2 (real sources). Memory helps with consistency and calibration learning, but does not solve the fidelity problem.

### 2305.14325 (Multi-Agent Debate)

**Finding**: Debate requires inter-agent communication. Stubborn prompts produce better outcomes. Convergence is not success.

**Sub-agents mapping**: This is where the architecture breaks. Debate requires PEER communication -- agents exchanging arguments, challenging each other, responding to challenges. Subagents are HIERARCHICAL -- a parent delegates to a child, the child returns a result. There is no peer-to-peer channel between subagents.

The only way two subagents "communicate" is through the parent: Parent spawns Subagent A, gets result, spawns Subagent B with A's result injected into prompt, gets result, spawns Subagent A again with B's result. This is serial mediation, not direct debate. It works, but it is fundamentally different from SendMessage-based peer exchange, and it is SLOW (sequential, not concurrent).

The structured stubbornness requirement maps to the subagent's system prompt. The hooks mechanism (PreToolUse on SendMessage) maps to the no-numbers enforcement. But the debate TOPOLOGY -- pairs of archetypes challenging each other directly -- does not map cleanly to the subagent model.

### 2409.19839 (ForecastBench)

**Finding**: Superforecaster methodology needs to be preloaded. LLMs significantly underperform superforecasters.

**Sub-agents mapping**: `skills: [oathfish:archetype-reasoning]` is the exact mechanism. The skill content (decompose, base rate, falsify, state uncertainties) is injected at subagent startup. Every archetype gets the same methodology regardless of which round it is in. This is a clean, elegant mapping.

### 2402.19379 (Wisdom of the Silicon Crowd)

**Finding**: Per-domain bias tracking benefits from cross-run memory. Social updating degrades accuracy. Independent prediction aggregation beats social updating.

**Sub-agents mapping**: `memory: project` handles cross-run bias tracking. The independent prediction in Round 6 maps naturally to the subagent model -- each archetype subagent produces its prediction independently, in its own context, without seeing others' numbers. The hooks mechanism enforces no-number-sharing in rounds 1-5.

The deeper insight: the subagent model is actually BETTER for independent prediction than the Teams model. In Teams, archetypes are persistent members who could potentially see each other's messages. In the subagent model, each archetype is isolated in its own context window -- true independence by architecture, not just by protocol.

---

## <what 10x the outcome>

### Option 1: Coordinator as Main Thread (The Clean Architecture)

Run OathFish as `claude --agent coordinator`. The coordinator IS the main thread. It spawns archetype subagents per round using the Agent tool with `Agent(archetype-vc, archetype-founder, archetype-regulator, ...)` restrictions. No Teams involved.

```
claude --agent coordinator "How will AI regulation affect the startup ecosystem?"
    |
    |-- Agent(archetype-cautious-vc) → reasons, returns argument
    |-- Agent(archetype-tech-optimist) → reasons, returns argument
    |-- Agent(archetype-policy-maker) → reasons, returns argument
    |-- ... (30 total, potentially parallel as background subagents)
    |
    Coordinator collects arguments, calls MCP tools for tracking
    |
    Round 2: Resume archetype subagents via SendMessage with round 2 prompt
    |-- Resumed archetype-cautious-vc → receives Round 1 arguments, reasons, returns
    |-- ...
```

**Why this is 10x**:
- No Teams overhead (avoids WARNING-01 about Teams scale at 32 members)
- Each archetype has its own context window (genuine isolation)
- `memory: project` on each archetype for cross-run learning
- Hooks for no-numbers enforcement
- Skills for superforecaster methodology
- Model tiering per archetype
- Resume mechanism preserves full deliberation history across rounds
- Background subagents enable parallel execution within a round
- Coordinator has full spawning power as main thread

**The critical question**: Can background subagents run 30 at a time? The docs say background subagents "run concurrently while you continue working" but do not specify a concurrency limit. If the limit is low (3-5 concurrent), rounds would need to be batched. If high (30+), full parallelism is possible.

### Option 2: Team Lead as Coordinator, Archetypes as Subagents (The Hybrid)

Use a Claude Team where the Team lead runs as `claude --agent coordinator`. Teammates are not archetypes -- they are functional roles (research-assistant, amplification-manager, report-analyst). The coordinator (as main thread) spawns archetype subagents per round.

```
Team Lead (claude --agent coordinator)
    |
    |-- Teammate: research-assistant (UNDERSTAND phase)
    |-- Teammate: amplification-manager (AMPLIFY phase)
    |-- Teammate: report-analyst (SYNTHESIZE phase)
    |
    For DELIBERATE: coordinator spawns archetype subagents directly
    |-- Agent(archetype-cautious-vc) → ...
    |-- Agent(archetype-tech-optimist) → ...
```

**Why this might be better than Option 1**: Functional teammates handle phases in parallel while the coordinator focuses on deliberation orchestration. The report-analyst can work on synthesis while the coordinator manages the final prediction round.

**Why this might be worse**: Added complexity. Team setup overhead. The coordinator's main benefit (spawning subagents) works the same in both options. Teams are better when workers need sustained parallel execution with their own persistent context -- but archetypes already get that from subagent memory.

### Option 3: Skills-Based Archetype Execution (The Workaround)

If subagent concurrency is too limited for 30 parallel archetypes, use skills with `context: fork` instead. Each archetype becomes a skill that runs in a forked subagent context. The coordinator invokes `/archetype-cautious-vc` as a skill, which internally launches a subagent.

The problem: skills with `context: fork` still create subagents. They are subject to the same no-nesting constraint. This only works if the coordinator is the main thread.

**Verdict**: This is not fundamentally different from Option 1. It just uses the skill invocation mechanism instead of direct Agent tool calls. The underlying architecture is the same.

---

## <why?>

### Why Option 1 Is The Right Architecture

The v3 redesign says: "Coordinator in Team; archetypes as subagents spawned per round." But the subagent docs reveal that the correct statement is: "Coordinator as main thread; archetypes as subagents spawned per round."

The difference is subtle but critical:
- "Coordinator in Team" implies the coordinator is a team member, which is a separate Claude Code instance. A team member is NOT a main thread. It cannot spawn subagents.
- "Coordinator as main thread" means running `claude --agent coordinator`. This IS the main thread. It CAN spawn subagents.

The v3 redesign's language was written before the no-nesting constraint was fully understood. The research-driven-redesign.md says (section 7, WARNING-01): "Moving archetypes to persistent subagents (not all Team members) reduces Team size. Coordinator in Team; archetypes as subagents spawned per round. This sidesteps the 32-member limit entirely." The intent is correct (archetypes as subagents). The mechanism is wrong (coordinator cannot be IN a Team and ALSO spawn subagents, unless the Team lead IS running as `claude --agent`).

The fix is simple: the coordinator IS the main thread. There is no Team for deliberation. The Team concept (if used at all) is reserved for functional parallelism across OathFish phases (research, amplification, reporting), not for archetype deliberation.

### Why This Actually Makes the Architecture Better

The subagent model is architecturally superior to the Teams model for archetype deliberation:

1. **True isolation**: Each archetype subagent has its own context window. In Teams, all members share visibility into the mailbox. In subagents, isolation is enforced by the runtime, not by protocol.

2. **Independent prediction is structural**: In Round 6, each archetype subagent produces predictions in its own isolated context. There is no possibility of information leakage. This perfectly implements the research mandate from 2402.19379 (independent aggregation beats social updating).

3. **Coordinator has full control**: The coordinator sees all archetype outputs and decides what to pass forward. In Teams, members can SendMessage to each other without coordinator mediation. In the subagent model, ALL communication flows through the coordinator. This enables the "arguments without numbers" protocol more robustly.

4. **Memory is per-archetype**: Each archetype's `.claude/agent-memory/archetype-{id}/` is completely isolated. No archetype can read another's memory. Cross-run learning is genuinely per-persona.

5. **No scale limit**: Unlike Teams (WARNING-01: untested at 32 members), subagent spawning has no documented member limit. The coordinator spawns 30 subagents -- potentially in parallel as background tasks -- without hitting a Team member cap.

### Why This Creates New Constraints

1. **Serial mediation**: All communication between archetypes flows through the coordinator. Archetype A cannot directly challenge Archetype B. The coordinator must relay A's arguments to B and B's response back to A. This adds latency and requires the coordinator to faithfully relay arguments without summarizing or filtering.

2. **Context accumulation**: Each subagent's result returns to the coordinator's main context. 30 archetype responses per round x 6 rounds = 180 result payloads in the coordinator's context. Even with auto-compaction at 95%, this is substantial pressure. The coordinator needs aggressive summarization between rounds.

3. **Debate topology is indirect**: STRUCTURED_DEBATE (rounds 3-4) pairs opposing archetypes for direct challenges. In the subagent model, "direct" means the coordinator spawns Archetype A, collects its argument, then spawns Archetype B with A's argument injected as context, collects B's challenge, then resumes Archetype A with B's challenge. This is 3 sequential subagent calls per debate pair. With 15 pairs, that is 45 sequential calls per debate round. If background execution enables parallelism across pairs, this drops to 3 sequential calls (one per exchange step).

4. **No true peer networking**: The v3 redesign envisions archetypes as a deliberating swarm. The subagent model makes them isolated workers mediated by a controller. This is philosophically different -- a hub-and-spoke topology instead of a mesh. The research question is whether mediated argument exchange produces the same reasoning quality as direct peer exchange. The debate paper (2305.14325) tested direct debate between agents, not mediated debate. The transfer of this finding to the mediated model is an untested assumption.

---

## <reality check?>

### The No-Nesting Constraint Is NOT a Showstopper

After careful analysis, the constraint "subagents cannot spawn other subagents" is NOT a showstopper for OathFish. It is an architectural constraint that REDIRECTS the design, and the redirected design is arguably better than the original.

The key insight: the v3 redesign never required nested subagent spawning. It required:
1. A coordinator that spawns archetypes -- WORKS if coordinator is main thread
2. Archetypes with persistent memory -- WORKS via `memory: project`
3. Archetypes with hooks and skills -- WORKS via subagent frontmatter
4. Archetypes communicating -- WORKS via coordinator mediation

What the constraint eliminates is the possibility of archetypes spawning their OWN sub-workers. The v3 design never required this. No archetype needs to delegate to a sub-archetype. The hierarchy is exactly two levels deep: coordinator -> archetypes.

### The Real Showstoppers Are Elsewhere

**1. Coordinator context pressure (CRITICAL)**: 30 archetype responses per round, 6 rounds, plus MCP tool calls, plus argument relay -- the coordinator's context will hit 95% auto-compaction multiple times per run. When compaction fires, the coordinator loses detailed argument history from early rounds. This degrades its ability to track argument evolution, detect premature consensus, and faithfully relay arguments in later rounds.

**Mitigation**: Aggressive use of MCP tools for persistence. After each round, the coordinator calls `deliberation_record_round()` to persist all positions to disk. When compaction fires, the coordinator can re-read summaries from disk. The MCP server becomes the coordinator's external memory, compensating for context window pressure.

**2. Subagent concurrency limit (UNKNOWN)**: The docs do not specify how many background subagents can run concurrently. If the limit is low (say, 5), then each round requires 6 batches of 5 archetypes each, serializing what should be parallel. A round that should take 1 subagent-duration takes 6x.

**Mitigation**: Test empirically. If concurrency is limited, batch archetypes by priority (high-centrality first). Alternatively, use the headless SDK (`claude -p`) for archetype execution within a round -- the coordinator spawns subagents for high-centrality archetypes (opus/sonnet) and uses `claude -p` for low-centrality archetypes (haiku), parallelizing the haiku calls via Python async.

**3. Debate topology is mediated, not direct (MODERATE)**: The STRUCTURED_DEBATE round type requires paired challenges. In the subagent model, each exchange requires 3 sequential subagent calls per pair. With 15 pairs and 2-3 exchange cycles per debate, that is 90-135 sequential subagent calls per debate round. Even with parallel pairs (background subagents), each exchange cycle is sequential within a pair: A argues -> B challenges -> A responds.

**Mitigation**: Accept the mediated topology. The coordinator constructs debate prompts that include the opponent's full argument, so each archetype "sees" the challenge even though it was not sent directly. The reasoning quality may be equivalent -- the research has not tested direct vs mediated debate. Reduce exchange cycles from 3 to 2 per debate pair to limit call count.

**4. The INTERACT phase is problematic (MODERATE)**: The feature request says "All 30 archetype agents remain alive in the Team" for post-run interaction. In the subagent model, subagents complete and return results. To "remain alive," each archetype would need to be resumed via its agent ID when the user requests interaction. This works (resume is a documented feature), but it means archetypes are not proactively listening -- they only activate when explicitly resumed.

**Mitigation**: Implement `/oathfish-chat --archetype "The Cautious VC"` as: coordinator receives user message, resumes the specific archetype subagent with the user's question as context, archetype responds, coordinator relays response. The archetype's full deliberation history is preserved in its transcript. This is functionally equivalent to the Teams-based INTERACT, just mediated through the coordinator.

### What the v3 Feature Request Must Change

1. **C-04**: "Claude Teams with 30 archetypes via SendMessage" -> "Coordinator as main thread (`claude --agent coordinator`); 30 archetypes as subagents with `memory: project`. Communication mediated through coordinator, not direct SendMessage."

2. **WARNING-01**: "Claude Teams untested at 32 concurrent members" -> ELIMINATED. No Teams for deliberation. Subagent spawning has no documented member limit.

3. **Section 4.2.1 (deliberation-coordinator)**: Tools list must include `Agent(archetype-cautious-vc, archetype-tech-optimist, ...)` or simply `Agent` for unrestricted spawning. Must NOT include SendMessage (that is a Teams tool). Must include Read, Bash, and all oathfish-engine MCP tools.

4. **Section 4.2.2 (archetype-agent)**: Tools list changes from `Read, SendMessage` to `Read` only (or Read plus oathfish-engine MCP read tools). Archetypes do not SendMessage -- they return results to the coordinator through the normal subagent completion mechanism. If archetypes need to produce structured output, the coordinator's invocation prompt should specify the format, or use `--json-schema` equivalent in the Agent tool parameters.

5. **Architecture diagram (Section 2.1)**: Remove "TeamCreate" reference. Replace with "`claude --agent coordinator` spawns archetype subagents per round." Remove all "SendMessage" references between coordinator and archetypes. Replace with "Agent tool invocation" and "subagent resume via agent ID."

6. **INTERACT phase**: Replace "All 30 archetype agents remain alive in the Team" with "Archetype subagents are resumed on demand via agent ID. Each archetype's full deliberation transcript is preserved and loaded on resume."

---

## <citations from the references document>

### From references/sub-agents.md (local reference)

> "Subagents CANNOT spawn other subagents"
> "Only agents running as main thread with `claude --agent` can spawn subagents"

### From the fetched documentation (https://code.claude.com/docs/en/sub-agents)

> "Subagents cannot spawn other subagents. If your workflow requires nested delegation, use Skills or chain subagents from the main conversation."

> "When an agent runs as the main thread with `claude --agent`, it can spawn subagents using the Agent tool. To restrict which subagent types it can spawn, use `Agent(agent_type)` syntax in the `tools` field."

> "This restriction only applies to agents running as the main thread with `claude --agent`. Subagents cannot spawn other subagents, so `Agent(agent_type)` has no effect in subagent definitions."

> "If you need multiple agents working in parallel and communicating with each other, see agent teams instead. Subagents work within a single session; agent teams coordinate across separate sessions."

> "This prevents infinite nesting (subagents cannot spawn other subagents) while still gathering necessary context." [from Plan subagent description]

> "Each subagent invocation creates a new instance with fresh context. To continue an existing subagent's work instead of starting over, ask Claude to resume it. Resumed subagents retain their full conversation history, including all previous tool calls, results, and reasoning."

> "If a stopped subagent receives a SendMessage, it auto-resumes in the background without requiring a new Agent invocation."

### From references/agent-teams.md (local reference)

> "Team lead (main session) + Teammates (separate Claude Code instances)"
> "No nested teams (teammates can't spawn their own teams)"
> "One team per session"

### From research papers (via research-driven-redesign.md)

> 2411.10109: "85% as accurately as participants replicate their own answers" -- persona fidelity requires persistent data, maps to `memory: project`

> 2305.14325: "more stubborn led to LONGER debates and BETTER final solutions" -- structured stubbornness encoded in subagent system prompts; "debates typically converged into single final answers [that] were not necessarily correct" -- convergence tracking via coordinator, not via subagent self-assessment

> 2409.19839: superforecasters significantly outperform LLMs (p<0.001) -- superforecaster methodology injected via `skills: [oathfish:archetype-reasoning]`

> 2402.19379: "simple averaging beats LLM updating (p=0.011 GPT-4, p=0.001 Claude 2)" -- independent prediction in subagent isolation is structurally superior to shared-context prediction; 57% positive prediction rate (acquiescence bias) -- tracked via `memory: project` cross-run accumulation

### From spec-audit.md (local reference)

> SPEC-01: "Position model/API/prompt assume numbers every round; C-33/C-14 forbid numbers until round 6" -- subagent hooks (PreToolUse) enforce this at runtime

> WARNING-01: "Claude Teams untested at 32 concurrent members" -- ELIMINATED by moving to subagent architecture without Teams for deliberation

### From feature-request.md v3 (local reference)

> C-04: "Claude Teams with 30 archetypes via SendMessage" -- MUST BE REVISED per this analysis

> Section 4.2.2: "archetype-{id} ... memory: project ... skills: [oathfish:archetype-reasoning] ... hooks: PreToolUse" -- all confirmed feasible via subagent frontmatter, but invocation mechanism must change from SendMessage to Agent tool
