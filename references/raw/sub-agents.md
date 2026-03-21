# Create Custom Subagents

**Source**: https://code.claude.com/docs/en/sub-agents
**Fetched**: 2026-03-18

---

Subagents are specialized AI assistants running in own context window with custom system prompt, tool access, and independent permissions.

## Built-in Subagents

- **Explore**: Haiku model, read-only (denied Write/Edit). For file discovery, code search.
- **Plan**: Inherits model, read-only. For planning research.
- **general-purpose**: Inherits model, all tools. For complex multi-step tasks.
- **Bash**: Inherits. Terminal commands in separate context.
- **statusline-setup**: Sonnet. For /statusline configuration.
- **Claude Code Guide**: Haiku. For questions about Claude Code.

## Where Subagents Live

| Location | Scope | Priority |
|----------|-------|----------|
| `--agents` CLI flag | Current session | 1 (highest) |
| `.claude/agents/` | Current project | 2 |
| `~/.claude/agents/` | All your projects | 3 |
| Plugin `agents/` | Where plugin enabled | 4 (lowest) |

### CLI-defined subagents
```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer.",
    "prompt": "You are a senior code reviewer.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

## Subagent File Format

Markdown with YAML frontmatter:
```markdown
---
name: code-reviewer
description: Reviews code for quality
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer. Analyze code and provide feedback.
```

Body becomes system prompt (NOT the full Claude Code system prompt).

## Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique ID (lowercase, hyphens) |
| `description` | Yes | When Claude should delegate |
| `tools` | No | Tool allowlist. Inherits all if omitted |
| `disallowedTools` | No | Tool denylist |
| `model` | No | `sonnet`, `opus`, `haiku`, full ID, or `inherit` (default) |
| `permissionMode` | No | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `maxTurns` | No | Max agentic turns |
| `skills` | No | Skills preloaded at startup (full content injected) |
| `mcpServers` | No | MCP servers for this subagent |
| `hooks` | No | Lifecycle hooks scoped to subagent |
| `memory` | No | Persistent memory: `user`, `project`, `local` |
| `background` | No | `true` = always run as background task |
| `isolation` | No | `worktree` = run in temp git worktree |

## Persistent Memory

| Scope | Location | Use when |
|-------|----------|----------|
| `user` | `~/.claude/agent-memory/<name>/` | Learnings across all projects |
| `project` | `.claude/agent-memory/<name>/` | Project-specific, shareable via VCS |
| `local` | `.claude/agent-memory-local/<name>/` | Project-specific, not committed |

When enabled:
- System prompt includes instructions for reading/writing memory
- First 200 lines of MEMORY.md auto-loaded
- Read, Write, Edit tools auto-enabled

## MCP Server Scoping

```yaml
---
name: browser-tester
mcpServers:
  # Inline: scoped to this subagent only
  - playwright:
      type: stdio
      command: npx
      args: ["-y", "@playwright/mcp@latest"]
  # Reference: reuses already-configured server
  - github
---
```

Inline definitions connected at subagent start, disconnected at finish.

## Plugin Subagents

For security: `hooks`, `mcpServers`, `permissionMode` fields IGNORED for plugin subagents.

## Hooks in Subagent Frontmatter

```yaml
---
name: code-reviewer
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-command.sh"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./scripts/run-linter.sh"
---
```

`Stop` hooks auto-converted to `SubagentStop`.

### Project-level hooks for subagent events

In settings.json:
- `SubagentStart`: matcher on agent type name
- `SubagentStop`: matcher on agent type name

## Skills Preloading

```yaml
---
name: api-developer
skills:
  - api-conventions
  - error-handling-patterns
---
```

Full skill content injected at startup. Subagents DON'T inherit parent's skills.

## Invocation

1. **Natural language**: name subagent, Claude decides
2. **@-mention**: guarantees that subagent runs
3. **`--agent <name>`**: session-wide, replaces system prompt

Make default: `{ "agent": "code-reviewer" }` in `.claude/settings.json`

## Foreground vs Background

- **Foreground**: blocks main conversation. Permission prompts pass through.
- **Background**: runs concurrent. Permissions pre-approved before launch. AskUserQuestion fails.

`Ctrl+B` to background a running task.
`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` to disable.

## Resume

Each invocation creates fresh instance. Ask Claude to resume via agent ID for continued context.

Transcripts at: `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`

## Auto-compaction

Triggers at ~95% capacity. Configure via `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`.

## Restrict Spawnable Agents

```yaml
---
name: coordinator
tools: Agent(worker, researcher), Read, Bash
---
```

Only `worker` and `researcher` can be spawned. `Agent` without parens = any agent.

## CRITICAL CONSTRAINT

**Subagents CANNOT spawn other subagents.**

Only agents running as main thread with `claude --agent` can spawn subagents.

## Disable Specific Subagents

```json
{
  "permissions": {
    "deny": ["Agent(Explore)", "Agent(my-custom-agent)"]
  }
}
```
