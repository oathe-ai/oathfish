# Explore Report - Worker B
## Run: 0001-oathfish-swarm-engine
## Worker: B
## Lens: mcp-research

---

## 1. Dependency Map

### 1.1 Calibration Engine (planned: engine/calibration_engine.py)

**Inbound (what will use calibration engine)**:

| Caller | Purpose | Evidence |
|--------|---------|----------|
| amplify_aggregate() | Apply domain-level debiasing corrections before reporting | research-driven-redesign.md:237-247 |
| report-analyst agent | Reads calibration metrics for synthesis output | research-driven-redesign.md:326-334 |
| archetype-agent memory | Loads calibration history into archetype prompts via memory:project | feature-request.md:658, 640 |
| ForecastBench pipeline | Exports predictions in benchmark-compatible format | C-35:feature-request.md:1150 |
| /oathfish-calibrate command | User triggers outcome recording | research-driven-redesign.md:468 |

**Outbound (what calibration engine depends on)**:

| Dependency | Purpose | Evidence |
|------------|---------|----------|
| models.py (Pydantic) | CalibrationPrediction, CalibrationOutcome, DomainBias models | feature-request.md:1027 |
| Disk persistence (JSON) | Write-through caching of calibration data | C-23:feature-request.md:1177, mcp-analysis.md:92 |
| OATHFISH_DATA_DIR | Root path for persistent calibration state | mcp-analysis.md:53, 128 |
| state_machine.py | Current run_id, phase validation | feature-request.md:1019 |
| Domain taxonomy | Classification of topics into calibration domains | spec-audit.md:228 (UNDEFINED) |

### 1.2 Debiasing Infrastructure (within amplification_engine.py)

**Inbound**:

| Caller | Purpose | Evidence |
|--------|---------|----------|
| amplify/SKILL.md | Calls amplify_aggregate(apply_debiasing=True) | research-driven-redesign.md:238-244 |
| synthesize/SKILL.md | Reads raw + debiased distributions | research-driven-redesign.md:330 |

**Outbound**:

| Dependency | Purpose | Evidence |
|------------|---------|----------|
| calibration_engine.py | Gets domain bias corrections via calibration_get_domain_bias() | research-driven-redesign.md:262-265 |
| Historical resolved predictions | Enough observations to compute corrections | C-27:feature-request.md:1142 |

### 1.3 Question Competence Classifier (planned: engine/competence_classifier.py)

**Inbound**:

| Caller | Purpose | Evidence |
|--------|---------|----------|
| oathfish/SKILL.md dispatcher | Routes questions before UNDERSTAND phase | C-31:feature-request.md:1146 |

**Outbound**:

| Dependency | Purpose | Evidence |
|------------|---------|----------|
| Domain taxonomy | Maps question text to domain category | spec-audit.md:246 |
| Historical prediction data | Uses past domain performance to assess archetype competence | research-driven-redesign.md:109-113 |
| state_machine.py | May skip DELIBERATE for simple-binary questions | research-driven-redesign.md:110-111 |

### 1.4 Holdout Validation (within calibration_engine.py)

**Inbound**:

| Caller | Purpose | Evidence |
|--------|---------|----------|
| calibration_get_ensemble_metrics() | Reports holdout vs training accuracy gap | final-synthesis.md:143 |

**Outbound**:

| Dependency | Purpose | Evidence |
|------------|---------|----------|
| calibration_record_prediction() | Partition flag set at recording time | mcp-analysis.md:134 |
| calibration_record_outcome() | Computes Brier on holdout set separately | C-34:feature-request.md:1149 |

---

## 2. Coupling Analysis

### Coupled Components

| A | B | Type | Risk |
|---|---|------|------|
| calibration_engine | amplification_engine (debiasing) | Data -- corrections flow from calibration to aggregation | H-01 |
| calibration_engine | domain_taxonomy | Configuration -- all queries keyed by domain | H-02 |
| calibration_engine | disk persistence (OATHFISH_DATA_DIR) | State -- calibration history is cross-run persistent state | H-03 |
| competence_classifier | domain_taxonomy | Configuration -- shares domain categories with calibration | H-02 |
| holdout_partition | calibration_correction | Data -- holdout set MUST NOT feed into correction model | H-04 |
| calibration_engine | state_machine (run_id) | Identity -- predictions keyed by run_id | None |
| ForecastBench pipeline | calibration_engine | Data -- exports prediction records in external format | H-09 |
| baseline_amplify | amplification_engine | Comparison -- baseline stored separately for A/B delta | H-05 |

