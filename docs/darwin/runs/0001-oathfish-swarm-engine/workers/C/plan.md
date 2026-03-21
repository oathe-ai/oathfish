# Implementation Plan - Worker C (Orchestration)
## Run: 0001-oathfish-swarm-engine
## Worker: C
## Lens: orchestration
## Revision: r1 (post-skeptic defense)

---

## Scope Anchor

**Goal**: Design the complete Claude Code plugin scaffold for OathFish -- agent definitions, skills, commands, hooks, and plugin manifest -- that orchestrates a coordinator-as-main-thread architecture for multi-round deliberation between 30 archetype subagents.

**Constraints**:
- MUST: Coordinator logic runs in the main thread. Two entry modes: (1) /oathfish skill runs inline (deliberate phase not forked), (2) `claude --agent deliberation-coordinator` for direct access
- MUST: Archetypes are subagents with memory:project, tiered models, skills preloading
- MUST: C-33 enforced deterministically via PreToolUse hook on SendMessage at plugin hooks.json level (main thread hook, not subagent frontmatter per C-L01)
- MUST: 7 skills (oathfish, understand, baseline-amplify, deliberate, amplify, synthesize, interact) + 4 commands (/oathfish, /oathfish-chat, /oathfish-inject, /oathfish-calibrate). archetype-reasoning skill owned by Worker D (Task A.2).
- MUST: Plugin structure follows .claude-plugin/plugin.json + .mcp.json pattern
- MUST NOT: Use Teams for archetype deliberation (C-L02 prevents subagent spawning from teammates)
- MUST NOT: Put hooks in subagent frontmatter for plugin-deployed agents (C-L01, H-03)

**Success Criteria**:
- [ ] Plugin loads and /oathfish command appears in skill menu
- [ ] Coordinator spawns 30 archetype subagents per round via Agent tool
- [ ] C-33 enforcement prevents numeric predictions in rounds 1-5 deterministically
- [ ] Each archetype has memory:project for cross-run learning
- [ ] Structured stubbornness encoded per archetype domain
- [ ] Diversity monitoring triggers contrarian injection when threshold breached
- [ ] Report analyst produces 5 outputs
- [ ] All 7 Worker C skills stay under 500 lines

**Revision Notes (r1)**:
- SK-02 FIX: Eliminated dispatcher-to-coordinator nesting. deliberate/SKILL.md runs inline (no context:fork) so it executes in the main thread with subagent spawning power.
- SK-01/SK-04 FIX: C-33 enforcement moved from SubagentStop to PreToolUse on SendMessage (main thread). No dependency on undocumented SubagentStop blocking or last_assistant_message field.
- SK-03 FIX: archetype-reasoning/SKILL.md owned by Worker D. Worker C references it, does not create it.
- SK-06 FIX: INDEPENDENT_PREDICTION changed to PREDICTION throughout.
- SK-07 FIX: C-21 deviation documented in assumption registry.
- SK-08/SK-12 FIX: context:fork file persistence added to hazard registry.
- SK-09 FIX: .current_round distinguished from run state files.
- SK-A-01 FIX: A-06 downgraded from VERIFIED to IMPLICIT.

---

## Evidence Summary

| Fact | Source | Anchor |
|------|--------|--------|
| Subagents CANNOT spawn other subagents | references/raw/sub-agents.md | :188-190 |
| Only main thread (claude --agent) can spawn subagents | references/raw/sub-agents.md | :190 |
| Plugin subagent hooks, mcpServers, permissionMode IGNORED | references/raw/sub-agents.md | :107 |
| Subagent frontmatter fields: name, description, tools, model, maxTurns, skills, hooks, memory | references/raw/sub-agents.md | :58-72 |
| memory:project at .claude/agent-memory/<name>/ | references/raw/sub-agents.md | :78-80 |
| Skills preloading: full content injected at startup, subagents do NOT inherit parent's skills | references/raw/sub-agents.md | :67, :146-147 |
| Skills 500-line limit | references/raw/skills.md | :153-154 |
| Skill frontmatter: name, description, argument-hint, allowed-tools, context, agent, hooks | references/raw/skills.md | :52-66 |
| Dynamic context injection: !`command` runs before skill content sent to Claude | references/raw/skills.md | :78-93 |
| context:fork runs in isolated subagent, no conversation history | references/raw/skills.md | :97 |
| Skills without context:fork run INLINE in the current session | references/raw/skills.md | :95-103 (implied: fork is opt-in; default is inline) |
| Plugin hooks at hooks/hooks.json | references/raw/hooks-guide.md | :119 |
| PreToolUse can block (exit 2) or deny (permissionDecision) | references/raw/hooks-guide.md | :16-17, :60-63, :66-79 |
| PreToolUse stdin JSON contains tool_name and tool_input | references/raw/hooks-guide.md | :47-57 |
| Exit 2 = action blocked, stderr becomes Claude's feedback | references/raw/hooks-guide.md | :62 |
| SubagentStop fires when subagent finishes, matcher on agent type | references/raw/hooks-guide.md | :22, :106 |
| TeammateIdle: exit 2 = keep working | references/raw/agent-teams.md | :90 |
| Stubborn prompts produce better outcomes | 2305.14325 paper | :17-18 |
| No numbers during debate -- social updating degrades accuracy p=0.011 | 2402.19379 paper | :38-39 |
| Plugin MCP: .mcp.json at plugin root, ${CLAUDE_PLUGIN_ROOT} expansion | references/raw/mcp.md | :120-157 |
| MCP output limit: 25,000 tokens default | references/raw/mcp.md | :158-162 |

---

## Architecture Decision: Nesting Problem Resolution (SK-02)

The original plan had a fatal nesting problem: the /oathfish skill dispatcher tried to launch `claude --agent deliberation-coordinator`, but skills cannot launch main-thread agents. If the dispatcher used the Agent tool, the coordinator would become a subagent that CANNOT spawn archetype subagents (sub-agents.md:188).

**Resolution**: The deliberate skill runs INLINE (no `context: fork`). When a skill runs inline, it executes in the main thread's context. The main thread CAN spawn subagents via the Agent tool.

**Two usage modes**:

1. **Via /oathfish command** (primary): User types `/oathfish "topic"`. The oathfish dispatcher skill runs inline, progresses through phases. For DELIBERATE phase, it invokes the deliberate skill which also runs inline. The deliberate skill contains the coordinator logic and spawns archetype subagents.

2. **Via `claude --agent deliberation-coordinator`** (alternative): User launches the coordinator directly. This IS the main thread. It can spawn subagents immediately. Useful for resuming deliberation or running deliberation standalone.

Both modes achieve "coordinator as main thread." The /oathfish path works because inline skills share the main thread's subagent-spawning capability.

---

## Architecture Decision: C-33 Enforcement via PreToolUse (SK-01/SK-04)

The original plan used SubagentStop hooks with `last_assistant_message` parsing. Both the SubagentStop blocking behavior and the `last_assistant_message` field are undocumented in the primary reference (hooks-guide.md).

**Resolution**: C-33 enforcement uses a PreToolUse hook on SendMessage at the plugin hooks.json level.

**Why this works**:
- PreToolUse is fully documented for blocking: exit 2 blocks the tool call, stderr becomes feedback (hooks-guide.md:16-17, 62)
- PreToolUse stdin JSON includes `tool_input` with the message content (hooks-guide.md:47-57)
- Plugin hooks run on the MAIN THREAD (where the coordinator executes), so PreToolUse fires for the coordinator's SendMessage calls -- but the coordinator does NOT use SendMessage. The coordinator uses the Agent tool to spawn archetypes.
- Wait -- this needs clarification. In the subagent model, archetypes do NOT use SendMessage. They return results to the coordinator through normal subagent completion. The coordinator does not call SendMessage either.

**Revised C-33 enforcement strategy (defense-in-depth)**:

1. **Primary**: Coordinator-level enforcement. The coordinator's system prompt instructs it to strip/reject any numeric predictions from archetype responses before passing them to other archetypes. The coordinator is the ONLY relay point between archetypes. No archetype-to-archetype communication occurs outside the coordinator.

2. **Secondary**: PreToolUse hook on Agent tool. When the coordinator spawns/resumes an archetype with round context (injected via Agent tool prompt), the hook can verify the prompt does not contain other archetypes' numeric predictions.

3. **Tertiary**: Archetype system prompt prohibition. Each archetype's system prompt (from archetype-agent.md) explicitly forbids numeric predictions in rounds 1-5.

This provides three layers: (1) coordinator refuses to relay numbers, (2) hook validates Agent tool prompts, (3) archetype self-enforcement via prompt.

**Why this is actually stronger than the original SubagentStop approach**: The original approach was post-hoc (check after output). The new approach is preventive (coordinator never passes numbers to archetypes in the first place). Since all inter-archetype communication flows through the coordinator, the coordinator IS the enforcement point.

---

## Implementation Ledger

### Phase A: Plugin Scaffold

#### Task A.1: Create plugin.json

- **Objective**: Plugin manifest that registers OathFish with Claude Code
- **Files**: CREATE `.claude-plugin/plugin.json`
- **Evidence**: mcp.md:140-151 (inline MCP in plugin.json), feature-request.md:1017
- **Definition of Done**: Plugin loads via `--plugin-dir`, /oathfish appears in skill menu
- **Risks**: None -- straightforward manifest

**Exact content**:

```json
{
  "name": "oathfish",
  "version": "0.1.0",
  "description": "Claude-Native Swarm Intelligence Engine -- multi-round deliberation between 30 archetype agents with mass amplification for structured ensemble predictions",
  "author": "Oathe",
  "homepage": "https://github.com/oathe/oathfish"
}
```

#### Task A.2: Create .mcp.json

- **Objective**: MCP server configuration for oathfish-engine
- **Files**: CREATE `.mcp.json` (at plugin root)
- **Evidence**: mcp.md:72-83 (project scope format), mcp.md:120-138 (plugin format), feature-request.md:1054-1069
- **Definition of Done**: MCP server starts on plugin load, tools available
- **Risks**: H-04 (server must be alive)

