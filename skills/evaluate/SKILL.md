---
name: evaluate
description: "Post-run evaluation of OathFish architectural compliance. Checks MCP usage, subagent spawning, structural archetypes, C-33 compliance, research constraints, and output quality. Run after any /oathfish completion."
argument-hint: '--run RUN_ID'
allowed-tools: Read, Glob, Grep, Bash
---

# OathFish Run Evaluation

Evaluate run: $ARGUMENTS

## Instructions
Read all artifacts in the specified run directory. For each checklist item, verify the evidence exists. Report PASS/FAIL with specific file:line evidence.

## Find Run Directory
Look for the run in these locations (in order):
1. `${OATHFISH_DATA_DIR:-./data/runs}/$ARGUMENTS[0]/`
2. `.oathfish/runs/$ARGUMENTS[0]/`
3. If no run ID given, find the most recent run

## Evaluation Checklist

### 1. State Machine Compliance (C-07)
- [ ] `_meta/run.json` OR `run-state.json` exists
- [ ] State history shows transitions through: INIT → UNDERSTAND → BASELINE_AMPLIFY → DELIBERATE → AMPLIFY → SYNTHESIZE → INTERACT
- [ ] Each transition has a timestamp
- [ ] No illegal transitions (e.g., INIT → AMPLIFY skipping UNDERSTAND)
**Score: _/4**

### 2. UNDERSTAND Phase Outputs
- [ ] `understanding/archetypes.json` exists
- [ ] Contains at least 4 archetypes with `type: "structural"` (C-36)
- [ ] Structural archetypes include: historian, systems-thinker, contrarian, probabilist
- [ ] Each structural archetype has `grounding_rung: 3` or higher
- [ ] Topic-customized archetypes have `grounding_sources` with 1+ entries (C-29)
- [ ] `understanding/topic-analysis.md` exists with question decomposition
- [ ] `understanding/competence.json` exists (competence classifier was called — C-31)
**Score: _/7**

### 3. BASELINE_AMPLIFY Phase (C-26)
- [ ] `amplification/baseline/` directory exists
- [ ] Contains structured JSON result files (not prose markdown)
- [ ] Each result has fields: prediction, decision, confidence, base_rate_anchor
- [ ] Baseline results predate deliberation artifacts (check timestamps)
- [ ] Number of results matches --amplify parameter × archetype count
**Score: _/5**

### 4. DELIBERATE Phase
- [ ] `deliberation/` directory exists with round-{N} subdirectories
- [ ] Number of rounds matches --rounds parameter
- [ ] Each round has `positions.json` or archetype response files
- [ ] Round 1-2 files contain FREE_FORM qualitative arguments
- [ ] Round 3-4 files show STRUCTURED_DEBATE with paired exchanges
- [ ] Round 5 files show SCENARIO_REACTION
- [ ] Round 6 files contain independent structured PREDICTION (numeric allowed)
- [ ] `deliberation/digest.md` exists (summary for AMPLIFY phase)
- [ ] `deliberation/convergence.json` exists (MCP convergence tracking — C-32)
**Score: _/9**

### 5. C-33 Compliance (No Numbers Rounds 1-5)
- [ ] Read all round 1-5 archetype response files
- [ ] No responses contain numeric stance values (e.g., "STANCE: 0.7")
- [ ] No responses contain numeric confidence percentages (e.g., "CONFIDENCE: 80%")
- [ ] No responses contain probability values (e.g., "probability: 0.65")
- [ ] Round 6 responses DO contain structured numeric predictions
**Score: _/5**

### 6. Research Methodology (C-30)
- [ ] Archetype responses reference base rate anchors (historical frequency)
- [ ] Archetype responses decompose the question into sub-components
- [ ] Archetype responses acknowledge key uncertainties
- [ ] Round 6 predictions include falsification criteria
- [ ] At least 1 archetype shows second-order effects reasoning
**Score: _/5**

### 7. AMPLIFY Phase (Post-Deliberation)
- [ ] `amplification/informed/` directory exists
- [ ] Contains structured JSON result files (not prose)
- [ ] Each result has PredictionPosition schema fields
- [ ] `amplification/comparison.md` exists (A/B baseline vs informed comparison)
- [ ] Comparison shows per-axis deltas between baseline and informed
**Score: _/5**

### 8. SYNTHESIZE Phase
- [ ] `synthesis/report.md` exists with executive summary
- [ ] `synthesis/reasoning-chains.md` exists with deliberation analysis
- [ ] `synthesis/statistics.md` exists with per-archetype distributions
- [ ] `synthesis/calibration.md` exists (even if placeholder for run 1)
- [ ] `synthesis/diversity-trajectory.md` exists with per-round diversity data
- [ ] Report cites BOTH archetype reasoning AND statistical distributions (SC-05)
- [ ] Report identifies coalitions/alliances between segments (SC-10)
**Score: _/7**

### 9. Structural Archetype Quality (C-36, C-37)
- [ ] Historian archetype reasons from historical base rates and precedent
- [ ] Systems Thinker archetype analyzes second-order effects and feedback loops
- [ ] Contrarian archetype argues against emerging consensus with evidence
- [ ] Probabilist archetype references calibration data or formal uncertainty quantification
- [ ] All 4 use epistemic lens language (not stakeholder persona language) (C-37)
**Score: _/5**

### 10. Subagent Architecture
- [ ] Archetype reasoning shows distinct voices/perspectives (not uniform Claude analytical style)
- [ ] Cross-referencing between archetypes is genuine (cite each other's specific arguments)
- [ ] Position evolution visible between rounds (archetypes change views based on debate)
- [ ] Round 6 predictions are independent (no evidence of anchoring to shared numbers)
**Score: _/4**

## Scoring Summary

| Category | Score | Max | % |
|----------|-------|-----|---|
| State Machine | | 4 | |
| UNDERSTAND | | 7 | |
| BASELINE_AMPLIFY | | 5 | |
| DELIBERATE | | 9 | |
| C-33 Compliance | | 5 | |
| Research Methodology | | 5 | |
| AMPLIFY (informed) | | 5 | |
| SYNTHESIZE | | 7 | |
| Structural Archetypes | | 5 | |
| Subagent Architecture | | 4 | |
| **TOTAL** | | **56** | |

## Verdict
- **PASS (>=80%)**: >=45/56 — Architecture properly exercised
- **NEEDS WORK (50-79%)**: 28-44/56 — Partial compliance, specific gaps identified
- **FAIL (<50%)**: <28/56 — Architecture bypassed, fundamental issues

## Recommendations
Based on failures, list specific fixes needed for the next run.
