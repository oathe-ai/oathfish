# Output Styles — OathFish Analysis

**Source**: https://code.claude.com/docs/en/output-styles
**Date fetched**: 2026-03-18

---

## <reading document>

Output styles modify Claude Code's system prompt directly. Three built-in styles exist: Default (software engineering), Explanatory (educational Insights), Learning (collaborative TODO(human)). Custom styles are Markdown files with frontmatter stored in `~/.claude/output-styles` or `.claude/output-styles`.

Key mechanics:
- Custom styles EXCLUDE default coding instructions unless `keep-coding-instructions: true`
- Always active once selected (unlike skills which are invoked on demand)
- Changes take effect at next session start (prompt caching)
- Set via `/config` > Output style, saved to `.claude/settings.local.json`

The critical distinction:
- Output styles **REPLACE** parts of system prompt
- CLAUDE.md **ADDS** as user message after system prompt
- `--append-system-prompt` **APPENDS** to system prompt
- Skills are task-specific, invoked on demand

## <what I learned>

Output styles are a system prompt replacement mechanism. They're designed for turning Claude Code into a non-coding agent (analyst, researcher, writer). The `keep-coding-instructions: true` flag preserves coding capabilities while adding custom instructions.

The key insight: output styles are **always active** — they modify every response in a session. This is fundamentally different from skills (invoked per task) or CLAUDE.md (additive, not replacing).

Output styles are session-scoped and require a restart to take effect.

## <what maps to OathFish>

### Marginal mapping: "OathFish Analyst" style for SYNTHESIZE phase

The existing reference summary suggested creating an "OathFish Analyst" output style for the synthesis phase. This would replace the default software engineering prompt with social dynamics analysis instructions.

**But this mapping is weak for several reasons:**

1. The SYNTHESIZE phase uses a `report-analyst` agent (§4.2.3), which already has its own system prompt via the agent definition. An output style would conflict with or duplicate the agent's built-in prompt.

2. Output styles are session-scoped — they'd affect ALL phases, not just SYNTHESIZE. You can't toggle an output style mid-session for one phase.

3. The archetype agents need `--system-prompt` for identity (headless mode), not output styles.

### Actual mapping: None that isn't better served by other mechanisms

| OathFish Need | Better Mechanism | Why Not Output Style |
|--------------|-----------------|---------------------|
| Archetype persona | `--system-prompt` flag | Output styles don't work in `-p` mode |
| Superforecaster methodology | `skills` field in subagent | Skills preload into subagent context |
| Report analyst reasoning | Agent definition body | Agent body IS the system prompt |
| Coordinator orchestration | Agent definition body | Same |
| Phase-specific behavior | Skill content | Skills invoked per phase |

## <what maps to the research>

### Minimal mapping

- **2409.19839** (superforecaster methodology): Output styles COULD encode forecasting methodology as always-active context. But this is better done via skill preloading (`skills: [archetype-reasoning]`) which is scoped to the subagent, not the whole session.

- **2411.10109** (persona fidelity): Output styles could theoretically encode persona depth. But archetypes use `--system-prompt` for full identity replacement, which is more precise.

The research doesn't argue for a global reasoning mode shift — it argues for per-archetype methodology (skills) and per-call identity (system prompts).

## <what 10x the outcome>

**Honest answer: Output styles are at most a 1.2x improvement for OathFish, not a 10x lever.**

The one scenario where output styles could add value: if OathFish supported a **persistent analysis mode** where the user is interactively exploring predictions across multiple sessions. An "OathFish Explorer" style could replace the coding-focused system prompt with:

```markdown
---
name: OathFish Explorer
description: Social dynamics analysis and prediction exploration mode
keep-coding-instructions: false
---

You are a social dynamics analyst. When the user asks questions:
1. Frame answers through the lens of population segment behavior
2. Reference archived OathFish runs for historical predictions
3. Use probabilistic language with explicit confidence levels
4. Always decompose into base rate + adjustment (superforecaster method)
```

This would make Claude Code feel like a dedicated prediction analysis tool rather than a coding assistant. But this is a post-MVP luxury, not a core architecture component.

## <why?>

Output styles exist to turn Claude Code into a non-coding agent. OathFish is a coding plugin that USES Claude Code — its agents already define their own system prompts. The output style mechanism is designed for the human-facing session, not for programmatic agent behavior.

The feature request's architecture already handles system prompt customization through:
- Agent definitions (deliberation-coordinator, archetype-agent, report-analyst)
- `--system-prompt` flag for mass amplification calls
- Skill content for phase-specific instructions
- CLAUDE.md for project-wide context

Output styles would be a fifth mechanism for the same purpose, adding complexity without unique value.

## <reality check?>

### What the existing reference summary got wrong

The existing `references/output-styles.md` said: "Create 'OathFish Analyst' output style for synthesis phase. Shifts Claude's entire reasoning approach to social dynamics analysis. Reusable across runs."

**This is misleading.** Output styles:
1. Cannot be scoped to a single phase — they're session-wide
2. Would conflict with agent definitions that already have system prompts
3. Don't work in `-p` mode (mass amplification layer)
4. Are set at session start and require restart to change

### Honest assessment

Output styles are the **least relevant** Claude Code feature for OathFish. Every use case the existing reference identified is better served by agent definitions, skills, or `--system-prompt` flags. The only genuine use case is a post-MVP "explorer mode" for interactive prediction analysis.

**Priority**: LOW — implement after all core phases work. Possibly never.

## <citations from the references document>

From raw docs:
> "Output styles allow you to use Claude Code as any type of agent while keeping core capabilities"

> "Custom output styles exclude instructions for coding (such as verifying code with tests), unless `keep-coding-instructions` is true"

> "Output styles directly modify Claude Code's system prompt"

> "Changes take effect the next time you start a new session. This keeps the system prompt stable throughout a conversation so prompt caching can reduce latency and cost."

> "Output Styles vs. Agents: Output styles directly affect the main agent loop and only affect the system prompt. Agents are invoked to handle specific tasks and can include additional settings like the model to use, the tools they have available"

> "Output Styles vs. Skills: Output styles modify how Claude responds (formatting, tone, structure) and are always active once selected. Skills are task-specific prompts that you invoke with `/skill-name`"
