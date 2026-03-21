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
  --json-schema '{"type":"object","properties":{"prediction":{"type":"string"},"action":{"type":"string","enum":["adopt","wait","reject","modify"]},"confidence":{"type":"number","minimum":0,"maximum":1},"reasoning":{"type":"string"}},"required":["prediction","action","confidence","reasoning"]}' \
  --system-prompt "$ARCHETYPE_IDENTITY_WITH_EVOLVED_POSITION" \
  --append-system-prompt "$VARIATION_DELTA" \
  --no-session-persistence
```

Note: Uses --no-session-persistence. The deliberation context is injected via
the system prompt and the prompt content, NOT via --resume. This is a deliberate
deviation from C-21's --resume specification (see assumption A-10). Rationale:
(1) preserves full statelessness per SPEC-03 resolution,
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

Results tagged as INFORMED. Include deliberation digest in each prompt. Use EVOLVED archetype positions.

## MANDATORY MCP CALLS
- [ ] `mcp__oathfish-engine__amplify_init(archetypes, variations_per, model, scenario)`
- [ ] `mcp__oathfish-engine__amplify_record_batch(batch_id, results)` — for each batch
- [ ] `mcp__oathfish-engine__amplify_aggregate(apply_debiasing)` — after all batches
- [ ] `mcp__oathfish-engine__state_transition("SYNTHESIZE")`
