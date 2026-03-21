# Run Claude Code Programmatically (Headless / Agent SDK)

**Source**: https://code.claude.com/docs/en/headless
**Fetched**: 2026-03-18

---

> Use the Agent SDK to run Claude Code programmatically from the CLI, Python, or TypeScript.

The Agent SDK gives you the same tools, agent loop, and context management that power Claude Code. It's available as a CLI for scripts and CI/CD, or as Python and TypeScript packages for full programmatic control.

> Note: The CLI was previously called "headless mode." The `-p` flag and all CLI options work the same way.

```bash
claude -p "Find and fix the bug in auth.py" --allowedTools "Read,Edit,Bash"
```

## Basic usage

Add the `-p` (or `--print`) flag to any `claude` command to run it non-interactively. All CLI options work with `-p`, including:

- `--continue` for continuing conversations
- `--allowedTools` for auto-approving tools
- `--output-format` for structured output

```bash
claude -p "What does the auth module do?"
```

## Get structured output

Use `--output-format` to control how responses are returned:

- `text` (default): plain text output
- `json`: structured JSON with result, session ID, and metadata
- `stream-json`: newline-delimited JSON for real-time streaming

```bash
claude -p "Summarize this project" --output-format json
```

To get output conforming to a specific schema, use `--output-format json` with `--json-schema` and a JSON Schema definition. The response includes metadata about the request (session ID, usage, etc.) with the structured output in the `structured_output` field.

```bash
claude -p "Extract the main function names from auth.py" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"functions":{"type":"array","items":{"type":"string"}}},"required":["functions"]}'
```

Extract with jq:
```bash
# Extract the text result
claude -p "Summarize this project" --output-format json | jq -r '.result'

# Extract structured output
claude -p "Extract function names from auth.py" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"functions":{"type":"array","items":{"type":"string"}}},"required":["functions"]}' \
  | jq '.structured_output'
```

## Stream responses

```bash
claude -p "Explain recursion" --output-format stream-json --verbose --include-partial-messages
```

Filter for text deltas:
```bash
claude -p "Write a poem" --output-format stream-json --verbose --include-partial-messages | \
  jq -rj 'select(.type == "stream_event" and .event.delta.type? == "text_delta") | .event.delta.text'
```

### Retry events (system/api_retry)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `"system"` | message type |
| `subtype` | `"api_retry"` | identifies retry event |
| `attempt` | integer | current attempt number, starting at 1 |
| `max_retries` | integer | total retries permitted |
| `retry_delay_ms` | integer | ms until next attempt |
| `error_status` | integer or null | HTTP status code |
| `error` | string | error category: authentication_failed, billing_error, rate_limit, invalid_request, server_error, max_output_tokens, unknown |
| `session_id` | string | session the event belongs to |

## Auto-approve tools

```bash
claude -p "Run the test suite and fix any failures" \
  --allowedTools "Bash,Read,Edit"
```

## Create a commit

```bash
claude -p "Look at my staged changes and create an appropriate commit" \
  --allowedTools "Bash(git diff *),Bash(git log *),Bash(git status *),Bash(git commit *)"
```

The `--allowedTools` flag uses permission rule syntax. The trailing ` *` enables prefix matching, so `Bash(git diff *)` allows any command starting with `git diff`. The space before `*` is important.

> Note: User-invoked skills and built-in commands are only available in interactive mode. In `-p` mode, describe the task you want to accomplish instead.

## Customize the system prompt

```bash
gh pr diff "$1" | claude -p \
  --append-system-prompt "You are a security engineer. Review for vulnerabilities." \
  --output-format json
```

System prompt flags:
- `--system-prompt`: FULLY REPLACE default prompt
- `--system-prompt-file`: Replace from file
- `--append-system-prompt`: Append to default prompt
- `--append-system-prompt-file`: Append file contents

## Continue conversations

```bash
# First request
claude -p "Review this codebase for performance issues"

# Continue the most recent conversation
claude -p "Now focus on the database queries" --continue
claude -p "Generate a summary of all issues found" --continue
```

Capture session ID for specific resume:
```bash
session_id=$(claude -p "Start a review" --output-format json | jq -r '.session_id')
claude -p "Continue that review" --resume "$session_id"
```

## Python/TypeScript SDK

Full programmatic control with:
- Native message objects
- Structured outputs via Pydantic models
- Tool approval callbacks
- Async/await for parallel execution
- Type-safe aggregation
