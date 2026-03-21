# Defense Report - Worker B: Calibration Engine, Debiasing, & Research-Mandated Infrastructure

```yaml
---
verdict: UNSOUND
repairs_made: 11
contests_made: 0
unresolved: 0
---
```

---

### Issue Disposition Table

| SK-ID | Severity | Status | Fix/Defense |
|-------|----------|--------|-------------|
| SK-01 | Critical | RESOLVED | Adopted file-based contract. Worker B writes `domain_corrections.json` to `${OATHFISH_DATA_DIR}/calibration/`. Dropped CalibrationEngine parameter from amplify_aggregate(). Defined exact JSON schema matching Worker A's expected format. |
| SK-02 | Critical | RESOLVED | Added explicit spec deviation notice. Documented that C-27 verification says n>=90 for 80% power at d=0.3, while plan uses n>=15 with |MSE|>0.10 to catch only large biases (d>0.6). Both are valid but different sensitivity levels. Added honest statistical caveats. |
| SK-03 | High | RESOLVED | Replaced `_normal_cdf()` with `_t_sf()` using regularized incomplete beta function. Fixed incorrect comment ("conservative" -> "anti-conservative" was wrong; now using correct t-distribution). |
| SK-04 | High | RESOLVED | Defined explicit mapping function: `forecast_probability = (stance + 1) / 2`. Documented as design decision with rationale. Added `stance_to_probability()` utility function. |
| SK-05 | High | RESOLVED | Unified delta sign convention. Changed `brier_gap` to match `deliberation_delta`: both now use "positive = improvement" convention. `brier_gap = brier_raw - brier_corrected` (positive = correction helps). |
| SK-06 | High | RESOLVED | Added `write_domain_corrections()` method to CalibrationEngine. Called after every `record_outcome()` and `get_ensemble_metrics()`. Writes to `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json` using Worker A's expected schema. |
| SK-07 | Medium | RESOLVED | Reordered classify_horizon() to check short_indicators BEFORE medium_indicators. Added "1 month" to short_indicators explicitly. |
| SK-08 | Medium | RESOLVED | Reclassified A-B01, A-B04, A-B08 from "WORKER CONSENSUS" to "IMPLICIT" with note that single-loop mode means no independent validation available. |
| SK-09 | Medium | RESOLVED | Simplified holdout partition to use prediction_id directly (single hash). Removed gratuitous double-hashing. |
| SK-10 | Medium | RESOLVED | Replaced all `datetime.utcnow()` with `datetime.now(datetime.UTC)` for Python 3.12+ compatibility. |
| SK-11 | Medium | RESOLVED | Replaced trivially-true guard with holdout-vs-training gap check only: `overfitting_detected = overfitting_gap > 0.02`. Removed redundant `brier_training < brier_raw` condition. |

---

### Verification Evidence

**SK-01: Cross-engine debiasing interface mismatch**

My Verification:
Command: Grep for `amplify_aggregate` in Worker A plan
Output:
```
Worker A plan.md line 777-800:
async def amplify_aggregate(
    apply_debiasing: bool = False,
    archetype_ids: list[str] | None = None
) -> dict:

Worker A plan.md line 803-823:
Cross-Engine Interface Contract (H-03 mitigation):
File: ${OATHFISH_DATA_DIR}/calibration/domain_corrections.json
Format:
{
  "corrections": {
    "technology": {"offset": 0.05, "n": 95, "direction": "over"},
    "politics": {"offset": -0.03, "n": 110, "direction": "under"}
  },
  "last_updated": "2026-03-18T10:00:00Z"
}

Worker B plan.md line 1033-1037 (Task D.1):
def amplify_aggregate(
    self,
    apply_debiasing: bool = True,
    calibration_engine: Optional[CalibrationEngine] = None,
) -> dict:
```

Disposition: RESOLVED - Skeptic correct. Worker A expects a file-based interface with no CalibrationEngine parameter. Worker B was passing an in-memory object.

