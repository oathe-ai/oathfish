# CLI Reference

**Source**: https://code.claude.com/docs/en/cli-reference
**Fetched**: 2026-03-18

---

## CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `claude` | Start interactive session | `claude` |
| `claude "query"` | Start with initial prompt | `claude "explain this project"` |
| `claude -p "query"` | Query via SDK, then exit | `claude -p "explain this function"` |
| `cat file \| claude -p` | Process piped content | `cat logs.txt \| claude -p "explain"` |
| `claude -c` | Continue most recent conversation | `claude -c` |
| `claude -c -p "query"` | Continue via SDK | `claude -c -p "Check for type errors"` |
| `claude -r "<session>"` | Resume session by ID or name | `claude -r "auth-refactor" "Finish this PR"` |
| `claude update` | Update to latest version | `claude update` |
| `claude auth login` | Sign in (--email, --sso flags) | `claude auth login --email user@example.com` |
| `claude auth logout` | Log out | `claude auth logout` |
| `claude auth status` | Auth status as JSON (--text for readable) | `claude auth status` |
| `claude agents` | List all configured subagents | `claude agents` |
| `claude mcp` | Configure MCP servers | See MCP docs |
| `claude remote-control` | Start Remote Control server | `claude remote-control --name "My Project"` |

## CLI Flags (Complete)

| Flag | Description | Example |
|------|-------------|---------|
| `--add-dir` | Add additional working directories | `claude --add-dir ../apps ../lib` |
| `--agent` | Specify agent for session | `claude --agent my-custom-agent` |
| `--agents` | Define subagents via JSON | `claude --agents '{"reviewer":{...}}'` |
| `--allow-dangerously-skip-permissions` | Enable bypass as option | With `--permission-mode` |
| `--allowedTools` | Tools auto-approved | `"Bash(git log *)" "Read"` |
| `--append-system-prompt` | Append to default system prompt | `claude --append-system-prompt "Use TypeScript"` |
| `--append-system-prompt-file` | Append from file | `claude --append-system-prompt-file ./rules.txt` |
| `--betas` | Beta headers for API (API key users) | `claude --betas interleaved-thinking` |
| `--chrome` | Enable Chrome browser integration | `claude --chrome` |
| `--continue`, `-c` | Continue most recent conversation | `claude --continue` |
| `--dangerously-skip-permissions` | Skip permission prompts | `claude --dangerously-skip-permissions` |
| `--debug` | Debug mode with category filtering | `claude --debug "api,mcp"` |
| `--disable-slash-commands` | Disable all skills/commands | `claude --disable-slash-commands` |
| `--disallowedTools` | Tools removed from context | `"Bash(git log *)" "Edit"` |
| `--effort` | Effort level: low/medium/high/max (Opus only) | `claude --effort high` |
| `--fallback-model` | Fallback when default overloaded (-p only) | `claude -p --fallback-model sonnet "query"` |
| `--fork-session` | New session ID when resuming | `claude --resume abc --fork-session` |
| `--from-pr` | Resume sessions linked to PR | `claude --from-pr 123` |
| `--ide` | Auto-connect to IDE | `claude --ide` |
| `--init` | Run init hooks + interactive | `claude --init` |
| `--init-only` | Run init hooks + exit | `claude --init-only` |
| `--include-partial-messages` | Partial streaming events | Requires -p + stream-json |
| `--input-format` | Input format for -p mode | `text`, `stream-json` |
| `--json-schema` | Validated JSON output matching schema | `claude -p --json-schema '{...}' "query"` |
| `--maintenance` | Run maintenance hooks + exit | `claude --maintenance` |
| `--max-budget-usd` | Max dollar spend (-p only) | `claude -p --max-budget-usd 5.00` |
| `--max-turns` | Limit agentic turns (-p only) | `claude -p --max-turns 3` |
| `--mcp-config` | Load MCP from JSON files | `claude --mcp-config ./mcp.json` |
| `--model` | Set model (alias or full name) | `claude --model claude-sonnet-4-6` |
| `--name`, `-n` | Session display name | `claude -n "my-feature-work"` |
| `--no-chrome` | Disable Chrome integration | `claude --no-chrome` |
| `--no-session-persistence` | Don't save session (-p only) | `claude -p --no-session-persistence` |
| `--output-format` | Output format: text/json/stream-json | `claude -p --output-format json` |
| `--permission-mode` | Start in permission mode | `claude --permission-mode plan` |
| `--permission-prompt-tool` | MCP tool for permission prompts | Non-interactive mode |
| `--plugin-dir` | Load plugins from directory | `claude --plugin-dir ./my-plugins` |
| `--print`, `-p` | Non-interactive mode | `claude -p "query"` |
| `--remote` | Create web session on claude.ai | `claude --remote "Fix login bug"` |
| `--remote-control`, `--rc` | Interactive with Remote Control | `claude --rc "My Project"` |
| `--resume`, `-r` | Resume specific session | `claude --resume auth-refactor` |
| `--session-id` | Use specific UUID | `claude --session-id "550e8400-..."` |
| `--setting-sources` | Which settings to load | `claude --setting-sources user,project` |
| `--settings` | Additional settings file/JSON | `claude --settings ./settings.json` |
| `--strict-mcp-config` | Only use --mcp-config servers | `claude --strict-mcp-config` |
| `--system-prompt` | Replace entire system prompt | `claude --system-prompt "You are..."` |
| `--system-prompt-file` | Replace from file | `claude --system-prompt-file ./prompt.txt` |
| `--teammate-mode` | Team display: auto/in-process/tmux | `claude --teammate-mode in-process` |
| `--teleport` | Resume web session locally | `claude --teleport` |
| `--tools` | Restrict available tools | `claude --tools "Bash,Edit,Read"` |
| `--verbose` | Verbose logging | `claude --verbose` |
| `--version`, `-v` | Version number | `claude -v` |
| `--worktree`, `-w` | Start in isolated git worktree | `claude -w feature-auth` |

## System Prompt Flags

| Flag | Behavior |
|------|----------|
| `--system-prompt` | Replaces entire default prompt |
| `--system-prompt-file` | Replaces with file contents |
| `--append-system-prompt` | Appends to default prompt |
| `--append-system-prompt-file` | Appends file contents |

`--system-prompt` and `--system-prompt-file` are mutually exclusive. Append flags combinable with either.