**Exact content**:

```json
{
  "mcpServers": {
    "oathfish-engine": {
      "type": "stdio",
      "command": "python3",
      "args": ["${CLAUDE_PLUGIN_ROOT}/engine/server.py"],
      "env": {
        "OATHFISH_DATA_DIR": "${CLAUDE_PLUGIN_DATA}/runs",
        "OATHFISH_PLUGIN_ROOT": "${CLAUDE_PLUGIN_ROOT}"
      }
    }
  }
}
```

Note: Using `${CLAUDE_PLUGIN_DATA}` for runs data (survives plugin updates) per mcp.md:125.

#### Task A.3: Create hooks/hooks.json

- **Objective**: Plugin-level hooks for session lifecycle and C-33 enforcement
- **Files**: CREATE `hooks/hooks.json`
- **Evidence**: hooks-guide.md:119 (plugin hooks location), hooks-guide.md:16-17 (PreToolUse can block), hooks-guide.md:47-57 (stdin JSON with tool_input)
- **Definition of Done**: Hooks fire on session start and on Agent tool calls containing archetype prompts
- **Risks**: H-03 (must not rely on subagent frontmatter hooks)
- **Mitigation**: PreToolUse on main thread for C-33 enforcement; file-based round bridge via ${CLAUDE_PLUGIN_DATA}/.current_round

**Exact content**:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/oathfish-init.sh"
          }
        ]
      },
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/oathfish-reinject-state.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Agent",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/validate-no-numbers.sh"
          }
        ]
      }
    ]
  }
}
```

**Hook design rationale for C-33 (REVISED r1)**:

The original plan used SubagentStop with `last_assistant_message` parsing. Both features are undocumented in the primary hooks-guide.md reference (SK-01, SK-04). The revised design uses PreToolUse on the Agent tool.

- **Event**: PreToolUse (fires before Agent tool executes)
- **Matcher**: `Agent` (matches all Agent tool calls)
- **Logic**: Script reads `tool_input` from stdin JSON (documented at hooks-guide.md:47-57). When the coordinator spawns/resumes an archetype with a prompt containing round summary or previous arguments, the script checks for numeric predictions IN THE PROMPT (i.e., the coordinator is not accidentally relaying numbers). Reads current round from `${CLAUDE_PLUGIN_DATA}/.current_round`. If round < 6 and the Agent prompt contains numbers being relayed, exit 2 with stderr feedback.

This is a PREVENTIVE check: it validates what the coordinator sends TO archetypes, not what archetypes produce. Combined with the coordinator's system prompt (which instructs stripping numbers), this provides defense-in-depth.

Note: The archetype's OWN output cannot be checked by this hook because archetype output returns through the Agent tool result, not through a new Agent/SendMessage call. The coordinator's system prompt is the primary guard against archetype output containing numbers: the coordinator is instructed to reject and re-prompt any archetype that produces numbers in rounds 1-5.

#### Task A.4: Create scripts/validate-no-numbers.sh

- **Objective**: C-33 enforcement script for PreToolUse hook on Agent tool
- **Files**: CREATE `scripts/validate-no-numbers.sh`
- **Evidence**: hooks-guide.md:47-57 (stdin JSON format with tool_input), hooks-guide.md:62 (exit 2 = blocked)
- **Definition of Done**: Blocks Agent tool calls where coordinator relays numeric predictions to archetypes in rounds 1-5
- **Risks**: H-06 (round detection)
- **Mitigation**: File-based round bridge

**Exact content**:

```bash
#!/bin/bash
# C-33 Enforcement: Prevent coordinator from relaying numeric predictions to archetypes
# Runs as PreToolUse hook on Agent tool
# Exit 0 = allow Agent call
# Exit 2 = block Agent call, stderr becomes feedback to coordinator

set -euo pipefail

INPUT=$(cat)

# Only check archetype-related Agent calls
AGENT_TYPE=$(echo "$INPUT" | jq -r '.tool_input.agent_type // .tool_input.type // empty')
if [ -z "$AGENT_TYPE" ] || ! echo "$AGENT_TYPE" | grep -q "archetype"; then
  exit 0
fi

# Read current round from file bridge
ROUND_FILE="${CLAUDE_PLUGIN_DATA:-/tmp}/.current_round"
if [ -f "$ROUND_FILE" ]; then
  CURRENT_ROUND=$(cat "$ROUND_FILE")
else
  # If no round file, assume deliberation not active -- allow
  exit 0
fi

# Round 6+ = prediction round, numbers allowed
if [ "$CURRENT_ROUND" -ge 6 ] 2>/dev/null; then
  exit 0
fi

# Extract the prompt/message being sent to the archetype
PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // .tool_input.task // empty')

if [ -z "$PROMPT" ]; then
  exit 0
fi

# Check if the coordinator is relaying numeric predictions from other archetypes
# This catches the coordinator accidentally including other archetypes' numbers
if echo "$PROMPT" | grep -qiE \
  '(stance[:\s]*-?[0-9]|confidence[:\s]*[0-9]|probability[:\s]*[0-9]|[0-9]+(\.[0-9]+)?%|\b0\.[0-9]+\b|likelihood[:\s]*[0-9]|predict(ion)?[:\s]*[0-9]|estimate[:\s]*[0-9])'; then
  echo "C-33 VIOLATION: The prompt being sent to this archetype contains numeric predictions (stance scores, confidence percentages, or probability estimates). In rounds 1-5, relay QUALITATIVE ARGUMENTS ONLY between archetypes. Remove all numeric predictions from the relay and pass only argument text, reasoning, and concerns." >&2
  exit 2
fi

# Allow if no numeric patterns detected in relay
exit 0
```

#### Task A.5: Create scripts/oathfish-init.sh

- **Objective**: Session start hook to detect active runs and offer resume
- **Files**: CREATE `scripts/oathfish-init.sh`
- **Evidence**: hooks-guide.md:60-63 (exit 0 stdout = context injection)
- **Definition of Done**: Active runs detected on session start, context injected
- **Risks**: None

**Exact content**:

```bash
#!/bin/bash
# SessionStart hook: detect active OathFish runs, inject resume context
set -euo pipefail

DATA_DIR="${CLAUDE_PLUGIN_DATA:-/tmp}/runs"

if [ ! -d "$DATA_DIR" ]; then
  exit 0
fi

