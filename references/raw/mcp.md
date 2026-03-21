# Connect Claude Code to Tools via MCP

**Source**: https://code.claude.com/docs/en/mcp
**Fetched**: 2026-03-18

---

Claude Code can connect to external tools and data sources through the Model Context Protocol (MCP), an open source standard for AI-tool integrations.

## Installing MCP servers

### Option 1: Add a remote HTTP server (recommended for remote)

```bash
claude mcp add --transport http <name> <url>

# Example with Bearer token
claude mcp add --transport http secure-api https://api.example.com/mcp \
  --header "Authorization: Bearer your-token"
```

### Option 2: Add a remote SSE server (deprecated)

```bash
claude mcp add --transport sse <name> <url>
```

### Option 3: Add a local stdio server

```bash
claude mcp add [options] <name> -- <command> [args...]

# Example
claude mcp add --transport stdio --env AIRTABLE_API_KEY=YOUR_KEY airtable \
  -- npx -y airtable-mcp-server
```

**Important: Option ordering** — All options must come before the server name. `--` separates server name from command/args.

### Managing servers

```bash
claude mcp list
claude mcp get github
claude mcp remove github
/mcp  # within Claude Code
```

### Dynamic tool updates

Claude Code supports MCP `list_changed` notifications, allowing servers to dynamically update their available tools, prompts, and resources without reconnection.

## MCP Installation Scopes

### Local scope (default)

Stored in `~/.claude.json` under project path. Private, current project only.

```bash
claude mcp add --transport http stripe https://mcp.stripe.com
claude mcp add --transport http stripe --scope local https://mcp.stripe.com
```

### Project scope

Stored in `.mcp.json` at project root. Shared via version control.

```bash
claude mcp add --transport http paypal --scope project https://mcp.paypal.com/mcp
```

`.mcp.json` format:
```json
{
  "mcpServers": {
    "shared-server": {
      "command": "/path/to/server",
      "args": [],
      "env": {}
    }
  }
}
```

Claude Code prompts for approval before using project-scoped servers. Reset with `claude mcp reset-project-choices`.

### User scope

Stored in `~/.claude.json`. Available across all projects.

```bash
claude mcp add --transport http hubspot --scope user https://mcp.hubspot.com/anthropic
```

### Scope hierarchy

Local > Project > User (local-scoped servers override project/user).

## Environment Variable Expansion in .mcp.json

- `${VAR}` — Expands to env var value
- `${VAR:-default}` — Expands with default fallback

Works in: `command`, `args`, `env`, `url`, `headers`

```json
{
  "mcpServers": {
    "api-server": {
      "type": "http",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

## Plugin-provided MCP servers

- Defined in `.mcp.json` at plugin root or inline in `plugin.json`
- Auto-start when plugin enabled
- Use `${CLAUDE_PLUGIN_ROOT}` for bundled files
- Use `${CLAUDE_PLUGIN_DATA}` for persistent state surviving updates

In `.mcp.json` at plugin root:
```json
{
  "database-tools": {
    "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
    "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
    "env": {
      "DB_URL": "${DB_URL}"
    }
  }
}
```

Or inline in `plugin.json`:
```json
{
  "name": "my-plugin",
  "mcpServers": {
    "plugin-api": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/api-server",
      "args": ["--port", "8080"]
    }
  }
}
```

**Plugin MCP features:**
- Automatic lifecycle: connect at session startup for enabled plugins
- `/reload-plugins` to connect/disconnect during session
- Multiple transport types: stdio, SSE, HTTP

## MCP Output Limits

- Warning at 10,000 tokens per tool output
- Default max: 25,000 tokens
- Configure via `MAX_MCP_OUTPUT_TOKENS` env var

```bash
export MAX_MCP_OUTPUT_TOKENS=50000
claude
```

## MCP Tool Search

Auto-enabled when tool descriptions exceed 10% of context window.

1. MCP tools deferred rather than loaded upfront
2. Claude uses search tool to discover relevant MCP tools
3. Only needed tools loaded into context

### Configure tool search

| Value | Behavior |
|-------|----------|
| (unset) | Enabled by default |
| `true` | Always enabled |
| `auto` | Activates when MCP tools exceed 10% of context |
| `auto:<N>` | Custom threshold (e.g., `auto:5` for 5%) |
| `false` | Disabled, all MCP tools loaded upfront |

```bash
ENABLE_TOOL_SEARCH=auto:5 claude
ENABLE_TOOL_SEARCH=false claude
```

Requires Sonnet 4+ or Opus 4+. Haiku does not support tool search.

## MCP Resources

Reference via `@server:protocol://resource/path`. Fuzzy-searchable in autocomplete. Auto-fetched as attachments.

```
Can you analyze @github:issue://123 and suggest a fix?
Compare @postgres:schema://users with @docs:file://database/user-model
```

## MCP Prompts as Commands

Available as `/mcp__servername__promptname`. Accept space-separated arguments.

```
/mcp__github__list_prs
/mcp__github__pr_review 456
```

## Use Claude Code AS MCP Server

```bash
claude mcp serve
```

In Claude Desktop config:
```json
{
  "mcpServers": {
    "claude-code": {
      "type": "stdio",
      "command": "claude",
      "args": ["mcp", "serve"],
      "env": {}
    }
  }
}
```

## Managed MCP Configuration

### Option 1: managed-mcp.json (exclusive control)

Deploy to system directory:
- macOS: `/Library/Application Support/ClaudeCode/managed-mcp.json`
- Linux/WSL: `/etc/claude-code/managed-mcp.json`

Users cannot add/modify MCP servers when this exists.

### Option 2: allowedMcpServers / deniedMcpServers

Policy-based control in managed settings file.

Restriction types:
- `serverName`: by configured name
- `serverCommand`: by exact command array
- `serverUrl`: by URL pattern with wildcards

Denylist takes absolute precedence over allowlist.

## OAuth Authentication

Supports OAuth 2.0 for remote servers:
- `--callback-port` for fixed redirect URI
- `--client-id` and `--client-secret` for pre-configured credentials
- `authServerMetadataUrl` for overriding OAuth discovery

## MCP Elicitation

Servers can request structured input mid-task. Two modes:
- Form mode: dialog with fields
- URL mode: opens browser for auth

Auto-respond via `Elicitation` hook.
