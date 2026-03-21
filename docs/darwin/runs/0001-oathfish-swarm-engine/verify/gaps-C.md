# Gaps Report - Worker C (Orchestration Layer)

**Run ID**: 0001-oathfish-swarm-engine
**Worker**: C
**Verdict**: FIXABLE
**Gaps Found**: 1

---

## Run Context

| Field | Value |
|-------|-------|
| run_id | 0001-oathfish-swarm-engine |
| feature | OathFish Swarm Intelligence Engine |
| worker | C (Orchestration) |
| report_path | docs/darwin/runs/0001-oathfish-swarm-engine/verify/report-C.md |
| test_path | tests/verify_0001_worker_c/ |
| total_tests | 263 |
| passed | 261 |
| failed | 2 |
| regression | 0 (99/99 pass) |

---

## Coverage Summary

| Category | Covered | Total | Percentage |
|----------|---------|-------|-----------|
| SC (Worker C scope) | 4 | 4 | 100% |
| Constraints (Worker C scope) | 7 | 8 | 88% |
| Task DoD | 22 | 22 | 100% |
| Hazards (testable) | 7 | 8 | 88% |
| Edge Cases | 37 | 37 | 100% |
| Integration | 18 | 18 | 100% |
| Regression | 99 | 99 | 100% |

---

## Gap V-C01: Synthesize Skill Subagent Nesting Violation

### Context

| Field | Value |
|-------|-------|
| V-ID | V-C01 |
| Category | Constraint violation |
| Source | C-L02 (sub-agents.md:188) |
| Severity | HIGH (will fail at runtime) |
| Confidence | 98% |
| File | skills/synthesize/SKILL.md |

### Spec Requirement

From sub-agents.md line 188:
> **Subagents CANNOT spawn other subagents.**
> Only agents running as main thread with `claude --agent` can spawn subagents.

From skills.md line 63-64:
> `context: fork` = run in forked subagent context
> `agent` field: built-in or custom subagents

### What Happens

1. The oathfish dispatcher invokes `/synthesize` skill
2. `skills/synthesize/SKILL.md` has `context: fork` + `agent: general-purpose`
3. This creates a **general-purpose subagent** to execute the skill
4. The skill content instructs: "Launch @report-analyst with full context"
5. The skill has `allowed-tools: Read, Write, Agent, Glob, Grep` -- Agent is listed
6. The subagent attempts to spawn `@report-analyst` via Agent tool
7. **This fails** because subagents cannot spawn other subagents (C-L02)

### Evidence

Current synthesize/SKILL.md frontmatter:
```yaml
context: fork
agent: general-purpose
allowed-tools: Read, Write, Agent, Glob, Grep
```

Body contains:
```
### Step 2: Spawn Report Analyst
Launch @report-analyst with full context:
```

### Test Output

```
FAILED tests/verify_0001_worker_c/constraints/test_constraints.py::TestCL02SubagentsCannotSpawn::test_synthesize_nesting_issue

E  Failed: C-L02 VIOLATION: synthesize skill runs with context:fork (= subagent)
   but has Agent in allowed-tools. A forked subagent CANNOT spawn another subagent
   (report-analyst). This will fail at runtime.
```

### Suggested Fix (3 options, ranked by preference)

**Option A (Recommended): Change agent type to report-analyst**

```yaml
---
name: synthesize
description: >
  OathFish SYNTHESIZE phase...
user-invocable: false
context: fork
agent: report-analyst      # <-- Changed from general-purpose
allowed-tools: Read, Write, Glob, Grep  # <-- Removed Agent
---
```

This makes the forked subagent BE the report analyst. The SKILL.md content becomes the task
that the report-analyst agent executes. No nesting needed. This is architecturally clean and
preserves context isolation.

**Option B: Remove context:fork (run inline)**

```yaml
---
name: synthesize
description: >
  OathFish SYNTHESIZE phase...
user-invocable: false
# No context: fork -- runs inline like deliberate
allowed-tools: Read, Write, Agent, Glob, Grep
---
```

This runs synthesize in the main thread, which CAN spawn report-analyst. Downside: consumes
main thread context window. But the oathfish dispatcher already runs inline, so this is
consistent.

**Option C: Remove Agent tool, restructure as direct instructions**

Remove Agent from allowed-tools. Instead of spawning report-analyst, have the synthesize
skill content directly instruct the report generation work. The forked general-purpose
subagent does the report analysis itself using the report-analyst's system prompt
content inline.

---

## Suggested Next Steps

Start a new `/darwin` session to apply fix V-C01:

```
/darwin fix 0001-oathfish-swarm-engine --gaps docs/darwin/runs/0001-oathfish-swarm-engine/verify/gaps-C.md
```

The fix is a 3-line change to `skills/synthesize/SKILL.md` frontmatter (Option A).
After applying the fix, re-run verification:

```
python3 -m pytest tests/verify_0001_worker_c/ -v
```

All 263 tests should pass.