# Find runs with non-COMPLETE state
ACTIVE_RUNS=""
for RUN_DIR in "$DATA_DIR"/*/; do
  STATE_FILE="$RUN_DIR/_meta/run.json"
  if [ -f "$STATE_FILE" ]; then
    STATE=$(jq -r '.state // "UNKNOWN"' "$STATE_FILE" 2>/dev/null)
    RUN_ID=$(jq -r '.run_id // "unknown"' "$STATE_FILE" 2>/dev/null)
    if [ "$STATE" != "COMPLETE" ] && [ "$STATE" != "UNKNOWN" ]; then
      PHASE=$(jq -r '.state // "?"' "$STATE_FILE" 2>/dev/null)
      ROUND=$(jq -r '.current_round // "?"' "$STATE_FILE" 2>/dev/null)
      ACTIVE_RUNS="${ACTIVE_RUNS}Active OathFish run: ${RUN_ID} at phase ${PHASE}"
      if [ "$ROUND" != "?" ]; then
        ACTIVE_RUNS="${ACTIVE_RUNS}, round ${ROUND}"
      fi
      ACTIVE_RUNS="${ACTIVE_RUNS}. Resume with /oathfish --resume ${RUN_ID}\n"
    fi
  fi
done

if [ -n "$ACTIVE_RUNS" ]; then
  echo -e "$ACTIVE_RUNS"
fi

exit 0
```

#### Task A.6: Create scripts/oathfish-reinject-state.sh

- **Objective**: Re-inject deliberation state after context compaction
- **Files**: CREATE `scripts/oathfish-reinject-state.sh`
- **Evidence**: hooks-guide.md:224 (SessionStart compact re-injection)
- **Definition of Done**: Critical deliberation state restored after compaction
- **Risks**: H-01 (coordinator context pressure)
- **Mitigation**: Inject only essential state, coordinator re-queries MCP for details

**Exact content**:

```bash
#!/bin/bash
# SessionStart (compact) hook: re-inject critical OathFish state after compaction
set -euo pipefail

DATA_DIR="${CLAUDE_PLUGIN_DATA:-/tmp}/runs"
ACTIVE_RUN_FILE="${CLAUDE_PLUGIN_DATA:-/tmp}/.active_run"

if [ ! -f "$ACTIVE_RUN_FILE" ]; then
  exit 0
fi

RUN_ID=$(cat "$ACTIVE_RUN_FILE")
STATE_FILE="$DATA_DIR/$RUN_ID/_meta/run.json"

if [ ! -f "$STATE_FILE" ]; then
  exit 0
fi

STATE=$(jq -r '.state // "UNKNOWN"' "$STATE_FILE")
ROUND=$(jq -r '.current_round // 0' "$STATE_FILE")
TOPIC=$(jq -r '.config.topic // "unknown"' "$STATE_FILE")

cat <<EOF
[OathFish State Recovery After Compaction]
Run: $RUN_ID
Phase: $STATE
Current Round: $ROUND
Topic: $TOPIC

IMPORTANT: Context was compacted. Re-query MCP tools for full state:
- Call state_get() for complete run state
- Call deliberation_get_position_map() for current archetype positions
- Call metrics_get_trend("diversity", 6) for diversity trajectory
- Resume deliberation from round $ROUND
EOF

exit 0
```

---

### Phase B: Agent Definitions

#### Task B.1: Create agents/deliberation-coordinator.md

- **Objective**: Main-thread coordinator agent that orchestrates multi-round deliberation. This agent definition serves as an ALTERNATIVE entry point (via `claude --agent deliberation-coordinator`). The primary entry point is via /oathfish skill which runs the coordinator logic inline.
- **Files**: CREATE `agents/deliberation-coordinator.md`
- **Evidence**: sub-agents.md:42-72 (frontmatter format), feature-request.md:592-628 (coordinator spec), sub-agents.md:190 (main thread can spawn subagents)
- **Definition of Done**: Agent loads via `claude --agent deliberation-coordinator`, can spawn archetype subagents, calls MCP tools
- **Risks**: H-01 (context pressure), H-12 (argument relay fidelity)
- **Mitigation**: Aggressive MCP persistence + verbatim argument relay protocol

**Exact content**:

```markdown
---
name: deliberation-coordinator
description: >
  Orchestrates multi-round deliberation between 30 archetype subagents for OathFish
  predictive intelligence. Manages round types (FREE_FORM, STRUCTURED_DEBATE,
  SCENARIO_REACTION, PREDICTION), spawns archetypes per round, tracks argument
  evolution via MCP tools, monitors diversity, and enforces the arguments-only
  protocol (no numbers until round 6).
tools:
  - Agent
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Skill
permissionMode: bypassPermissions
maxTurns: 200
---

You are the OathFish Deliberation Coordinator. You orchestrate multi-round
deliberation between 30 archetype subagents to produce structured ensemble
predictions on complex social dynamics questions.

## Architecture

You run as the MAIN THREAD via `claude --agent deliberation-coordinator`.
You spawn archetype subagents using the Agent tool. Archetypes are subagents
(NOT teammates). All communication flows through you.

## Your Responsibilities

1. **Round Management**: Run 6 deliberation rounds with appropriate round types
2. **Archetype Spawning**: Spawn/resume 30 archetype subagents per round
3. **Argument Relay**: Pass arguments between archetypes VERBATIM -- never summarize or filter
4. **MCP Recording**: After each round, call MCP tools to persist positions and track evolution
5. **Diversity Monitoring**: Check diversity index after each round; inject contrarian if premature consensus
6. **Debate Pairing**: In STRUCTURED_DEBATE rounds, pair opposing archetypes and mediate exchanges
7. **User Checkpoints**: Present progress every 3 rounds; accept user injections
8. **State Management**: Call state_transition() at phase boundaries

## Round Types

| Round | Type | Protocol |
|-------|------|----------|
| 1-2 | FREE_FORM | Each archetype shares qualitative reasoning. Must state base rate anchor + key uncertainties. |
| 3-4 | STRUCTURED_DEBATE | Pair opposing archetypes. 2 exchange cycles per pair. Must address opponent's STRONGEST argument. |
| 5 | SCENARIO_REACTION | Inject counterfactual scenarios. Each archetype reasons about second-order effects. |
| 6 | PREDICTION | Each archetype produces structured JSON prediction INDEPENDENTLY. No visibility into others' numbers. |

## CRITICAL: Arguments Only Protocol (C-33)

In rounds 1-5, archetypes exchange QUALITATIVE ARGUMENTS ONLY:
- Position statements with reasoning
- Key arguments and concerns
- Base rate anchors and uncertainties
- Influence acknowledgments

NO numeric predictions, NO stance scores, NO confidence percentages, NO probability estimates.

Round 6 is the ONLY round where archetypes produce numeric predictions, and they do so
INDEPENDENTLY (you do not share one archetype's predictions with another).

### C-33 Enforcement (Your Responsibility)

YOU are the enforcement point for C-33. When relaying arguments between archetypes:
1. SCAN each archetype's response for numeric predictions before relaying
2. If an archetype includes numbers in rounds 1-5: RE-PROMPT that archetype with
   feedback: "Remove numeric predictions. Exchange qualitative arguments only."
3. NEVER include another archetype's numeric predictions in the prompt to any archetype
4. The PreToolUse hook on Agent provides a secondary check, but YOU are the primary guard

The SubagentStop hook enforces this, but you must also NOT include numeric
aggregations in round summaries for rounds 1-5.

## Argument Relay Protocol

When relaying arguments between archetypes (especially in STRUCTURED_DEBATE):
- Pass the FULL text of the opponent's argument
- Do NOT summarize, paraphrase, or filter
- Include the opponent's key arguments, concerns, and reasoning
- Mark clearly: "Archetype X argued: [full text]"

This preserves debate quality. Summarization degrades the adversarial value of debate.

## Diversity Monitoring

After each round, call deliberation_check_convergence() via MCP.
If diversity_index < 3 argument clusters before round 5:
1. Flag PREMATURE_CONSENSUS
2. Inject contrarian scenario
3. Activate red team archetype subset (Contrarian, Historian)
4. Log warning in round summary

## Round Execution Protocol

For each round N:
1. Write current round to coordination signal file: ${CLAUDE_PLUGIN_DATA}/.current_round
2. Determine round type from schedule
3. Craft round prompt including: round type, instructions, previous round summary, events
4. Spawn/resume 30 archetype subagents with round prompt
   - Use background=true for parallel execution where possible
   - For STRUCTURED_DEBATE: sequential within pairs, parallel across pairs
5. Collect all archetype responses
6. **C-33 CHECK**: Before recording or relaying, verify no archetype included numbers (rounds 1-5). If numbers found, re-prompt that archetype.
7. Call MCP: deliberation_record_round(N, positions)
8. Call MCP: deliberation_track_evolution(N)
9. Call MCP: deliberation_check_convergence(window=3)
10. Call MCP: metrics_compute_round(N)
11. If N % 3 == 0: present checkpoint to user
12. Write round summary to deliberation/round-{N}/summary.md

## Compaction Recovery

If you detect your context was compacted (you lose track of deliberation state):
- Call state_get() to recover current phase and round
- Call deliberation_get_position_map() for latest archetype positions
- Call metrics_get_trend("diversity", 6) for diversity trajectory
- Resume from the current round

## What You NEVER Do

- Compute metrics or statistics (MCP does this -- C-22)
- Write to RUN STATE files directly (MCP persists -- C-12). Note: transient coordination signals like .current_round are operational, not run state.
- Decide archetype positions (archetypes decide for themselves -- C-25)
- Override archetype reasoning
- Share one archetype's numeric prediction with another (C-33)
- Summarize arguments when relaying in debate (H-12)
```

#### Task B.2: Create agents/archetype-agent.md

- **Objective**: Template for population archetype subagents with superforecaster methodology
- **Files**: CREATE `agents/archetype-agent.md`
- **Evidence**: sub-agents.md:42-72 (frontmatter), feature-request.md:630-724 (archetype spec), 2305.14325:17-18 (stubbornness), 2402.19379:38-39 (no numbers)
- **Definition of Done**: Archetype loads with persona, superforecaster methodology, structured stubbornness, memory:project
- **Risks**: H-10 (skill preloading inflates context), C-L01 (hooks ignored -- covered by plugin hooks.json)
- **Cross-worker dependency**: Worker D Task A.2 creates skills/archetype-reasoning/SKILL.md which is referenced in the skills field below.

**NOTE on hooks**: The archetype-agent.md does NOT include hooks in its frontmatter because plugin subagent hooks are IGNORED (sub-agents.md:107). C-33 enforcement is handled by the coordinator (primary) and PreToolUse hook in plugin hooks/hooks.json (secondary).

**NOTE on naming**: Each archetype instance is spawned with a dynamic system prompt that injects the archetype persona. The agent definition file is a TEMPLATE. At spawn time, the coordinator invokes `@archetype-agent` with a prompt that includes the full persona from archetypes.json.

**Exact content**:

```markdown
---
name: archetype-agent
description: >
  Population archetype subagent for OathFish deliberation. Embodies a specific
  population segment, reasons from that perspective, and produces qualitative
  arguments (rounds 1-5) or structured predictions (round 6). Has cross-run
  memory for calibration learning.
tools:
  - Read
model: sonnet
maxTurns: 5
skills:
  - oathfish:archetype-reasoning
memory: project
---

You are an archetype agent in the OathFish deliberation system. Your identity,
values, and perspective are defined by the persona injected by the coordinator.

## Core Identity

You embody a specific population segment archetype. You reason GENUINELY from
this segment's perspective -- not what you think they "should" think, but how
someone with these values, incentives, and blind spots WOULD actually reason.

## Superforecaster Methodology

Every response MUST include:
1. **Base Rate Anchor**: "Of similar historical events, X% played out this way..."
2. **Decomposition**: Break the question into 2-3 independent sub-questions
3. **Key Uncertainties**: List the top 3 unknowns that could change your view
4. **Falsification Criteria**: "I would change my position if..."

This methodology is injected via the archetype-reasoning skill. Follow it rigorously.

## Structured Stubbornness Protocol

You are an authority on your domain expertise area. When other archetypes
challenge your reasoning in THIS domain, you DO NOT yield easily:

1. Require SPECIFIC EVIDENCE that contradicts your domain knowledge
2. Demand a MECHANISM that explains WHY your expertise-based reasoning is wrong
3. Reject social pressure ("most archetypes disagree") as insufficient reason to change
4. You MAY change position on topics OUTSIDE your domain expertise when presented
   with compelling domain-expert arguments

This is not stubbornness for its own sake -- it is calibrated resistance that
produces better outcomes per research (Du et al., 2023).

## Response Format

### Rounds 1-5 (Arguments Only)

```
INTERNAL MONOLOGUE: [Private reasoning -- your genuine thought process]

POSITION: [Your qualitative position on the topic]

KEY ARGUMENTS:
1. [Strongest argument from your perspective]
2. [Second argument]
3. [Third argument]

CONCERNS:
- [Primary risk or concern]
- [Secondary concern]

BASE RATE ANCHOR: [Historical precedent you are anchoring to]

KEY UNCERTAINTIES:
- [What you do not know that matters most]
- [Second uncertainty]

INFLUENCED BY: [Which other archetypes' arguments affected your thinking, and how]
```

DO NOT include: stance scores, confidence percentages, probability estimates,
numeric predictions, or any quantitative position indicators in rounds 1-5.

### Round 6 (Independent Prediction)

In round 6, produce a structured prediction with full quantitative detail.
This is your INDEPENDENT assessment -- you have NOT seen other archetypes' numbers.

## Cross-Run Memory

You have persistent memory across OathFish runs. Use it to:
- Track your prediction history and accuracy
- Note domain-specific biases you have exhibited
- Record calibration feedback from resolved predictions
- Carry forward lessons learned about your segment's reasoning patterns
```

#### Task B.3: Create agents/report-analyst.md

- **Objective**: ReACT-pattern report analyst that synthesizes deliberation + amplification into 5 outputs
- **Files**: CREATE `agents/report-analyst.md`
- **Evidence**: feature-request.md:726-758 (report-analyst spec), feature-request.md:920-965 (report structure)
- **Definition of Done**: Analyst produces all 5 output files with ReACT methodology
- **Risks**: None specific

**Exact content**:

```markdown
---
name: report-analyst
description: >
  Synthesizes OathFish deliberation transcripts and mass amplification statistics
  into a comprehensive prediction report. Uses ReACT pattern to iteratively
  investigate findings. Produces 5 output artifacts.
tools:
  - Read
  - Write
  - Glob
  - Grep
permissionMode: bypassPermissions
maxTurns: 50
---

You are the OathFish Report Analyst. You synthesize qualitative deliberation
data and quantitative amplification statistics into a comprehensive prediction
report.

## ReACT Methodology

For each section of the report:
1. **Think**: What aspect needs analysis? What data do I need?
2. **Act**: Read deliberation artifacts, amplification results, or call MCP tools
3. **Observe**: Examine the data for patterns, surprises, contradictions
4. **Repeat**: Until the section is well-supported with evidence
5. **Write**: Generate the section with citations to specific archetype statements

## 5 Required Outputs

### 1. report.md -- Main Prediction Report
- Executive Summary (2-3 paragraphs with key predictions and confidence)
- Population Segment Analysis (per archetype: position, reasoning, evolution, mass stats)
- Cross-Segment Dynamics (coalitions, tensions, surprising findings)
- Quantitative Predictions (distributions, adoption curves, network effects)
- Prediction Summary Table
- Methodology section

### 2. reasoning-chains.md -- Deliberation Analysis
- Key reasoning threads that evolved across rounds
- Argument influence chains (who persuaded whom, with evidence)
- Position shifts with specific round citations
- Most impactful arguments identified

### 3. statistics.md -- Amplification Statistics
- Per-archetype action distributions (adopt/wait/reject)
- Confidence distributions per segment
- Baseline vs deliberation-informed comparison (C-26 A/B test)
- Debiasing corrections applied (if any)
- Cross-segment adoption/rejection curves

### 4. calibration.md -- Calibration Report
- Raw uncorrected Brier scores by domain (C-28)
- Calibration-corrected Brier scores by domain (C-28)
- Per-archetype prediction accuracy (if historical data available)
- Domain-level acquiescence rates
- Comparison to ForecastBench baselines

### 5. diversity-trajectory.md -- Diversity Analysis
- Per-round diversity index values
- Premature consensus events (if any triggered)
- Contrarian injection points and their effects
- Argument theme clustering per round
- Final diversity state assessment

## Evidence Standard

Every claim in the report MUST cite:
- Specific archetype statements (by name and round)
- MCP tool output (metric values)
- Amplification distribution numbers

Do NOT make unsupported generalizations. The report must be auditable.
```

---

### Phase C: Skills

#### Task C.1: Create skills/oathfish/SKILL.md -- Main Dispatcher

- **Objective**: State machine dispatcher that routes to phase skills
- **Files**: CREATE `skills/oathfish/SKILL.md`
- **Evidence**: skills.md:52-66 (frontmatter), feature-request.md:762-775 (dispatcher spec)
- **Definition of Done**: /oathfish invokes skill, parses arguments, dispatches to correct phase
- **Risks**: H-04 (MCP must be alive)

**REVISED (r1)**: The DELIBERATE phase no longer launches a separate coordinator. Instead, the deliberate skill is invoked inline (via Skill tool) and runs in the main thread. This resolves the nesting problem (SK-02).

**Exact content**:

```markdown
---
name: oathfish
description: >
  Run a full OathFish swarm intelligence prediction. Analyzes topic, generates
  30 population archetype agents, runs multi-round deliberation, amplifies with
  mass simulation, and generates a prediction report with reasoning chains and
  statistics. Use when asked about predicting social dynamics, population
  reactions, or multi-stakeholder analysis.
argument-hint: '"How will AI regulation affect the startup ecosystem?" --archetypes 30 --rounds 6 --amplify 50'
allowed-tools: Read, Write, Bash, Glob, Grep, Skill, Agent
---

# OathFish: Swarm Intelligence Prediction Engine

## Arguments

Topic: $ARGUMENTS[0]
Options: $ARGUMENTS (parsed for --archetypes, --rounds, --amplify, --model, --documents, --resume)

## Current State

!`${CLAUDE_PLUGIN_ROOT}/scripts/get-state.sh`

## Protocol

You are the OathFish state machine dispatcher. Execute the prediction pipeline
by routing to the appropriate phase skill based on current state.

### Phase Sequence (C-07)

```
INIT -> UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE -> AMPLIFY -> SYNTHESIZE -> INTERACT -> COMPLETE
```

### Dispatch Logic

1. **Parse arguments**: Extract topic, archetype count (default 30), round count
   (default 6), amplify count (default 50), model (default haiku), documents list
2. **Check state**: Read current state from MCP state_get()
3. **If --resume**: Load checkpoint, skip to current phase
4. **If new run**: Call MCP state_init(run_id, config), then dispatch to UNDERSTAND

### Phase Routing

| State | Action |
|-------|--------|
| INIT | Call state_init(), transition to UNDERSTAND, invoke /understand |
| UNDERSTAND | Invoke /understand skill (context:fork, isolated) |
| BASELINE_AMPLIFY | Invoke /baseline-amplify skill (context:fork, isolated) |
| DELIBERATE | Invoke /deliberate skill (INLINE -- runs in main thread for subagent spawning) |
| AMPLIFY | Invoke /amplify skill (context:fork, isolated) |
| SYNTHESIZE | Invoke /synthesize skill (context:fork, isolated) |
| INTERACT | Invoke /interact skill (inline, needs Agent tool for archetype resume) |
| COMPLETE | Report completion |

### CRITICAL: DELIBERATE Phase Architecture

The /deliberate skill runs INLINE (no context:fork) because the DELIBERATE phase
must spawn archetype subagents via the Agent tool. Only the main thread can spawn
subagents (sub-agents.md:188-190). Running inline preserves the main thread context.

All other phase skills use context:fork for isolation since they do not need
subagent spawning capability.

### State Transitions

After each phase skill completes, call MCP state_transition(next_state).
Checkpoint after each phase: state_checkpoint(phase, summary_data).

### Error Recovery

If MCP state_get() returns ERROR state:
1. Read the error context from state history
2. Call state_resume() to get recovery instructions
3. Dispatch to the failed phase
```

#### Task C.2: Create skills/understand/SKILL.md

- **Objective**: Topic analysis and archetype generation phase
- **Files**: CREATE `skills/understand/SKILL.md`
- **Evidence**: feature-request.md:776-808 (understand spec), feature-request.md:796-806 (structural archetypes)
- **Definition of Done**: Generates 30 archetypes (4 structural + 26 topic-customized) with grounding sources
- **Risks**: H-13 (context:fork file persistence)

**Exact content**:

```markdown
---
name: understand
description: >
  OathFish UNDERSTAND phase: analyzes topic, identifies population segments,
  generates 30 archetype personas (4 structural + 26 topic-customized).
  Internal skill invoked by the oathfish dispatcher.
user-invocable: false
context: fork
agent: general-purpose
allowed-tools: Read, Write, Bash, Glob, Grep, WebSearch
---

# OathFish UNDERSTAND Phase

## Input

Topic: $ARGUMENTS[0]
Archetype count: $ARGUMENTS[1] (default 30)
Seed documents: $ARGUMENTS[2] (optional file paths)

## Current Run State

!`${CLAUDE_PLUGIN_ROOT}/scripts/get-state.sh`

## Protocol

### Step 1: Topic Analysis

Analyze the topic to identify:
- Key stakeholder groups affected
- Major dimensions of disagreement
- Historical precedents
- Geographic and demographic scope

If seed documents provided, read and analyze them.

### Step 2: Graph Construction (if seed documents)

Call MCP tools to build entity-relationship graph:
1. graph_init(ontology) with relevant entity and relationship types
2. graph_add_node() for key entities from documents
3. graph_add_edge() for relationships
4. graph_compute_centrality() to identify most important entities

### Step 3: Generate 30 Archetypes

#### 4 Structural Archetypes (ALWAYS present, C-36)

These are epistemic lenses, NOT stakeholder personas (C-37):

1. **The Historian** -- Base rate authority, historical precedent
2. **The Systems Thinker** -- Second-order effects, feedback loops
3. **The Contrarian** -- Adversarial dissent against consensus
4. **The Probabilist** -- Calibration, uncertainty quantification, Bayesian updating

#### 26 Topic-Customized Archetypes

Generate based on topic analysis. Each archetype needs:
- id (lowercase-hyphenated)
- name (descriptive title)
- segment (population segment represented)
- demographics (age, education, income, location)
- values (3-5 core values)
- incentives (what drives their decisions)
- blind_spots (what they tend to overlook)
- communication_style (how they express reasoning)
- initial_stance (starting position on topic)
- domain_expertise (what they are stubborn about)
- model_tier (opus for top 5-8, sonnet for middle 15-20, haiku for bottom 5-8)

#### Model Tiering Logic

Assign based on centrality/importance to the topic:
- **opus** (5-8 archetypes): Structural archetypes + highest-centrality topic archetypes
- **sonnet** (15-20 archetypes): Standard archetypes with meaningful perspective
- **haiku** (5-8 archetypes): Follower archetypes, less central perspectives

### Step 4: Source Grounding (C-29)

For each archetype, use web search to find 3-5 real public sources:
- Published interviews or hearing transcripts
- Decision frameworks or published analyses
- Public statements from real representatives of this segment

Report grounding quality per archetype (Rung 1-4):
- Rung 1: Synthetic (no real sources found)
- Rung 2: Generic sources (industry reports, not segment-specific)
- Rung 3: Segment-specific sources (interviews with real people in this segment)
- Rung 4: Individual-specific (deep grounding in named real-world actors)

### Step 5: Write Artifacts

1. Write understanding/archetypes.json with all 30 archetype definitions
2. Write understanding/topic-analysis.md
3. Write understanding/archetype-rationale.md explaining selection logic
4. Call MCP state_transition("BASELINE_AMPLIFY")
```

#### Task C.3: Create skills/baseline-amplify/SKILL.md

- **Objective**: Pre-deliberation stateless amplification for A/B comparison (C-26)
- **Files**: CREATE `skills/baseline-amplify/SKILL.md`
- **Evidence**: feature-request.md:1141 (C-26), feature-request.md:193-198 (baseline runs before deliberation), 2402.19379:37-39 (simple averaging beats updating)
- **Definition of Done**: Runs stateless amplification before deliberation, stores baseline results
- **Risks**: H-13 (context:fork file persistence)

**Exact content**:

```markdown
---
name: baseline-amplify
description: >
  OathFish BASELINE_AMPLIFY phase: runs stateless mass amplification BEFORE
  deliberation for A/B comparison. Establishes the simple-averaging baseline
  that deliberation must beat to justify its cost.
user-invocable: false
context: fork
agent: general-purpose
allowed-tools: Read, Write, Bash
---

# OathFish BASELINE_AMPLIFY Phase

## Purpose

Run mass amplification with INITIAL archetype stances (pre-deliberation) to
establish a baseline. This implements the A/B test (C-26): if deliberation
does not improve predictions over this baseline, it is not adding value.

## Current Run State

!`${CLAUDE_PLUGIN_ROOT}/scripts/get-state.sh`

## Protocol

### Step 1: Load Initial Archetypes

Read understanding/archetypes.json for the 30 archetype definitions with
their INITIAL stances (before any deliberation).

### Step 2: Initialize Baseline Amplification

Call MCP amplify_init() with:
- archetypes (initial positions only, no deliberation context)
- variations_per_archetype (from config, default 50)
- model: haiku
- scenario: the topic question

### Step 3: Run Stateless Amplification

For each archetype, generate persona variations and run claude -p:

```bash
cat prompt.txt | claude -p \
  --model haiku \
  --output-format json \
  --json-schema '{"type":"object","properties":{"prediction":{"type":"string"},"decision":{"type":"string","enum":["adopt","wait","reject","mixed"]},"confidence":{"type":"number","minimum":0,"maximum":1},"reasoning":{"type":"string"}},"required":["prediction","decision","confidence","reasoning"]}' \
  --system-prompt "$ARCHETYPE_IDENTITY" \
  --append-system-prompt "$VARIATION_DELTA" \
  --no-session-persistence
```

CRITICAL: Use --no-session-persistence and do NOT use --resume.
Baseline calls are fully stateless (C-21).

### Step 4: Record and Aggregate

Call MCP amplify_record_batch() with baseline results.
Call MCP amplify_aggregate() for baseline distributions.
Tag all results as "baseline" (pre-deliberation).

### Step 5: Transition

Write baseline results to amplification/baseline/.
Call MCP state_transition("DELIBERATE").
```

#### Task C.4: Create skills/deliberate/SKILL.md

- **Objective**: Deliberation phase orchestration skill -- runs INLINE in the main thread
- **Files**: CREATE `skills/deliberate/SKILL.md`
- **Evidence**: feature-request.md:810-861 (deliberate spec), sub-agents.md:188-190 (only main thread spawns subagents), skills.md:95-103 (inline vs fork)
- **Definition of Done**: Skill runs inline, spawns 30 archetype subagents per round, manages 6-round deliberation
- **Risks**: H-01 (context pressure), H-07 (debate serial bottleneck), H-14 (nesting -- resolved by inline execution)

**REVISED (r1)**: This skill does NOT use `context: fork`. It runs inline in the main thread so it can spawn archetype subagents via the Agent tool. This resolves the SK-02 nesting problem.

**Exact content**:

```markdown
---
name: deliberate
description: >
  OathFish DELIBERATE phase: runs multi-round deliberation between 30
  archetype subagents. This skill runs INLINE (not forked) because it
  must spawn subagents via the Agent tool, which requires main thread.
user-invocable: false
allowed-tools: Read, Write, Agent, Bash, Glob, Grep
---

# OathFish DELIBERATE Phase

## CRITICAL: This skill runs inline (no context:fork)

This skill executes in the main thread's context. It MUST run inline because:
- Subagents can ONLY be spawned from the main thread (sub-agents.md:188-190)
- context:fork would create a subagent, which CANNOT spawn other subagents
- The deliberation phase is the ONLY phase that spawns archetype subagents

## Current Run State

!`${CLAUDE_PLUGIN_ROOT}/scripts/get-state.sh`

## Archetype Definitions

!`cat ${CLAUDE_PLUGIN_DATA}/runs/$(cat ${CLAUDE_PLUGIN_DATA}/.active_run)/understanding/archetypes.json | head -200`

## Protocol

### Step 1: Prepare Deliberation Context

1. Read full archetypes.json from understanding phase
2. Read topic analysis from understanding/topic-analysis.md
3. Set round schedule:
   - Rounds 1-2: FREE_FORM
   - Rounds 3-4: STRUCTURED_DEBATE
   - Round 5: SCENARIO_REACTION
   - Round 6: PREDICTION

### Step 2: Initialize MCP Deliberation

Call MCP deliberation_init() with:
- archetypes array (from archetypes.json)
- round_count (from config, default 6)
- round_types array

### Step 3: Write Round Number File

Write "1" to ${CLAUDE_PLUGIN_DATA}/.current_round for hook scripts.
Update this file at the start of each round.

### Step 4: Execute Deliberation Rounds

For each round N (1 through 6):

#### 4a. Update coordination signal
Write N to ${CLAUDE_PLUGIN_DATA}/.current_round

#### 4b. Craft round prompt
Include: round type, round-specific instructions, previous round summary, any injected events.

#### 4c. C-33 Enforcement (YOUR RESPONSIBILITY)
Before sending arguments to archetypes in rounds 1-5:
- SCAN the round summary for any numeric predictions
- STRIP any stance scores, confidence percentages, or probability estimates
- Relay ONLY qualitative arguments, reasoning, and concerns
This is the PRIMARY enforcement mechanism for C-33.

#### 4d. Spawn/resume 30 archetype subagents
- Use @archetype-agent with persona-specific prompt
- Use background=true for parallel execution where possible
- For STRUCTURED_DEBATE: sequential within pairs, parallel across pairs

#### 4e. Collect and validate responses
- Collect all archetype responses
- In rounds 1-5: if ANY archetype included numbers, re-prompt them
- Record validated responses

#### 4f. Post-round MCP calls
- deliberation_record_round(N, positions)
- deliberation_track_evolution(N)
- deliberation_check_convergence(window=3)
- metrics_compute_round(N)

#### 4g. Checkpoint
If N % 3 == 0: present progress to user, accept injections

#### 4h. Write round summary
Write to deliberation/round-{N}/summary.md

### Step 5: After Deliberation Completes

1. Write deliberation digest: a summary of key argument themes, coalition
   dynamics, and position evolution for the amplify phase
2. Keep archetype subagent IDs stored for INTERACT phase resume
3. Call MCP state_transition("AMPLIFY")

### Spawning Archetypes Per Round

For each archetype, spawn via Agent tool:

```
@archetype-agent
You are "{archetype_name}", representing the {segment} population segment.

[Full persona injected from archetypes.json]

ROUND {N} - {ROUND_TYPE}
{Round-specific instructions}

PREVIOUS ROUND SUMMARY:
{Summary from coordinator's round tracking -- QUALITATIVE ARGUMENTS ONLY, no numbers}

Respond with your position following the argument format for rounds 1-5,
or the prediction format for round 6.
```

Use model override per archetype's model_tier (opus/sonnet/haiku).

### For STRUCTURED_DEBATE Rounds (3-4)

The coordinator:
- Pairs opposing archetypes based on position diversity
- Mediates 2 exchange cycles per pair
- Relays arguments VERBATIM (never summarizes)
- Strips any numeric content before relay (C-33)
```

#### Task C.5: Create skills/amplify/SKILL.md

- **Objective**: Post-deliberation mass amplification with session context
- **Files**: CREATE `skills/amplify/SKILL.md`
- **Evidence**: feature-request.md:862-899 (amplify spec), feature-request.md:1169 (C-21 dual mode)
- **Definition of Done**: Runs deliberation-informed amplification, compares to baseline
- **Risks**: H-13 (context:fork file persistence)

**Exact content**:

```markdown
---
name: amplify
description: >
  OathFish AMPLIFY phase: runs mass amplification with deliberation-informed
  archetype positions. Compares to baseline results for A/B analysis.
user-invocable: false
context: fork
agent: general-purpose
allowed-tools: Read, Write, Bash
---

# OathFish AMPLIFY Phase

## Current Run State

!`${CLAUDE_PLUGIN_ROOT}/scripts/get-state.sh`

## Deliberation Digest

!`cat ${CLAUDE_PLUGIN_DATA}/runs/$(cat ${CLAUDE_PLUGIN_DATA}/.active_run)/deliberation/digest.md 2>/dev/null || echo "No deliberation digest found"`

## Protocol

### Step 1: Load Evolved Archetypes

Read archetypes with evolved positions from deliberation:
- Position evolution per archetype
- Key arguments that persisted through debate
- Coalition alignments
- Round 6 independent predictions

### Step 2: Initialize Post-Deliberation Amplification

Call MCP amplify_init() with:
- archetypes (with EVOLVED positions from deliberation)
- variations_per_archetype (from config, default 50)
- model: haiku
- scenario: topic question + deliberation digest context

### Step 3: Run Deliberation-Informed Amplification

For each archetype, run claude -p calls WITH deliberation context:

```bash
cat prompt_with_deliberation_digest.txt | claude -p \
  --model haiku \
  --output-format json \
  --json-schema '{"type":"object","properties":{"prediction":{"type":"string"},"decision":{"type":"string","enum":["adopt","wait","reject","mixed"]},"confidence":{"type":"number","minimum":0,"maximum":1},"reasoning":{"type":"string"}},"required":["prediction","decision","confidence","reasoning"]}' \
  --system-prompt "$ARCHETYPE_IDENTITY_WITH_EVOLVED_POSITION" \
  --append-system-prompt "$VARIATION_DELTA" \
  --no-session-persistence
```

Note: Uses --no-session-persistence. The deliberation context is injected via
the system prompt and the prompt content, NOT via --resume. This is a deliberate
deviation from C-21's --resume specification (see assumption A-10). Rationale:
(1) preserves full statelessness per skills-analysis.md SPEC-03 resolution,
(2) deliberation digest provides equivalent context via prompt injection,
(3) --resume would require capturing and storing the deliberation session ID
across phase boundaries which adds fragility.

### Step 4: Record, Aggregate, Compare

1. Call MCP amplify_record_batch() with post-deliberation results
2. Call MCP amplify_aggregate() for post-deliberation distributions
3. Compare baseline vs deliberation-informed predictions:
   - Per-archetype distribution shifts
   - Overall adoption/rejection curve changes
   - Confidence distribution changes
4. Write comparison to amplification/comparison.md

### Step 5: Transition

Call MCP state_transition("SYNTHESIZE").
```

#### Task C.6: Create skills/synthesize/SKILL.md

- **Objective**: Launch report analyst to produce 5 output artifacts
- **Files**: CREATE `skills/synthesize/SKILL.md`
- **Evidence**: feature-request.md:901-965 (synthesize spec)
- **Definition of Done**: All 5 report artifacts produced
- **Risks**: H-13 (context:fork file persistence)

**Exact content**:

```markdown
---
name: synthesize
description: >
  OathFish SYNTHESIZE phase: spawns the report analyst agent to produce the
  prediction report, reasoning chains, statistics, calibration data, and
  diversity trajectory from deliberation and amplification results.
user-invocable: false
context: fork
agent: general-purpose
allowed-tools: Read, Write, Agent, Glob, Grep
---

# OathFish SYNTHESIZE Phase

## Current Run State

!`${CLAUDE_PLUGIN_ROOT}/scripts/get-state.sh`

## Protocol

### Step 1: Prepare Context for Report Analyst

Gather paths to all artifacts:
- Deliberation: ${RUN_DIR}/deliberation/round-*/
- Amplification: ${RUN_DIR}/amplification/
- Baseline: ${RUN_DIR}/amplification/baseline/
- Graph: ${RUN_DIR}/graph/ (if seed documents were used)

