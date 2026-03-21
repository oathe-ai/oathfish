# Claude Code Tools Reference — OathFish Analysis

**Source**: https://code.claude.com/docs/en/tools-reference
**Date fetched**: 2026-03-18

---

## Reading the document

The Tools Reference is a concise inventory of every tool Claude Code can invoke, organized into a single table with three columns: tool name (exact string used in permission rules and subagent tool lists), description, and whether user permission is required. It then provides a short section on Bash tool behavior (working directory persists; environment variables do not). The full list includes 28 tools, ranging from file I/O (Read, Write, Edit) to agent orchestration (Agent, SendMessage, TeamCreate) to web access (WebFetch, WebSearch) to task management (TaskCreate/Get/List/Update/Output/Stop) to scheduling (CronCreate/Delete/List) and code intelligence (LSP). Tool names in this document are the exact strings used in `--allowedTools`, `--disallowedTools`, `--tools`, subagent `tools` frontmatter, and permission rule matchers.

Key tools documented:

| Tool | Permission | Description |
|------|-----------|-------------|
| `Agent` | No | Spawns a subagent with its own context window |
| `Bash` | Yes | Executes shell commands |
| `Edit` | Yes | Targeted file edits |
| `Write` | Yes | Creates or overwrites files |
| `Read` | No | Reads file contents |
| `Glob` | No | Pattern-based file finding |
| `Grep` | No | Content pattern search |
| `Skill` | Yes | Executes a skill within the main conversation |
| `SendMessage` | — | Agent Teams inter-agent messaging (not in tools table; part of Teams) |
| `TaskCreate` | No | Creates a new task in the task list |
| `TaskGet` | No | Retrieves full details for a specific task |
| `TaskList` | No | Lists all tasks with current status |
| `TaskUpdate` | No | Updates task status, dependencies, details |
| `TaskOutput` | No | Retrieves output from a background task |
| `TaskStop` | No | Kills a running background task |
| `TodoWrite` | No | Session task checklist (non-interactive/Agent SDK mode) |
| `WebFetch` | Yes | Fetches URL content |
| `WebSearch` | Yes | Performs web searches |
| `NotebookEdit` | Yes | Modifies Jupyter notebook cells |
| `ToolSearch` | No | Searches/loads deferred tools (MCP tool search) |
| `EnterWorktree` | No | Creates isolated git worktree |
| `ExitWorktree` | No | Exits worktree session |
| `EnterPlanMode` | No | Switches to plan mode |
| `ExitPlanMode` | Yes | Presents plan for approval |
| `AskUserQuestion` | No | Asks multiple-choice questions to gather requirements |
| `CronCreate` | No | Schedules recurring/one-shot prompt within session |
| `CronDelete` | No | Cancels scheduled task |
| `CronList` | No | Lists scheduled tasks |
| `ListMcpResourcesTool` | No | Lists MCP server resources |
| `ReadMcpResourceTool` | No | Reads specific MCP resource by URI |
| `LSP` | No | Code intelligence via language servers |

Bash tool behavior specifics:
- Working directory persists across commands
- `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1` resets to project dir after each command
- Environment variables do NOT persist between commands
- `CLAUDE_ENV_FILE` or SessionStart hooks can persist env vars

---

## What I learned

### 1. Permission topology splits tools into two clean categories

Tools requiring permission (`Yes`): Bash, Edit, Write, Skill, WebFetch, WebSearch, NotebookEdit, ExitPlanMode. These are the "world-changing" tools — they modify files, execute commands, or reach external systems.

Tools requiring no permission (`No`): Agent, Read, Glob, Grep, all Task* tools, TodoWrite, ToolSearch, AskUserQuestion, Cron*, EnterWorktree, ExitWorktree, EnterPlanMode, ListMcpResourcesTool, ReadMcpResourceTool, LSP. These are "read-only" or "coordination" tools that observe state without modifying it.

This split matters for OathFish because archetype agents (C-20: "Read + SendMessage only") are deliberately in the no-permission tier. They cannot modify the world — they can only reason and communicate. The coordinator and report-analyst have Write and Bash (permission-required) because they create artifacts and orchestrate.

