# Skills — OathFish Analysis

**Source**: https://code.claude.com/docs/en/skills
**Date fetched**: 2026-03-18

---

## Reading the Document

The Claude Code Skills documentation describes a system for extending Claude's capabilities through `SKILL.md` files with YAML frontmatter and markdown instruction bodies. Skills are directories containing a required `SKILL.md` entrypoint plus optional supporting files (templates, scripts, examples, reference docs). They live at three scopes: personal (`~/.claude/skills/`), project (`.claude/skills/`), and plugin (`<plugin>/skills/`), with enterprise managed settings as a fourth tier. Higher-priority locations win on name conflicts: enterprise > personal > project.

Key mechanics:

1. **Frontmatter fields**: `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`, `context`, `agent`, `hooks`. All optional; only `description` is recommended.

2. **String substitutions**: `$ARGUMENTS` (all args), `$ARGUMENTS[N]` or `$N` (positional), `${CLAUDE_SESSION_ID}` (session ID), `${CLAUDE_SKILL_DIR}` (skill directory path). If `$ARGUMENTS` is absent from content, args are appended as `ARGUMENTS: <value>`.

3. **Dynamic context injection**: `` !`command` `` syntax runs shell commands BEFORE skill content is sent to Claude. Output replaces the placeholder. This is preprocessing, not runtime execution. Claude only sees the final rendered result.

4. **Subagent execution**: `context: fork` runs the skill in an isolated subagent. The skill content becomes the subagent's task prompt. No access to conversation history. `agent` field specifies execution environment (built-in: `Explore`, `Plan`, `general-purpose`; or custom subagents from `.claude/agents/`).

