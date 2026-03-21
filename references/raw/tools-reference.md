# Tools Reference

**Source**: https://code.claude.com/docs/en/tools-reference
**Fetched**: 2026-03-18

---

## Complete Tool List

| Tool | Description | Permission Required |
|------|-------------|-------------------|
| `Agent` | Spawns a subagent with its own context window | No |
| `AskUserQuestion` | Asks multiple-choice questions | No |
| `Bash` | Executes shell commands | Yes |
| `CronCreate` | Schedules recurring/one-shot prompt (session-scoped) | No |
| `CronDelete` | Cancels scheduled task by ID | No |
| `CronList` | Lists all scheduled tasks | No |
| `Edit` | Makes targeted edits to files | Yes |
| `EnterPlanMode` | Switches to plan mode | No |
| `EnterWorktree` | Creates isolated git worktree | No |
| `ExitPlanMode` | Presents plan for approval, exits plan mode | Yes |
| `ExitWorktree` | Exits worktree, returns to original directory | No |
| `Glob` | Finds files by pattern matching | No |
| `Grep` | Searches for patterns in file contents | No |
| `ListMcpResourcesTool` | Lists MCP server resources | No |
| `LSP` | Code intelligence via language servers (type errors, navigation) | No |
| `NotebookEdit` | Modifies Jupyter notebook cells | Yes |
| `Read` | Reads file contents | No |
| `ReadMcpResourceTool` | Reads specific MCP resource by URI | No |
| `Skill` | Executes a skill | Yes |
| `TaskCreate` | Creates new task in task list | No |
| `TaskGet` | Retrieves full task details | No |
| `TaskList` | Lists all tasks with status | No |
| `TaskOutput` | Retrieves background task output | No |
| `TaskStop` | Kills running background task | No |
| `TaskUpdate` | Updates task status/dependencies/details | No |
| `TodoWrite` | Session task checklist (non-interactive/SDK only) | No |
| `ToolSearch` | Searches for deferred tools (tool search enabled) | No |
| `WebFetch` | Fetches URL content | Yes |
| `WebSearch` | Performs web searches | Yes |
| `Write` | Creates or overwrites files | Yes |

## Bash Tool Behavior

- Working directory persists across commands
- Environment variables do NOT persist
- Set `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1` to reset to project dir after each command
- Activate virtualenv/conda before launching Claude Code
- Use `CLAUDE_ENV_FILE` or SessionStart hook for persistent env vars

## Additional Tools (Agent Teams)

- `TeamCreate` — Creates agent team
- `SendMessage` — Sends message to specific teammate
- `Broadcast` — Sends to all teammates