### 2. The Agent tool spawns subagents without permission

This is significant: spawning a subagent is a no-permission operation. The coordinator can spawn archetype subagents without user approval. But the subagent's *own* tool use may require permission depending on what tools it has and the permission mode. Since archetypes only have Read + SendMessage (both no-permission), archetype subagents can run fully autonomously once spawned.

### 3. Task management tools are free (no permission)

TaskCreate, TaskGet, TaskList, TaskUpdate, TaskOutput, TaskStop — all no-permission. This means the shared task list in Agent Teams is fully autonomous. The coordinator can create tasks, teammates can self-claim via TaskUpdate, and status changes propagate without user intervention. This is the backbone of the Agent Teams coordination model that OathFish's deliberation phase uses.

### 4. TodoWrite vs Task* tools serve different modes

TodoWrite is for non-interactive mode and the Agent SDK. Task* tools are for interactive sessions. OathFish's mass amplification (`claude -p`) runs in non-interactive mode, so amplification workers would use TodoWrite. The deliberation Team (interactive) uses Task* tools. This is a subtle but important distinction for the two-layer architecture.

### 5. MCP tools are accessed via ToolSearch and MCP resource tools

The `ToolSearch` tool loads deferred MCP tools dynamically. `ListMcpResourcesTool` and `ReadMcpResourceTool` provide access to MCP server resources. OathFish's ~28 MCP tools from the oathfish-engine server would be registered at startup and available via ToolSearch if deferred loading is enabled.

### 6. Bash tool's env var non-persistence is a constraint for amplification

The documented behavior — "Environment variables do not persist. An `export` in one command will not be available in the next" — means the amplification engine cannot set state via environment variables between `claude -p` calls. Each call is truly stateless (reinforcing C-21). The `CLAUDE_ENV_FILE` workaround is irrelevant for `claude -p` because each invocation is a separate process.

### 7. CronCreate enables scheduled tasks within a session

CronCreate can schedule "recurring or one-shot" prompts within the current session. This could be useful for OathFish's diversity monitoring: schedule a periodic check during deliberation that calls `deliberation_check_convergence()` and triggers contrarian injection if premature consensus is detected (C-32). However, Cron tasks are session-scoped (gone when Claude exits), so they are only useful within a single deliberation run.

### 8. AskUserQuestion is a no-permission clarification tool

AskUserQuestion presents multiple-choice questions. This maps to the user checkpoints every 3 rounds (C-24): the coordinator could use AskUserQuestion to present checkpoint summaries and let the user approve/redirect the deliberation.

---

## What maps to OathFish

### Agent allocation across OathFish's three agent types

**deliberation-coordinator** (feature-request.md line 593-608):
- Tools used: Read, Write, SendMessage, Bash, all oathfish-engine MCP tools
- Permission profile: Write (Yes), Bash (Yes), Skill (Yes). Needs `permissionMode: bypassPermissions` or `--dangerously-skip-permissions` for autonomous operation.
- Agent tool: Implicitly uses Agent to spawn archetype subagents for each round.
- Task tools: Uses TaskCreate to create deliberation tasks; TaskUpdate to track round progress.

**archetype-agent** (feature-request.md line 630-655):
- Tools: Read, SendMessage (C-20)
- Permission profile: Both are no-permission tools. Archetypes run fully autonomously — no user approval needed for any tool invocation.
- Deliberate limitation: No Write, no Bash, no Edit, no MCP tools. Archetypes cannot modify state directly. All state changes go through the coordinator calling MCP tools (C-12, C-22).
- This maps perfectly to the tools reference: Read (No permission) + SendMessage (Agent Teams messaging, no permission equivalent).

**report-analyst** (feature-request.md line 727-744):
- Tools: Read, Write, Grep, Glob, SendMessage, all oathfish-engine MCP tools
- Permission profile: Write (Yes). Needs permission bypass for autonomous report generation.
- Uses Grep/Glob (both no-permission) for codebase navigation through deliberation artifacts.
- SendMessage for archetype interviews during synthesis.

