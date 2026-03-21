# Automate Workflows with Hooks

**Source**: https://code.claude.com/docs/en/hooks-guide
**Fetched**: 2026-03-18

---

Hooks are user-defined shell commands that execute at specific points in Claude Code's lifecycle. They provide deterministic control over behavior.

## Hook Events

| Event | When it fires |
|-------|--------------|
| `SessionStart` | Session begins or resumes |
| `UserPromptSubmit` | Prompt submitted, before processing |
| `PreToolUse` | Before tool call executes. Can block it |
| `PermissionRequest` | When permission dialog appears |
| `PostToolUse` | After tool call succeeds |
| `PostToolUseFailure` | After tool call fails |
| `Notification` | When Claude Code sends notification |
| `SubagentStart` | When subagent spawned |
| `SubagentStop` | When subagent finishes |
| `Stop` | When Claude finishes responding |
| `TeammateIdle` | When team teammate about to go idle |
| `TaskCompleted` | When task being marked complete |
| `InstructionsLoaded` | When CLAUDE.md or rules loaded |
| `ConfigChange` | When config file changes during session |
| `WorktreeCreate` | When worktree being created |
| `WorktreeRemove` | When worktree being removed |
| `PreCompact` | Before context compaction |
| `PostCompact` | After compaction completes |
| `Elicitation` | When MCP server requests user input |
| `ElicitationResult` | After user responds to elicitation |
| `SessionEnd` | When session terminates |

## Hook Types

- `"type": "command"` — Run shell command
- `"type": "http"` — POST event data to URL
- `"type": "prompt"` — Single-turn LLM evaluation (yes/no decision)
- `"type": "agent"` — Multi-turn verification with tool access

## Hook Input/Output

### Input (JSON on stdin)

```json
{
  "session_id": "abc123",
  "cwd": "/Users/sarah/myproject",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm test"
  }
}
```

### Exit Codes

- **Exit 0**: action proceeds. For UserPromptSubmit/SessionStart, stdout added to context.
- **Exit 2**: action blocked. Stderr becomes Claude's feedback.
- **Any other**: action proceeds. Stderr logged but not shown.

### Structured JSON Output

PreToolUse can return permissionDecision:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Use rg instead of grep for better performance"
  }
}
```

Options: `"allow"`, `"deny"`, `"ask"`

Note: `"allow"` skips interactive prompt but does NOT override permission deny rules.

### PermissionRequest hooks

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow",
      "updatedPermissions": [
        { "type": "setMode", "mode": "acceptEdits", "destination": "session" }
      ]
    }
  }
}
```

## Matchers (regex filtering)

| Event | What matcher filters | Example |
|-------|---------------------|---------|
| PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest | tool name | `Bash`, `Edit\|Write`, `mcp__.*` |
| SessionStart | how session started | `startup`, `resume`, `clear`, `compact` |
| SessionEnd | why session ended | `clear`, `logout`, `prompt_input_exit` |
| Notification | notification type | `permission_prompt`, `idle_prompt` |
| SubagentStart, SubagentStop | agent type | `Bash`, `Explore`, `Plan`, custom |
| PreCompact, PostCompact | what triggered | `manual`, `auto` |
| ConfigChange | config source | `user_settings`, `project_settings`, `skills` |
| UserPromptSubmit, Stop, TeammateIdle, TaskCompleted | no matcher support | always fires |

## Hook Configuration Location

| Location | Scope | Shareable |
|----------|-------|-----------|
| `~/.claude/settings.json` | All projects | No |
| `.claude/settings.json` | Single project | Yes |
| `.claude/settings.local.json` | Single project | No |
| Managed policy settings | Organization-wide | Yes |
| Plugin `hooks/hooks.json` | When plugin enabled | Yes |
| Skill or agent frontmatter | While active | Yes |

## Prompt-based Hooks

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Check if all tasks are complete. If not, respond with {\"ok\": false, \"reason\": \"what remains\"}."
          }
        ]
      }
    ]
  }
}
```

Returns `"ok": true` (proceed) or `"ok": false` with reason (block).

## Agent-based Hooks

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "agent",
            "prompt": "Verify that all unit tests pass. Run the test suite and check the results. $ARGUMENTS",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

Default timeout 60s, up to 50 tool-use turns.

## HTTP Hooks

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "http",
            "url": "http://localhost:8080/hooks/tool-use",
            "headers": {
              "Authorization": "Bearer $MY_TOKEN"
            },
            "allowedEnvVars": ["MY_TOKEN"]
          }
        ]
      }
    ]
  }
}
```

## Common Patterns

### Desktop notification
```json
{
  "hooks": {
    "Notification": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "osascript -e 'display notification \"Claude Code needs your attention\" with title \"Claude Code\"'"
      }]
    }]
  }
}
```

### Auto-format after edits
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write"
      }]
    }]
  }
}
```

### Block protected files
PreToolUse hook on Edit|Write that checks file path against protected patterns. Exit 2 to block.

### Re-inject context after compaction
SessionStart hook with `compact` matcher. Stdout added to Claude's context.

### Stop hook infinite loop prevention
Check `stop_hook_active` field:
```bash
INPUT=$(cat)
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active')" = "true" ]; then
  exit 0
fi
```

## Limitations

- Command hooks communicate through stdout/stderr/exit codes only
- Hook timeout: 10 minutes default, configurable per hook
- PostToolUse hooks cannot undo actions
- PermissionRequest hooks do NOT fire in non-interactive mode (-p). Use PreToolUse instead.
- Stop hooks fire whenever Claude finishes responding, not only at task completion
