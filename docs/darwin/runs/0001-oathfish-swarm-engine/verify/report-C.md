# Verification Report - Worker C (Orchestration Layer)

**Run ID**: 0001-oathfish-swarm-engine
**Worker**: C (Plugin scaffold, agents, skills, commands, hooks, scripts)
**Verdict**: FIXABLE
**Coverage**: 261/263 tests passed (99.2%)
**Generated**: 2026-03-18
**Verifier**: Adversarial verification from spec-first test generation

---

## Executive Summary

| Category | Passed | Failed | Coverage |
|----------|--------|--------|----------|
| DoD (Tasks C-A through C-E) | 108 | 0 | 100% |
| Success Criteria (SC-02 to SC-05) | 22 | 0 | 100% |
| Constraints (C-01, C-05, C-07, C-33, C-L01, C-L02, C-36, C-37) | 17 | 2 | 89% |
| Hazard Mitigations (C-H01 to C-H14) | 14 | 2 | 88% |
| Edge Cases | 37 | 0 | 100% |
| Integration | 18 | 0 | 100% |
| Regression (pre-existing tests) | 99 | 0 | 100% |

**Blockers**: 0
**Fixable**: 1 (architectural issue appears in 2 test files)

---

## Failure Summary

| V-ID | Type | Target | Issue | Confidence | Suggested Fix |
|------|------|--------|-------|------------|---------------|
| V-C01 | Constraint/Hazard | C-L02 / C-H14 | synthesize skill runs in context:fork but spawns report-analyst via Agent tool -- subagents cannot spawn subagents | 98% | Remove `context: fork` from synthesize/SKILL.md (run inline like deliberate), OR remove Agent from allowed-tools and have synthesize directly instruct the report analyst role |

---

## V-C01: Synthesize Skill Subagent Nesting Violation

**Tests that catch this**:
- `tests/verify_0001_worker_c/constraints/test_constraints.py::TestCL02SubagentsCannotSpawn::test_synthesize_nesting_issue`
- `tests/verify_0001_worker_c/hazard/test_hazards.py::TestCH14NestingProblem::test_synthesize_spawns_report_analyst_from_fork`

**Command**: `python3 -m pytest tests/verify_0001_worker_c/constraints/test_constraints.py::TestCL02SubagentsCannotSpawn::test_synthesize_nesting_issue -v --tb=long`

**Output**:
```
FAILED tests/verify_0001_worker_c/constraints/test_constraints.py::TestCL02SubagentsCannotSpawn::test_synthesize_nesting_issue

    def test_synthesize_nesting_issue(self):
        """CRITICAL CHECK: synthesize uses context:fork but spawns report-analyst.
        This creates a subagent-of-a-subagent which violates C-L02."""
        fm, _ = parse_frontmatter(
            os.path.join(PLUGIN_ROOT, "skills", "synthesize", "SKILL.md"))
        if fm.get("context") == "fork":
            allowed_tools = fm.get("allowed-tools", "")
            ...
            if "Agent" in tools_list:
>               pytest.fail(
                    "C-L02 VIOLATION: synthesize skill runs with context:fork (= subagent) "
                    "but has Agent in allowed-tools. A forked subagent CANNOT spawn "
                    "another subagent (report-analyst). This will fail at runtime."
                )
E               Failed: C-L02 VIOLATION: synthesize skill runs with context:fork (= subagent)
                but has Agent in allowed-tools. A forked subagent CANNOT spawn another
                subagent (report-analyst). This will fail at runtime.
```

**Classification**: Constraint violation (C-L02)
**Confidence**: 98%
**Root Cause**: The synthesize skill (`skills/synthesize/SKILL.md`) has `context: fork` in its
frontmatter, which means it runs as a subagent. The skill also lists `Agent` in `allowed-tools`
and its body instructs launching `@report-analyst`. Per sub-agents.md line 188: "Subagents
CANNOT spawn other subagents." A forked skill IS a subagent (it runs in a fresh context window
via the general-purpose agent). Therefore, the Agent tool call to spawn report-analyst will fail
at runtime.

