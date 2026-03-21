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
