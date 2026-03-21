# Orchestrate Teams of Claude Code Sessions

**Source**: https://code.claude.com/docs/en/agent-teams
**Fetched**: 2026-03-18

---

> Agent teams are experimental and disabled by default. Enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`.

Agent teams coordinate multiple Claude Code instances. One session acts as team lead, coordinating work. Teammates work independently, each in its own context window, and communicate directly.

Unlike subagents (run within single session, report back only), you can interact with individual teammates directly.

Requires Claude Code v2.1.32+.

## When to Use

Best for:
- Research and review: multiple aspects simultaneously
- New modules/features: each teammate owns separate piece
- Debugging competing hypotheses: parallel theories
- Cross-layer coordination: frontend, backend, tests

Agent teams add coordination overhead and use significantly more tokens. For sequential tasks, same-file edits, or many dependencies, single session or subagents better.

### Compare with Subagents

| | Subagents | Agent teams |
|--|-----------|-------------|
| Context | Own window; results return to caller | Own window; fully independent |
| Communication | Report back to main agent only | Teammates message each other directly |
| Coordination | Main agent manages all | Shared task list with self-coordination |
| Best for | Focused tasks, result only matters | Complex work requiring discussion |
| Token cost | Lower: results summarized | Higher: each teammate separate instance |

## Enable

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

## Architecture

| Component | Role |
|-----------|------|
| Team lead | Main session that creates team, spawns teammates, coordinates |
| Teammates | Separate Claude Code instances on assigned tasks |
| Task list | Shared list teammates claim and complete |
| Mailbox | Messaging system for inter-agent communication |

Config stored at:
- Team config: `~/.claude/teams/{team-name}/config.json`
- Task list: `~/.claude/tasks/{team-name}/`

Team config contains `members` array with name, agent ID, agent type.

## Display Modes

- **In-process**: all in main terminal. Shift+Down to cycle. Works in any terminal.
- **Split panes**: each teammate own pane. Requires tmux or iTerm2.

Default: `"auto"` (split panes if in tmux, else in-process).

```json
{ "teammateMode": "in-process" }
```

Or: `claude --teammate-mode in-process`

## Task System

- States: pending, in-progress, completed
- Dependencies: blocked tasks can't be claimed until deps complete
- File-locked claiming prevents race conditions
- Self-claim: teammates pick up next unassigned, unblocked task

## Communication

- **SendMessage**: to one specific teammate
- **Broadcast**: to all (costs scale with team size)
- Automatic message delivery
- Idle notifications auto-sent to lead

## Hooks

- `TeammateIdle`: runs when teammate about to go idle. Exit 2 = keep them working.
- `TaskCompleted`: runs when task marked complete. Exit 2 = prevent completion.

## Plan Approval

Teammates can work in plan mode until lead approves:
- Teammate finishes planning → sends approval request to lead
- Lead reviews and approves or rejects with feedback
- Rejected → teammate stays in plan mode, revises

## Permissions

Teammates start with lead's permission settings. Can change individual after spawning.

## Context

Teammates load same project context as regular session (CLAUDE.md, MCP servers, skills). Lead's conversation history does NOT carry over.

## Best Practices

- **Team size**: 3-5 teammates for most workflows
- **Tasks per teammate**: 5-6 keeps everyone productive
- **Avoid file conflicts**: each teammate owns different files
- **Start with research/review** before parallel implementation
- **Monitor and steer**: check in on progress

## Limitations

- **No session resumption** with in-process teammates
- **Task status can lag**: teammates may fail to mark tasks complete
- **Shutdown can be slow**: teammates finish current request first
- **One team per session**
- **No nested teams**: teammates cannot spawn their own teams
- **Lead is fixed**: can't promote teammate
- **Permissions set at spawn**: can change after, not at spawn time
- **Split panes require tmux/iTerm2**: not VS Code terminal, Windows Terminal, or Ghostty