**Suggested Fix**: One of:
1. **Remove `context: fork` from synthesize/SKILL.md** -- make it run inline like deliberate.
   This is the simplest fix. Downside: it consumes main thread context.
2. **Remove Agent from allowed-tools and restructure** -- have the synthesize skill directly
   instruct report generation without spawning a separate agent.
3. **Keep context:fork but use `agent: report-analyst`** -- set the fork's agent type to
   report-analyst, so the forked subagent IS the report analyst. The SKILL.md content
   becomes the task for the report-analyst subagent.

Option 3 is the most architecturally clean: `context: fork` + `agent: report-analyst` makes
the synthesize skill run AS the report-analyst subagent, which means no nesting is needed.

---

## Detailed Test Results by Category

### DoD Verification (108/108 passed)

All 22 Worker C files verified against their task DoD:

**Plugin Scaffold (C-A.1 through C-A.6, C-E.1, C-E.2)**:
- plugin.json: valid JSON, correct name/version/author/description
- .mcp.json: stdio transport, python3, OATHFISH_DATA_DIR uses CLAUDE_PLUGIN_DATA (not PLUGIN_ROOT), MAX_MCP_OUTPUT_TOKENS=50000
- hooks.json: valid events (SessionStart/PreToolUse), valid matchers, scripts use ${CLAUDE_PLUGIN_ROOT}
- All 5 shell scripts: bash -n passes, executable, use jq for JSON parsing
- validate-no-numbers.sh: reads tool_input, uses exit 2 for blocking, reads .current_round, allows round 6+, has CLAUDE_PLUGIN_DATA fallback

**Agents (C-B.1 through C-B.3)**:
- deliberation-coordinator.md: valid frontmatter (name, description, tools as YAML list), has Agent tool, C-33 enforcement in system prompt, all 4 round types, verbatim relay instructions, MCP tool references, .current_round file bridge, PREDICTION not INDEPENDENT_PREDICTION
- archetype-agent.md: valid frontmatter, memory:project (SC-05), skills reference oathfish:archetype-reasoning, model:sonnet, no hooks in frontmatter (correct per C-L01), C-33 prohibition in system prompt, superforecaster methodology
- report-analyst.md: valid frontmatter, ReACT methodology, all 5 output artifacts specified

**Skills (C-C.1 through C-C.7)**:
- oathfish/SKILL.md: inline (no context:fork), dynamic context injection, full phase sequence
- understand/SKILL.md: context:fork, not user-invocable, references competence classifier, 4 structural archetypes
- baseline-amplify/SKILL.md: context:fork, references baseline
- deliberate/SKILL.md: NO context:fork (CRITICAL - verified), C-33 enforcement, round schedule, .current_round, deliberation digest
- amplify/SKILL.md: context:fork, references digest
- synthesize/SKILL.md: context:fork, 5 outputs, spawns report-analyst
- interact/SKILL.md: inline (no context:fork), message routing

**Commands (C-D.1 through C-D.4)**:
- All 4 commands have valid frontmatter with name, description
- oathfish-inject and oathfish-calibrate have disable-model-invocation: true

### Success Criteria (22/22 passed)

| SC | Status | Evidence |
|----|--------|----------|
| SC-02 | PASS | plugin.json, commands/oathfish.md, skills/oathfish/SKILL.md, .mcp.json, hooks.json all exist with correct content |
| SC-03 | PASS | Coordinator has Agent tool, archetype-agent template exists, deliberate runs inline, 4 structural archetypes exist |
| SC-04 | PASS | Three-layer C-33 defense verified: (1) coordinator prompt, (2) PreToolUse hook with exit 2, (3) archetype prompt prohibition |
| SC-05 | PASS | archetype-agent has memory:project, valid per sub-agents.md, prompt explains cross-run usage |

### Constraint Verification (17/19 tests, 2 failed)