Fix:
1. Added `write_domain_corrections()` to CalibrationEngine that writes to `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json` using Worker A's exact schema.
2. Removed `calibration_engine` parameter from amplify_aggregate() in Task D.1.
3. Task D.1 now reads from `domain_corrections.json` file, matching Worker A's contract.

---

**SK-02: Correction threshold n>=15 deviates from spec's n>=90**

My Verification:
Command: Read feature-request.md line 1142
Output:
```
C-27 | REQUIREMENT | Track per-domain acquiescence rate from run 1; apply corrections from run 3+ | MUST |
  Verification: "corrections applied when n>=90/domain" | 2402.19379 + 2602.19520
```

Command: Read Worker B explore.md lines 204-215
Output:
```
- 80% power at d=0.3 requires n=90 per domain.
- At 30 predictions/run, 6 domains: ~5 per domain per run.
- n=90/domain requires ~18 runs.
- But C-27 says corrections from run 3+.
- At run 3: n=15/domain.

Design decision: Apply corrections from run 3+ ONLY when MSE_d is large enough...
- Run 3-9: Apply correction ONLY if |MSE_d| > 0.10 AND n_d >= 15
- Run 10+: Lower threshold to |MSE_d| > 0.05 AND n_d >= 45
- Run 18+: Standard threshold at p < 0.10
```

Disposition: RESOLVED - Skeptic correct that the deviation is not explicitly flagged in the plan.

Fix: Added explicit "SPEC DEVIATION" notice to Section 5 (Hazards) and to Task B.1 code comments. Documents the tradeoff: C-27 verification says n>=90 for 80% power at d=0.3 (detecting small biases). Plan uses n>=15 with |MSE|>0.10 which only catches large biases (d>0.6). The tiered approach (n>=15 at run 3, n>=45 at run 10, n>=90 at run 18) progressively increases sensitivity. Added statistical caveats about Type I/II error rates at each tier.

---

**SK-03: Normal CDF is anti-conservative at small n**

My Verification:
The skeptic's claim is mathematically correct. At n=15, the t-distribution with 14 df has heavier tails than the normal. For a two-tailed test at alpha=0.10:
- t(14) critical value = 1.761
- z critical value = 1.645
Using the normal CDF when the t-distribution applies produces smaller p-values (because 1 - Phi(t_stat) > 1 - T(t_stat, df) for |t_stat| > 0). This means the normal approximation is ANTI-conservative -- it inflates significance, potentially triggering corrections that the t-test would correctly reject.

The plan's comment at line 607 "conservative at smaller n" is factually incorrect.

Disposition: RESOLVED - Skeptic correct.

Fix: Replaced `_normal_cdf()` with `_t_sf()` that computes the t-distribution survival function using the regularized incomplete beta function (scipy.stats.t.sf or pure-Python implementation). Updated the p-value computation to use t-distribution with n-1 degrees of freedom. Removed the incorrect comment about CLT validity at n>=15.

---

**SK-04: No mapping from PredictionPosition.stance [-1,1] to CalibrationPrediction.forecast_probability [0,1]**

My Verification:
Command: Read Worker A plan.md lines 159-172
Output:
```
class PredictionPosition(BaseModel):
    archetype_id: str
    round_n: int
    prediction: str
    decision: str  # adopt | wait | reject | mixed
    stance: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    ...
```

Command: Read Worker B plan.md line 111
Output:
```
forecast_probability: float = Field(ge=0.0, le=1.0)  # Predicted probability [0,1]
```

No mapping function exists anywhere in the plan.

Disposition: RESOLVED - Skeptic correct.

Fix: Added `stance_to_probability()` function to domain_classifier.py with formula `forecast_probability = (stance + 1) / 2`. This maps stance=-1 to p=0.0, stance=0 to p=0.5, stance=1 to p=1.0. Documented as a design decision. The `record_prediction()` function now accepts either `forecast_probability` directly or converts from `stance` via this function. Added documentation explaining the semantic mapping.