5. **Invocation control**: `disable-model-invocation: true` means only the user can trigger (not in Claude's context at all). `user-invocable: false` means only Claude can trigger (hidden from `/` menu). Default: both can invoke. Description loaded into context budget (2% of context window, fallback 16,000 chars); full content only loads when invoked.

6. **Supporting files**: Keep `SKILL.md` under 500 lines. Reference other files (`reference.md`, `examples.md`, scripts) so Claude loads them on demand. Scripts can be in any language. Skills can generate visual output (HTML files opened in browser).

7. **Auto-discovery**: Nested `.claude/skills/` directories are found when working in subdirectories. `--add-dir` directories also contribute skills with live change detection.

8. **Bundled skills**: `/batch` (parallel changes via worktrees), `/claude-api` (API reference), `/debug` (session troubleshooting), `/loop` (recurring tasks), `/simplify` (code quality review).

9. **Permission control**: `Skill` tool can be denied globally via `/permissions`. Specific skills can be allowed/denied with `Skill(name)` exact match or `Skill(name *)` prefix match. `allowed-tools` in frontmatter grants tool access without per-use approval while skill is active.

10. **Skills + Subagents bidirectional relationship**: Skills with `context: fork` push a task into an agent. Subagents with a `skills` field pull skill content into their startup context. Two different composition patterns.

11. **Extended thinking**: Including the word "ultrathink" anywhere in skill content enables extended thinking mode.

12. **Hooks**: Skills can scope hooks to their own lifecycle using the `hooks` frontmatter field. Format follows the same structure as hooks in agents.

---

## What I Learned

### Skills are prompt-driven orchestration, not code execution

The most important insight from the documentation is that skills are fundamentally **prompt delivery mechanisms with lifecycle control**. Unlike traditional plugins that execute code, skills deliver structured prompts to Claude with control over who can trigger them, what tools are available, and whether they run inline or in isolation. The bundled `/batch` skill demonstrates this: it "gives Claude a detailed playbook and lets it orchestrate the work using its tools" — it can "spawn parallel agents, read files, and adapt to your codebase."

This means OathFish's skills are not wrappers around MCP tools. They are the **orchestration intelligence** that tells Claude how to sequence MCP tool calls, manage state transitions, coordinate agents, and interpret results. The MCP server provides deterministic primitives; skills provide the reasoning strategy.

### Dynamic context injection is underappreciated

The `` !`command` `` preprocessing syntax is extremely powerful for OathFish. It runs BEFORE Claude sees the skill content, meaning we can inject live state into the prompt without consuming agentic turns. Example: `` !`python mcp_client.py get_state` `` could inject the current phase, round number, active archetypes, and deliberation progress directly into the skill prompt. Claude receives a fully contextualized prompt on the first turn rather than needing to query state.

### The 500-line limit is a design constraint, not a suggestion

The documentation explicitly says "Keep SKILL.md under 500 lines. Move detailed reference material to separate files." This is critical for OathFish because several of our skills (especially `deliberate/SKILL.md` and `amplify/SKILL.md`) will need substantial instruction sets. The supporting-files pattern (templates, scripts, reference docs in the skill directory) is the intended solution — SKILL.md serves as an index and dispatcher, with details loaded on demand.

### `context: fork` creates true isolation

When a skill runs with `context: fork`, the subagent has NO access to conversation history. The skill content IS the entire prompt. This is fundamentally different from inline execution where the skill supplements an ongoing conversation. For OathFish, this means forked skills must be self-contained: they receive all necessary context through `$ARGUMENTS`, dynamic injection (`` !`command` ``), and supporting files.

### The description budget matters at scale

Skill descriptions are loaded into a budget of 2% of the context window (fallback 16,000 chars). With 6 skills + 3 commands, OathFish is well within this budget. But if archetype-specific skills are added (e.g., per-archetype reasoning templates), the budget could be exceeded. The `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable provides an override.

### Skills and subagents compose in two directions

The documentation explicitly describes a bidirectional pattern:
- **Skills with `context: fork`**: You write the task in the skill, pick an agent type to execute it. Skill pushes task to agent.
- **Subagents with `skills` field**: Subagent receives preloaded skill content at startup. Agent pulls skill content into its context.

This second pattern — skills preloaded into subagents — is how superforecaster methodology gets injected into every archetype. The subagent definition for each archetype includes `skills: [oathfish:archetype-reasoning]`, and the full skill content (decompose, base rate, falsify) is available from the first turn.

### `allowed-tools` is per-skill scoping

The `allowed-tools` frontmatter field auto-approves tools while a skill is active. This means the `deliberate/SKILL.md` can grant `SendMessage` and MCP tool access without per-use permission prompts, while `understand/SKILL.md` can restrict to `Read` + `Grep` + MCP tools for research-only behavior.

---

## What Maps to OathFish

### Direct mappings (current spec aligns with docs)

| OathFish Component | Skills Feature | Notes |
|---|---|---|
| `/oathfish` command (entry point) | User-invocable skill with `$ARGUMENTS` | `$0` = topic, named args for `--archetypes` / `--rounds` |
| 5-phase state machine | Main dispatcher skill calling phase skills | `oathfish/SKILL.md` orchestrates; phase skills execute |
| Phase isolation | `context: fork` per phase skill | Each phase runs in isolated subagent, no cross-contamination |
| MCP tool access | `allowed-tools` per skill | Each phase gets exactly the MCP tools it needs |
| Archetype reasoning template | `skills` preloading in subagent config | `archetype-reasoning` skill injected at subagent startup |
| `/oathfish-chat` post-run interaction | Separate user-invocable skill | Routes to archetype subagents with deliberation memory |
| `/oathfish-inject` mid-run injection | `disable-model-invocation: true` skill | User-only trigger for injecting scenarios mid-deliberation |
| Supporting files per phase | Skill directory structure | `deliberate/templates/`, `amplify/scripts/`, etc. |

### Mappings that need design decisions

| OathFish Need | Skills Feature | Design Decision |
|---|---|---|
| State machine dispatch | Main skill invokes phase skills | Should `oathfish/SKILL.md` use `context: fork` for each phase, or invoke them inline? Fork provides isolation but loses conversation context between phases. |
| Deliberation rounds 1-5 vs round 6 | Argument vs Prediction templates in supporting files | Two response format templates in `deliberate/templates/`: `argument-format.md` (rounds 1-5) and `prediction-format.md` (round 6). Resolves SPEC-01. |
| Baseline amplification before deliberation (C-26) | Dynamic injection of pre-deliberation state | `` !`python get_baseline_stances.py` `` injects initial archetype stances into amplify skill before deliberation context exists. Resolves SPEC-02. |
| Deliberation digest for amplification (resolving SPEC-03) | Supporting file generated by deliberate skill | `deliberate/` skill writes `deliberation-digest.md` as output artifact. `amplify/SKILL.md` references it via `` !`cat deliberation-digest.md` ``. No `--resume` needed. |
| Per-archetype model tiering | `model` field in subagent config | Central archetypes get Opus, peripheral get Sonnet. Configured in subagent definitions, not skills. |
| Diversity tracking | MCP tool called within deliberate skill | `deliberation_check_diversity(round_n)` called per round; skill interprets result and triggers contrarian injection if needed. |

### The dispatcher pattern

OathFish's main skill (`oathfish/SKILL.md`) mirrors the oathe-research state machine. The skill:
1. Parses `$ARGUMENTS` for topic, archetype count, round count
2. Reads current state via dynamic injection (`` !`python mcp_client.py get_state` ``)
3. Dispatches to the appropriate phase skill based on state
4. Handles phase transitions via MCP `state_transition()` tool
5. Checkpoints after each phase

This is a prompt-driven state machine. The MCP server holds state; the skill holds orchestration logic. The skill never computes metrics (C-22) — it delegates all deterministic work to MCP tools.

---

## What Maps to the Research

### 2305.14325 (Multi-Agent Debate) -- Deliberation Skill Architecture

The debate paper's core finding — that "stubborn" prompts produce longer debates and better outcomes — maps directly to skill design. Each archetype's preloaded `archetype-reasoning` skill should encode **structured stubbornness**: domain-specific priors that resist easy persuasion. The Cautious VC resists on downside risk; the Tech Optimist resists on adoption curve projections. This is implemented through the `skills` field in subagent configuration, not through the deliberation skill itself.

The paper's agreeableness warning (agents converge too quickly due to RLHF instruction-tuning) maps to the `deliberate/SKILL.md` design: the coordinator must monitor diversity per round (via MCP `deliberation_check_diversity()`) and inject contrarian prompts when premature consensus is detected. This is a skill-level orchestration decision, not an MCP-level computation.

The arguments-only design (C-33: no numbers until round 6) is implemented through two supporting file templates in the deliberate skill directory:
- `templates/argument-format.md` — rounds 1-5 response structure (qualitative only)
- `templates/prediction-format.md` — round 6 response structure (structured JSON with `--json-schema` enforcement)

### 2402.19379 (Wisdom of the Silicon Crowd) -- Amplification Skill + Debiasing

The ensemble paper proved that simple averaging beats deliberative updating (GPT-4: p=0.011; Claude 2: p=0.001). This validates the architectural separation between deliberation (qualitative reasoning exchange) and prediction (independent structured output). The `amplify/SKILL.md` must enforce independence: each `claude -p` call receives a deliberation digest (not a session resume) and produces predictions without seeing others' numbers.

The acquiescence bias finding (57% positive predictions, p<0.001) maps to a debiasing step in the amplification aggregation. The `amplify/SKILL.md` should include instructions to call `calibration_get_domain_bias()` and apply additive corrections during aggregation. Dynamic injection (`` !`python get_domain_biases.py` ``) can preload known biases into the skill prompt so the coordinator applies corrections without querying mid-run.

### 2409.19839 (ForecastBench) -- Superforecaster Methodology via Skills Preloading

The ForecastBench finding that individual LLMs perform at the level of inexperienced human forecasters (Brier ~0.15-0.20 vs superforecasters at ~0.096) validates the need for **encoded methodology**, not just persona prompting. The `archetype-reasoning` skill — preloaded into every archetype subagent via the `skills` field — should encode the superforecaster protocol:

1. State the reference class and base rate
2. Decompose into independent sub-questions
3. List key uncertainties and their directional effects
4. State falsification criteria ("I would change my prediction if...")
5. Anchor to base rate, then adjust incrementally

This is the single most direct mapping from research to skills architecture. Every archetype gets the methodology injected at startup (via subagent `skills` preloading), ensuring uniform analytical rigor regardless of persona. The persona provides INPUTS (what this archetype cares about); the superforecaster skill provides the REASONING METHOD (how to think about predictions).

### 2411.10109 (Generative Agent Simulations of 1,000 People) -- Archetype Grounding via Supporting Files

The persona paper's finding that deep qualitative personas (85% fidelity with real interviews) dramatically outperform demographic-only descriptions maps to the supporting-files pattern. Each archetype's grounding materials — curated public sources, published decision frameworks, known positions — should live in the skill directory as supporting files:

```
archetype-reasoning/
  SKILL.md                    # Superforecaster methodology
  grounding/
    vc-cautious.md            # 3-5 curated sources for this archetype
    founder-technical.md      # Curated sources
    ...
```

The hybrid grounding approach (AMB-02 resolution) maps cleanly: pre-curated archetypes reference their grounding files; dynamically generated archetypes start at "Rung 1" (synthetic) with no grounding file, and the report discloses which archetypes are grounded vs ungrounded.

### 2602.19520 (Calibration Decomposition) -- Calibration Memory via Dynamic Injection

The calibration paper's finding that 87.3% of calibration variance decomposes into 4 structured components (horizon, domain, domain-by-horizon, scale) maps to the dynamic injection pattern. Before each deliberation round, the skill can inject per-archetype calibration history:

```markdown
## Your calibration history
!`python get_archetype_calibration.py ${ARCHETYPE_ID}`
```

This injects historical accuracy data (directional biases, domain-specific errors) directly into the archetype's prompt without consuming agentic turns. The archetype receives "last time you predicted in the Politics domain, you were overconfident by 12 points" as part of its initial context.

The resolution latency risk (predictions resolve in 3-12 months; calibration loop starved for year 1) maps to a design decision in the `oathfish/SKILL.md` dispatcher: include short-horizon bootstrap questions (1-4 week resolution) in every run to generate calibration feedback faster.

---

## What 10x the Outcome

### 1. Dynamic context injection as the universal state bridge

The current spec has three critical contradictions (SPEC-01, SPEC-02, SPEC-03) that all stem from the same problem: how to transfer state between phases without violating isolation or statelessness constraints. The `` !`command` `` preprocessing syntax resolves ALL THREE:

- **SPEC-01** (position model vs arguments-only): Dynamic injection loads the correct response format template per round. `` !`python get_round_format.py ${ROUND_N}` `` injects `argument-format.md` for rounds 1-5 or `prediction-format.md` for round 6. No Pydantic model change needed at the skill layer.

- **SPEC-02** (baseline before deliberation vs state machine flow): The baseline amplification skill uses `` !`python get_initial_stances.py` `` to inject UNDERSTAND-phase archetype stances. The post-deliberation amplification skill uses `` !`python get_deliberation_digest.py` `` to inject evolved context. Two different skills, two different injection sources, same amplification logic. State machine becomes: UNDERSTAND -> BASELINE_AMPLIFY -> DELIBERATE -> AMPLIFY -> SYNTHESIZE -> INTERACT.

- **SPEC-03** (`--resume` vs statelessness): Drop `--resume` entirely. The deliberate skill writes a `deliberation-digest.md` artifact. The amplify skill injects it via `` !`cat ${RUN_DIR}/deliberation-digest.md` ``. Claude receives the digest as static text, not a live session. Statelessness preserved. C-21 satisfied.

**This is the single highest-leverage insight from the skills documentation for OathFish.** Dynamic context injection transforms skills from static prompts into state-aware orchestration templates without violating architectural constraints.

### 2. Per-phase `allowed-tools` as architectural guardrails

Each phase skill can declare exactly which MCP tools it needs:

| Phase Skill | `allowed-tools` | Rationale |
|---|---|---|
| `understand/SKILL.md` | `Read, Grep, Glob, mcp__oathfish__state_transition, mcp__oathfish__archetype_create, mcp__oathfish__graph_add_node` | Research + archetype generation only |
| `deliberate/SKILL.md` | `SendMessage, mcp__oathfish__deliberation_record_round, mcp__oathfish__deliberation_check_diversity, mcp__oathfish__deliberation_track_evolution` | Communication + deliberation tracking only |
| `amplify/SKILL.md` | `Bash(claude -p *), mcp__oathfish__amplify_aggregate, mcp__oathfish__calibration_get_domain_bias` | CLI execution + aggregation only |
| `synthesize/SKILL.md` | `Read, Write, mcp__oathfish__graph_query, mcp__oathfish__calibration_get_ensemble_metrics` | Report generation only |
| `interact/SKILL.md` | `Read, SendMessage, mcp__oathfish__graph_query` | Conversation routing only |

This enforces C-22 (coordinator never computes metrics), C-12 (all state mutations through MCP), and C-20 (archetype agents have restricted tools) through the skills system itself, not just through prompt instructions. A deliberation-phase agent literally cannot call amplification tools because they are not in its `allowed-tools` list.

### 3. `/batch` as the amplification engine

The bundled `/batch` skill "spawns one background agent per unit in an isolated git worktree" and "decomposes the work into 5 to 30 independent units." OathFish's mass amplification layer needs to spawn 50 variations per archetype (1500 total) as independent, parallel, stateless calls. Rather than building a custom Python SDK amplification engine from scratch, OathFish could model its amplification skill after `/batch`:

1. Decompose: 30 archetypes x 50 variations = 1500 units
2. Plan: Each unit gets archetype identity + variation delta + deliberation digest
3. Execute: Parallel `claude -p` calls with `--json-schema` enforcement
4. Aggregate: Collect structured JSON, apply debiasing, compute distributions

The `/batch` pattern of "research -> decompose -> plan (approval gate) -> parallel execution -> collect results" IS the amplification pipeline. The key difference: `/batch` uses worktrees for code changes; `amplify/` uses `claude -p` for stateless predictions.

### 4. The "ultrathink" keyword for deliberation rounds 3-4

The documentation reveals that including "ultrathink" anywhere in skill content enables extended thinking mode. This is underutilized in the current spec. Structured debate rounds (rounds 3-4) — where archetypes must address opponents' strongest arguments and defend domain expertise — benefit most from extended reasoning. The `deliberate/templates/structured-debate-format.md` supporting file should include "ultrathink" to activate deep reasoning specifically for adversarial rounds, while free-form rounds (1-2) use standard reasoning to save cost.

This creates a tiered reasoning investment: free-form rounds get standard reasoning (cheap), structured debate gets extended thinking (expensive but valuable for the adversarial challenge), scenario injection gets standard reasoning, and independent prediction gets standard reasoning with `--json-schema` enforcement. Cost scales with reasoning difficulty.

### 5. `hooks` scoped to skills for deliberation lifecycle management

The `hooks` frontmatter field lets skills define lifecycle hooks. For the deliberation skill, this enables:

```yaml
hooks:
  PostToolUse:
    - matcher: "mcp__oathfish__deliberation_record_round"
      hooks:
        - type: command
          command: "python check_diversity_and_inject.py"
```

After each round is recorded, a hook automatically checks diversity and injects a contrarian prompt if premature consensus is detected. This removes the diversity-monitoring burden from the coordinator's prompt (reducing prompt complexity) and makes it a deterministic system behavior. The hook runs the MCP `deliberation_check_diversity()` tool and returns exit code 2 (keep working) if diversity drops below threshold, forcing contrarian injection.

This hook-based approach is architecturally cleaner than prompt-based diversity monitoring because:
- It cannot be forgotten or misinterpreted by the coordinator
- It runs deterministically after every round
- It can trigger Python-side logic (calculate diversity index, select contrarian archetype, generate injection prompt)
- It aligns with C-32 (diversity index tracked per round) as a system guarantee

### 6. Subagent `memory: project` for cross-run archetype learning

The subagent documentation (referenced by skills preloading) shows that `memory: project` provides persistent cross-session storage. Combined with skills preloading, this creates an archetype that:
- Starts each run with superforecaster methodology (preloaded skill)
- Loads its calibration history at startup (dynamic injection in skill)
- Accumulates learning across runs (subagent `memory: project`)
- Is grounded in real public sources (supporting files in skill directory)

This is the "persistent archetype subagent" architecture described in the research-driven-redesign (section 4.2.2). Skills provide the methodology; memory provides the learning; grounding files provide the fidelity. Each mechanism maps to a different skills feature.

### 7. `${CLAUDE_SESSION_ID}` for run-level artifact tracking

The session ID substitution enables traceable artifact creation. Each OathFish run produces artifacts (archetype definitions, deliberation transcripts, amplification results, reports) that must be linked to a specific session for auditability. Using `${CLAUDE_SESSION_ID}` in file paths ensures all artifacts from a single run are correlated:

```
runs/${CLAUDE_SESSION_ID}/
  archetypes.json
  deliberation/
    round-1.json
    ...
  amplification/
    results.json
  report.md
```

This resolves the implicit need for run-level traceability without a custom run ID system. The MCP server can use the session ID as the run identifier.

### 8. `user-invocable: false` for internal orchestration skills

The `archetype-reasoning` skill (superforecaster methodology) should be `user-invocable: false`. Users should never invoke `/archetype-reasoning` directly — it is background knowledge that Claude loads when relevant (injected into archetype subagents via `skills` preloading). Similarly, internal helper skills (e.g., a `contrarian-injection` skill that generates diversity-preserving challenges) should be Claude-only.

This creates a clean separation:
- **User-facing**: `/oathfish`, `/oathfish-chat`, `/oathfish-inject` (all `disable-model-invocation: true`)
- **Claude-facing**: `archetype-reasoning`, `contrarian-injection`, `calibration-prompt` (all `user-invocable: false`)
- **Both**: `understand`, `deliberate`, `amplify`, `synthesize`, `interact` (default invocation)

---

## Why?

### Why does dynamic context injection resolve the three spec contradictions?

Because the contradictions all share a common root: the spec assumed that transferring state between phases required either (a) live session continuity (`--resume`, violating statelessness) or (b) mandatory data structures (Position model with floats, violating arguments-only constraint) or (c) violating the state machine's sequential phase ordering (running AMPLIFY before DELIBERATE). Dynamic injection provides a fourth option: **preprocessing that renders state into the prompt before Claude sees it**. The skill becomes a stateless template that receives pre-rendered state, satisfying all three constraints simultaneously.

### Why is per-phase `allowed-tools` more than a nice-to-have?

Because OathFish's constraints are only as strong as their enforcement mechanism. C-22 (coordinator never computes metrics) is a prompt instruction today — the coordinator COULD call metric tools and the system would not prevent it. With `allowed-tools`, C-22 becomes a hard boundary: the deliberation skill literally does not have metric computation tools in its toolkit. This transforms architectural invariants from "should not" to "cannot," which is the difference between a fragile prompt contract and a robust system guarantee.

### Why model amplification after `/batch` instead of building from scratch?

Because `/batch` already solves the hardest orchestration problems: parallel agent spawning, plan decomposition with approval gate, isolated execution, result collection. OathFish's amplification has the same shape (decompose -> plan -> parallel execute -> collect). The key insight is that `/batch` proves Claude Code can orchestrate 5-30 parallel agents via skills; OathFish needs to orchestrate 50 parallel `claude -p` calls per archetype. The pattern is validated; the parameters differ.

### Why is "ultrathink" for structured debate rounds specifically?

Because extended thinking has the highest marginal value when the reasoning task is adversarial. Free-form exploration (rounds 1-2) benefits from breadth; structured debate (rounds 3-4) benefits from depth — specifically, the ability to steelman opponents' arguments before dismantling them. The debate paper (2305.14325) showed that "stubborn" reasoning (which requires deep engagement with counterarguments) produces better outcomes. Extended thinking provides the reasoning budget for genuine stubbornness rather than surface-level disagreement.

### Why use hooks instead of prompt instructions for diversity monitoring?

Because prompt-based monitoring is probabilistic (Claude may or may not check diversity after each round) while hook-based monitoring is deterministic (the hook fires after every `deliberation_record_round` call, guaranteed). The research consensus is that premature consensus is the #1 failure mode of multi-agent deliberation (2305.14325). A failure mode this critical should not depend on prompt compliance. Hooks make diversity monitoring a system invariant.

---

## Reality Check?

### What could go wrong with this skills architecture?

**1. Dynamic injection complexity at scale.** Every `` !`command` `` call adds a subprocess invocation before the skill loads. With 6 phases, each potentially injecting 3-5 state values, that is 18-30 subprocess calls per run. If the MCP server is slow to respond or the Python scripts have import overhead, skill loading becomes sluggish. Mitigation: cache state in a single JSON file; inject it once per phase rather than per-field.

**2. The 500-line limit is tight for complex orchestration.** The `deliberate/SKILL.md` must describe 5 round types, diversity monitoring logic, contrarian injection triggers, coordinator responsibilities, and archetype communication patterns. This easily exceeds 500 lines without supporting files. Mitigation: aggressively move detail into supporting files. SKILL.md becomes a dispatcher; `templates/`, `protocols/`, and `scripts/` hold the substance.

**3. `context: fork` loses conversation history.** If each phase runs in a forked subagent, the synthesize phase has no memory of what happened in deliberation. All inter-phase context must flow through artifacts (written files) or dynamic injection. This is architecturally clean but operationally fragile — if an artifact is missing or malformed, the next phase fails silently. Mitigation: MCP `state_validate()` tool checks artifact completeness before each phase transition.

**4. `allowed-tools` may be too restrictive.** If the deliberation skill needs to read an archetype's grounding file (Read tool) but `allowed-tools` only includes SendMessage and MCP tools, the skill cannot access supporting files. Mitigation: include `Read` in every phase's `allowed-tools` for reference material access; restrict `Write` and `Bash` to phases that need them.

**5. Skills preloading inflates subagent context.** The `archetype-reasoning` skill (superforecaster methodology) is injected into all 30 archetype subagents at startup. If this skill is 200 lines, that is 200 lines x 30 subagents = 6,000 lines of duplicated methodology in memory. This is inherent to the design — each subagent is independent — but increases cost. Mitigation: keep the reasoning skill concise (under 100 lines) and reference supporting files for edge cases.

**6. No skill-level error handling.** If a `claude -p` call in the amplification skill fails (rate limit, timeout, malformed response), the skill has no built-in retry logic. The bundled `/batch` skill handles this through its orchestration logic, but OathFish's amplification skill must implement equivalent robustness. Mitigation: amplification script (supporting file) includes exponential backoff, retry with jitter, and partial-result collection.

**7. Skill description budget with many archetypes.** If OathFish eventually adds per-archetype skills (e.g., a `vc-cautious-reasoning` skill that extends the generic `archetype-reasoning`), the description budget (2% of context window, ~16,000 chars fallback) could be exceeded with 30+ archetype-specific skills. Mitigation: archetype-specific reasoning stays in subagent configuration and grounding files, not in separate skills. Keep the skill count low (6 phase skills + 3 commands + 2-3 internal skills = ~12 total).

**8. The dispatcher pattern has a single point of failure.** `oathfish/SKILL.md` is the state machine. If it misinterprets state, dispatches to the wrong phase, or fails to checkpoint, the entire run is corrupted. No redundancy. Mitigation: MCP `state_validate()` tool provides ground-truth state validation before every dispatch; the skill checks MCP state rather than maintaining its own.

### What assumptions am I making that could be wrong?

- **Assumption**: Dynamic injection commands (`` !`command` ``) can call the MCP server's Python client. Reality: these are shell commands; they need a standalone Python script that connects to the MCP server via stdio. If the MCP server is running as a Claude Code subprocess, a separate client script may not be able to connect to it. **This must be verified.**

- **Assumption**: `allowed-tools` includes MCP tools by their full namespaced name (`mcp__oathfish__tool_name`). Reality: the docs show `Read, Grep, Glob` and `Bash(gh *)` as examples. MCP tool scoping may work differently. **The exact syntax for MCP tools in `allowed-tools` must be tested.**

- **Assumption**: Skills with `context: fork` can write artifacts to the filesystem that subsequent skills read. Reality: forked subagents run in isolation. Their file writes may or may not persist to the parent context's filesystem depending on isolation level. If `isolation: worktree` is implied by `context: fork`, file writes happen in a temporary worktree that is cleaned up. **The persistence behavior of forked skill file writes must be verified.**

- **Assumption**: The `hooks` field in skill frontmatter can reference MCP tools. Reality: hooks run shell commands (`type: command`), not MCP tool calls. The hook script would need to independently call the MCP server. **This is the same MCP client connectivity question as dynamic injection.**

---

## Citations from the References Document

### From `references/skills.md`
- Skill structure: "SKILL.md with YAML frontmatter + markdown instructions" (line 6)
- Locations: "~/.claude/skills/, .claude/skills/, plugin skills/" (line 8)
- Supporting files: "Directory can include supporting files (templates, scripts, examples)" (line 7)
- 500-line limit: "Keep SKILL.md under 500 lines, move details to supporting files" (line 50)
- Invocation control: "disable-model-invocation: true: only user can invoke" (line 14), "user-invocable: false: only Claude can invoke" (line 15)
- Dynamic injection: "!`command` syntax runs shell commands BEFORE skill content sent to Claude" (line 29)
- Fork execution: "Skill content becomes the prompt driving the subagent; No access to conversation history" (lines 35-36)
- Skills preloading: "Full skill content injected at subagent startup" (from `references/sub-agents.md` line 17)

### From the research papers (via OathFish synthesis)
- **2305.14325** (Multi-Agent Debate): "Prompts that encouraged models to be more 'stubborn' led to LONGER debates and BETTER final solutions" — maps to structured stubbornness in archetype skills. "Language model agents are relatively 'agreeable'" — maps to diversity monitoring hooks in deliberation skill.
- **2402.19379** (Silicon Crowd): "Simple average of human+machine predictions BEATS the LLM's own update (GPT-4: p=0.011; Claude 2: p=0.001)" — maps to arguments-only deliberation + independent prediction design. "Mean model predictions significantly above 50%: M=57.35, p<0.001" — maps to debiasing injection in amplification skill.
- **2409.19839** (ForecastBench): "Expert forecasters significantly outperform best LLMs (p<0.001)" — maps to superforecaster methodology skill preloading. "Superforecaster methodology (decompose, base rate, update incrementally) should be codified into archetype reasoning" — direct mapping to `archetype-reasoning` skill.
- **2411.10109** (Generative Agents 1000): "Architecture based on qualitative interviews dramatically outperforms demographic-only persona descriptions" — maps to grounding files in skill directory. "Depth > breadth for personas" — validates supporting-file-based rich grounding over thin demographic prompts.
- **2602.19520** (Calibration Decomposition): "87.3% of calibration variance explained by 4 structured components" — maps to per-domain calibration injection via dynamic context. "Domain-by-horizon interactions alone explain 26%" — maps to structured calibration state injected per phase.

### From spec constraints (via `feature-request.md` and `spec-audit.md`)
- **C-04**: "Claude Teams with 30 archetypes via SendMessage" — maps to `deliberate/SKILL.md` `allowed-tools` including SendMessage
- **C-07**: "5-phase state machine: UNDERSTAND->DELIBERATE->AMPLIFY->SYNTHESIZE->INTERACT" — maps to main dispatcher skill
- **C-12**: "All state mutations through MCP server" — enforced via `allowed-tools` excluding Write from most phases
- **C-21**: "`claude -p` calls are stateless" — preserved via dynamic injection instead of `--resume`
- **C-22**: "Coordinator never computes metrics" — enforced via `allowed-tools` excluding metric MCP tools from coordinator
- **C-26**: "A/B test: baseline amplification BEFORE deliberation every run" — resolved via BASELINE_AMPLIFY sub-phase with dynamic injection of initial stances
- **C-30**: "Superforecaster methodology in every archetype prompt" — implemented via `archetype-reasoning` skill preloaded into subagents
- **C-32**: "Diversity index per round; premature consensus triggers contrarian injection" — implemented via PostToolUse hook on `deliberation_record_round`
- **C-33**: "No numeric predictions shared until final round" — implemented via round-specific template injection
- **SPEC-01**: Position model contradiction — resolved by dynamic injection of round-appropriate format templates
- **SPEC-02**: Baseline timing contradiction — resolved by BASELINE_AMPLIFY sub-phase between UNDERSTAND and DELIBERATE
- **SPEC-03**: `--resume` vs statelessness contradiction — resolved by deliberation digest artifact + dynamic injection, dropping `--resume`
- **AMB-01**: Evolution tracking without numbers — resolved by Option B (private numeric stances recorded by MCP, never shared between archetypes; "no numbers shared" not "no numbers produced")
- **AMB-02**: Source curation for dynamic archetypes — resolved by hybrid approach (pre-curated library + synthetic fallback with honest disclosure)