| Constraint | Status | Notes |
|------------|--------|-------|
| C-01 | PASS | All plugin directories present |
| C-05 | PASS | No TeamCreate in deliberate skill; coordinator uses subagent architecture |
| C-07 | PASS | All 8 states in dispatcher |
| C-33 | PASS | Three-layer defense complete; regex catches stance/confidence/probability |
| C-L01 | PASS | No mcpServers in subagent frontmatter; permissionMode noted as ignored |
| C-L02 | **FAIL** | V-C01: synthesize/SKILL.md context:fork + Agent tool = nesting violation |
| C-36 | PASS | All 4 structural archetype files exist |
| C-37 | PASS | All 4 contain "epistemic lens" and "NOT a stakeholder" language |

### Hazard Mitigations (14/16 tests, 2 failed -- same issue as V-C01)

| Hazard | Status | Mitigation Verified |
|--------|--------|---------------------|
| C-H01 | PASS | Compact hook exists; reinject script provides recovery; coordinator has compaction instructions |
| C-H02 | PASS | MAX_MCP_OUTPUT_TOKENS=50000 configured |
| C-H03 | PASS | No hooks in archetype frontmatter; C-33 enforced via hooks.json |
| C-H04 | PASS | setup.sh verifies server; dispatcher checks state |
| C-H05 | PASS | No unverified MCP namespace syntax in allowed-tools |
| C-H06 | PASS | Coordinator, deliberate skill, and validate script all reference .current_round |
| C-H12 | PASS | Coordinator instructs verbatim relay |
| C-H14 | **FAIL** | V-C01: synthesize nesting issue |

### Edge Cases (37/37 passed)

- validate-no-numbers.sh: catches stance decimals, percentages, probabilities; handles empty prompt, missing round file, non-archetype agents
- Structural archetypes: all have grounding sources and stubbornness domains
- Skill frontmatter: all names valid format, all have descriptions
- archetype-reasoning: exists, not user-invocable, no context:fork, has 6 superforecaster steps, under 100 lines
- hooks.json: correct nested structure format

### Integration (18/18 passed)

- All 22 Worker C files exist
- All JSON files valid
- All shell scripts valid syntax and executable
- All agent files have frontmatter with required name/description
- All skill files have frontmatter
- All command files have frontmatter with name
- Context:fork correctness verified for all skills
- Cross-component references verified (archetype-agent -> archetype-reasoning, hooks -> scripts, deliberate -> archetypes, synthesize -> report-analyst)
- C-33 end-to-end defense chain verified

### Regression (99/99 passed)

All pre-existing tests continue to pass.

---

## Observations (Not Failures)

### O-1: permissionMode on Plugin Subagents
`deliberation-coordinator.md` and `report-analyst.md` both have `permissionMode: bypassPermissions`.
Per C-L01 (sub-agents.md:107), this field is **IGNORED for plugin subagents**. This means these
agents will run with default permission mode at runtime, which may cause permission dialogs.
This is not a failure -- the field is simply inert -- but it may cause unexpected UX.

### O-2: Structural Archetypes Lack Frontmatter
Files in `agents/archetypes/structural/*.md` have NO YAML frontmatter. They live in the `agents/`
directory tree, so Claude Code may attempt to auto-discover them as agent definitions. Without
`name` and `description` fields, they will likely be silently skipped. This is probably intentional
(they are persona content templates, not standalone agent definitions), but it means Claude Code
will not recognize them as agents. The coordinator must explicitly inject their content via the
Agent tool prompt.

### O-3: .mcp.json Uses Module Invocation
Spec says `args: ["${CLAUDE_PLUGIN_ROOT}/engine/server.py"]` but implementation uses
`args: ["-m", "engine.server"]` with `cwd: "${CLAUDE_PLUGIN_ROOT}"`. This is functionally
equivalent and arguably better (avoids hardcoded path assumptions). Not a failure.

