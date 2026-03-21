# Skeptic Critique - Worker B: Calibration Engine, Debiasing, & Research-Mandated Infrastructure

```yaml
---
verdict: UNSOUND
issues_critical: 2
issues_high: 4
issues_medium: 5
---
```

### Executive Verdict

**Status**: UNSOUND

**Top 3 Blockers**:
1. [SK-01] Cross-engine debiasing interface mismatch: Worker B passes `CalibrationEngine` object directly to `amplify_aggregate()`; Worker A expects a file-based `domain_corrections.json` interface. These two designs are incompatible.
2. [SK-02] Feature request C-27 verification column says "corrections applied when n>=90/domain" but Worker B applies corrections at n>=15 from run 3+. The plan explicitly deviates from the spec's stated verification criterion without acknowledging the discrepancy.
3. [SK-03] Normal CDF approximation used for p-values instead of t-distribution. At n=15 (the plan's minimum correction threshold), the normal approximation significantly underestimates tail probabilities, producing artificially small p-values that may trigger corrections prematurely.

---

### Kill List (Falsified Claims & Omissions)

| SK-ID | Severity | Type | Claim/Omission | Evidence |
|-------|----------|------|----------------|----------|
| SK-01 | Critical | Integration | Worker B's `amplify_aggregate()` takes `CalibrationEngine` as a parameter; Worker A's `amplify_aggregate()` reads from `domain_corrections.json` file | Worker A plan (line 777-823): `amplify_aggregate(apply_debiasing: bool = False, archetype_ids: list[str] | None = None)` with no CalibrationEngine param. Uses file: `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json`. Worker B plan (Task D.1): `amplify_aggregate(self, apply_debiasing: bool = True, calibration_engine: Optional[CalibrationEngine] = None)`. Incompatible signatures. |
| SK-02 | Critical | Semantic | Plan claims "corrections from run 3+" with n>=15 threshold, but C-27 verification says "corrections applied when n>=90/domain" | feature-request.md C-27 (line 1142): verification column states "corrections applied when n>=90/domain". Worker B plan section 5.2/explore.md: "Run 3-9: Apply correction ONLY if abs(MSE_d) > 0.10 AND n_d >= 15." The plan correctly identifies n=90 as the power threshold but applies corrections far below it. This is arguably a sound statistical choice, but it contradicts the spec's explicit verification criterion and the plan does not flag this as a spec deviation. |
| SK-03 | High | Empirical | Plan uses `_normal_cdf()` for p-values in t-test, claims "valid at n >= 15 by CLT" | Plan line 607-608: "Approximate p-value using normal distribution for simplicity (valid at n >= 15 by CLT; conservative at smaller n)". This is backwards: the normal approximation is ANTI-CONSERVATIVE at small n (it produces smaller p-values than the t-distribution), not conservative. At n=15, t(14) at alpha=0.10 requires t=1.761 vs z=1.645 for the normal. Using the normal CDF inflates significance, potentially activating corrections that the t-distribution would correctly reject. |
| SK-04 | High | Integration | Worker B's `CalibrationPrediction` model has `forecast_probability` field; Worker A's `PredictionPosition` has `stance` and `confidence` but no `forecast_probability` | Worker A models.py (line 159-173): `PredictionPosition` has `stance: float` (ge=-1.0, le=1.0) and `confidence: float` (ge=0.0, le=1.0). Worker B `CalibrationPrediction` (line 111): `forecast_probability: float` (ge=0.0, le=1.0). No mapping defined between Worker A's `stance`/`confidence` and Worker B's `forecast_probability`. How does a deliberation-round prediction become a calibration prediction? |
| SK-05 | High | Semantic | `brier_gap` definition inconsistent with plan's stated semantics | Plan line 162: `brier_gap: float # corrected - raw (negative = correction helps)`. Plan line 808: returns `brier_gap=round(brier_corrected - brier_raw, 6)`. But `brier_corrected` is computed USING the domain corrections. If corrections are working, `brier_corrected < brier_raw`, so `brier_gap < 0`, which the comment says means "correction helps". However, the `deliberation_delta` (line 164) is defined as `baseline - informed (positive = deliberation helps)`. These two delta conventions have OPPOSITE sign semantics. One is "lower is better minus baseline" and the other is "baseline minus lower-is-better". This inconsistency will confuse consumers of the API. |
| SK-06 | High | Omission | No mechanism to write `domain_corrections.json` that Worker A expects to read | Worker A plan explicitly documents a file-based contract at `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json` with a specific schema (`corrections`, `last_updated`). Worker B's calibration engine does NOT write this file. Worker B stores data in `predictions.json` and `outcomes.json`. The cross-engine interface is disconnected. |
| SK-07 | Medium | Semantic | `classify_horizon()` ordering bug: "1 month" matched by MEDIUM before SHORT checks run | Plan line 331-333: `medium_indicators = ["month", "quarter", "2 month", "3 month", "90 day"]`. The word "month" will match any text containing "month", including "1 month". But "1 month" should be SHORT. The checking order is extended -> long -> medium -> short, so "1 month" would match "month" in medium_indicators before reaching short_indicators. |
| SK-08 | Medium | Assumption | A-B01 and A-B04 classified as "WORKER CONSENSUS" but this is single-loop mode | Plan section 9: A-B01 and A-B04 labeled "WORKER CONSENSUS". But this is a single-loop DARWIN run -- Worker B is the only worker on this scope. "WORKER CONSENSUS" requires multiple workers to agree. In single-loop mode, this is a self-agreement label and provides no independent validation. |
| SK-09 | Medium | Empirical | Holdout partition hash uses `prediction_id` (line 116), but `compute_holdout_flag()` takes `prediction_id` (line 372-377) while the model says `is_holdout: bool # Deterministic: hash(prediction_id) % 5 == 0` | These are consistent in isolation, but note the `prediction_id` is itself `hash(run_id:archetype_id:question_id)[:16]` (line 383). The holdout flag computation double-hashes: SHA-256 of an already-truncated SHA-256 hex string. While SHA-256 of a hex string is still uniformly distributed, this is a gratuitous layering that could confuse maintainers. Not a bug, but unnecessary complexity. |
| SK-10 | Medium | Omission | `datetime.utcnow()` is deprecated in Python 3.12+ | Plan uses `datetime.utcnow()` throughout (lines 495, 519-521, 1288). Python 3.12 deprecated `datetime.utcnow()` in favor of `datetime.now(datetime.UTC)`. Since the plan targets Python 3.11+, this will emit deprecation warnings on 3.12+. |
| SK-11 | Medium | Omission | Overfitting detection logic compares `brier_training < brier_raw` which may always be true | Plan line 776-779: `overfitting_detected = (overfitting_gap > 0.02 and brier_training < brier_raw)`. But `brier_training` is computed on non-holdout resolved predictions and `brier_raw` is computed on ALL resolved predictions (including holdout). Since holdout predictions are excluded from correction but included in raw, and training predictions are a superset of the correction basis, `brier_training` will naturally tend to be lower (better) than `brier_raw` whenever corrections help at all. This condition may be trivially true and provide no real guard. |

---

### Assumption Audit

| A-ID | Classification | Skeptic Finding | Status |
|------|----------------|-----------------|--------|
| A-B01 | WORKER CONSENSUS | Invalid classification in single-loop mode. Worker B is the only worker reviewing this scope. | SK-08 |
| A-B02 | IMPLICIT | Valid. 6-domain taxonomy is a reasonable starting point with UNCLASSIFIED fallback. | PASS |
| A-B03 | VERIFIED | Claim is mathematically correct. SHA-256 mod 5 produces uniform distribution. | PASS |
| A-B04 | WORKER CONSENSUS | Invalid classification in single-loop mode. Same issue as A-B01. | SK-08 |
| A-B05 | VERIFIED | Claim is correct. Abramowitz-Stegun error < 1.5e-7 is well-established. However, the choice to use normal CDF instead of t-distribution is itself the issue (SK-03). | PASS (the approximation is accurate for the normal; the problem is using normal instead of t) |
| A-B06 | IMPLICIT | Valid. ForecastBench format assumption is explicitly flagged with modular export design. | PASS |
| A-B07 | IMPLICIT | Valid. Risk honestly stated. | PASS |
| A-B08 | WORKER CONSENSUS | Invalid classification, same as A-B01. The substantive claim (stdlib sufficient) is reasonable, but the label is wrong. | SK-08 |

---

### Hazard Audit

| H-ID | Hazard | Mitigation Found | Mitigation Valid | Notes |
|------|--------|-----------------|-----------------|-------|
| H-01 | Noise corrections at small n | Yes (n-thresholds) | Partially | The n>=15 threshold at run 3+ is reasonable but contradicts C-27's verification criterion of n>=90. The normal CDF approximation (SK-03) weakens the statistical test. |
| H-02 | Domain taxonomy undefined | Yes (Task A.2, A.3) | Yes | 6 domains with configurable JSON. Keyword classifier design is sound for deterministic requirement. |
| H-03 | Data lost on plugin update | Yes (Task CFG.1) | Yes | Correctly changes .mcp.json to CLAUDE_PLUGIN_DATA. |
| H-04 | Holdout contamination | Yes (hash partition, exclude_holdout) | Yes | Hash-based partition is sound. Default exclusion enforced. |
| H-05 | A/B temporal confound | Yes (timestamps, stratification) | Partially | Timestamps recorded but no test verifies the temporal gap is reported. Mitigation is documentation, not prevention. |
| H-06 | Cold-start / resolution latency | Yes (bootstrap questions) | Partially | Bootstrap field exists in model, but no mechanism to GENERATE bootstrap questions. The plan assumes they are available but provides no source. H-06 says "short-horizon bootstrap questions may not resolve fast enough" -- the mitigation says "include them" but does not address where they come from. |
| H-07 | Domain-varying acquiescence | Yes (per-domain corrections) | Yes | Per-domain MSE computation and correction is correctly designed. |
| H-08 | Competence classifier timing paradox | Yes (two-stage design) | Yes | Stage 1 (text-only) before UNDERSTAND, Stage 2 (archetype-aware) post-UNDERSTAND. Sound resolution. |
| H-09 | ForecastBench format unknown | Yes (modular export) | Yes | Explicitly deferred with modular design. |
| H-10 | Logistic recalibration unstable at small n | Yes (deferred to run 50+) | Yes | Schedule prevents premature activation. |
| H-11 | Gap > 0.05 triggers undefined action | Yes (report recommendation) | Partially | Only reports the gap. No automated response or escalation path. The mitigation is "Worker D concern" -- this is a cross-worker coordination gap. |
| H-12 | Ensemble metrics grows unbounded | Yes (window parameter) | Yes | Default window=10 runs is reasonable. |
| H-CFG-01 | OATHFISH_DATA_DIR misconfigured | Yes (Task CFG.1) | Yes | Fix is correct. |
| H-CFG-02 | Correction threshold hardcoded | Yes (per-domain n-threshold) | Yes | Per-domain activation resolves this. |
| H-CFG-03 | Domain taxonomy not configurable | Yes (JSON config) | Yes | Config file with override capability. |

---

### Ambiguity Register

| Claim | Strategies Tried | Result |
|-------|------------------|--------|
| "80% power at d=0.3 requires n=90 per domain" (E-06) | 1. Searched calibration paper (2602.19520): no power analysis found. 2. Searched synthesis-report.md: no n=90 mention. 3. Searched final-synthesis.md: found at line 99, 125 -- stated as recommendation, not derived from paper data. 4. Verified mathematically: standard power analysis for one-sample t-test at alpha=0.05, d=0.3, power=0.80 gives n~90. | The n=90 claim is mathematically correct for a two-tailed one-sample t-test, but it does not come from the calibration paper as implied by E-06 attribution "2602.19520:OathFish Relevance". The paper's OathFish Relevance section does not contain a power analysis. The number comes from the debate synthesis applying standard power analysis formulas. |
| Bootstrap question sourcing mechanism | Searched plan for how bootstrap questions are generated/discovered. | Plan states bootstrap questions come from "ForecastBench short-horizon subset (if available)", "Known upcoming events", and "Market-implied predictions" (explore.md section 5.7). But no concrete mechanism (API, manual entry, automated scraping) is specified. This is underspecified. |

---

### Certified Facts

| Claim | Evidence |
|-------|----------|
| Brier score formula is correct: BS = (1/N) * SUM((f_i - o_i)^2) | Plan line 828-836: `_compute_brier()` correctly implements the formula. Verified against standard definition. |
| Mean Signed Error formula is correct: MSE_d = (1/N_d) * SUM(f_i - o_i) | Plan line 600: `mse = sum(errors) / n` where errors are `f - o`. Correct. |
| Additive correction formula is correct: f_corrected = clamp(f - alpha_d, 0, 1) | Plan line 843-854: `_compute_brier_corrected()` correctly implements `max(0.0, min(1.0, f - alpha))`. |
| Logistic recalibration formula matches research: p* = p^theta / (p^theta + (1-p)^theta) | Plan section 5.1 (line 192-193) and explore.md section 5.1. Not implemented in code (deferred to run 50+). Formula matches round-1-ffa.md:272. |
| Holdout partition produces approximately 20% holdout | SHA-256 modulo 5 produces uniform distribution by construction. |
| Correction schedule: RECORD_ONLY -> DOMAIN_ADDITIVE -> ARCHETYPE_ADDITIVE -> LOGISTIC | Plan lines 787-794: Stage transitions at runs <3, 3-9, 10-49, 50+. Matches explore.md section 5.1. |
| Domain taxonomy has 6 domains + UNCLASSIFIED | Plan Task A.1 defines PredictionDomain enum with 7 values (6 + UNCLASSIFIED). Task A.2 provides full taxonomy config. |
| All 15 hazards from explore.md have mitigations in the plan | Section 10 "Hazard Coverage Check" maps all H-IDs. Verified by checking section 5 mitigations. |
| 5 calibration MCP tools are well-specified | record_prediction, record_outcome, get_domain_bias, get_archetype_bias, get_ensemble_metrics all have complete signatures with input/output types and implementation code. |
| Feature request C-34 (holdout 20%) correctly addressed | Hash-based partition at recording time. `exclude_holdout=True` default in all bias computation functions. |
| Feature request C-28 (dual-metric reporting) correctly addressed | EnsembleMetrics model has both `brier_raw` and `brier_corrected`. amplify_aggregate returns both raw and debiased. |
| Feature request C-35 (ForecastBench pipeline) correctly addressed | Task F.1 creates modular export function with acknowledged format uncertainty. |

---

### Cross-Worker Conflict Analysis

| Conflict | Workers | Severity | Description |
|----------|---------|----------|-------------|
| Debiasing interface mismatch | A vs B | Critical (SK-01, SK-06) | Worker A expects `domain_corrections.json` file interface. Worker B passes `CalibrationEngine` object in-memory. These are fundamentally different integration patterns. One worker must change. |
| PredictionPosition vs CalibrationPrediction field mapping | A vs B | High (SK-04) | Worker A's `PredictionPosition.stance` is [-1, 1] and `PredictionPosition.confidence` is [0, 1]. Worker B's `CalibrationPrediction.forecast_probability` is [0, 1]. No mapping function defined. How does stance + confidence become a forecast probability? |
| /oathfish-calibrate command ownership | B vs C | Low | Worker C defines the command (Task D.4) that calls Worker B's MCP tools. No conflict -- proper separation of concerns. Worker C's command correctly delegates to Worker B's tools. |
| amplify_aggregate signature | A vs B vs D | High | Worker A: `amplify_aggregate(apply_debiasing, archetype_ids)`. Worker B: `amplify_aggregate(self, apply_debiasing, calibration_engine)`. Worker D calls `amplify_aggregate(apply_debiasing=True)`. All three assume different signatures. |

---

### Issue Ledger

| SK-ID | Severity | Status | Notes |
|-------|----------|--------|-------|
| SK-01 | Critical | OPEN | Cross-engine interface mismatch. Must resolve before implementation. |
| SK-02 | Critical | OPEN | Spec deviation on C-27 verification criterion. Must explicitly flag as deviation or change threshold. |
| SK-03 | High | OPEN | Normal vs t-distribution. Will produce incorrect p-values at small n. |
| SK-04 | High | OPEN | PredictionPosition-to-CalibrationPrediction mapping undefined. |
| SK-05 | High | OPEN | Inconsistent delta sign conventions in EnsembleMetrics. |
| SK-06 | High | OPEN | Missing domain_corrections.json write mechanism. |
| SK-07 | Medium | OPEN | classify_horizon ordering bug with "month" substring. |
| SK-08 | Medium | OPEN | 3 assumptions mislabeled as WORKER CONSENSUS. |
| SK-09 | Medium | OPEN | Double-hashing in holdout partition (style, not correctness). |
| SK-10 | Medium | OPEN | datetime.utcnow() deprecated in Python 3.12+. |
| SK-11 | Medium | OPEN | Overfitting detection guard condition may be trivially true. |
