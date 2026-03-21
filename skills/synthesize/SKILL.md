---
name: synthesize
description: >
  OathFish SYNTHESIZE phase: spawns the report analyst agent to produce the
  prediction report, reasoning chains, statistics, calibration data, and
  diversity trajectory from deliberation and amplification results.
user-invocable: false
context: fork
agent: report-analyst
allowed-tools: Read, Write, Glob, Grep
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