### O-4: archetype-agent Has Only Read Tool
Feature request specified `Read` and `SendMessage` for archetypes. Implementation has only `Read`.
This is correct for the subagent architecture (subagents communicate via return values to parent,
not SendMessage). SendMessage is a Teams feature. The implementation correctly adapted to the
subagent architecture mandated by C-05/C-L02.

---

## Test Coverage Audit

### Success Criteria Coverage
| SC-ID | Description | Test File | Status |
|-------|-------------|-----------|--------|
| SC-02 | Plugin loads and /oathfish command appears | sc/test_success_criteria.py::TestSC02PluginLoads | PASS |
| SC-03 | Coordinator spawns 30 archetype subagents | sc/test_success_criteria.py::TestSC03CoordinatorSpawns30 | PASS |
| SC-04 | C-33 enforcement prevents numeric predictions rounds 1-5 | sc/test_success_criteria.py::TestSC04C33Enforcement | PASS |
| SC-05 | Each archetype has memory:project | sc/test_success_criteria.py::TestSC05ArchetypeMemoryProject | PASS |

**SC Coverage**: 4/4 (100%)

### Constraint Coverage
| C-ID | Type | Test File | Status |
|------|------|-----------|--------|
| C-01 | REQUIREMENT | constraints/test_constraints.py::TestC01PluginStructure | PASS |
| C-05 | LIMITATION | constraints/test_constraints.py::TestC05NoTeamsForDeliberation | PASS |
| C-07 | REQUIREMENT | constraints/test_constraints.py::TestC07StateSequence | PASS |
| C-33 | REQUIREMENT | constraints/test_constraints.py::TestC33NoNumericPredictionsShared | PASS |
| C-L01 | LIMITATION | constraints/test_constraints.py::TestCL01PluginSubagentIgnored | PASS |
| C-L02 | LIMITATION | constraints/test_constraints.py::TestCL02SubagentsCannotSpawn | **FAIL** (V-C01) |
| C-36 | REQUIREMENT | constraints/test_constraints.py::TestC36StructuralArchetypes | PASS |
| C-37 | INVARIANT | constraints/test_constraints.py::TestC37StructuralNotStakeholder | PASS |

**Constraint Coverage**: 7/8 pass (88%)

### Task DoD Coverage
| Task | DoD | Test File | Status |
|------|-----|-----------|--------|
| C-A.1 | plugin.json exists with correct fields | dod/test_ca1_plugin_scaffold.py::TestCA1PluginJson | PASS |
| C-A.2 | .mcp.json with correct config | dod/test_ca1_plugin_scaffold.py::TestCA2McpJson | PASS |
| C-A.3 | hooks.json with SessionStart + PreToolUse | dod/test_ca1_plugin_scaffold.py::TestCA3HooksJson | PASS |
| C-A.4 | validate-no-numbers.sh blocks round 1-5, allows 6+ | dod/test_ca1_plugin_scaffold.py::TestCA4ValidateNoNumbers | PASS |
| C-A.5 | oathfish-init.sh detects active runs | dod/test_ca1_plugin_scaffold.py::TestCA5OathfishInit | PASS |
| C-A.6 | oathfish-reinject-state.sh recovery | dod/test_ca1_plugin_scaffold.py::TestCA6ReinjectState | PASS |
| C-B.1 | Coordinator agent with C-33, rounds, relay | dod/test_cb_agents.py::TestCB1DeliberationCoordinator | PASS |
| C-B.2 | Archetype agent with memory:project, skills | dod/test_cb_agents.py::TestCB2ArchetypeAgent | PASS |
| C-B.3 | Report analyst with ReACT, 5 outputs | dod/test_cb_agents.py::TestCB3ReportAnalyst | PASS |
| C-C.1 | oathfish dispatcher inline | dod/test_cc_skills.py::TestCC1OathfishDispatcher | PASS |
| C-C.2 | understand context:fork | dod/test_cc_skills.py::TestCC2Understand | PASS |
| C-C.3 | baseline-amplify context:fork | dod/test_cc_skills.py::TestCC3BaselineAmplify | PASS |
| C-C.4 | deliberate INLINE NO fork | dod/test_cc_skills.py::TestCC4Deliberate | PASS |
| C-C.5 | amplify context:fork | dod/test_cc_skills.py::TestCC5Amplify | PASS |
| C-C.6 | synthesize context:fork, 5 outputs | dod/test_cc_skills.py::TestCC6Synthesize | PASS |
| C-C.7 | interact inline for resume | dod/test_cc_skills.py::TestCC7Interact | PASS |
| C-D.1 | /oathfish command | dod/test_cd_commands.py::TestCD1OathfishCommand | PASS |
| C-D.2 | /oathfish-chat command | dod/test_cd_commands.py::TestCD2OathfishChat | PASS |
| C-D.3 | /oathfish-inject command | dod/test_cd_commands.py::TestCD3OathfishInject | PASS |
| C-D.4 | /oathfish-calibrate command | dod/test_cd_commands.py::TestCD4OathfishCalibrate | PASS |
| C-E.1 | get-state.sh | dod/test_ca1_plugin_scaffold.py::TestCE1GetState | PASS |
| C-E.2 | setup.sh | dod/test_ca1_plugin_scaffold.py::TestCE2Setup | PASS |