### Decoupled (Safe to modify independently)

| Component A | Component B | Evidence |
|-------------|-------------|----------|
| calibration_engine | deliberation_engine | No direct coupling; calibration reads prediction outputs, not deliberation state |
| calibration_engine | graph_engine | No shared state; graph is entity/relationship, calibration is prediction/outcome |
| competence_classifier | archetype generation | Classifier runs BEFORE archetypes exist; operates on topic text only (spec-audit.md:247) |
| ForecastBench pipeline | debiasing | ForecastBench uses raw submission; debiasing is internal correction |

---

## 3. Hazard Registry

| H-ID | Category | Hazard | Evidence | Failure Mode | Severity |
|------|----------|--------|----------|--------------|----------|
| H-01 | Data | Calibration corrections applied to domains with insufficient data (n < 90) producing noise corrections that degrade predictions | 2602.19520-calibration-decomposition.md:63 ("OathFish will have ~300-600 predictions"); power analysis requires n=90/domain for 80% power at d=0.3 | Corrections add noise rather than reducing bias. Brier score worsens after "debiasing." | High |
| H-02 | Configuration | Domain taxonomy undefined -- SC-14 references "6 domains" but no taxonomy exists in spec | spec-audit.md:226-228 ("6 domains are not defined anywhere in the spec") | Every calibration tool query fails or returns meaningless results; domain bias tracking impossible | Critical |
| H-03 | State | Calibration history lost on plugin update because OATHFISH_DATA_DIR points to CLAUDE_PLUGIN_ROOT instead of CLAUDE_PLUGIN_DATA | feature-request.md:1064 (current wrong: "${CLAUDE_PLUGIN_ROOT}/docs/runs"); mcp-analysis.md:53 (correct: CLAUDE_PLUGIN_DATA) | All cross-run calibration data destroyed. Corrections reset to zero. Years of accumulated bias data lost. | Critical |
| H-04 | Data | Holdout set contamination -- corrections computed using holdout predictions, violating C-34 and causing overfitting | feature-request.md:356 ("NEVER feed calibration corrections from holdout set"), C-34:1149 | Calibration appears to improve but is overfitting to resolved outcomes. Generalization degrades. | High |
| H-05 | Data | Baseline vs deliberation comparison confounded by temporal effects -- baseline runs first, deliberation runs second, time-of-day or API changes could affect results | C-26:feature-request.md:1141, 2402.19379-silicon-crowd.md:37-40 | A/B delta reflects temporal confound not deliberation value. Wrong conclusions about deliberation utility. | Medium |
| H-06 | State | Cold-start problem -- runs 1-2 have zero resolved outcomes for calibration, and short-horizon bootstrap questions may not resolve fast enough | A-09:feature-request.md:1232 ("3-12 months for primary questions"); research-driven-redesign.md:428 | Calibration engine returns empty results for first 6-12 months. No corrections possible. Calibration "moat" is hollow. | High |
| H-07 | Data | Acquiescence rate varies by domain but single global correction applied, missing the dominant variance component | 2602.19520-calibration-decomposition.md:30 (domain-by-horizon = 26.0% R-squared); round-1-ffa.md:234 ("acquiescence bias will vary BY DOMAIN") | Undercorrects technology predictions (higher acquiescence) and overcorrects regulatory predictions (lower acquiescence). Net effect may be zero or negative. | High |
| H-08 | Integration | Competence classifier runs before UNDERSTAND phase but needs archetype information to assess domain relevance -- timing paradox | spec-audit.md:247 ("How is archetype relevance assessed BEFORE archetypes are generated?") | Classifier cannot assess archetype competence for a question if archetypes do not yet exist. Classification is degraded to topic-only heuristic. | Medium |
| H-09 | Integration | ForecastBench submission format unknown -- the pipeline must produce predictions compatible with forecastbench.org API/format | 2409.19839-forecastbench.md:17 ("Public leaderboard at forecastbench.org") | Cannot submit to benchmark. SC-11 (Brier < 0.122) is unverifiable. | Medium |
| H-10 | Data | Logistic recalibration (run 50+) requires fitting theta parameter but at small n the fit is unstable, producing extreme corrections | round-1-ffa.md:272 ("p* = p^theta / (p^theta + (1-p)^theta)"); synthesis-report.md:129 ("n >= 10 per cell") | Theta estimate swings wildly at small n. Extreme recalibration (e.g., theta=3.0) maps moderate probabilities to near-0 or near-1. | Medium |
| H-11 | Data | Dual-metric reporting gap (corrected - uncorrected > 0.05) triggers archetype re-grounding, but re-grounding criteria are undefined | C-28:feature-request.md:1143, final-synthesis.md:133 ("Gap > 0.05 = persona needs re-grounding") | System detects gap but has no automated response. Alert is raised but no action is taken. Manual intervention required with no clear protocol. | Low |
| H-12 | Performance | calibration_get_ensemble_metrics() computes over entire prediction history -- at scale this grows linearly with run count | mcp-analysis.md:31 (25,000 token output limit) | Computation time and output size grow unbounded. Eventually exceeds MCP output token limit. | Low |