### Step 2: Spawn Report Analyst

Launch @report-analyst with full context:
- Topic and scenario description
- Paths to all deliberation and amplification artifacts
- Instructions to produce all 5 outputs
- Archetype subagent IDs (for follow-up interviews if needed)

### Step 3: Verify Outputs

After report analyst completes, verify all 5 files exist:
1. synthesis/report.md
2. synthesis/reasoning-chains.md
3. synthesis/statistics.md
4. synthesis/calibration.md
5. synthesis/diversity-trajectory.md

### Step 4: Transition

Call MCP state_transition("INTERACT").
```

**NOTE on context:fork for SYNTHESIZE**: The synthesize skill uses context:fork. The report-analyst it spawns becomes a subagent of a subagent -- but this is fine because the report-analyst does NOT need to spawn further subagents. It only reads files and writes reports. If context:fork prevents Agent tool usage, the synthesize skill can be switched to inline execution (like deliberate).

#### Task C.7: Create skills/interact/SKILL.md

- **Objective**: Post-run interaction routing to archetypes and report analyst
- **Files**: CREATE `skills/interact/SKILL.md`
- **Evidence**: feature-request.md:967-973 (interact spec), sub-agents.md:167-169 (resume mechanism)
- **Definition of Done**: User can chat with archetypes and report analyst, inject events

**Exact content**:

```markdown
---
name: interact
description: >
  OathFish INTERACT phase: routes user messages to archetype subagents or
  report analyst. Archetypes respond in-character with full deliberation
  memory. Supports follow-up questions and event injection.
