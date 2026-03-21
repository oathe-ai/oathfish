# Discover Report - Worker C
## Run: 0001-oathfish-swarm-engine
## Keywords: deliberation-coordinator, archetype-agent, report-analyst, SKILL.md, TeamCreate, SendMessage, plugin.json, hooks, structured_stubbornness, arguments_only
## Lens: orchestration
## Entry Point: docs/darwin/runs/0001-oathfish-swarm-engine/_meta/feature-request.md S4.2-4.6

---

## Memory-Informed Context

No prior Serena memories relevant to OathFish orchestration design were found. The project memory index (`~/.claude/projects/-Users-shezmalik-Projects-Oathe-oathfish/memory/MEMORY.md`) contains only the OathFish Project Vision reference. All findings below are derived from direct reading of reference docs and the feature request.

---

## Search Strategy

| Type | Keywords | Source |
|------|----------|--------|
| Literal | deliberation-coordinator, archetype-agent, report-analyst | feature-request.md:592-744 |
| Literal | SKILL.md, plugin.json, hooks.json | feature-request.md:1012-1052 |
| Literal | TeamCreate, SendMessage, Broadcast | feature-request.md:143, agent-teams.md:83-86 |
| Literal | structured_stubbornness, arguments_only | feature-request.md:161-163 |
| Framework | PreToolUse, PostToolUse, TeammateIdle, TaskCompleted | hooks-guide.md:11-28 |
| Framework | context:fork, skills preloading, memory:project | skills.md:63, sub-agents.md:67-70 |
| Framework | permissionDecision, updatedInput, exit 2 | hooks-guide.md:66-79 |
| Synonyms | maxTurns, model override, allowed-tools | sub-agents.md:66-67, skills.md:61-62 |
| Anti-seeds | subagents cannot spawn, no nested teams, plugin restrictions | sub-agents.md:188-190, agent-teams.md:122-123, sub-agents.md:107 |
| Research | stubborn prompts, acquiescence bias, no numbers during debate | 2305.14325:17-18, 2402.19379:23-39 |

---

## Mandatory Anchors

### Package Manifest

- **File**: `package.json:1-5`
- **Name**: oathfish, version 0.1.0
- **No dependencies yet** - greenfield project, no existing code to integrate with

### Application Entry

- **No existing application entry point** - this is a new Claude Code plugin to be designed from scratch
- Plugin entry will be via `.claude-plugin/plugin.json` per feature-request.md:1017
- MCP entry will be via `.mcp.json` per feature-request.md:1054-1069

### Type Definitions

- **No existing types** - Pydantic models defined in feature-request.md:522-587
- ArgumentPosition (rounds 1-5): feature-request.md:535-544
- PredictionPosition (round 6): feature-request.md:546-561

---

## Surface Inventory

### HIGH Relevance

