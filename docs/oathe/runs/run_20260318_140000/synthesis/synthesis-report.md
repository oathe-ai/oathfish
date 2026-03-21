# OathFish Architecture: Research Synthesis Report

**Run**: `run_20260318_140000`
**Date**: 2026-03-18
**Source**: 5-Perspective Free-For-All Debate (3 rounds)
**Papers**: 2305.14325, 2402.19379, 2409.19839, 2411.10109, 2602.19520

---

## Executive Summary

Five research perspectives — multi-agent debate, ensemble forecasting, superforecaster benchmarking, persona fidelity, and calibration science — debated OathFish's architecture across 3 adversarial rounds. The debate surfaced 10 hypotheses and 5 recommendations, stress-tested through cross-perspective attack.

**Bottom line**: OathFish's architecture is directionally sound but carries two critical, unvalidated assumptions: (1) that multi-round deliberation adds value over simple aggregation, and (2) that calibration tracking is meaningful at the data volumes OathFish will realistically achieve. Both must be empirically tested before they can be claimed as advantages.

---

## 1. What the Evidence Supports

### 1.1 The ensemble principle is robustly validated
- 12-LLM ensemble matches 925-human crowd (Brier 0.20 vs 0.19, p=0.850) [2402.19379]
- Multi-agent debate outperforms single agents on reasoning tasks by 8-15 percentage points [2305.14325]
- Different initialization prompts (personas) provide additional 3.1pp gains [2305.14325]
- **Verdict**: OathFish's core bet — that combining multiple diverse predictors beats any individual — is well-supported across multiple papers and task types.

### 1.2 The superforecaster gap is real and architecture-dependent
- Expert forecasters significantly outperform best LLMs (Brier 0.096 vs 0.122, p<0.001) [2409.19839]
- The gap is larger than multiple generations of model improvement (0.026 > 0.005 gap between GPT-4 and GPT-4o) [2409.19839]
- No tested ensemble or debate system has closed this gap on the ForecastBench benchmark [2409.19839]
- **Verdict**: There IS a gap to close, and closing it requires more than better base models. But no existing evidence proves that multi-agent deliberation closes it either.

### 1.3 Calibration is structured, not scalar
- 87.3% of calibration variance decomposes into 4 structured components [2602.19520]
- Domain-by-horizon interactions alone explain 26% — the single largest domain-specific factor [2602.19520]
- Domain-agnostic calibration models miss the dominant source of variation [2602.19520]
- **Verdict**: Per-archetype Brier scores are necessary but insufficient. Calibration must be stratified by domain and time horizon.

### 1.4 Persona depth matters more than persona count
- Deep qualitative personas replicate human responses at 85% accuracy (vs 87% human self-replication) [2411.10109]
- Rich backstories reduce racial and ideological bias vs demographic-only descriptions [2411.10109]
- **Verdict**: OathFish's choice of 30 deep archetypes over 1,000 shallow ones is directionally correct, but synthetic personas have unknown fidelity compared to interview-grounded ones.

---

## 2. What the Evidence Challenges

### 2.1 Deliberation may destroy rather than add value [CRITICAL]
**Strength of evidence: HIGH**

The ensemble paper's most important finding: when frontier LLMs (GPT-4, Claude 2) were asked to UPDATE their forecasts after seeing human crowd predictions, the updated forecasts were LESS accurate than simply averaging the machine and human predictions (GPT-4: p=0.011; Claude 2: p=0.001) [2402.19379].

This implies that LLM "reasoning" about how to integrate competing information degrades prediction quality. If this generalizes to OathFish's multi-round deliberation: the DELIBERATE phase (6+ rounds of agents processing each other's positions) could produce WORSE predictions than 30 independent predictions with median aggregation.

**Counterargument** (from debate perspective): The updating experiment tested a single model processing a single scalar, not multi-perspective adversarial debate. Debate produces emergent reasoning from universally-wrong starting points, which averaging cannot do [2305.14325]. The extrapolation is aggressive.

**Resolution**: This is an open empirical question that OathFish MUST test directly. See Recommendation #1.

### 2.2 Calibration tracking is statistically underpowered at OathFish scale [CRITICAL]
**Strength of evidence: HIGH**

The calibration paper's decomposition used 292 million trades across 327,000 contracts. Its model has 72 parameters for 216 analysis cells [2602.19520]. OathFish will have 300-600 data points (30 archetypes x 10-20 runs) before domain/horizon stratification. With 6 domains and 4 time horizons, most (archetype, domain, horizon) cells will have 0-1 observations.

