# Output Styles

**Source**: https://code.claude.com/docs/en/output-styles
**Fetched**: 2026-03-18

---

Output styles allow you to use Claude Code as any type of agent while keeping core capabilities.

## Built-in Output Styles

- **Default**: Standard software engineering system prompt
- **Explanatory**: Educational "Insights" between tasks
- **Learning**: Collaborative learn-by-doing with `TODO(human)` markers

## How Output Styles Work

- Directly modify Claude Code's system prompt
- All output styles EXCLUDE instructions for efficient output (responding concisely)
- Custom output styles EXCLUDE instructions for coding (verifying with tests), unless `keep-coding-instructions: true`
- Custom instructions added to end of system prompt
- Reminders triggered during conversation to adhere to style

## Change Your Output Style

Run `/config` > **Output style**. Saved to `.claude/settings.local.json`.

Or edit directly:
```json
{
  "outputStyle": "Explanatory"
}
```

Changes take effect at next session start (prompt caching optimization).

## Create a Custom Output Style

Markdown files with frontmatter:

```markdown
---
name: My Custom Style
description: A brief description
---

# Custom Style Instructions

You are an interactive CLI tool that helps users...

## Specific Behaviors
...
```

### Locations
- User: `~/.claude/output-styles`
- Project: `.claude/output-styles`

### Frontmatter

| Field | Purpose | Default |
|-------|---------|---------|
| `name` | Display name | File name |
| `description` | Shown in /config picker | None |
| `keep-coding-instructions` | Keep coding parts of system prompt | false |

## Key Distinctions

- **Output Styles**: REPLACE parts of system prompt. Always active once selected.
- **CLAUDE.md**: ADDS as user message following system prompt. Always active.
- **--append-system-prompt**: APPENDS to system prompt.
- **Skills**: Task-specific, invoked on demand.
- **Agents**: Invoked for specific tasks, include model/tools/context settings.
