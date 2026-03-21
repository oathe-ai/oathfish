# OathFish Research Debate: Final Synthesis & Judge Scores

**Run**: run_20260318_140000
**Format**: 3-round Free-For-All with 5 paper agents + cross-challenges
**Papers**: 2305.14325, 2402.19379, 2409.19839, 2411.10109, 2602.19520

---

## What the Debate Proved

This was a genuine adversarial debate — agents challenged each other directly, conceded when evidence demanded it, and produced evolved positions stronger than any single perspective. The key breakthroughs came from CROSS-PAPER connections that no individual paper contains.

---

## Final Statements: Summary & Scores

### paper-debate (2305.14325: Multi-Agent Debate)

**Recommendation**: Separate deliberation into ARGUMENTS (rounds 1-5, qualitative reasoning exchanged) and PREDICTIONS (round 6, independent structured JSON, no number-sharing). This respects both debate's value (reasoning improvement) AND ensemble's value (independent aggregation).

**Prediction**: Deliberation improves Brier 0.03-0.06 on multi-factor questions, neutral-to-harmful on simple binaries. Confidence: 60% direction, 30% magnitude.

**Concession**: Convergence is NOT a success metric. Their own paper shows confident false consensus on wrong answers. Slower convergence = better outcomes.

**Risk**: Confident false consensus on systematically biased predictions that no perspective can detect.

| Criterion | Score |
|-----------|-------|
| Evidence quality | 8/10 — Table 1 data directly supports argument/prediction separation |
| OathFish relevance | 9/10 — Most architecturally actionable recommendation in the debate |
| Novelty | 9/10 — "Arguments without numbers until final round" is genuinely new |
| Adversarial survival | 8/10 — Conceded forecasting transfer gap honestly; core claim intact |
| **Total** | **34/40** |

---

### paper-ensemble (2402.19379: Wisdom of the Silicon Crowd)

**Recommendation**: Implement structured debiasing (acquiescence correction by domain/horizon) BEFORE optimizing deliberation. Debiased averaging is a stronger baseline.

**Prediction**: 55-60% positive-prediction rate raw (75% confidence). Deliberation helps combination questions, hurts simple binaries (55% confidence).

**Concession**: Blanket claim "averaging beats updating" was too aggressive. Debate is mechanistically different from single-model scalar updating.

**Risk**: Single-model correlated failures. 30 Claude instances share blind spots. Effective ensemble size may be 3-5, not 30.

| Criterion | Score |
|-----------|-------|
| Evidence quality | 9/10 — Brier scores, p-values, specific statistics throughout |
| OathFish relevance | 8/10 — Debiasing-first ordering is pragmatic and important |
| Novelty | 7/10 — Acquiescence bias was already known; structured decomposition adds value |
| Adversarial survival | 9/10 — Key concession strengthened position; correlated-failure risk uncontested |
| **Total** | **33/40** |

---

### paper-forecast (2409.19839: ForecastBench)

**Recommendation**: Submit to ForecastBench before any public accuracy claims. Threshold: below 0.122 = architecture adds value, below 0.10 = genuinely novel.

**Prediction**: Brier 0.108-0.135 on 100+ questions. Confidence: 65%.

**Concession**: Treated persona fidelity as binary (valid/invalid) when it's a gradient. Reasoning traces have independent value beyond probability accuracy.

**Risk**: No competence boundary detection — OathFish can't tell when a question is outside its archetype-set's expertise. Will produce confident noise on out-of-domain questions.

| Criterion | Score |
|-----------|-------|
| Evidence quality | 9/10 — ForecastBench data is the gold standard; specific Brier thresholds |
| OathFish relevance | 9/10 — External validation is non-negotiable |
| Novelty | 8/10 — Competence boundary detection is a genuinely overlooked risk |
| Adversarial survival | 9/10 — Nobody contested ForecastBench recommendation across all 3 rounds |
| **Total** | **35/40** — Highest score |

---

### paper-persona (2411.10109: Generative Agent Simulations)