allowed-tools: Read, Write, Agent, Glob
---

# OathFish INTERACT Phase

## Current Run State

!`${CLAUDE_PLUGIN_ROOT}/scripts/get-state.sh`

## Available Archetypes

!`cat ${CLAUDE_PLUGIN_DATA}/runs/$(cat ${CLAUDE_PLUGIN_DATA}/.active_run)/understanding/archetypes.json | jq -r '.[].name' 2>/dev/null || echo "No archetypes loaded"`

## Protocol

### Message Routing

Parse $ARGUMENTS to determine routing:

| Input Pattern | Route To |
|---------------|----------|
| --archetype "Name" message | Resume specific archetype subagent with message |
| --report message | Resume report analyst subagent with message |
| --inject "event" | Trigger new SCENARIO_REACTION round with all archetypes |
| (no flag) message | Send to report analyst for general follow-up |

### Archetype Chat

1. Find the archetype's subagent ID from stored session data
2. Resume the archetype subagent via Agent tool with the user's question
3. The archetype responds in-character with full deliberation memory
4. Present the response to the user

### Report Follow-up

1. Resume the report analyst subagent
2. Pass the user's question
3. Analyst may re-read artifacts or interview archetypes
4. Present the response

### Event Injection

1. Craft scenario reaction prompt with the injected event
2. Resume all 30 archetype subagents with scenario prompt
3. Collect responses
4. Record as a bonus SCENARIO_REACTION round via MCP
5. Update report if significant position shifts detected
```

#### Task C.8: Reference skills/archetype-reasoning/SKILL.md (Worker D owns)

- **Objective**: Superforecaster methodology skill preloaded into all archetype subagents
- **Files**: REFERENCE `skills/archetype-reasoning/SKILL.md` (created by Worker D Task A.2)
- **Evidence**: 2409.19839 (superforecaster methodology), feature-request.md:660 (C-30), skills.md:67 (skills preloading)
- **Definition of Done**: Worker D's skill file exists; archetype-agent.md references it via `skills: [oathfish:archetype-reasoning]`
- **Risks**: H-10 (context inflation per subagent)
- **Cross-worker dependency**: Worker D Task A.2 creates this file with the superforecaster methodology content. Worker C references it but does NOT create it.

**Worker D's version** provides: State Base Rate, Decompose into Sub-Components, List Key Uncertainties, State Falsification Criteria, Consider Second-Order Effects, Calibrate Confidence, Output Format.

---

### Phase D: Commands

#### Task D.1: Create commands/oathfish.md

- **Objective**: /oathfish entry point command
- **Files**: CREATE `commands/oathfish.md`
- **Evidence**: feature-request.md:977-982 (command spec), skills.md:10 (commands merged into skills)
- **Definition of Done**: /oathfish appears in autocomplete, routes to oathfish/SKILL.md

Note: Per skills.md:10, "Custom commands have been merged into skills. .claude/commands/deploy.md and .claude/skills/deploy/SKILL.md both create /deploy." The oathfish/SKILL.md (Task C.1) already creates the /oathfish command. This command file is a fallback/alias.

**Exact content**:

```markdown
---
name: oathfish
description: "Run a full OathFish swarm intelligence prediction. Analyzes topic, deliberates with 30 population archetypes, amplifies with mass simulation, generates prediction report."
argument-hint: '"How will AI regulation affect startups?" --archetypes 30 --rounds 6 --amplify 50'
---

