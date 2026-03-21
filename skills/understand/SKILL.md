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

### Step 1: Question Competence Classification (C-31)

Before any analysis, call MCP competence_classify_question(question_text=topic).
This returns a CompetenceAssessment with:
- domain (POLICY, ECONOMICS, TECHNOLOGY, SCIENCE, ENVIRONMENT, SOCIAL, UNCLASSIFIED)
- complexity (SIMPLE_BINARY or MULTI_FACTOR)
- routing_recommendation: "SKIP_DELIBERATE" | "FULL_PIPELINE" | "LOW_CONFIDENCE"
- flags (e.g., "UNCLASSIFIED_DOMAIN", "UNCALIBRATED_DOMAIN")

**Routing based on recommendation:**
- FULL_PIPELINE: proceed with all steps below
- SKIP_DELIBERATE: generate archetypes but write skip_deliberation=true to run config.
  The dispatcher will skip DELIBERATE phase and go straight from BASELINE_AMPLIFY to AMPLIFY.
- LOW_CONFIDENCE: proceed with FULL_PIPELINE but flag in topic-analysis.md

Write the competence assessment to understanding/competence.json.

### Step 2: Topic Analysis

Analyze the topic to identify:
- Key stakeholder groups affected
- Major dimensions of disagreement
- Historical precedents
- Geographic and demographic scope

If seed documents provided, read and analyze them.

### Step 3: Graph Construction (if seed documents)

Call MCP tools to build entity-relationship graph:
1. graph_init(ontology) with relevant entity and relationship types
2. graph_add_node() for key entities from documents
3. graph_add_edge() for relationships
4. graph_compute_centrality() to identify most important entities

### Step 4: Generate 30 Archetypes

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

### Step 5: Source Grounding (C-29)

For each archetype, use web search to find 3-5 real public sources:
- Published interviews or hearing transcripts
- Decision frameworks or published analyses
- Public statements from real representatives of this segment

Report grounding quality per archetype (Rung 1-4):
- Rung 1: Synthetic (no real sources found)
- Rung 2: Generic sources (industry reports, not segment-specific)
- Rung 3: Segment-specific sources (interviews with real people in this segment)
- Rung 4: Individual-specific (deep grounding in named real-world actors)

### Step 6: Write Artifacts

1. Write understanding/archetypes.json with all 30 archetype definitions
2. Write understanding/topic-analysis.md
3. Write understanding/archetype-rationale.md explaining selection logic
4. Call MCP state_transition("BASELINE_AMPLIFY")

## MANDATORY CHECKLIST — Verify before completing this phase

### MCP Calls (must be made)
- [ ] `mcp__oathfish-engine__competence_classify_question(topic)` — Run FIRST, before any archetype generation
- [ ] `mcp__oathfish-engine__state_transition("BASELINE_AMPLIFY")` — Run LAST, after all outputs written

### Structural Archetypes (C-36 — EVERY run, non-negotiable)
These 4 archetypes MUST be included regardless of --archetypes parameter:
1. **Historian** — Agent definition: `oathfish:archetypes:structural:archetype-historian`
2. **Systems Thinker** — Agent definition: `oathfish:archetypes:structural:archetype-systems-thinker`
3. **Contrarian** — Agent definition: `oathfish:archetypes:structural:archetype-contrarian`
4. **Probabilist** — Agent definition: `oathfish:archetypes:structural:archetype-probabilist`

If --archetypes 5, generate: 4 structural + 1 topic-customized (NOT 0 structural + 5 topic)
If --archetypes 30, generate: 4 structural + 26 topic-customized

### Source Grounding (C-29)
For EACH archetype, use WebSearch to find 3-5 real public sources relevant to their domain.
Record in archetypes.json: `grounding_sources: ["source1 URL/title", "source2 URL/title", ...]` and `grounding_rung: 1-4`.
Structural archetypes are pre-grounded (Rung 3) — their sources are in their agent definition files.

### Required Outputs
- [ ] `understanding/archetypes.json` — Array of 30 archetype objects (4 structural + 26 topic)
- [ ] `understanding/topic-analysis.md` — Topic decomposition
- [ ] `understanding/competence.json` — Competence classification result