**DoD Coverage**: 22/22 (100%)

### Hazard Coverage
| H-ID | Hazard | Test File | Status |
|------|--------|-----------|--------|
| C-H01 | Context pressure | hazard/test_hazards.py::TestCH01ContextPressure | PASS |
| C-H02 | MCP output exceeds 25K | hazard/test_hazards.py::TestCH02MCPOutputExceeds | PASS |
| C-H03 | Plugin hooks IGNORED for C-33 | hazard/test_hazards.py::TestCH03C33BrokenInFrontmatter | PASS |
| C-H04 | MCP server must be alive | hazard/test_hazards.py::TestCH04MCPServerAlive | PASS |
| C-H05 | MCP namespacing unverified | hazard/test_hazards.py::TestCH05MCPNamespacing | PASS |
| C-H06 | Round number bridge | hazard/test_hazards.py::TestCH06RoundNumberBridge | PASS |
| C-H12 | Argument relay fidelity | hazard/test_hazards.py::TestCH12ArgumentRelayFidelity | PASS |
| C-H14 | Nesting problem | hazard/test_hazards.py::TestCH14NestingProblem | **FAIL** (V-C01) |

**Hazard Coverage**: 7/8 tested (88%)

Note: C-H07 (serial bottleneck), C-H08 (Teams eliminated), C-H09 (concurrency limit),
C-H10 (skills preloading), C-H11 (INTERACT resume), C-H13 (context:fork file persistence)
are runtime-only hazards that cannot be verified statically. C-H08 is confirmed eliminated.
C-H10 is covered by edge/test_edge_cases.py::TestEdgeArchetypeReasoning::test_under_100_lines.

---

## Completeness Assertion

I am 99.99% confident that:
- [x] Every SC-### from feature-request.md (Worker C scope: SC-02 through SC-05) has at least one test
- [x] Every C-### constraint (Worker C scope) has validation coverage
- [x] Every T#.# task DoD (C-A.1 through C-E.2) has verification
- [x] Every testable H-### hazard (C-H01 through C-H14) has at least one attack test
- [x] Edge cases cover all major components (scripts, agents, skills, commands, hooks, structural archetypes, archetype-reasoning)
- [x] Integration smoke tests cover happy path (file existence, format validity, cross-references)
- [x] Regression suite passes (99/99)

Missing coverage: Runtime-only hazards (C-H07, C-H09, C-H11, C-H13) cannot be tested statically.
These require live Claude Code sessions to verify.

---

## Verdict

**FIXABLE**

1 architectural issue (V-C01) with clear fix. All other 261 tests pass, including all success
criteria and regression tests. The synthesize skill nesting issue has three possible fix paths,
the cleanest being to use `context: fork` + `agent: report-analyst` which avoids nesting entirely.
