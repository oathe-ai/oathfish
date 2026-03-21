# Extend Claude with Skills

**Source**: https://code.claude.com/docs/en/skills
**Fetched**: 2026-03-18

---

Skills extend what Claude can do. Create a `SKILL.md` file with instructions, and Claude adds it to its toolkit.

> Custom commands have been merged into skills. `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create `/deploy`.

Claude Code skills follow the Agent Skills open standard (agentskills.io).

## Bundled Skills

| Skill | Purpose |
|-------|---------|
| `/batch <instruction>` | Parallel changes across codebase via worktrees. 5-30 independent units. |
| `/claude-api` | Claude API reference for your language |
| `/debug [description]` | Troubleshoot session via debug log |
| `/loop [interval] <prompt>` | Run prompt repeatedly on interval |
| `/simplify [focus]` | Review changed files for quality |

## Where Skills Live

| Location | Path | Applies to |
|----------|------|-----------|
| Enterprise | Managed settings | All org users |
| Personal | `~/.claude/skills/<name>/SKILL.md` | All your projects |
| Project | `.claude/skills/<name>/SKILL.md` | This project only |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Where plugin enabled |

Priority: enterprise > personal > project. Plugin skills use namespace `plugin-name:skill-name`.

### Skill directory structure
```
my-skill/
├── SKILL.md           # Main instructions (required)
├── template.md
├── examples/
│   └── sample.md
└── scripts/
    └── validate.sh
```

### Auto-discovery from nested directories
Skills in subdirectory `.claude/skills/` discovered when working with files there. Supports monorepos.

### Skills from --add-dir
Skills from additional directories loaded and live-detected.

## Frontmatter Reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Display name (lowercase, hyphens, max 64 chars) |
| `description` | Recommended | What skill does, when to use. Claude uses for auto-invocation. |
| `argument-hint` | No | Autocomplete hint. E.g., `[issue-number]` |
| `disable-model-invocation` | No | `true` = only user can invoke. Default: false |
| `user-invocable` | No | `false` = hidden from / menu. Default: true |
| `allowed-tools` | No | Tools permitted without per-use approval |
| `model` | No | Model override when skill active |
| `context` | No | `fork` = run in forked subagent context |
| `agent` | No | Which subagent type for context: fork |
| `hooks` | No | Hooks scoped to skill lifecycle |

## String Substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All args passed. If absent, appended as `ARGUMENTS: <value>` |
| `$ARGUMENTS[N]` | Specific arg by 0-based index |
| `$N` | Shorthand for `$ARGUMENTS[N]` |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Directory containing SKILL.md |

## Dynamic Context Injection

`` !`command` `` syntax runs shell commands BEFORE skill content sent to Claude. Output replaces placeholder.

```yaml
---
name: pr-summary
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`
```

## context: fork (Subagent Execution)

Skill content becomes the prompt driving the subagent. No access to conversation history.

| Approach | System prompt | Task | Also loads |
|----------|--------------|------|-----------|
| Skill with `context: fork` | From agent type | SKILL.md content | CLAUDE.md |
| Subagent with `skills` field | Subagent's body | Claude's delegation | Preloaded skills + CLAUDE.md |

`agent` field: built-in (Explore, Plan, general-purpose) or custom subagents. Default: general-purpose.

## Invocation Control

| Frontmatter | You invoke | Claude invokes | When loaded |
|-------------|-----------|---------------|------------|
| (default) | Yes | Yes | Description always, full on invoke |
| `disable-model-invocation: true` | Yes | No | Not in context |
| `user-invocable: false` | No | Yes | Description always |

## Tool Access Restriction

```yaml
---
name: safe-reader
allowed-tools: Read, Grep, Glob
---
```

## Arguments

```yaml
---
name: fix-issue
disable-model-invocation: true
---

Fix GitHub issue $ARGUMENTS following our coding standards.
```

Positional: `$ARGUMENTS[0]`, `$ARGUMENTS[1]` or `$0`, `$1`, `$2`.

## Skill Restriction

Deny Skill tool in permissions:
```
Skill           # deny all
Skill(deploy *) # deny specific
Skill(commit)   # deny exact
```

## Extended Thinking

Include "ultrathink" in skill content to enable extended thinking.

## Troubleshooting

- Skill not triggering: check description keywords, verify in "What skills are available?"
- Triggers too often: make description more specific, add `disable-model-invocation: true`
- Too many skills: budget = 2% of context window (fallback 16,000 chars). Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET`.
- Keep SKILL.md under 500 lines.