---

## 4. Constraint Registry

### From feature-request.md (INHERITED)

| C-ID | Type | Constraint | Source | Verified | Evidence |
|------|------|------------|--------|----------|----------|
| C-26 | REQUIREMENT | A/B test: baseline amplification BEFORE deliberation every run | feature-request.md:1141 | INHERITED | User stated |
| C-27 | REQUIREMENT | Track per-domain acquiescence from run 1; corrections from run 3+ | feature-request.md:1142 | INHERITED | User stated |
| C-28 | REQUIREMENT | Dual-metric reporting (corrected + uncorrected Brier) | feature-request.md:1143 | INHERITED | User stated |
| C-31 | REQUIREMENT | Question competence classifier before UNDERSTAND | feature-request.md:1146 | INHERITED | User stated |
| C-34 | REQUIREMENT | Holdout 20% from calibration feedback | feature-request.md:1149 | INHERITED | User stated |
| C-35 | REQUIREMENT | ForecastBench submission pipeline | feature-request.md:1150 | INHERITED | User stated |

### From code/research (DISCOVERED)

| C-ID | Type | Constraint | Source | Verified | Evidence |
|------|------|------------|--------|----------|----------|
| C-B01 | LIMITATION | 300-600 predictions in year 1 -- formal variance decomposition impossible | 2602.19520:63, round-1-ffa.md:116 | YES | Research consensus across 3 debate rounds |
| C-B02 | LIMITATION | 80% statistical power requires n=90/domain for d=0.3 effect | 2602.19520:OathFish Relevance | YES | Power analysis from calibration paper |
| C-B03 | INVARIANT | Holdout predictions NEVER feed into correction model | feature-request.md:356, C-34:1149 | YES | Hard boundary in spec |
| C-B04 | LIMITATION | Competence classifier must operate on topic text alone (archetypes not yet generated) | spec-audit.md:247 | YES | Timing constraint in pipeline |
| C-B05 | REQUIREMENT | All calibration computations must be deterministic (MCP, no LLM in correction loop) | mcp-analysis.md:237-243, C-02:feature-request.md:1123 | YES | Architectural invariant; LLM in correction loop inherits acquiescence |
| C-B06 | REQUIREMENT | Calibration data must persist at CLAUDE_PLUGIN_DATA, not CLAUDE_PLUGIN_ROOT | mcp-analysis.md:53, 166-170 | YES | Plugin updates must not destroy calibration history |

### Constraint Conflicts

| REQUIREMENT | LIMITATION | Evidence | Severity | Generated Hazard |
|-------------|------------|----------|----------|-----------------|
| C-27 (corrections from run 3+) | C-B01 (300-600 predictions total in year 1) | At 30 predictions/run, run 3 has n=90 total but only ~15/domain if 6 domains | HIGH | H-01 |
| C-31 (competence classifier before UNDERSTAND) | C-B04 (archetypes not yet generated) | spec-audit.md:247 | MEDIUM | H-08 |
| SC-14 (2/6 domains significant) | C-B02 (n=90/domain required) | 6 domains x 90 = 540 predictions = ~18 runs to achieve full power | HIGH | H-06 |

---

## 5. Lens-Specific Analysis: MCP-Research

### 5.1 Statistical Methodology for Small-n Calibration