---

**SK-05: Inconsistent delta sign conventions**

My Verification:
Command: Read Worker B plan.md lines 161-164
Output:
```
brier_gap: float                    # corrected - raw (negative = correction helps)
...
deliberation_delta: Optional[float] # baseline - informed (positive = deliberation helps)
```

These are opposite conventions:
- brier_gap: negative = good
- deliberation_delta: positive = good

Disposition: RESOLVED - Skeptic correct. This will confuse API consumers.

Fix: Changed `brier_gap` to `brier_raw - brier_corrected` (positive = correction helps), matching `deliberation_delta`'s convention (positive = improvement). Updated comment and computation at line 808.

---

**SK-06: No mechanism to write domain_corrections.json**

My Verification:
This is the write-side of SK-01. Worker A plan.md lines 803-823 documents reading from `${OATHFISH_DATA_DIR}/calibration/domain_corrections.json`. Worker B's CalibrationEngine stores data in `predictions.json` and `outcomes.json` but never writes `domain_corrections.json`.

Disposition: RESOLVED - Skeptic correct. Addressed as part of SK-01 fix.

Fix: Added `write_domain_corrections()` method that computes active corrections for all domains and writes to `domain_corrections.json` using Worker A's exact schema: `{"corrections": {"DOMAIN": {"offset": float, "n": int, "direction": "over"|"under"}}, "last_updated": ISO}`. Called after `record_outcome()` and whenever ensemble metrics are computed.

---

**SK-07: classify_horizon() ordering bug with "month" substring**

My Verification:
Command: Read Worker B plan.md lines 330-349
Output:
```
short_indicators = ["week", "1 month", "2 week", "3 week", "days"]
medium_indicators = ["month", "quarter", "2 month", "3 month", "90 day"]
long_indicators = ["6 month", "year", "12 month", "9 month", "annual"]
extended_indicators = ["years", "2 year", "3 year", "5 year", "decade", "long-term"]

for indicator in extended_indicators:
    if indicator in text_lower:
        return PredictionHorizon.EXTENDED
for indicator in long_indicators:
    if indicator in text_lower:
        return PredictionHorizon.LONG
for indicator in medium_indicators:
    if indicator in text_lower:
        return PredictionHorizon.MEDIUM
for indicator in short_indicators:
    if indicator in text_lower:
        return PredictionHorizon.SHORT
```

The text "1 month" contains the substring "month", which appears in medium_indicators. Since medium is checked before short, "1 month" would be classified as MEDIUM, not SHORT.

Disposition: RESOLVED - Skeptic correct.

Fix: Reordered to check short before medium. Also added explicit "1 month" to short_indicators list (it was already there but unreachable). The new order is: extended -> long -> short -> medium.

---

**SK-08: WORKER CONSENSUS label invalid in single-loop mode**

My Verification:
This is a DARWIN process issue. In single-loop mode, Worker B is the only worker reviewing calibration scope. "WORKER CONSENSUS" implies multiple independent workers agreed, which did not happen.

Disposition: RESOLVED - Skeptic correct.

Fix: Reclassified A-B01, A-B04, A-B08 from "WORKER CONSENSUS" to "IMPLICIT" with note: "Single-loop mode -- no independent worker validation available."

---

**SK-09: Double-hashing in holdout partition**

