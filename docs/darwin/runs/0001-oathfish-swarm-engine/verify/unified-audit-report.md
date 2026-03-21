# OATHFISH DARWIN VERIFICATION AUDIT: UNIFIED GAP REPORT

*Produced: 2026-03-19*
*Method: 8-agent team audit (oathfish-audit) with cross-referencing via SendMessage*
*Scope: 950 tests analyzed, 156 session subagents forensically traced, all DARWIN artifacts reviewed*

---

## HEADLINE FINDINGS

### 1. The Teams Paradox

OathFish was conceived as a showcase for Agent Teams (TeamCreate/SendMessage peer deliberation). Platform constraints (subagents can't spawn subagents, Teams untested at 30 members) forced a pivot to hub-and-spoke subagent architecture. The DARWIN build process that created OathFish used a **hybrid model**: 5 TeamCreate calls, 43 SendMessages, and 75 Agent calls. Independent subagents for structured DARWIN phases (discover, explore, plan, critique, revise, verify) + Teams for collaborative phases (research debate, parallel execution, adversarial audit). The build had architectural freedom the product doesn't.

The research debate ran 5 agents via Teams in 23 minutes, suggesting the scaling concern that forced the pivot to subagents may have been overly conservative.

### 2. Structurally Complete, Never Actually Run

All files exist. 940 tests pass. But **10 of 14 Success Criteria have never been tested at runtime.** No OathFish prediction has ever been executed end-to-end. The system built a 56-point runtime evaluator (evaluate skill) but never had a runtime to evaluate.

### 3. Verification Reports Are Stale

Report-C claims 261/263 pass. **Actual: 253/263 (10 failures).** Implementation drifted after verification -- MCP config moved from `.mcp.json` to `plugin.json`, author field changed format. The verification report was never re-run.

---

## GAPS BY SEVERITY

### CRITICAL (blocks runtime)

| # | Gap | Source | Impact |
|---|-----|--------|--------|
| G-01 | **SKIP_DELIBERATE transition missing** | worker-a + worker-b + feature | Worker B's competence classifier recommends SKIP_DELIBERATE but Worker A's state machine rejects the transition. Research-mandated question routing is dead code. |
| G-02 | **V-C01 synthesize nesting violation** | worker-c | `context:fork` + `agent:report-analyst` body text still references spawning. Partially fixed but tests still fail. |
| G-03 | **No end-to-end runtime test** | verification + feature | 10/14 SCs untested. Plugin loading, 30-subagent spawning, cross-round deliberation, amplification SDK, calibration feedback -- all unverified. |

### HIGH (correctness risk)

| # | Gap | Source | Impact |
|---|-----|--------|--------|
| G-04 | **C-33 enforcement is probabilistic, not deterministic** | worker-c | PreToolUse hook only checks coordinator→archetype relay, not archetype output. SC-04 ("deterministic enforcement") is overstated. |
| G-05 | **Debiasing applied globally, not per-domain** | worker-b | `amplify_aggregate` applies correction to `avg_confidence` globally instead of per-prediction per-domain. Loses domain-level granularity. |
| G-06 | **10 stale test failures** | verification + worker-c | Implementation drifted (plugin.json structure, .mcp.json emptied). Verification report-C is no longer accurate. |
| G-07 | **30 MCP tools, not 27** | feature + worker-b | 3 undocumented calibration tools added. Server instructions still say "27 tools." |
| G-08 | **Worker C/D tests are static analysis, not behavioral** | verification + worker-d | `assert "asyncio.Semaphore" in source_code` verifies a string exists, not that concurrency limiting works. 212 Worker D tests are regex/AST, zero runtime. |

### MEDIUM (quality/completeness)

| # | Gap | Source | Impact |
|---|-----|--------|--------|
| G-09 | **Bootstrap question sourcing unoperationalized** | worker-b + feature | `is_bootstrap` field exists but no mechanism to generate/import bootstrap questions. Cold-start mitigation is structural but not functional. |
| G-10 | **Topic-customized archetype generation is design-only** | worker-d | Tasks C.1-C.3 (generation prompt, web search, persona assembly) exist only in the plan. Only 4 structural archetypes were actually created. |
| G-11 | **Coalition detection is hollow** | feature | Data models include coalition fields but no engine populates them. SC-10 depends on this. |
| G-12 | **Empty learnings.md** | verification + session | Zero learnings captured from a 25-hour, 156-subagent build. Operational lessons lost. |
| G-13 | **Feature-request.md not updated** | feature | C-04 still says "Claude Teams." C-21 still says "--resume." Neither reflects the consolidated spec corrections. |
| G-14 | **No shared infrastructure with oathe-research** | research | Both plugins implement debate, state machines, persistence independently. No shared libraries despite parallel patterns. |
| G-15 | **ForecastBench is export-only** | research + worker-b | `forecastbench.py` exports JSON but has no submission pipeline or result tracking. |
| G-16 | **Calibration persistence not atomic** | feature | `calibration_engine.py` uses plain `json.dump()`, not `atomic_write_json()`. Violates C-15/C-23. |

### LOW

| # | Gap | Source | Impact |
|---|-----|--------|--------|
| G-17 | Persona variation aliasing (edu_idx = axis1_idx = n%5) | worker-d | Reduces diversity but 50 unique strings still produced. |
| G-18 | `asyncio.get_event_loop()` deprecation | worker-a | All tests use deprecated pattern. Should use `asyncio.run()`. |
| G-19 | HoldoutReport.gap_trend never computed | worker-b | Model field exists but no code populates it. |
| G-20 | Structural archetypes lack YAML frontmatter | worker-c | Won't auto-discover as Claude Code agents. Must be injected via prompts. |

---

## WHAT WENT WRONG

1. **The final mile was rushed.** Phase 5 (final audits) ran at 3:35 AM in 24 minutes. No end-to-end runtime test was attempted. The system was verified statically but never actually run as a plugin.

2. **Cross-worker integration was assumed, not tested.** Worker B built a classifier that outputs SKIP_DELIBERATE. Worker A built a state machine that doesn't accept it. Both passed their own tests. The gap lives at the seam.

3. **Implementation drifted after verification.** Code changed (plugin.json restructured, .mcp.json emptied) but verification reports weren't re-run. This creates a false confidence picture.

4. **DARWIN's structured phases didn't use Teams.** 156 subagents in hub-and-spoke for discover/explore/plan phases, no team coordination. Workers A-D couldn't message each other during execution. The adversarial prosecutor/defender verification is naturally a team debate but was implemented as isolated subagent spawning.

5. **Learnings weren't captured.** A 25-hour build with 156 subagents and multiple retries produced zero documented learnings.

---

## WHAT WAS DONE WELL

1. **Research-driven development is genuinely impressive.** oathe-research was used as a meta-tool to stress-test OathFish's own architecture before implementation. 5 papers debated for 3 rounds, producing 10 constraints and 5 novel cross-paper insights no individual paper contains.

2. **Spec audit resolution was thorough.** All 3 CRITICAL contradictions and 2 blocking ambiguities were resolved with evidence-based architectural changes (position type split, baseline timing, digest-over-resume).

3. **Skeptic-defense cycles were rigorous.** Across all 4 workers: ~45 issues identified, ~40 resolved with code evidence, contests were well-reasoned (SK-08 MAX_MCP_OUTPUT_TOKENS defense caught the skeptic's error). The critique phase genuinely improved the architecture.

4. **Worker D's structural archetypes are production-ready.** Rich, differentiated, research-grounded epistemic lenses with distinct analytical frameworks and stubbornness domains. The archetype-reasoning skill as single source of truth prevents methodology drift.

5. **Worker B's statistical methodology is sound.** Tiered correction schedule, t-distribution (not normal CDF), holdout validation, acquiescence tracking. The mathematical rigor is real.

6. **The calibration engine is sophisticated.** 1084 lines of pure Python implementing a graduated bias correction system that honestly acknowledges its small-n limitations.

7. **C-33 (arguments-only) enforcement is multilayered.** Three layers plus a data model split. Not fully deterministic (G-04) but meaningfully defense-in-depth.

8. **Honest self-assessment throughout.** The system calls itself "structured ensemble estimates," not predictions. The integration plan honestly shows 10/14 SCs untested. Spec deviations are documented with rationale.

---

## WHAT COULD BE BETTER

1. **DARWIN should use Agent Teams for its own structured phases.** Workers A-D should be team members using SendMessage, not isolated subagents. The prosecutor/defender verification is naturally a team debate.

2. **Integration tests at the seam.** Cross-worker contract tests would have caught G-01 (SKIP_DELIBERATE), G-05 (global debiasing), and G-07 (tool count mismatch).

3. **Re-run verification after any code change.** A CI-like pipeline that re-runs the full test suite would prevent stale reports (G-06).

4. **Runtime integration sprint before declaring "verified."** The integration plan correctly identifies this as Sprint 2 but it should be part of Sprint 1.

5. **Capture learnings continuously.** The learnings.md should be populated during execution, not after. Each executor/verifier agent should append findings.

6. **Share MCP infrastructure between oathe and oathfish.** Atomic persistence, state machines, debate protocols -- these patterns are reimplemented independently in each plugin.

7. **Revisit the Teams pivot.** The research debate ran 5 agents via Teams in 23 minutes successfully. Testing Teams at 10-15 archetypes (not 30) might be feasible and would enable the peer-to-peer deliberation and coalition formation the original vision described.

---

## SCORECARD

| Dimension | Rating |
|-----------|--------|
| Vision faithfulness | 9/10 |
| Spec audit resolution | 10/10 |
| Implementation completeness | 7/10 |
| Research integration | 9/10 |
| Test coverage (behavioral) | 6/10 |
| Test coverage (static) | 9/10 |
| Cross-worker integration | 5/10 |
| Verification accuracy | 6/10 |
| Runtime readiness | 2/10 |

---

## WORKER ASSESSMENTS

| Worker | Scope | Tests | Pass Rate | Verdict |
|--------|-------|-------|-----------|---------|
| A (MCP Core) | 6 engines, 21 tools, models, persistence | 226 | 100% | STRONG -- real behavioral tests, sound architecture |
| B (Calibration) | Calibration engine, domain classifier, competence classifier, ForecastBench | 130 | 100% | STRONG -- rigorous statistical methodology, all skeptic issues resolved |
| C (Orchestration) | Plugin scaffold, agents, skills, commands, hooks | 253 | 96.2% (10 fail) | GOOD -- strongest skeptic cycle, but implementation drifted post-verify |
| D (Domain Logic) | Structural archetypes, amplification SDK, superforecaster methodology | 212 | 100% | STRONG -- highest quality output, but tests are static analysis only |

---

## APPENDIX: CROSS-TEAM COORDINATION EVIDENCE

This audit was performed by an 8-agent team using Agent Teams (TeamCreate/SendMessage). Key cross-references that surfaced findings no single agent would have caught:

1. **feature-analyst ↔ worker-a-analyst**: Confirmed SKIP_DELIBERATE is a cross-worker integration gap (classifier outputs recommendation state machine rejects)
2. **worker-c-analyst → verification-analyst**: C-33 enforcement gaps and stale test count cross-validated
3. **verification-analyst → feature-analyst**: SC coverage gaps aligned with feature-request audit
4. **feature-analyst ← session-analyst**: Teams paradox nuanced -- build DID use 5 Teams, not zero
5. **research-analyst → worker-c-analyst**: Teams pivot rationale cross-referenced with architectural constraints
6. **worker-b-analyst → feature-analyst**: Spec deviations (30 tools not 27, tiered thresholds) surfaced for gap report
7. **session-analyst → verification-analyst**: Error analysis and wasted effort from forensic logs
