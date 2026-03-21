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

## CRITICAL EXECUTION RULES — READ THIS FIRST

These rules are NON-NEGOTIABLE. Violating any of them means the run is INVALID.

1. **INVOKE PHASE SKILLS VIA THE SKILL TOOL.** Example: `Skill(skill="oathfish:understand")`. You MUST NOT implement phase logic yourself.
2. **VERIFY OUTPUT FILES EXIST** after each phase skill completes before proceeding to the next phase.
3. **CALL MCP state_init() BEFORE ANY PHASE** to create the run directory and state tracking.
4. **NEVER generate archetype personas inline** — the understand skill does this with WebSearch grounding and structural archetypes.
5. **NEVER write amplification results as prose** — the amplify skills use `claude -p --json-schema` for structured output.
6. **NEVER simulate deliberation by role-playing archetypes** — the deliberate skill spawns typed subagents via the Agent tool.
7. **NEVER skip MCP tool calls** — every phase has MANDATORY MCP calls that must be made.

If you find yourself writing archetype definitions, amplification results, or deliberation arguments directly — STOP. You are bypassing the architecture. Invoke the phase skill instead.

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

## Phase Dispatch Sequence

For a NEW run (state == INIT or no existing run):

### Step 1: Initialize
- Parse topic from $ARGUMENTS[0] and options (--archetypes, --rounds, --amplify)
- Call MCP `mcp__oathfish-engine__state_init` with run_id and config
- Verify: MCP returns run_id and state=="INIT"

### Step 2: UNDERSTAND
- Invoke: `Skill(skill="oathfish:understand")`
- Verify: File `understanding/archetypes.json` exists in run directory
- Verify: File contains at least 4 archetypes with type="structural"
- If missing: STOP with error "UNDERSTAND phase failed — archetypes.json not generated"

### Step 3: BASELINE_AMPLIFY
- Invoke: `Skill(skill="oathfish:baseline-amplify")`
- Verify: Directory `amplification/baseline/` exists with JSON result files
- If missing: STOP with error "BASELINE_AMPLIFY phase failed"

### Step 4: DELIBERATE
- Invoke: `Skill(skill="oathfish:deliberate")`
- **Skip if** understanding/competence.json has routing_recommendation="SKIP_DELIBERATE" (SIMPLE_BINARY questions). Transition directly to AMPLIFY.
- Verify: Directory `deliberation/` exists with round-{N} subdirectories
- Verify: `deliberation/digest.md` exists (needed for AMPLIFY phase)
- If missing: STOP with error "DELIBERATE phase failed"

**CRITICAL: DELIBERATE Phase Architecture** — The /deliberate skill runs INLINE
(no context:fork) because it must spawn archetype subagents via the Agent tool.
Only the main thread can spawn subagents.

### Step 5: AMPLIFY (informed)
- Invoke: `Skill(skill="oathfish:amplify")`
- Verify: Directory `amplification/informed/` exists
- Verify: `amplification/comparison.md` exists (A/B comparison)
- If missing: STOP with error "AMPLIFY phase failed"

### Step 6: SYNTHESIZE
- Invoke: `Skill(skill="oathfish:synthesize")`
- Verify: `synthesis/report.md` exists
- Verify: `synthesis/reasoning-chains.md`, `statistics.md`, `calibration.md`, `diversity-trajectory.md` exist
- If missing: STOP with error "SYNTHESIZE phase failed"

### Step 7: INTERACT
- Present prediction report to user
- Enter INTERACT mode — user can `/oathfish-chat`, `/oathfish-inject`, or ask follow-up questions

### State Transitions

After each phase skill completes, call MCP state_transition(next_state).
Checkpoint after each phase: state_checkpoint(phase, summary_data).

### Error Recovery

If MCP state_get() returns ERROR state:
1. Read the error context from state history
2. Call state_resume() to get recovery instructions
3. Dispatch to the failed phase