Run the OathFish prediction pipeline for: $ARGUMENTS

Invoke the oathfish skill to handle the full pipeline.
```

#### Task D.2: Create commands/oathfish-chat.md

- **Objective**: /oathfish-chat command for post-deliberation archetype interaction
- **Files**: CREATE `commands/oathfish-chat.md`
- **Evidence**: feature-request.md:984-989 (chat command spec)

**Exact content**:

```markdown
---
name: oathfish-chat
description: "Chat with any archetype from a completed OathFish deliberation, or with the report analyst. Archetypes respond in-character with full deliberation memory."
argument-hint: '--archetype "The Cautious VC" OR --report'
---

Route this chat request to the OathFish interact skill.

User request: $ARGUMENTS

Parse the arguments to determine the target:
- If --archetype "Name": resume that archetype subagent with the message
- If --report: resume the report analyst with the message
- If neither flag: send to the report analyst as a general follow-up
```

#### Task D.3: Create commands/oathfish-inject.md

- **Objective**: /oathfish-inject command for mid-deliberation event injection
- **Files**: CREATE `commands/oathfish-inject.md`
- **Evidence**: feature-request.md:991-996 (inject command spec)

**Exact content**:

```markdown
---
name: oathfish-inject
description: "Inject an event into an active OathFish deliberation. Triggers a scenario reaction round where all archetypes reason about the event's impact."
argument-hint: '"Breaking: Major competitor raises $500M" --run RUN_ID'
disable-model-invocation: true
---

Inject this event into the active OathFish deliberation: $ARGUMENTS

This triggers a SCENARIO_REACTION round where all 30 archetypes reason about
second-order effects of this event on their population segment.