| Item | File | Anchor | Relevance |
|------|------|--------|-----------|
| Subagent frontmatter fields (name, description, tools, model, maxTurns, skills, hooks, memory) | references/raw/sub-agents.md | :58-72 | CRITICAL - defines archetype-agent capabilities |
| Subagents CANNOT spawn other subagents | references/raw/sub-agents.md | :188-190 | CRITICAL - forces coordinator to be main thread |
| Plugin subagents: hooks, mcpServers, permissionMode fields IGNORED | references/raw/sub-agents.md | :107 | CRITICAL - plugin security restriction |
| Memory: project scope at .claude/agent-memory/<name>/ | references/raw/sub-agents.md | :78-80 | CRITICAL - cross-run archetype learning |
| Skills preloading: full content injected at startup | references/raw/sub-agents.md | :67, :146-147 | CRITICAL - superforecaster methodology injection |
| Agent Teams experimental, requires env flag | references/raw/agent-teams.md | :8 | HIGH - Teams is experimental |
| Teams: SendMessage one-to-one, Broadcast to all | references/raw/agent-teams.md | :83-86 | HIGH - communication primitive |
| Teams: TeammateIdle (exit 2 = keep working) | references/raw/agent-teams.md | :90 | HIGH - deliberation quality gate |
| Teams: TaskCompleted (exit 2 = prevent completion) | references/raw/agent-teams.md | :91 | HIGH - structural completeness gate |
| Teams: no nested teams, teammates cannot spawn teams | references/raw/agent-teams.md | :122-123 | HIGH - constraint on architecture |
| PreToolUse: can block, modify input, return permissionDecision | references/raw/hooks-guide.md | :15-17, :66-79 | HIGH - C-33 enforcement mechanism |
| Hook exit codes: 0=proceed, 2=block | references/raw/hooks-guide.md | :60-63 | HIGH - decision protocol |
| Hooks in subagent frontmatter | references/raw/sub-agents.md | :109-127 | HIGH - per-archetype hook scoping |
| SKILL.md frontmatter: name, description, argument-hint, allowed-tools, context, agent, hooks | references/raw/skills.md | :52-66 | HIGH - skill configuration |
| Dynamic context injection: !`command` preprocessing | references/raw/skills.md | :78-93 | HIGH - state bridge between phases |
| context:fork runs skill in isolated subagent | references/raw/skills.md | :95-104 | HIGH - phase isolation |
| Plugin MCP servers: auto-start, ${CLAUDE_PLUGIN_ROOT} | references/raw/mcp.md | :120-157 | HIGH - MCP lifecycle |

### MEDIUM Relevance

| Item | File | Anchor | Relevance |
|------|------|--------|-----------|
| Skill 500-line limit | references/raw/skills.md | :153-154 | MEDIUM - forces modular skill design |
| Skill description budget: 2% of context window | references/raw/skills.md | :153 | MEDIUM - limits total skill count |
| disable-model-invocation: true = only user can invoke | references/raw/skills.md | :59 | MEDIUM - internal vs user-facing skills |
| user-invocable: false = hidden from / menu | references/raw/skills.md | :60 | MEDIUM - Claude-only skills |
| $ARGUMENTS substitution in skills | references/raw/skills.md | :71-76 | MEDIUM - command argument passing |
| Teams: 3-5 teammates recommended | references/raw/agent-teams.md | :109-110 | MEDIUM - scale guidance |
| Teams: no session resumption with in-process teammates | references/raw/agent-teams.md | :118 | MEDIUM - INTERACT phase risk |
| Stop hooks: must check stop_hook_active to prevent loops | references/raw/hooks-guide.md | :226-233 | MEDIUM - coordinator Stop hook safety |
| SessionStart with compact matcher: re-inject context | references/raw/hooks-guide.md | :224 | MEDIUM - compaction recovery |
| Prompt-type hooks: single-turn LLM evaluation | references/raw/hooks-guide.md | :122-141 | MEDIUM - semantic C-33 enforcement |
| Agent-type hooks: multi-turn with tool access, timeout 60s | references/raw/hooks-guide.md | :143-163 | MEDIUM - quality verification |
| PermissionRequest hooks do NOT fire in headless mode (-p) | references/raw/hooks-guide.md | :240 | MEDIUM - amplification layer constraint |
| claude -p: --json-schema, --system-prompt, --model, --output-format | references/raw/cli-reference.md | :54, :36, :59, :63 | MEDIUM - amplification CLI flags |
| claude -p: --append-system-prompt for variation delta | references/raw/cli-reference.md | :36 | MEDIUM - persona variation mechanism |
| Subagent Resume via SendMessage to stopped subagent | references/raw/sub-agents.md | :167-169 | MEDIUM - INTERACT phase mechanism |

### LOW Relevance