**Recommendation**: Ground archetypes in real public sources (Rung 2 of grounding ladder) before launch. Report BOTH corrected and uncorrected Brier scores to detect calibration masking weak personas.

**Prediction**: Rung 2 archetypes will show inter-archetype correlation 0.15 lower than Rung 1 (synthetic). Confidence: 65%.

**Concession**: Conflated replication fidelity (interpolation) with prediction capacity (extrapolation). The 85% doesn't transfer to forecasting.

**Risk**: Calibration-persona overfitting feedback loop. Re-grounding archetypes based on past prediction errors = overfitting to calibration set. Needs holdout validation.

| Criterion | Score |
|-----------|-------|
| Evidence quality | 7/10 — 85% result well-cited but transferability honestly unknown |
| OathFish relevance | 9/10 — Grounding ladder is immediately actionable; dual-metric is elegant |
| Novelty | 9/10 — Overfitting risk in calibration-persona loop is genuinely new insight |
| Adversarial survival | 8/10 — Grounding ladder survived; magnitude claims appropriately uncertain |
| **Total** | **33/40** |

---

### paper-calibration (2602.19520: Calibration Decomposition)

**Recommendation**: Domain-level directional bias tracking from run 1. Corrections at run 3+ (80% power at n=90/domain). Not cell-level, not archetype-level until n=50+.

**Prediction**: 2/6 domains show significant directional bias after 5 runs. Additive correction improves Brier by 0.01+. Confidence: 65%.

**Concession**: 720-cell matrix was overengineered. Calibration as prompt engineering matters more than statistical precision at small n.

**Risk**: Outcome resolution latency starves calibration loop for 6-12 months. Predictions resolve in 3-12 months; calibration can't start until outcomes are known. The "time moat" is hollow for year one.

| Criterion | Score |
|-----------|-------|
| Evidence quality | 9/10 — Power analysis is rigorous; explicit sample size requirements |
| OathFish relevance | 8/10 — Conservative correction schedule is honest and practical |
| Novelty | 8/10 — Resolution latency risk is devastating and unaddressed by others |
| Adversarial survival | 9/10 — Scale critique was accepted and evolved into stronger position |
| **Total** | **34/40** |

---

## RANKED RECOMMENDATIONS (Final)

### Tier 1: Non-Negotiable (implement before launch)

1. **Submit to ForecastBench** (35/40) — External validation before any claims. Threshold: <0.122 = valuable, <0.10 = novel.

2. **Separate arguments from predictions in DELIBERATE** (34/40) — Rounds 1-5 exchange qualitative reasoning. Round 6 is independent structured JSON predictions. Aggregate via median. This respects both debate value AND ensemble independence.

3. **Domain-level debiasing from run 1** (34/40) — Track acquiescence rates and directional bias per domain. Apply additive corrections at run 3+ where statistically detectable (n=90/domain, 80% power at d=0.3).

### Tier 2: High-Value (implement in first 5 runs)

4. **Grounding ladder: Rung 2 for all archetypes** (33/40) — Curate 3-5 real public sources per archetype before production. Track inter-archetype correlation as diversity metric.

5. **A/B test deliberation vs baseline every run** (33/40) — Run amplification BEFORE and AFTER deliberation. Stratify by question type (simple binary vs multi-factor). If deliberation consistently loses on a question type, skip it.

6. **Dual-metric reporting** (33/40) — Always report calibration-corrected AND raw uncorrected Brier. Gap > 0.05 = persona needs re-grounding, not more calibration.

### Tier 3: Important (address within first year)

7. **Competence boundary detection** (35/40 risk score) — Classify incoming questions for archetype relevance before UNDERSTAND phase. Flag low-relevance questions as "outside core competence."

8. **Short-horizon questions for fast calibration** (34/40 risk score) — Include 1-4 week resolution questions in every run to generate calibration feedback faster than the 3-12 month primary questions.

9. **Inter-archetype correlation monitoring** — Measure effective ensemble diversity. If pairwise correlation >0.8, the 30-archetype architecture provides ~3-5 effective predictors.