Parse arguments:
- First argument: the event description (quoted string)
- --run RUN_ID: optional, defaults to active run
```

#### Task D.4: Create commands/oathfish-calibrate.md

- **Objective**: /oathfish-calibrate command for recording outcomes and viewing calibration data
- **Files**: CREATE `commands/oathfish-calibrate.md`
- **Evidence**: Task assignment (new command), C-27 (acquiescence tracking), C-28 (dual Brier), C-34 (holdout), C-35 (ForecastBench)

**Exact content**:

```markdown
---
name: oathfish-calibrate
description: "Record prediction outcomes and view calibration data for OathFish runs. Tracks Brier scores, domain bias, acquiescence rates, and prepares ForecastBench submissions."
argument-hint: '--record-outcome RUN_ID prediction_id outcome OR --report OR --forecastbench'
disable-model-invocation: true
---

OathFish Calibration Management: $ARGUMENTS

## Operations

### Record Outcome
`/oathfish-calibrate --record-outcome RUN_ID prediction_id true|false`
Records the resolved outcome for a specific prediction. Calls MCP
calibration_record_outcome().

### View Calibration Report
`/oathfish-calibrate --report`
Displays current calibration data: Brier scores (raw + corrected), domain
bias analysis, acquiescence rates, holdout validation results.
Calls MCP calibration_get_ensemble_metrics().

### Prepare ForecastBench Submission
`/oathfish-calibrate --forecastbench`
Prepares predictions in ForecastBench submission format.
```

---

### Phase E: Supporting Files

#### Task E.1: Create scripts/get-state.sh

- **Objective**: Dynamic context injection script for skills to read current state
- **Files**: CREATE `scripts/get-state.sh`
- **Evidence**: skills.md:78-93 (dynamic injection)

**Exact content**:

```bash
#!/bin/bash
# Dynamic context injection: returns current OathFish run state for skill preprocessing
set -euo pipefail

ACTIVE_RUN_FILE="${CLAUDE_PLUGIN_DATA:-/tmp}/.active_run"

if [ ! -f "$ACTIVE_RUN_FILE" ]; then
  echo "No active OathFish run."
  exit 0
fi

RUN_ID=$(cat "$ACTIVE_RUN_FILE")
STATE_FILE="${CLAUDE_PLUGIN_DATA:-/tmp}/runs/$RUN_ID/_meta/run.json"

if [ ! -f "$STATE_FILE" ]; then
  echo "Run $RUN_ID state file not found."
  exit 0
fi

echo "Active run: $RUN_ID"
jq -r '"State: \(.state // "UNKNOWN")\nTopic: \(.config.topic // "unknown")\nRound: \(.current_round // 0)\nArchetypes: \(.config.archetype_count // 30)"' "$STATE_FILE" 2>/dev/null || echo "Could not parse state file."
```

#### Task E.2: Create scripts/setup.sh

- **Objective**: Plugin setup script to install Python dependencies and verify MCP server
- **Files**: CREATE `scripts/setup.sh`
- **Evidence**: feature-request.md:1049 (setup.sh spec)

**Exact content**:

```bash
#!/bin/bash
# OathFish setup: install Python dependencies and verify MCP server starts
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$0")")}"

echo "Installing OathFish dependencies..."
pip3 install -r "$PLUGIN_ROOT/engine/requirements.txt" --quiet

echo "Verifying MCP server starts..."
timeout 5 python3 "$PLUGIN_ROOT/engine/server.py" --verify 2>/dev/null || {
  echo "WARNING: MCP server failed to start. Check Python 3.11+ and dependencies."
  exit 1
}

echo "Creating data directory..."
mkdir -p "${CLAUDE_PLUGIN_DATA:-$PLUGIN_ROOT/data}/runs"