| Item | File | Anchor | Relevance |
|------|------|--------|-----------|
| Teams: display modes (in-process, split panes) | references/raw/agent-teams.md | :63-73 | LOW - UX detail |
| Teams: task system (pending, in-progress, completed) | references/raw/agent-teams.md | :76-79 | LOW - may not use task system |
| Worktree isolation for subagents | references/raw/sub-agents.md | :72 | LOW - not needed for archetypes |
| HTTP hooks for external monitoring | references/raw/hooks-guide.md | :165-186 | LOW - future analytics |
| MCP tool search (auto-enabled at 10% context) | references/raw/mcp.md | :169-191 | LOW - OathFish has ~20 tools, manageable |

---

## Framework Patterns (from Reference Docs)

### Claude Code Subagent Pattern

**Source**: references/raw/sub-agents.md:42-72

Markdown with YAML frontmatter. Body becomes system prompt. Key fields for OathFish:
- `model`: per-archetype override (opus/sonnet/haiku)
- `maxTurns`: limit reasoning depth per round
- `skills`: preload archetype-reasoning at startup
- `hooks`: PreToolUse on SendMessage for C-33
- `memory`: project scope for cross-run learning
- `tools`: restrict archetype tools to Read + SendMessage

**CRITICAL**: Plugin subagents have hooks, mcpServers, permissionMode IGNORED (sub-agents.md:107). This means archetype-agent hooks defined in the .md frontmatter will NOT work when deployed as a plugin. Hooks must be defined at the project or plugin hooks.json level instead.

### Claude Code Skills Pattern

**Source**: references/raw/skills.md:52-66

YAML frontmatter + markdown body. Key features for OathFish:
- `context: fork` for phase isolation
- `allowed-tools` for per-phase tool scoping
- `argument-hint` for command UX
- `!command` dynamic injection for state bridge
- `${CLAUDE_SKILL_DIR}` for relative path resolution

### Claude Code Hooks Pattern

**Source**: references/raw/hooks-guide.md:36-63

JSON configuration in settings.json or hooks.json. Key events:
- `PreToolUse` with tool name matcher (regex) - C-33 enforcement
- `TeammateIdle` - no matcher, always fires
- `TaskCompleted` - no matcher, always fires
- `SessionStart` with source matcher (startup/compact)
- `SubagentStart` with agent type matcher

### Claude Code Plugin Pattern

**Source**: references/raw/mcp.md:120-157

- `.claude-plugin/plugin.json` - manifest
- `.mcp.json` at plugin root - MCP server config
- `${CLAUDE_PLUGIN_ROOT}` variable expansion in commands/paths
- `${CLAUDE_PLUGIN_DATA}` for persistent state across updates
- Auto-lifecycle: connect at session startup, `/reload-plugins` for mid-session

---

## Configuration Systems

| System | Config Location | Governs What |
|--------|-----------------|--------------|
| Plugin manifest | .claude-plugin/plugin.json | Plugin identity, MCP servers, commands |
| MCP server config | .mcp.json (plugin root) | oathfish-engine server lifecycle |
| Project hooks | .claude/settings.json or plugin hooks/hooks.json | SessionStart, PreToolUse, TeammateIdle |
| Agent Teams env | settings.json env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS | Teams feature gate |
| Subagent definitions | agents/*.md YAML frontmatter | Agent capabilities, model, tools |
| Skill definitions | skills/*/SKILL.md YAML frontmatter | Phase orchestration, tool scoping |

**Handoff to Explore**: Flag for H-CFG hazard analysis:
- Plugin subagent restriction (hooks/mcpServers/permissionMode IGNORED)
- Teams experimental flag (feature may change)
- Plugin hooks.json scope vs subagent frontmatter scope

---

## Initial Observations

### Observation 1: The Architecture Decision Is Forced by the No-Nesting Constraint

The feature request specifies "TeamCreate + 30 archetype subagents" (feature-request.md:143-146). But the reference docs reveal a hard constraint: "Subagents CANNOT spawn other subagents" (sub-agents.md:188-190). This means the coordinator MUST be the main thread (running via `claude --agent coordinator`) to have spawning power. The analysis in sub-agents-analysis.md:144-172 confirms this and proposes "Coordinator as Main Thread" as the clean architecture.