At n=10 runs, the 95% confidence interval on a Brier score is approximately +/- 0.08, meaning you cannot distinguish a Brier 0.17 archetype from a Brier 0.25 archetype — the former is good, the latter is guessing.

**Counterargument** (from persona perspective): Calibration serves dual purposes — statistical analysis AND prompt engineering. Loading "last time I predicted X and was wrong" into an archetype's memory changes its reasoning regardless of statistical significance [2411.10109 framework].

**Resolution**: Reframe calibration as directional bias tracking (did this archetype predict too high or too low?) rather than precision scoring. Directional tracking is meaningful at much smaller sample sizes. See Recommendation #5.

### 2.3 Acquiescence bias will infect all archetypes [IMPORTANT]
**Strength of evidence: HIGH**

LLMs predict positive outcomes 57% of the time even when only 45% of events resolve positively [2402.19379]. This is a systematic, cross-model bias. All 30 Claude-powered archetypes will share it. Multi-round deliberation may amplify it through social proof (agents seeing other agents' optimistic predictions and adjusting upward).

**Resolution**: Track per-domain acquiescence rates from run 1. Implement explicit debiasing in archetype prompts ("your historical positive-prediction rate is X%; the domain base rate is Y%"). See Recommendation #5.

### 2.4 Single-model ensembles have correlated errors [IMPORTANT]
**Strength of evidence: MODERATE**

The ensemble paper's 12-model ensemble worked because different models have DIFFERENT biases that partially cancel [2402.19379]. OathFish's 30 archetypes are all Claude instances. They share training data, RLHF objectives, and systematic biases. The "wisdom of crowds" effect requires independence — and 30 instances of Claude are not independent predictors in the statistical sense.

**Counterargument**: Different system prompts and persona framings DO produce measurably different outputs [2305.14325]. The archetypes are not identical even if the base model is.

**Resolution**: Persona diversity provides SOME independence but less than model diversity. OathFish should measure effective ensemble diversity (correlation between archetype predictions) and flag when it falls below useful levels.

### 2.5 Synthetic personas have unknown fidelity for novel predictions [IMPORTANT]
**Strength of evidence: MODERATE**

The persona paper's 85% accuracy was achieved with personas built from REAL interviews, tested on the SAME types of questions used to build the personas [2411.10109]. OathFish generates synthetic personas from topic analysis and asks them to predict novel scenarios. There is no evidence that synthetic personas achieve comparable fidelity, or that any personas generalize to novel prediction domains.

**Resolution**: Where possible, ground archetype personas in real data (published interviews, public statements, known decision frameworks). Track per-archetype prediction accuracy to empirically measure which personas provide forecasting value.

---

## 3. Ranked Recommendations

Ordered by debate survival score (evidence quality + OathFish relevance + novelty + adversarial robustness).

### Recommendation #1: A/B Test Deliberation vs Baseline Aggregation [Score: 35/40]
**Source**: Ensemble Forecasting perspective, survived all adversarial challenges

**What**: Run Mass Amplification BEFORE deliberation (as an independent baseline) AND after deliberation. Compare: does deliberation improve or degrade accuracy against simple median aggregation of independent predictions?

**Why**: This is the single most important empirical question for OathFish's architecture. The strongest positive evidence (debate improves reasoning [2305.14325]) comes from math/logic tasks, not forecasting. The strongest negative evidence (LLM updating degrades accuracy vs simple averaging [2402.19379]) comes from forecasting. Neither settles the question for OathFish's specific design. The test is cheap to run and definitively answers whether the DELIBERATE phase adds value.

**Implementation**:
1. Before DELIBERATE, run 1,500 stateless amplification calls (baseline)
2. Run DELIBERATE as designed
3. After DELIBERATE, run 1,500 stateless amplification calls (deliberation-informed)
4. Report both predictions in every output
5. Track comparative accuracy across runs
6. If baseline consistently beats deliberation after 5+ runs, simplify the architecture

**Evidence base**: Brier 0.20 ensemble vs degraded updated forecasts (p=0.011 for GPT-4, p=0.001 for Claude 2) [2402.19379]; debate improvements of 8-15pp on reasoning tasks [2305.14325]; no debate system in top 10 of ForecastBench [2409.19839].

---

### Recommendation #2: Structured Calibration Matrix from Run 1 [Score: 35/40]
**Source**: Calibration Science perspective, survived all adversarial challenges

**What**: Track predictions in a structured (archetype, domain, horizon) matrix from the first run. Don't wait for statistical significance to begin bias correction. Track three simple metrics: (1) directional bias per archetype per domain, (2) confidence calibration per archetype per horizon, (3) acquiescence rate per domain.

**Why**: Full variance decomposition requires hundreds of data points per cell [2602.19520]. But directional bias tracking (does this archetype predict too high or too low in this domain?) is meaningful at n=3-5. The calibration paper shows that domain-by-horizon interaction is the largest component (26% of variance) — so the matrix structure matters more than the precision of individual estimates.

**Implementation**:
1. Define a taxonomy: 6 domains x 4 horizons x 30 archetypes = 720-cell matrix
2. Record every prediction with (archetype, domain, horizon, probability, outcome) tuple
3. After n >= 3 observations per cell, compute directional bias (mean signed error)
4. Apply simple additive correction to predictions in that cell
5. After n >= 10 per cell, switch to logistic recalibration using slope estimation
6. Track acquiescence rate (% of positive predictions) per domain — flag if it significantly deviates from base rates

**Evidence base**: 4-component decomposition explains 87.3% of calibration variance [2602.19520]; LLMs predict positive 57% vs 45% resolution rate [2402.19379]; domain-agnostic calibration misses largest variance source [2602.19520].

---

### Recommendation #3: Benchmark Against ForecastBench [Score: 34/40]
**Source**: Superforecasters perspective, uncontested in adversarial round

**What**: Submit OathFish predictions to the ForecastBench public leaderboard before making any claims about prediction accuracy.

**Why**: ForecastBench provides the only apples-to-apples comparison between OathFish, individual LLMs, LLM ensembles, the general public, and superforecasters [2409.19839]. The benchmark uses exclusively unresolved questions (no data leakage), covers multiple domains and time horizons, and has established baselines. Without this benchmark, claims about OathFish's accuracy are untestable marketing.

**Implementation**:
1. Run OathFish on the current ForecastBench question set (1,000 questions)
2. Submit predictions to the public leaderboard
3. Track score evolution across question set updates
4. Target: Brier < 0.10 (superforecaster range) is genuinely novel; 0.10-0.12 is competitive; 0.12+ is matching existing LLM baselines

**Key threshold**: Superforecaster median Brier = 0.096; best individual LLM = 0.122; general public = 0.121. OathFish must beat 0.122 to demonstrate that multi-agent architecture provides value beyond a single well-prompted model.

**Evidence base**: Superforecasters 0.096, best LLM 0.122 (p<0.001 gap) [2409.19839]; LLM ensemble 0.20 matching human crowd [2402.19379].

---

### Recommendation #4: Encode Superforecaster Methodology in Every Archetype [Score: 34/40]
**Source**: Persona Fidelity perspective, novel cross-paper synthesis

**What**: Restructure archetype design along two orthogonal dimensions: (1) INFORMATION PERSPECTIVE (stakeholder-specific domain knowledge) and (2) REASONING METHODOLOGY (uniformly superforecaster-grade). Every archetype should use Tetlock's decomposition, base-rate anchoring, and incremental updating, while maintaining their unique information perspective.

**Why**: The superforecaster gap (Brier 0.096 vs 0.122) is the primary target [2409.19839]. Superforecasters aren't smarter — they use specific cognitive habits that can be encoded in prompts. Persona research shows that behavioral patterns transfer from humans to LLM agents with high fidelity [2411.10109]. Current OathFish design gives archetypes stakeholder identity but only partially encodes forecasting methodology.

**Implementation**:
1. Every archetype prompt includes a mandatory forecasting protocol:
   - State the base rate before any prediction
   - Decompose the question into at least 3 sub-components
   - Assign probabilities to each sub-component independently
   - List the top 3 uncertainties with probability ranges
   - State falsification criteria
   - Reference calibration history if available
2. Stakeholder-specific framing provides the INPUTS to this protocol (what information the archetype has access to, what scenarios concern them)
3. The protocol provides the REASONING METHOD (how they process that information)
4. Track which archetypes' unique perspectives actually improve ensemble accuracy vs which are redundant

**Evidence base**: Superforecaster habits from Tetlock's research; persona behavioral fidelity at 85% [2411.10109]; superforecaster gap at p<0.001 [2409.19839]; different initialization prompts improve accuracy by 3.1pp [2305.14325].

---

### Recommendation #5: Diversity-Preserving Deliberation [Score: 33/40]
**Source**: Multi-Agent Debate perspective, novel cross-paper synthesis

**What**: Replace the convergence-optimizing design (stance delta < 0.1) with a diversity-preserving design that tracks position diversity across rounds and treats premature consensus as a failure mode.

**Why**: The debate paper shows that "stubborn" prompts (which maintain disagreement longer) produce BETTER final answers than "agreeable" prompts [2305.14325]. Acquiescence bias will push all Claude-powered archetypes toward agreement [2402.19379]. OathFish currently treats convergence as success. It should treat early convergence as a warning sign of groupthink or acquiescence.

**Implementation**:
1. Compute a DIVERSITY INDEX at each round: standard deviation of archetype predictions
2. Track diversity trajectory: it should DECREASE across rounds but not collapse early
3. If diversity drops below threshold before the penultimate round, trigger:
   - Inject a contrarian scenario ("What if the opposite happens?")
   - Activate a "red team" archetype subset that argues against emerging consensus
   - Flag the prediction as potentially acquiescence-contaminated
4. The final convergence check (round 6+) remains, but it should be LATE convergence after sustained disagreement, not EARLY convergence from agreement
5. Report diversity trajectory in synthesis output as a prediction quality indicator

**Evidence base**: Stubborn prompts produce better results despite slower convergence [2305.14325]; acquiescence bias at 57% [2402.19379]; RLHF models are "too agreeable" [2305.14325]; false consensus with high confidence on wrong answers [2305.14325].

---

## 4. Architecture Risk Matrix

| Risk | Severity | Probability | Mitigation | Detection |
|------|----------|-------------|------------|-----------|
| Deliberation destroys value vs simple aggregation | CRITICAL | MODERATE (40%) | Rec #1: A/B test every run | Compare pre/post deliberation accuracy |
| Acquiescence bias amplified through social dynamics | HIGH | HIGH (70%) | Rec #5: diversity tracking; per-domain acquiescence monitoring | Track positive-prediction rate vs base rate per domain |
| Calibration tracking produces noise, not signal | HIGH | HIGH (60%) | Rec #2: directional bias tracking at n>=3, not formal decomposition | Compare bias-corrected vs uncorrected accuracy |
| Single-model ensemble lacks independence | HIGH | MODERATE (50%) | Measure inter-archetype prediction correlation; consider multi-model archetypes | If correlation > 0.8, effective ensemble size is << 30 |
| Synthetic personas lack fidelity for forecasting | MODERATE | MODERATE (40%) | Ground personas in real data where possible; track per-archetype accuracy | Drop archetypes that consistently underperform median |
| 30-agent context overflow degrades deliberation quality | MODERATE | MODERATE (30%) | Summarization between rounds (validated in 2305.14325); tiered model routing | Track reasoning quality across rounds; late-round reasoning should reference early-round arguments |
| Convergence on confident wrong predictions | HIGH | MODERATE (50%) | Rec #5: diversity preservation; explicit uncertainty tracking | Flag predictions where confidence > 0.9 but diversity was low throughout |

---

## 5. Novel Cross-Paper Connections

### Connection 1: Acquiescence x Domain = Structured Prediction Error
P2's acquiescence bias (57% positive predictions) + P5's domain-specific calibration patterns = OathFish will have domain-dependent acquiescence. Technology/adoption questions ("Will X succeed?") will be more afflicted than regulatory/restrictive questions ("Will Y be banned?"). This is testable and correctable.

### Connection 2: Debate x Combination Questions = Highest-Value Application
P1's finding that debate produces emergent reasoning from wrong starting points + P3's finding that the superforecaster gap is widest on combination questions = OathFish's deliberation may provide the most value on questions requiring joint-probability reasoning about multiple interacting factors. This is precisely the kind of question OathFish is designed for (stakeholder interactions, cascade effects).

### Connection 3: Persona Depth x Superforecaster Methodology = Archetype 2.0
P4's validated persona fidelity + P3's identified superforecaster gap + Tetlock's methodology research = a new archetype design principle. Don't simulate how stakeholders ACTUALLY think. Simulate how superforecasters would think IF THEY HAD that stakeholder's information and perspective. This separates domain knowledge (persona-provided) from reasoning quality (methodology-provided).

### Connection 4: Calibration as Prompt Engineering, Not Just Statistics
P5's rigorous decomposition framework + P4's behavioral transfer finding + P5-H2's scale critique = calibration serves two functions in OathFish. As STATISTICS, it's underpowered. As PROMPT ENGINEERING (loading calibration history into archetype memory to change reasoning behavior), it may be valuable regardless of statistical power. The behavioral effect of knowing "I was wrong last time" doesn't require a statistically significant sample.

### Connection 5: Simple Averaging as the Benchmark That Must Be Beat
P2's finding that simple averaging beats LLM updating + P3's finding that no ensemble has beaten superforecasters + P1's finding that debate beats averaging on reasoning tasks = OathFish's architecture is only justified if it can beat the dumbest possible baseline (median of independent predictions). This is the minimum viability threshold, not an aspiration. Every additional architectural complexity (deliberation, calibration, memory) must demonstrate value ABOVE this baseline.

---

## 6. Implementation Priority

### Phase 1: Foundational (Before first production run)
1. Implement A/B test infrastructure (Rec #1) — baseline aggregation vs deliberation
2. Implement structured prediction tracking matrix (Rec #2) — (archetype, domain, horizon) tuples
3. Encode superforecaster methodology in all archetype prompts (Rec #4)
4. Implement diversity index tracking across deliberation rounds (Rec #5)

### Phase 2: Validation (Runs 1-5)
5. Submit to ForecastBench (Rec #3) — establish baseline accuracy
6. Measure effective ensemble diversity (inter-archetype correlation)
7. Track acquiescence rates per domain
8. Compare deliberation vs baseline on each run

### Phase 3: Optimization (Runs 5-20)
9. Begin directional bias corrections per (archetype, domain, horizon) cell
10. Drop underperforming archetypes, strengthen strong ones
11. Tune diversity preservation thresholds based on empirical data
12. If deliberation consistently underperforms, simplify architecture

### Phase 4: Maturity (Runs 20+)
13. Formal calibration decomposition becomes statistically viable
14. Persistent archetype memory should show measurable accuracy improvement
15. The "time moat" becomes real — if and only if calibration tracking works

---

## 7. Open Questions for Future Research Rounds

1. **Does debate help forecasting?** The debate paper tested math/logic; the ensemble paper tested single-model updating. Neither tested multi-agent debate on forecasting questions. OathFish will be among the first systems to generate this evidence.

2. **What is the effective ensemble diversity of 30 Claude instances with different personas?** If the inter-archetype prediction correlation is > 0.9, the effective ensemble size is ~3, not 30.

3. **Does calibration memory change archetype behavior?** Even if the statistical signal is weak, does loading "you were wrong last time" into an agent's context actually produce better predictions? This is a prompt engineering question, not a statistics question.

4. **Where does deliberation help most?** Connection #2 predicts that deliberation adds the most value on combination/interaction questions. If true, OathFish should emphasize deliberation for multi-factor predictions and skip it for simple binary questions.

5. **Can synthetic personas approach interview-grounded persona fidelity?** If OathFish's archetypes are grounded in real interview data (VC podcasts, regulatory hearing transcripts, founder AMAs), does this meaningfully improve prediction accuracy vs purely synthetic personas?

---

## Appendix: Paper Reference Key

| ID | Paper | Key Finding for OathFish |
|----|-------|------------------------|
| 2305.14325 | Du et al., "Improving Factuality and Reasoning in LLMs through Multiagent Debate" | Debate improves reasoning 8-15pp; different personas help; context length is the constraint; "stubborn" prompts work better |
| 2402.19379 | Schoenegger et al., "Wisdom of the Silicon Crowd" | 12-LLM ensemble matches human crowd; acquiescence bias at 57%; simple averaging beats LLM updating; poor individual calibration |
| 2409.19839 | Karger et al., "ForecastBench" | Superforecasters beat best LLMs (p<0.001); gap largest on combination questions; news retrieval doesn't help; the benchmark to beat |
| 2411.10109 | Persona Fidelity paper | 85% behavioral replication with deep personas; depth > count; reduces bias vs demographics-only |
| 2602.19520 | Calibration Science paper | 87.3% variance explained by 4 structured components; domain-by-horizon is 26%; domain-agnostic calibration misses dominant variance |