### Tool-to-constraint mapping

| Tool | Constraint | How it's used |
|------|-----------|--------------|
| `Agent` | C-04, C-08 | Spawns 30 archetype subagents + report-analyst |
| `SendMessage` | C-04, C-33 | Inter-agent communication; arguments exchanged rounds 1-5 |
| `Bash` | C-05 | Coordinator runs `claude -p` amplification calls |
| `Write` | C-15 | Coordinator/report-analyst create artifact files |
| `Read` | C-20 | All agents read state files; archetypes read deliberation prompts |
| `Skill` | C-07 | Executes 6 phase skills (understand, deliberate, amplify, synthesize, interact, dispatcher) |
| `TaskCreate/Update` | C-07 | Shared task list for Team coordination |
| `Glob/Grep` | C-11 | Report-analyst navigates deliberation transcripts |
| `ToolSearch` | C-06 | Loads oathfish-engine MCP tools at startup |

### Permission modes per agent type

The tools reference indicates which tools need permission. Combined with subagent `permissionMode` options:

| Agent | permissionMode | Why |
|-------|---------------|-----|
| deliberation-coordinator | `bypassPermissions` | Must autonomously Write, Bash, Skill without user prompts during multi-hour deliberation runs |
| archetype-agent | `default` or `dontAsk` | Only uses no-permission tools (Read, SendMessage), so permissionMode is irrelevant — nothing to approve |
| report-analyst | `bypassPermissions` | Must autonomously Write report artifacts |

---

## What maps to the research

### Paper 2305.14325 (Multi-Agent Debate) — Tool constraints enforce debate structure

The debate paper's core finding — "stubborn prompts produce better outcomes" and "separate arguments from predictions" — maps to tool-level enforcement. Archetype agents having ONLY Read + SendMessage means they physically cannot write their own numeric predictions to files. The coordinator controls what gets recorded via MCP tools. During rounds 1-5 (arguments only), the coordinator calls `deliberation_record_round()` with `ArgumentPosition` data. The archetype's PreToolUse hook on SendMessage (line 646-651 of feature-request.md) validates that no numeric predictions are shared. The tool architecture enforces the separation: archetypes have no tool to "cheat" the arguments-only protocol.

### Paper 2402.19379 (Silicon Crowd) — Independent prediction via tool isolation

The ensemble paper's finding that "social updating degrades accuracy (p=0.011)" is enforced by the tool topology. In round 6 (INDEPENDENT_PREDICTION), archetype agents still only have Read + SendMessage. But the coordinator does NOT broadcast other archetypes' predictions. Each archetype sends its structured prediction to the coordinator, and the coordinator records it via MCP. No archetype has access to `deliberation_get_position_map()` (an MCP tool they lack). The independence is enforced by tool access, not just prompting.

### Paper 2409.19839 (ForecastBench) — Bash tool enables external submission

The forecast paper's non-negotiable recommendation — "Submit to ForecastBench before any public accuracy claims" (Tier 1, 35/40) — requires Bash tool access to run submission scripts. The coordinator or a dedicated submission subagent would use Bash to submit predictions. This is a permission-required tool, so the user must approve submission (appropriate for an external-facing action).

### Paper 2411.10109 (Generative Agents) — Persistent memory via subagent memory:project

The persona paper's grounding ladder recommendation maps to the subagent `memory` field. With `memory: project`, each archetype-agent accumulates cross-run learning in `.claude/agent-memory/<archetype-id>/`. The tools reference shows Read, Write, and Edit are automatically enabled when memory is active, but OathFish's archetype definition restricts tools to Read + SendMessage. This creates a tension: memory requires Write (to update memory files), but C-20 restricts archetypes to Read + SendMessage. Resolution: the `memory: project` feature automatically adds Read/Write/Edit for the memory directory specifically, not for general file access. The archetype cannot write to arbitrary files but CAN update its memory store.

### Paper 2602.19520 (Calibration Decomposition) — MCP tools enforce deterministic metrics