10. **Holdout validation set** — Reserve 20% of resolved predictions from calibration loop. Detect overfitting if calibration-set accuracy improves but holdout plateaus.

---

## 5 CONSENSUS POINTS (All perspectives agreed)

1. **Ensemble approach is validated** — combining diverse predictors beats individuals
2. **Acquiescence bias is the #1 known error source** — quantified, systematic, correctable
3. **Deliberation value is conditional on question type** — not universally good or bad
4. **External benchmarking is non-negotiable** — ForecastBench before claims
5. **Single-model correlation limits effective ensemble diversity** — 30 Claude ≠ 30 independent predictors

## 5 OPEN QUESTIONS (No perspective could answer)

1. Does multi-agent debate improve probabilistic forecasting? (tested on math/logic, not forecasting)
2. Do rich synthetic personas outperform simple role prompts specifically for forecasting?
3. What is the actual effective ensemble size of 30 Claude instances with different personas?
4. Does calibration memory change archetype reasoning behavior at small n?
5. Can OathFish close the superforecaster gap (Brier 0.096), or is there a single-model ceiling?

## 5 RISKS NO PERSPECTIVE SOLVED

1. **Confident false consensus** on systematically biased predictions (paper-debate)
2. **Single-model correlated failures** reducing effective ensemble to 3-5 (paper-ensemble)
3. **Competence boundary blindness** producing noise on out-of-domain questions (paper-forecast)
4. **Calibration-persona overfitting** loop degrading generalization (paper-persona)
5. **Resolution latency** starving calibration for 6-12 months (paper-calibration)

---

## FALSIFIABLE PREDICTIONS (Scoreboard for Future Validation)

| Agent | Prediction | Confidence | Falsification Criteria |
|-------|-----------|------------|----------------------|
| paper-forecast | Brier 0.108-0.135 on 100+ ForecastBench questions | 65% | Score outside this range on first submission |
| paper-ensemble | 55-60% positive-prediction rate in raw output | 75% | Rate outside range on first 5 runs |
| paper-ensemble | Deliberation helps combination Qs, hurts simple binaries | 55% | A/B test shows no task-type effect |
| paper-debate | 0.03-0.06 Brier improvement on multi-factor questions | 30% (magnitude) | Measured improvement outside range |
| paper-persona | 0.15 lower inter-archetype correlation with Rung 2 grounding | 65% | Correlation difference <0.05 |
| paper-calibration | 2/6 domains show significant directional bias after 5 runs | 65% | 0 or 1 domains significant at p<0.10 |
| paper-calibration | Additive correction improves Brier by 0.01+ | 65% | No measurable improvement |

---

## Architecture Changes Mandated by Research

### v3 Plan Updates Required

1. **DELIBERATE phase restructure**: Arguments-only rounds 1-5, independent predictions round 6 (paper-debate insight)
2. **Question routing**: Classify questions as simple-binary vs multi-factor. Route simple to direct amplification, multi-factor through full deliberation (paper-forecast + paper-ensemble convergence)
3. **Debiasing layer**: Per-domain acquiescence tracking and additive correction from run 3+ (paper-ensemble + paper-calibration convergence)
4. **Competence classifier**: Pre-UNDERSTAND gate that assesses archetype relevance to incoming question (paper-forecast)
5. **Grounding requirement**: Rung 2 minimum — 3-5 public sources per archetype (paper-persona)
6. **Dual metrics**: Always report corrected + uncorrected Brier (paper-persona)
7. **Short-horizon bootstrap questions**: Include fast-resolving questions for early calibration data (paper-calibration)
8. **Holdout set**: 20% of resolved predictions reserved from calibration loop (paper-persona)
9. **Correlation monitoring**: Track effective ensemble diversity per run (paper-ensemble)
10. **Honest positioning**: "Structured ensemble estimates from archetypal stakeholder perspectives" — not "population predictions" (paper-forecast + paper-persona convergence)
