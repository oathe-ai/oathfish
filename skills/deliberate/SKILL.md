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

## MANDATORY: SPAWN TYPED SUBAGENTS — DO NOT ROLE-PLAY

For EACH archetype, you MUST use the Agent tool with the correct subagent_type:

**Topic-customized archetypes:**
```
Agent(
  subagent_type="oathfish:archetype-agent",
  description="Archetype: {name} Round {N}",
  prompt="You are {name}...\n\nROUND {N} - {TYPE}\n{instructions}\n\nPREVIOUS ARGUMENTS:\n{summary}"
)
```

**Structural archetypes (use their specific agent type):**
```
Agent(subagent_type="oathfish:archetypes:structural:archetype-historian", ...)
Agent(subagent_type="oathfish:archetypes:structural:archetype-systems-thinker", ...)
Agent(subagent_type="oathfish:archetypes:structural:archetype-contrarian", ...)
Agent(subagent_type="oathfish:archetypes:structural:archetype-probabilist", ...)
```

**DO NOT:**
- Role-play archetypes in the main thread
- Use `Agent(subagent_type="general-purpose")` for archetypes
- Generate archetype responses without spawning a subagent

## MANDATORY MCP CALLS — Per Round
After collecting all archetype responses for round N:
- [ ] `mcp__oathfish-engine__deliberation_record_round(round_n, positions)`
- [ ] `mcp__oathfish-engine__deliberation_track_evolution(round_n)`
- [ ] `mcp__oathfish-engine__deliberation_check_convergence(window=3)`
- [ ] `mcp__oathfish-engine__metrics_compute_round(round_n)`

## MANDATORY: C-33 ARGUMENTS-ONLY ENFORCEMENT (Rounds 1-5)
Before relaying ANY archetype response to other archetypes:
1. SCAN the response text for numeric predictions (numbers followed by %, "stance:", "confidence:", probability values like 0.7)
2. If found: DO NOT RELAY. Re-prompt that archetype: "Remove numeric predictions. Share arguments only."
3. In Round 6 (PREDICTION): Numbers ARE allowed. Each archetype produces independent structured prediction.

## MANDATORY: DELIBERATION DIGEST
After the final round, write a deliberation digest (500-1000 words) summarizing:
- Key themes and arguments
- Points of consensus
- Unresolved disagreements
- Coalition patterns
- Position evolution highlights
Save to: `deliberation/digest.md` (needed by AMPLIFY phase)