The calibration paper's 4-component decomposition model is deterministic math that belongs in the MCP server. The tools reference confirms that MCP tools are separate from Claude's built-in tools. The 5 calibration MCP tools (`calibration_record_prediction`, `calibration_record_outcome`, `calibration_get_domain_bias`, `calibration_get_archetype_bias`, `calibration_get_ensemble_metrics`) are all deterministic computations. Only the coordinator and report-analyst have access to these tools. Archetypes never see calibration data (prevents overfitting, per paper-persona's risk).

---

## What 10x the outcome

### 1. Use `Agent(archetype-*)` restrictions in the coordinator to prevent subagent sprawl

The subagent docs show `Agent(worker, researcher)` syntax to restrict which subagent types can be spawned. OathFish should use this in the coordinator definition:

```yaml
tools:
  - Agent(archetype-*, report-analyst)
  - Read
  - Write
  - SendMessage
  - Bash
  - all oathfish-engine MCP tools
```

This prevents the coordinator from spawning arbitrary subagents — it can only spawn archetype agents and the report-analyst. Combined with `maxTurns` per subagent, this bounds the system's computational footprint.

### 2. Use `TaskCreate`/`TaskUpdate` as the shared task list for deliberation rounds

Agent Teams use shared task lists with three states: pending, in progress, completed. Tasks can have dependencies. Map this to deliberation:

- Each round becomes a Task with dependencies on the previous round
- Each archetype's response within a round becomes a sub-task
- The coordinator creates tasks; archetypes self-claim their response tasks
- Task dependencies prevent archetypes from responding to round N+1 before round N completes
- This replaces ad-hoc coordination with the built-in task system

File-locking prevents race conditions when multiple archetypes try to claim the same task simultaneously (documented in Agent Teams reference).

### 3. Use `CronCreate` for periodic diversity monitoring during deliberation

Instead of the coordinator manually checking diversity after every round, schedule a Cron task:

```
CronCreate: Every 2 minutes during deliberation, call deliberation_check_convergence()
and trigger contrarian injection if diversity_index < 3 clusters
```

This implements C-32 (diversity index tracking) without consuming coordinator context on monitoring logic. The Cron task runs within the session and disappears when the run completes.

### 4. Use `AskUserQuestion` for structured checkpoint approvals (C-24)

Instead of the coordinator writing checkpoint summaries and waiting for free-text user input, use AskUserQuestion:

```
After round 3: "Deliberation halfway point. Diversity index: 4.2. Key argument themes: [X, Y, Z].
Coalition structure: [A]. How would you like to proceed?"
Options:
  A) Continue deliberation as planned
  B) Inject a contrarian scenario to increase diversity
  C) Skip remaining rounds and go to independent prediction
  D) Pause and let me review transcripts
```

This gives the user structured control without breaking the coordinator's flow.

### 5. Exploit the `background` subagent field for parallel archetype responses

The subagent docs show a `background` field that runs subagents concurrently. For each deliberation round, spawn all 30 archetype responses as background subagents:

```yaml
background: true  # Run in parallel, don't block coordinator
```

The coordinator spawns 30 background archetype tasks, then waits for all TaskOutput results. This parallelizes deliberation rounds instead of serial archetype-by-archetype processing. Token cost is higher (each archetype has its own context), but wall-clock time drops from O(30 * response_time) to O(max_response_time).

### 6. Use `isolation: worktree` for A/B baseline amplification

The subagent docs show `isolation: worktree` which runs the subagent in a temporary git worktree. For the baseline amplification (C-26), run it in an isolated worktree so its results cannot contaminate the deliberation-informed amplification:

```yaml
name: baseline-amplifier
isolation: worktree  # Isolated copy of repository
tools: Bash, Read, Write
```

The baseline amplifier works in a clean copy, writes its results, and the main session reads them for comparison. The worktree is auto-cleaned if no changes are made.

### 7. Use `EnterPlanMode`/`ExitPlanMode` for teammate plan approval in deliberation

The Agent Teams docs describe requiring plan approval before teammates implement. Map this to deliberation: before each archetype responds in STRUCTURED_DEBATE rounds, require the coordinator to approve its debate strategy. This prevents low-quality debate exchanges:

```
Coordinator: "Archetype 'Cautious VC', plan your debate response against 'Tech Optimist'
on the adoption timeline argument."
Archetype plans → Coordinator reviews → Approves or rejects with feedback
```

This uses the documented plan approval workflow to improve debate quality (aligns with paper-debate's finding that structured, stubborn debates produce better outcomes).

### 8. Use `disallowedTools` to enforce C-33 at the tool level

Instead of relying solely on the PreToolUse hook to block numeric predictions in rounds 1-5, use dynamic tool restrictions:

- Rounds 1-5: `disallowedTools: ["Write", "Edit"]` — archetypes cannot write anything
- Round 6: Remove the restriction — archetypes can now produce structured predictions

This is defense-in-depth: even if the PreToolUse hook fails, the tool restriction prevents information leakage. The tools reference confirms that `disallowedTools` removes tools from the model's context entirely — the archetype will not even know Write exists during argument rounds.

---

## Why?

The tools reference reveals that OathFish's architecture is not just using Claude Code as an API — it is exploiting the permission topology and tool isolation system as an enforcement mechanism for research-mandated constraints. The fact that archetype agents have only Read + SendMessage (both no-permission) is not just a cost optimization — it is a structural guarantee that archetypes cannot bypass the deliberation protocol. They cannot write their own files, cannot compute their own metrics, cannot access calibration data, and cannot see other archetypes' numeric predictions. The coordinator holds all the "power" tools (Write, Bash, MCP) and mediates all state changes. This maps directly to the research consensus: separate creative reasoning (archetype tools) from deterministic computation (coordinator + MCP tools).

The 10x insight is that Claude Code's tool system provides exactly the kind of "information barrier" that the research papers demand. The ensemble paper (2402.19379) proved that sharing numeric predictions between agents degrades accuracy. The debate paper (2305.14325) proved that arguments without numbers produce better reasoning. The tools reference shows how to enforce these findings architecturally: give agents only the tools that enable the desired behavior, and structurally deny tools that would enable the undesired behavior. This is not prompt engineering — it is capability engineering.

---

## Reality check?

### Tool counts are manageable but non-trivial

OathFish uses ~28 MCP tools + the standard built-in tools. The `ToolSearch` deferred loading mechanism helps: not all tools need to be in context simultaneously. But 28 MCP tools means 28 tool descriptions in the system prompt, consuming context tokens. At scale (30 archetypes), this is fine because archetypes only see Read + SendMessage (2 tools), not the full MCP set.

### Permission bypass is required for autonomous operation

Three agents need `permissionMode: bypassPermissions` — this is a significant security posture. The coordinator runs for hours unattended with full Write + Bash access. The tools reference notes that even with bypassPermissions, writes to `.git`, `.claude`, `.vscode`, and `.idea` directories still prompt for confirmation. This is a safety net, but OathFish's file writes go to the run directory (`docs/oathfish/runs/`), which is unrestricted.

### Background subagents have limitations

Background subagents auto-deny permission prompts that were not pre-approved. Since archetype agents only use no-permission tools, this is fine. But if any archetype tool changes in the future (e.g., adding Bash for source grounding), background mode would break.

### Agent tool spawns subagents, not Team members

There is an important distinction between the `Agent` tool (spawns subagents within a session) and `TeamCreate` (creates an Agent Team with separate sessions). The feature request uses BOTH: Teams for the overall coordination structure, and subagents for the archetype agents. This dual model is architecturally sound but adds complexity. The tools reference does not explicitly document SendMessage or TeamCreate in the main table — these are part of the experimental Agent Teams feature, which has known limitations (no session resumption with in-process teammates, task status can lag, one team per session).

### Memory:project for 30 archetypes creates 30 memory directories

Each archetype with `memory: project` gets `.claude/agent-memory/<archetype-id>/`. With 30 archetypes, that is 30 directories accumulating data across runs. This is manageable but needs a cleanup strategy. The tools reference notes automatic cleanup based on `cleanupPeriodDays` (default 30 days), but archetype memory should persist across runs indefinitely for calibration learning.

### The Bash tool's env var non-persistence reinforces statelessness

The documented behavior that environment variables do not persist between Bash commands means even the coordinator cannot smuggle state between amplification calls via env vars. Each `claude -p` invocation is a separate process with a clean environment. This architecturally enforces C-21 (stateless mass layer) at the tool level, not just the prompt level.

---

## Citations from the reference document

> "Claude Code has access to a set of tools that help it understand and modify your codebase. The tool names below are the exact strings you use in permission rules, subagent tool lists, and hook matchers."
— Tools Reference, introduction

> "Agent: Spawns a subagent with its own context window to handle a task — Permission Required: No"
— Tools Reference, tool table

> "Bash: Executes shell commands in your environment — Permission Required: Yes"
— Tools Reference, tool table

> "Skill: Executes a skill within the main conversation — Permission Required: Yes"
— Tools Reference, tool table

> "TaskCreate: Creates a new task in the task list — Permission Required: No"
— Tools Reference, tool table

> "TaskUpdate: Updates task status, dependencies, details, or deletes tasks — Permission Required: No"
— Tools Reference, tool table

> "TodoWrite: Manages the session task checklist. Available in non-interactive mode and the Agent SDK; interactive sessions use TaskCreate, TaskGet, TaskList, and TaskUpdate instead — Permission Required: No"
— Tools Reference, tool table

> "ToolSearch: Searches for and loads deferred tools when tool search is enabled — Permission Required: No"
— Tools Reference, tool table

> "Working directory persists across commands. Set CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1 to reset to the project directory after each command."
— Tools Reference, Bash tool behavior

> "Environment variables do not persist. An export in one command will not be available in the next."
— Tools Reference, Bash tool behavior

> "Activate your virtualenv or conda environment before launching Claude Code. To make environment variables persist across Bash commands, set CLAUDE_ENV_FILE to a shell script before launching Claude Code, or use a SessionStart hook to populate it dynamically."
— Tools Reference, Bash tool behavior

> "AskUserQuestion: Asks multiple-choice questions to gather requirements or clarify ambiguity — Permission Required: No"
— Tools Reference, tool table

> "CronCreate: Schedules a recurring or one-shot prompt within the current session (gone when Claude exits) — Permission Required: No"
— Tools Reference, tool table

> "EnterWorktree: Creates an isolated git worktree and switches into it — Permission Required: No"
— Tools Reference, tool table

> "LSP: Code intelligence via language servers. Reports type errors and warnings automatically after file edits. — Permission Required: No"
— Tools Reference, tool table

**Cross-referenced with Agent Teams documentation** (https://code.claude.com/docs/en/agent-teams):

> "Teammates share a task list, claim work, and communicate directly with each other."
— Agent Teams, architecture comparison

> "Task claiming uses file locking to prevent race conditions when multiple teammates try to claim the same task simultaneously."
— Agent Teams, task coordination

> "The shared task list coordinates work across the team. The lead creates tasks and teammates work through them. Tasks have three states: pending, in progress, and completed. Tasks can also depend on other tasks."
— Agent Teams, task management

**Cross-referenced with Subagents documentation** (https://code.claude.com/docs/en/sub-agents):

> "To restrict tools, use the tools field (allowlist) or disallowedTools field (denylist)"
— Subagents, tool control

> "Set to true to always run this subagent as a background task."
— Subagents, background field

> "Set to worktree to run the subagent in a temporary git worktree, giving it an isolated copy of the repository."
— Subagents, isolation field

> "When memory is enabled: The subagent's system prompt includes instructions for reading and writing to the memory directory. Read, Write, and Edit tools are automatically enabled so the subagent can manage its memory files."
— Subagents, persistent memory

> "Use Agent(agent_type) syntax in the tools field... This is an allowlist: only the worker and researcher subagents can be spawned."
— Subagents, restricting subagent spawning

> "bypassPermissions: Skip permission prompts"
— Subagents, permission modes