The core challenge for the calibration engine: the research paper (2602.19520) used 292 million data points. OathFish will have orders of magnitude fewer. The statistical methodology must be designed for small samples.

**Brier Score computation** (standard, well-defined):
```
BS = (1/N) * SUM_{i=1}^{N} (f_i - o_i)^2
```
Where f_i is the forecast probability [0,1] and o_i is the binary outcome {0,1}. This is well-behaved at any n (including n=1), but the confidence interval at small n is enormous. At n=30, the 95% CI on Brier is approximately +/- 0.08 (synthesis-report.md:63).

**Mean Signed Error (directional bias)** -- the primary correction signal:
```
MSE_d = (1/N_d) * SUM_{i in domain d} (f_i - o_i)
```
Positive MSE_d: ensemble predicts too high in domain d (overconfident / acquiescent).
Negative MSE_d: ensemble predicts too low (underconfident).

**Statistical test for directional bias significance**:
One-sample t-test against zero: `t = MSE_d / (s_d / sqrt(N_d))`
Where s_d = standard deviation of (f_i - o_i) in domain d.
Reject at p < 0.10 (per SC-14, feature-request.md:116).

**Additive correction** (runs 3-9):
```
f_corrected_i = clamp(f_i - alpha_d, 0, 1)
```
Where alpha_d = MSE_d. Simple, robust, no overfitting risk at small n.

**Logistic recalibration** (run 50+, requires large n per domain):
```
p* = p^theta / (p^theta + (1-p)^theta)
```
Where theta is the calibration slope estimated via logistic regression. From round-1-ffa.md:272. This requires n >= 50 to estimate theta reliably (synthetic-report.md:129 suggests n >= 10 per cell, but cells are domain x horizon, so per domain n >= 40-50 minimum).

**Acquiescence rate**:
```
ACQ_d = mean(f_i) for all predictions i in domain d
```
Compare against base rate (proportion of positive resolutions in domain d). Deviation = acquiescence.

### 5.2 Power Analysis Implications

From 2602.19520 (OathFish Relevance section) and final-synthesis.md:99:

- **80% power at d=0.3 requires n=90** per domain.
- At 30 predictions/run (one per archetype) spread across 6 domains: ~5 per domain per run.
- n=90/domain requires ~18 runs.
- But C-27 says corrections from run 3+ (feature-request.md:1142).
- At run 3: n=15/domain. This is far below the power threshold.

**Design decision**: Apply corrections from run 3+ ONLY when the MSE_d is large enough to be directionally clear despite small n. Specifically:
- Run 3-9: Apply correction ONLY if |MSE_d| > 0.10 AND n_d >= 15. This is a conservative threshold -- only correct large, obvious biases.
- Run 10+: Lower threshold to |MSE_d| > 0.05 AND n_d >= 45.
- Run 18+: Standard threshold |MSE_d| significantly different from 0 at p < 0.10.

### 5.3 Domain Taxonomy Design

The spec-audit (spec-audit.md:228) flagged that "6 domains" are undefined. Worker B must define this taxonomy.

**Design decision**: 6 domains, auto-classified via keyword matching and topic analysis.

| Domain ID | Label | Description | Example Topics | Classification Keywords |
|-----------|-------|-------------|----------------|------------------------|
| POLICY | Policy & Regulation | Government action, regulation, political outcomes | AI regulation, election results, trade policy | regulation, law, government, policy, election, legislation, ban, mandate |
| ECONOMICS | Business & Economics | Markets, business, financial outcomes | Startup fundraising, market cap, GDP growth | market, economy, revenue, GDP, stock, funding, IPO, recession |
| TECHNOLOGY | Technology & Adoption | Tech adoption, product launches, innovation outcomes | AI product launch, adoption curves, feature rollout | technology, software, AI, adoption, launch, product, platform, app |
| SCIENCE | Science & Health | Scientific outcomes, medical trials, health events | Clinical trial results, pandemic trajectory | science, research, clinical, health, medical, study, vaccine, disease |
| ENVIRONMENT | Environment & Climate | Climate events, environmental outcomes, natural systems | Climate targets, natural disasters, emissions | climate, environment, emission, weather, energy, renewable, carbon |
| SOCIAL | Social & Cultural | Social dynamics, cultural shifts, consumer behavior, entertainment | Social media trends, cultural movements, entertainment outcomes | social, culture, consumer, media, public opinion, trend, demographic |