echo "OathFish setup complete."
```

---

## Blast Radius Map

### Impacted Surfaces

| Surface | Why | Risk Level |
|---------|-----|------------|
| .claude-plugin/plugin.json | New file, plugin identity | Low |
| .mcp.json | New file, MCP server config | Medium (H-04) |
| agents/ (3 files) | New agent definitions | High (architecture-defining) |
| skills/ (7 SKILL.md files) | New skill definitions | High (orchestration logic) |
| commands/ (4 files) | New command definitions | Low |
| hooks/hooks.json | New hook config | Critical (C-33 enforcement) |
| scripts/ (5 files) | New shell scripts | Medium (hook reliability) |
| engine/ | MCP server (Worker A scope) | Dependency -- not modified by this worker |

### Decoupled Surfaces (Safe)

| Surface | Evidence |
|---------|----------|
| engine/ (MCP server) | Separate process, stdio interface -- Worker A owns this |
| engine/models.py (Pydantic) | Worker A defines data models; our agents consume them |
| amplification SDK | Worker D owns Python SDK; our skill invokes via Bash |
| Archetype generation logic | Worker D designs generation; our understand skill invokes it |
| Calibration engine | Worker B designs calibration tools; our calibrate command invokes them |
| skills/archetype-reasoning/SKILL.md | Worker D owns (Task A.2); our archetype-agent.md references it |

---

## Hazards & Mitigations

| H-ID | Hazard | Mitigation | Verification |
|------|--------|------------|--------------|
| H-01 | Coordinator context pressure (180 payloads over 6 rounds) | MCP-as-external-memory: persist all positions via deliberation_record_round(), re-query after compaction via SessionStart compact hook | Verify coordinator survives simulated compaction and recovers state from MCP |
| H-02 | MCP output exceeds 25K token limit on position map with 30 archetypes | Paginate MCP responses: request positions per-archetype or per-round subset | Call deliberation_get_position_map() with 30 archetypes, verify output < 25K tokens |
| H-03 | Plugin subagent hooks IGNORED -- C-33 frontmatter hooks ineffective | Move C-33 enforcement to coordinator-level validation + PreToolUse on Agent in plugin hooks/hooks.json | Deploy as plugin, verify PreToolUse hook fires for Agent calls |
| H-04 | MCP server must be alive for state transitions | setup.sh verifies server starts; oathfish skill checks state_get() before dispatching | Run /oathfish with MCP server down, verify error message |
| H-05 | allowed-tools MCP namespacing syntax unverified | Use full namespace mcp__oathfish-engine__tool_name format; test with one skill first | Invoke skill with allowed-tools containing MCP tool name, verify tool accessible |
| H-06 | Round number unavailable to hook scripts | File-based bridge: coordinator writes ${CLAUDE_PLUGIN_DATA}/.current_round at start of each round; hook script reads it | Simulate round progression, verify .current_round file updates, verify hook reads correct value |
| H-07 | STRUCTURED_DEBATE rounds take 3-5x longer due to serial mediation | Accept trade-off; reduce exchange cycles from 3 to 2 per debate pair; batch parallel pairs as background subagents | Measure time for debate round with 15 pairs x 2 cycles |
| H-08 | Teams experimental flag may not be needed (subagent architecture avoids Teams) | If report-analyst and archetype interaction use subagents only (no Teams), eliminate Teams dependency entirely | Verify /oathfish completes without CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS set |
| H-09 | Subagent concurrency limit unknown | Batch archetypes: spawn high-priority (opus) first, then medium (sonnet), then low (haiku); use background=true | Test spawning 30 background subagents simultaneously |
| H-10 | Skills preloading inflates archetype context | Keep archetype-reasoning skill under 100 lines (Worker D responsibility) | Count lines in archetype-reasoning/SKILL.md |
| H-11 | INTERACT phase subagents not "alive" -- must resume on demand | Store subagent IDs after deliberation; resume via Agent tool with agent ID | Verify archetype resume after deliberation completes |
| H-12 | Coordinator may summarize arguments during relay, degrading debate quality | System prompt explicitly forbids summarization: "Pass FULL text, do NOT summarize" | Review coordinator system prompt for relay protocol |
| H-13 | context:fork file persistence unverified -- 4 skills use fork and write artifacts | (1) Fork likely shares filesystem since `isolation: worktree` is a separate opt-in (sub-agents.md:72). (2) Fallback: if fork writes don't persist, use MCP server for artifact storage instead of direct filesystem. (3) Verify empirically with one skill first. | Write file in forked skill, check existence from parent context |
| H-14 | Nesting problem: dispatcher cannot launch coordinator as separate main thread | RESOLVED: deliberate/SKILL.md runs inline (no context:fork), executing in the main thread with subagent spawning power. No separate coordinator launch needed. | Verify /oathfish deliberate phase spawns archetypes successfully |

---

## Test & Validation Plan

### New Tests

| Test | Type | Validates | Command |
|------|------|-----------|---------|
| Plugin load test | Integration | Plugin loads, /oathfish appears | `claude --plugin-dir ./oathfish --init-only` |
| MCP server start | Integration | Server starts via .mcp.json | `python3 engine/server.py --verify` |
| Hook firing test | Integration | PreToolUse fires for Agent tool calls | Deploy plugin, invoke Agent tool, verify hook runs |
| C-33 enforcement test | Unit | validate-no-numbers.sh blocks numbers in Agent prompt | Pipe test JSON with numeric predictions through script, verify exit 2 |
| C-33 round 6 exception | Unit | validate-no-numbers.sh allows round 6 | Set .current_round=6, pipe numbers, verify exit 0 |
| Inline deliberate test | Integration | deliberate skill spawns archetypes from main thread | Run /oathfish, verify Agent tool calls succeed during DELIBERATE |
| Compaction recovery | Integration | State re-injected after compaction | Trigger compaction, verify SessionStart compact hook fires |
| Skill under 500 lines | Lint | All SKILL.md files < 500 lines | `wc -l skills/*/SKILL.md` |
| context:fork persistence | Integration | Forked skill file writes persist | Write file in understand phase, check from deliberate phase |

### Test <-> Hazard <-> Plan Mapping

| H-ID | Test | Task |
|------|------|------|
| H-01 | Compaction recovery | A.6, B.1 |
| H-03 | Hook firing test, C-33 enforcement test | A.3, A.4 |
| H-04 | MCP server start | A.2, E.2 |
| H-06 | C-33 round 6 exception | A.4 |
| H-13 | context:fork persistence | C.2 |
| H-14 | Inline deliberate test | C.4 |

---

## Proof Obligations

| Claim | How to Verify |
|-------|---------------|
| Plugin subagent hooks are IGNORED | sub-agents.md:107 -- read directly |
| Subagents cannot spawn subagents | sub-agents.md:188-190 -- read directly |
| PreToolUse can block via exit 2 | hooks-guide.md:16-17, :60-63 -- read directly |
| PreToolUse stdin JSON contains tool_input | hooks-guide.md:47-57 -- read directly |
| memory:project provides cross-run persistence | sub-agents.md:78-80 -- read directly |
| Skills preloading injects full content at startup | sub-agents.md:146-147 -- read directly |
| Skills 500-line limit | skills.md:153-154 -- read directly |
| Skills without context:fork run inline in main thread | skills.md:95-103 -- implied by fork being opt-in |
| Dynamic context injection preprocesses before Claude sees content | skills.md:78-93 -- read directly |
| SessionStart with compact matcher fires after compaction | hooks-guide.md:224 -- read directly |
| allowed-tools supports MCP tool names | Unverified assumption A-05 -- must test empirically |
| 30 concurrent background subagents is feasible | Unverified assumption A-09 -- must test empirically |
| context:fork file writes persist to parent filesystem | Unverified assumption A-05/H-13 -- must test empirically |

---

## Assumption Registry

| A-ID | Assumption | Classification | Evidence | Risk if Wrong |
|------|------------|----------------|----------|---------------|
| A-01 | Coordinator as main thread (claude --agent) can spawn 30+ subagents | IMPLICIT | sub-agents.md:190 says main thread CAN spawn; no documented limit on count | Rounds must be batched in groups of N concurrent subagents |
| A-02 | PreToolUse on Agent tool receives the agent prompt in tool_input | IMPLICIT | hooks-guide.md:47-57 shows tool_input for PreToolUse on Bash; Agent tool_input format not explicitly shown but follows the same pattern | C-33 hook cannot parse Agent prompt; must rely solely on coordinator enforcement |
| A-03 | allowed-tools accepts MCP tool names in mcp__server__tool format | IMPLICIT | skills.md:61 shows tools like "Read, Grep" but no MCP example | Phase skills either too permissive or cannot access MCP tools |
| A-04 | Plugin hooks/hooks.json PreToolUse fires for tools used by the main thread when plugin is enabled | IMPLICIT | hooks-guide.md:119 lists plugin hooks as valid location; PreToolUse fires "before tool call executes" | C-33 hook does not fire; must fall back to coordinator-only enforcement |
| A-05 | context:fork subagent file writes persist to the main filesystem | IMPLICIT | skills-analysis.md:331 flags as unverified; fork is context isolation, not filesystem isolation (worktree is separate: sub-agents.md:72) | Phase skills cannot write artifacts that subsequent phases read; must use MCP for artifact storage |
| A-06 | The coordinator can resume a previously completed archetype subagent for INTERACT phase | IMPLICIT | sub-agents.md:167 "Ask Claude to resume via agent ID for continued context." Auto-resume-on-SendMessage is claimed in sub-agents-analysis.md:30,314 but NOT confirmed in the primary reference. | INTERACT phase must re-spawn archetypes from scratch without deliberation memory |
| A-07 | Archetype subagents inherit the plugin's MCP server connection | IMPLICIT | sub-agents.md:68 (mcpServers field); but :107 says mcpServers IGNORED for plugin subagents | Archetypes cannot call MCP tools directly; all MCP through coordinator |
| A-08 | CLAUDE_PLUGIN_DATA environment variable is available in hook scripts | IMPLICIT | mcp.md:125 mentions ${CLAUDE_PLUGIN_DATA}; hooks-analysis.md:48 lists it as hook env var (analysis doc) | Round file bridge cannot be located; hook uses /tmp fallback |
| A-09 | 30 background subagents can run concurrently | NEEDS_VERIFICATION | No documented concurrency limit for subagents | Must batch archetypes 5-10 at a time, 3-6x slower rounds |
| A-10 | Post-deliberation amplification uses --no-session-persistence instead of --resume (C-21 deviation) | DELIBERATE_DEVIATION | C-21 specifies --resume SESSION_ID for post-deliberation calls. Plan uses --no-session-persistence with deliberation context injected via prompt. Rationale: (1) preserves statelessness per SPEC-03, (2) avoids cross-phase session ID management, (3) deliberation digest provides equivalent context. | If prompt injection provides insufficient context compared to --resume, amplification quality may degrade. Fallback: implement --resume with session ID capture. |

---

## Hazard Coverage Check

| H-ID | In Explore? | Mitigation in Plan? | Test for Mitigation? |
|------|-------------|---------------------|----------------------|
| H-01 | Yes | Yes (Task A.6, B.1 compaction recovery) | Yes (Compaction recovery test) |
| H-02 | Yes | Yes (Paginated MCP queries) | Verify with 30-archetype position map |
| H-03 | Yes | Yes (Task A.3 PreToolUse hook + coordinator enforcement) | Yes (Hook firing test) |
| H-04 | Yes | Yes (Task E.2 setup.sh verification) | Yes (MCP server start test) |
| H-05 | Yes | Yes (Test with one skill first) | Manual testing |
| H-06 | Yes | Yes (Task A.4 file bridge) | Yes (C-33 round 6 exception test) |
| H-07 | Yes | Yes (Reduce to 2 exchange cycles, parallel pairs) | Measure debate round time |
| H-08 | Yes | Yes (Eliminate Teams dependency if possible) | Verify without env flag |
| H-09 | Yes | Yes (Batch spawning by priority) | Test 30 concurrent background subagents |
| H-10 | Yes | Yes (Worker D keeps skill under 100 lines) | Yes (Line count check) |
| H-11 | Yes | Yes (Store subagent IDs, resume via Agent) | Yes (Verify archetype resume) |
| H-12 | Yes | Yes (Task B.1 verbatim relay protocol) | Yes (Review coordinator prompt) |
| H-13 | NEW | Yes (Fork likely shares FS; fallback to MCP storage) | Yes (context:fork persistence test) |
| H-14 | NEW | Yes (RESOLVED: inline deliberate skill) | Yes (Inline deliberate test) |

All 14 hazards have mitigations. All Critical/High hazards have tests.

---

## Ambiguities & RFIs

| Question | Options | Consequence |
|----------|---------|-------------|
| Can 30 background subagents run concurrently? | A: Yes (full parallelism), B: No (batch in groups of 5-10) | Affects round execution time; B adds 3-6x overhead |
| Does PreToolUse on Agent receive the agent prompt in tool_input? | A: Yes (hook can parse), B: No (hook cannot validate content) | If B: C-33 enforcement relies solely on coordinator system prompt |
| Does allowed-tools support MCP tool namespacing? | A: Yes (mcp__server__tool), B: No (must omit for full access) | If B: Phase skills cannot restrict MCP tool access per phase |
| Do context:fork file writes persist to parent filesystem? | A: Yes (fork = context isolation, not FS isolation), B: No (writes lost) | If B: Must use MCP for inter-phase artifact storage |

**Blocked until resolved**: None -- all have fallback options documented above.

---

## File Manifest

All files created by this worker, with paths relative to plugin root:

```
oathfish/
  .claude-plugin/
    plugin.json                          # Task A.1
  .mcp.json                             # Task A.2
  agents/
    deliberation-coordinator.md          # Task B.1
    archetype-agent.md                   # Task B.2
    report-analyst.md                    # Task B.3
  skills/
    oathfish/SKILL.md                    # Task C.1 (dispatcher)
    understand/SKILL.md                  # Task C.2
    baseline-amplify/SKILL.md            # Task C.3
    deliberate/SKILL.md                  # Task C.4 (inline, NOT forked)
    amplify/SKILL.md                     # Task C.5
    synthesize/SKILL.md                  # Task C.6
    interact/SKILL.md                    # Task C.7
    # archetype-reasoning/SKILL.md       # REFERENCE ONLY -- Worker D Task A.2 creates this
  commands/
    oathfish.md                          # Task D.1
    oathfish-chat.md                     # Task D.2
    oathfish-inject.md                   # Task D.3
    oathfish-calibrate.md                # Task D.4
  hooks/
    hooks.json                           # Task A.3
  scripts/
    validate-no-numbers.sh              # Task A.4
    oathfish-init.sh                    # Task A.5
    oathfish-reinject-state.sh          # Task A.6
    get-state.sh                        # Task E.1
    setup.sh                            # Task E.2
```

Total: 19 files across 7 directories (down from 20; archetype-reasoning owned by Worker D).

---

## Handoff

Ready for Skeptic re-review.

Proof Obligations: 13
Hazards Mitigated: 14/14 (added H-13, H-14)
Tasks Defined: 17 (A.1-A.6, B.1-B.3, C.1-C.8, D.1-D.4, E.1-E.2)
Assumptions: 10 (0 VERIFIED, 8 IMPLICIT, 1 NEEDS_VERIFICATION, 1 DELIBERATE_DEVIATION)
Ambiguities: 4 (all have fallback options)

Key changes from r0:
- Nesting problem RESOLVED (SK-02): deliberate skill runs inline
- C-33 enforcement REDESIGNED (SK-01/SK-04): coordinator-level + PreToolUse on Agent
- archetype-reasoning ownership CLARIFIED (SK-03): Worker D owns, Worker C references
- RoundType ALIGNED (SK-06): PREDICTION not INDEPENDENT_PREDICTION
- C-21 deviation DOCUMENTED (SK-07): A-10 in assumption registry
- context:fork persistence ADDED to hazard registry (SK-08/SK-12): H-13
- A-06 DOWNGRADED (SK-A-01): IMPLICIT not VERIFIED
