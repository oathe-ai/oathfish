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
  --json-schema '{"type":"object","properties":{"prediction":{"type":"string"},"action":{"type":"string","enum":["adopt","wait","reject","modify"]},"confidence":{"type":"number","minimum":0,"maximum":1},"reasoning":{"type":"string"}},"required":["prediction","action","confidence","reasoning"]}' \
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

## MANDATORY: STRUCTURED AMPLIFICATION VIA claude -p

Each amplification sample MUST be produced by an independent `claude -p` call with --json-schema enforcement.

**Command pattern:**
```bash
echo "{prompt}" | claude -p \
  --model haiku \
  --output-format json \
  --json-schema '{"type":"object","properties":{"prediction":{"type":"string"},"decision":{"type":"string","enum":["adopt","wait","reject","mixed"]},"confidence":{"type":"number","minimum":0,"maximum":1},"base_rate_anchor":{"type":"string"},"timeframe":{"type":"string"},"key_uncertainties":{"type":"array","items":{"type":"string"}},"falsification_criteria":{"type":"string"}},"required":["prediction","decision","confidence","base_rate_anchor","timeframe","falsification_criteria"]}'
```

**DO NOT:**
- Write amplification results as prose paragraphs
- Generate "samples" by having the main thread imagine what different personas would say
- Use Agent tool for amplification (use claude -p for stateless independent calls)

**Each result must be structured JSON conforming to the schema above.**

Results tagged as BASELINE. No deliberation context. Use INITIAL archetype stances only.

## MANDATORY MCP CALLS
- [ ] `mcp__oathfish-engine__amplify_init(archetypes, variations_per, model, scenario)`
- [ ] `mcp__oathfish-engine__amplify_record_batch(batch_id, results)` — for each batch
- [ ] `mcp__oathfish-engine__amplify_aggregate(apply_debiasing)` — after all batches
- [ ] `mcp__oathfish-engine__state_transition("DELIBERATE")`