**Auto-classification algorithm**: LLM-based classification is forbidden (C-B05: all calibration computations must be deterministic). Use keyword scoring:
1. For each domain, count keyword matches in the question text + topic description.
2. Normalize by total keywords per domain.
3. Assign to highest-scoring domain.
4. If no domain scores above threshold (2+ keyword matches), assign UNCLASSIFIED.
5. UNCLASSIFIED predictions are tracked but not used for domain-level corrections.

### 5.4 Competence Classifier Design

Resolving the timing paradox (H-08): The classifier runs BEFORE UNDERSTAND, so it cannot assess archetype relevance. It must operate on topic text alone.

**Design decision**: Two-stage classification.

**Stage 1 (pre-UNDERSTAND, deterministic MCP tool)**:
- Classifies question as SIMPLE_BINARY vs MULTI_FACTOR based on text analysis.
  - SIMPLE_BINARY: yes/no outcome, single variable. Keywords: "will X happen?", "yes or no", single outcome.
  - MULTI_FACTOR: multiple interacting factors, joint probabilities. Keywords: "how will X affect Y?", multiple stakeholders mentioned, cascade/interaction language.
- Maps question to domain using keyword taxonomy (section 5.3).
- Checks if domain has historical calibration data. If domain has n=0 resolved predictions: flags as UNCALIBRATED_DOMAIN.
- Returns routing recommendation: FULL_PIPELINE (multi-factor) vs SKIP_DELIBERATE (simple binary) vs LOW_CONFIDENCE (out-of-domain / uncalibrated).

**Stage 2 (post-UNDERSTAND, after archetypes generated)**:
- Computes Jaccard similarity between question domain keywords and archetype expertise keywords.
- If max archetype relevance < threshold: flags as OUT_OF_DOMAIN.
- This is informational only (adds metadata to prediction records), not a routing gate.

### 5.5 Holdout Partition Design

From C-34 (feature-request.md:1149) and mcp-analysis.md:134: "Every 5th resolved prediction flagged as holdout."

**Design decision**: Deterministic partition using prediction hash.
```
is_holdout = hash(run_id + archetype_id + prediction_text) % 5 == 0
```
This gives exactly 20% holdout, is deterministic (same prediction always gets same partition), and cannot be gamed. The hash-based approach is better than "every 5th" (sequential) because sequential ordering might correlate with domain or time effects.

**Enforcement of C-B03** (holdout never feeds corrections): The correction computation function takes a `exclude_holdout=True` parameter (default True). When computing MSE_d, predictions where `is_holdout=True` are excluded from the sum. The holdout set gets its own separate Brier computation for overfitting detection.

**Overfitting detection criterion**:
```
overfitting_gap = brier_holdout - brier_training
```
If `overfitting_gap > 0.02` AND `brier_training is improving across runs` AND `brier_holdout is NOT improving`: flag OVERFITTING_DETECTED.

### 5.6 ForecastBench Pipeline Design

From C-35 (feature-request.md:1150) and 2409.19839-forecastbench.md.

ForecastBench is a public benchmark at forecastbench.org. It provides ~1,000 binary questions about future events. Submissions are probability forecasts for each question.

**Pipeline steps**:
1. `forecastbench_get_questions()` -- Fetch current question set from ForecastBench API.
2. For each question: Run OathFish full pipeline (UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE -> AMPLIFY -> SYNTHESIZE).
3. Extract ensemble probability from amplify_aggregate() output (the median forecast).
4. `forecastbench_format_submission(run_id)` -- Format all predictions into ForecastBench submission format.
5. `forecastbench_submit(submission)` -- Submit to leaderboard.
6. Track scores over time in calibration data.

**Note**: The exact ForecastBench API format must be determined at implementation time. The pipeline should be modular so the submission format can be adapted.

### 5.7 Short-Horizon Bootstrap Question Design

From A-09 (feature-request.md:1232) and research-driven-redesign.md:428.

**Problem**: Primary OathFish predictions resolve in 3-12 months. Calibration data is starved for year 1.

**Solution**: Include short-horizon bootstrap questions (1-4 week resolution) in every run.

**Sources for bootstrap questions**:
1. ForecastBench short-horizon subset (if available).
2. Known upcoming events with definite resolution dates (earnings reports, election dates, scheduled policy announcements).
3. Market-implied predictions that resolve within weeks.