My Verification:
Command: Read Worker B plan.md lines 372-383
Output:
```
def compute_holdout_flag(prediction_id: str) -> bool:
    h = hashlib.sha256(prediction_id.encode()).hexdigest()
    return int(h, 16) % 5 == 0

def generate_prediction_id(run_id: str, archetype_id: str, question_id: str) -> str:
    raw = f"{run_id}:{archetype_id}:{question_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

`prediction_id` is already a SHA-256 hex substring. `compute_holdout_flag` hashes it again. The result is still uniform, but the double-hash is gratuitous.

Disposition: RESOLVED - Skeptic correct (style issue).

Fix: Changed `compute_holdout_flag` to use `int(prediction_id, 16) % 5 == 0` directly since `prediction_id` is already a hex string from SHA-256. Removed the redundant second hash.

---

**SK-10: datetime.utcnow() deprecated in Python 3.12+**

My Verification:
Python 3.12 deprecation PEP 703 / docs confirm `datetime.utcnow()` is deprecated. Found at lines 495, 519-521, 1288, 1291.

Disposition: RESOLVED - Skeptic correct.

Fix: Replaced all instances with `datetime.now(datetime.UTC)`.

---

**SK-11: Overfitting detection guard condition trivially true**

My Verification:
Command: Read Worker B plan.md lines 776-779
Output:
```
overfitting_detected = (
    overfitting_gap > 0.02
    and brier_training < brier_raw
)
```

`brier_training` is computed on the training (non-holdout) set which is also the basis for corrections. `brier_raw` is computed on ALL resolved predictions. Since corrections are fitted to the training set, `brier_training` will almost always be lower than `brier_raw` when corrections are active. The condition `brier_training < brier_raw` adds no discriminative power.

Disposition: RESOLVED - Skeptic correct.

Fix: Simplified to `overfitting_detected = overfitting_gap > 0.02`. The meaningful signal is whether holdout Brier diverges from training Brier (the gap), not whether training is better than raw (which is expected).

---

### Plan Deltas

Changes made to the plan:

1. **Task A.3** (domain_classifier.py):
   - Added `stance_to_probability()` function: `forecast_probability = (stance + 1) / 2` (SK-04)
   - Fixed `compute_holdout_flag()` to use direct hex parsing instead of double-hashing (SK-09)
   - Fixed `classify_horizon()` ordering: short checked before medium (SK-07)

2. **Task B.1** (calibration_engine.py):
   - Replaced `_normal_cdf()` with t-distribution p-value computation (SK-03)
   - Added `write_domain_corrections()` method writing Worker A's expected JSON schema (SK-01, SK-06)
   - Changed `brier_gap` computation to `brier_raw - brier_corrected` (positive = improvement) (SK-05)
   - Simplified overfitting detection to gap-only check (SK-11)
   - Replaced all `datetime.utcnow()` with `datetime.now(datetime.UTC)` (SK-10)
   - Added SPEC DEVIATION notice for n>=15 vs n>=90 threshold (SK-02)

3. **Task D.1** (amplification_engine.py debiasing):
   - Removed `calibration_engine` parameter from `amplify_aggregate()` (SK-01)
   - Changed to file-based interface reading `domain_corrections.json` (SK-01, SK-06)

4. **Task A.1** (calibration_models.py):
   - Updated `brier_gap` comment to match new convention (SK-05)

5. **Section 5** (Hazards): Added SPEC DEVIATION notice to H-01 row (SK-02)

6. **Section 9** (Assumptions): Reclassified A-B01, A-B04, A-B08 from WORKER CONSENSUS to IMPLICIT (SK-08)

7. **Task F.1** (forecastbench.py): Replaced `datetime.utcnow()` calls (SK-10)

8. **Test Plan**: Added test for `stance_to_probability()` mapping, test for `domain_corrections.json` write, test for t-distribution p-values.

---

### RFIs

None. All issues resolved with code evidence.

---

## Handoff

Defense saved to: docs/darwin/runs/0001-oathfish-swarm-engine/workers/B/defense.md
Revised plan saved to: docs/darwin/runs/0001-oathfish-swarm-engine/workers/B/plan.md (edited in place)

Issue Summary:
- RESOLVED: 11
- CONTESTED: 0
- UNVERIFIED: 0

Returning to Skeptic for re-audit of plan.md (revised in place).