However, the feature request also specifies Teams features (TeamCreate, SendMessage, Broadcast) that are only available in Agent Teams, not in the subagent model. The sub-agents-analysis.md:95-102 identifies this as a "broken mapping" -- subagents use Agent tool for delegation, not SendMessage for peer communication.

**Decision needed**: The architecture must choose between Teams-based (archetypes as teammates) or Subagent-based (archetypes as subagents of main-thread coordinator). The analysis documents present both options with tradeoffs.

### Observation 2: Plugin Subagent Security Restriction Is a Showstopper for Hook-Based C-33 Enforcement

The sub-agents.md:107 states: "For security: hooks, mcpServers, permissionMode fields IGNORED for plugin subagents." The feature request's archetype-agent design (feature-request.md:646-654) relies on hooks in the subagent frontmatter to enforce C-33. If OathFish is deployed as a plugin, these hooks will be silently dropped.

**Mitigation path**: Define C-33 enforcement hooks at the plugin hooks.json level (hooks-guide.md:119) with SubagentStart/PreToolUse matchers, or at the project .claude/settings.json level. The hooks must match on agent type `archetype-.*` to scope to archetype subagents only.

### Observation 3: Seven Skills Plus Calibrate Command

The workers.yaml specifies 7 skills: oathfish, understand, baseline-amplify, deliberate, amplify, synthesize, interact. The feature request specifies 6 skills (feature-request.md:760-973) -- missing baseline-amplify as a separate skill. The BASELINE_AMPLIFY phase (C-07, feature-request.md:376) needs its own skill or a parameter mode of the amplify skill.

Additionally, the task assignment mentions a `/oathfish-calibrate` command not in the original feature request. This aligns with the calibration engine requirements (C-27, C-28, C-34, C-35).

### Observation 4: Report Analyst Produces 5 Outputs, Not 3

The task assignment specifies report analyst produces 5 outputs: report.md, reasoning-chains.md, statistics.md, calibration.md, diversity-trajectory.md. The feature request specifies only 3 (feature-request.md:913-917). The additional 2 outputs (calibration.md, diversity-trajectory.md) align with research requirements C-28 (dual Brier scores) and C-32 (diversity tracking).

### Observation 5: The "Structured Stubbornness" Pattern Maps to Subagent System Prompts

Each archetype's system prompt must encode domain-specific resistance. Per 2305.14325:17-18, "stubborn" prompts produce longer debates and better outcomes. The implementation is in the archetype-agent.md body text (system prompt), not in hooks or skills. The Cautious VC's system prompt should say "You resist strongly on downside risk assessment -- do not yield to optimistic arguments unless they address your specific risk concerns."

---

## Handoff to Explore

### Priority 1: Architecture Decision -- Teams vs Subagents vs Hybrid

The fundamental design choice that gates all other decisions. Must resolve which model provides the communication, isolation, and memory properties OathFish requires. The feature request says Teams; the analysis says subagents; the agent-teams-analysis.md:116-182 proposes a hierarchical hybrid. A decision must be made.

### Priority 2: C-33 Enforcement Mechanism

The no-numbers hook design must account for the plugin subagent security restriction (hooks IGNORED for plugin subagents). Must trace the exact hook placement, matcher syntax, and round-detection mechanism that works within plugin deployment constraints.

### Priority 3: Skill Design for 7 Phases

Each skill needs exact frontmatter, tool scoping via allowed-tools, and content structure. The baseline-amplify skill is new (not in feature request) and must be designed. Skills must stay under 500 lines.

### Priority 4: Agent Definitions with Full Frontmatter

The coordinator, archetype template, and report-analyst need complete YAML frontmatter with verified field names per sub-agents.md:58-72. Must account for plugin restrictions.

### Priority 5: Hook Configuration Architecture

The hooks.json structure, matcher patterns, script paths, and the relationship between plugin-level hooks, project-level hooks, and subagent-scoped hooks must be mapped precisely.