**Bootstrap question data model**:
- Same CalibrationPrediction model as primary predictions.
- Additional field: `is_bootstrap: bool = False` (True for bootstrap questions).
- Bootstrap questions ARE included in calibration corrections (they are legitimate data).
- Bootstrap questions are NOT included in the primary Brier score reported to users (they are calibration infrastructure, not user-facing predictions).

### 5.8 Baseline Amplification (A/B Test) Design

From C-26 (feature-request.md:1141) and the state machine (C-07: 7 phases including BASELINE_AMPLIFY).

**Key design point from C-21** (feature-request.md:1169): Baseline calls are fully stateless -- no --resume, no session context. Post-deliberation calls use --resume SESSION_ID.

The baseline amplification lives in the BASELINE_AMPLIFY phase of the state machine, between UNDERSTAND and DELIBERATE.

**Baseline storage**: Baseline predictions are stored separately from deliberation-informed predictions:
```
{OATHFISH_DATA_DIR}/{run_id}/amplification/baseline/
  distributions.json      # Aggregated baseline distributions
  results/
    batch-{N}.json        # Raw baseline claude -p results
```

**A/B comparison**: Computed by calibration_get_ensemble_metrics() which reports:
- `brier_baseline`: Brier score of baseline median predictions
- `brier_informed`: Brier score of deliberation-informed median predictions
- `deliberation_delta`: `brier_baseline - brier_informed` (positive = deliberation helps)
- Stratified by question type (SIMPLE_BINARY vs MULTI_FACTOR)

---

## 6. Configuration Hazard Analysis

### H-CFG-01: OATHFISH_DATA_DIR Misconfiguration

| Aspect | Detail |
|--------|--------|
| Config Item | OATHFISH_DATA_DIR in .mcp.json env block |
| Current Value | `${CLAUDE_PLUGIN_ROOT}/docs/runs` (feature-request.md:1064) |
| Required Value | `${CLAUDE_PLUGIN_DATA}/runs` (mcp-analysis.md:53, 166-170) |
| Assumption | Plugin updates preserve data directory |
| Risk | Plugin update wipes all calibration history (H-03) |
| Evidence | mcp-analysis.md:53: "CLAUDE_PLUGIN_DATA for persistent state that survives plugin updates" |
| Mitigation | Change .mcp.json env to use CLAUDE_PLUGIN_DATA. Verify in integration test. |

### H-CFG-02: Correction Activation Threshold Hardcoded

| Aspect | Detail |
|--------|--------|
| Config Item | Run number at which corrections begin |
| Current Value | Hardcoded "run 3+" (C-27:feature-request.md:1142) |
| Risk | If domains are unevenly represented, some domains hit n=15 at run 3 but others have n=2. Blanket "run 3+" is misleading. |
| Mitigation | Activate corrections per-domain based on n_d threshold, not global run count. |

### H-CFG-03: Domain Taxonomy Not Configurable

| Aspect | Detail |
|--------|--------|
| Config Item | Domain categories for calibration |
| Current Value | Undefined (spec-audit.md:228) |
| Risk | Hardcoded taxonomy may not match user's prediction domains. No way to add/modify domains. |
| Mitigation | Store taxonomy in configurable JSON file. Ship with 6 defaults. Allow user override. |

---

## 7. Handoff to Plan

### Key Constraints for Implementation

1. **MUST** define domain taxonomy with auto-classification (H-02, Critical)
2. **MUST** use CLAUDE_PLUGIN_DATA for calibration persistence (H-03, H-CFG-01, Critical)
3. **MUST** implement per-domain n-threshold for correction activation, not blanket run count (H-01, H-CFG-02)
4. **MUST** enforce holdout partition invariant with hash-based deterministic split (H-04, C-B03)
5. **MUST** keep all calibration computation deterministic -- no LLM in correction loop (C-B05)
6. **SHOULD** design competence classifier as two-stage (pre-UNDERSTAND + post-UNDERSTAND) to resolve timing paradox (H-08)
7. **SHOULD** include short-horizon bootstrap question support to address cold-start (H-06)
8. **SHOULD** design A/B comparison with stratification by question type (H-05)
9. **MAY** defer logistic recalibration to v2 (requires n >= 50/domain, unlikely in year 1) (H-10)
10. **MAY** defer ForecastBench API integration pending format discovery (H-09)

---
