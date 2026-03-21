# Claude Code CLI Reference — OathFish Analysis

**Source**: https://code.claude.com/docs/en/cli-reference
**Date fetched**: 2026-03-18

---

## Reading the document

The CLI Reference documents two main surfaces: CLI commands (how you launch Claude Code) and CLI flags (how you customize behavior per session or per invocation). The document covers 13 commands and 50+ flags, organized into tables with flag name, description, and example.

### Commands (13 total)

| Command | Description |
|---------|-------------|
| `claude` | Start interactive session |
| `claude "query"` | Start interactive with initial prompt |
| `claude -p "query"` | Print mode (SDK) — query, then exit |
| `cat file \| claude -p "query"` | Process piped content |
| `claude -c` | Continue most recent conversation |
| `claude -c -p "query"` | Continue via SDK |
| `claude -r "<session>" "query"` | Resume session by ID or name |
| `claude update` | Update to latest version |
| `claude auth login/logout/status` | Authentication management |
| `claude agents` | List all configured subagents |
| `claude mcp` | Configure MCP servers |
| `claude remote-control` | Start Remote Control server |

### Key flags (50+ total, grouped by OathFish relevance)

**Prompt control flags:**
- `--system-prompt` — Replaces entire default system prompt
- `--system-prompt-file` — Replaces with file contents
- `--append-system-prompt` — Appends to default prompt
- `--append-system-prompt-file` — Appends file contents to default prompt
- `--system-prompt` and `--system-prompt-file` are mutually exclusive
- Append flags can be combined with either replacement flag

**Output control flags:**
- `--output-format` — Options: `text`, `json`, `stream-json` (print mode only)
- `--json-schema` — Validated JSON output matching a JSON Schema (print mode only)
- `--input-format` — Options: `text`, `stream-json`
- `--include-partial-messages` — Include partial streaming events (requires print + stream-json)

**Session management flags:**
- `--resume`, `-r` — Resume session by ID or name, or show interactive picker
- `--continue`, `-c` — Load most recent conversation in current directory
- `--session-id` — Use specific UUID for conversation
- `--fork-session` — Create new session ID when resuming
- `--name`, `-n` — Display name for session (shown in /resume, terminal title)
- `--no-session-persistence` — Disable session persistence (print mode only)
- `--from-pr` — Resume sessions linked to a GitHub PR

**Model and effort flags:**
- `--model` — Model alias (`sonnet`, `opus`, `haiku`) or full ID (`claude-sonnet-4-6`)
- `--fallback-model` — Automatic fallback when default overloaded (print mode only)
- `--effort` — Options: `low`, `medium`, `high`, `max` (Opus 4.6 only). Session-scoped.

**Tool control flags:**
- `--tools` — Restrict which built-in tools Claude can use. `""` = none, `"default"` = all, or `"Bash,Edit,Read"`
- `--allowedTools` — Tools that execute without permission prompts. Supports pattern matching.
- `--disallowedTools` — Tools removed from model context entirely
- `--permission-mode` — Options: `default`, `plan`, etc.
- `--dangerously-skip-permissions` — Skip all permission prompts
- `--allow-dangerously-skip-permissions` — Enable bypass as an option without activating
- `--permission-prompt-tool` — MCP tool to handle permission prompts in non-interactive mode

**Agent flags:**
- `--agent` — Specify agent for current session (overrides `agent` setting)
- `--agents` — Define custom subagents dynamically via JSON (same fields as frontmatter + `prompt`)
- `--teammate-mode` — Options: `auto`, `in-process`, `tmux`

**Execution limits:**
- `--max-turns` — Limit agentic turns (print mode only). Error on limit.
- `--max-budget-usd` — Maximum dollar spend before stopping (print mode only)

**MCP and plugin flags:**
- `--mcp-config` — Load MCP servers from JSON files or strings (space-separated)
- `--strict-mcp-config` — Only use MCP servers from --mcp-config, ignore all others
- `--plugin-dir` — Load plugins from directory for this session only

**Working environment flags:**
- `--worktree`, `-w` — Start in isolated git worktree at `<repo>/.claude/worktrees/<name>`
- `--add-dir` — Add additional working directories
- `--setting-sources` — Comma-separated: `user`, `project`, `local`
- `--settings` — Path to settings JSON file or JSON string

**Other flags:**
- `--verbose` — Full turn-by-turn output
- `--debug` — Debug mode with category filtering
- `--chrome` / `--no-chrome` — Chrome browser integration toggle
- `--init` / `--init-only` — Run initialization hooks
- `--maintenance` — Run maintenance hooks and exit
- `--disable-slash-commands` — Disable all skills and commands
- `--remote` — Create web session on claude.ai
- `--remote-control`, `--rc` — Interactive session with Remote Control
- `--teleport` — Resume web session locally
- `--ide` — Auto-connect to IDE
- `--betas` — Beta headers for API requests
- `--version`, `-v` — Output version number
- `--print`, `-p` — Non-interactive mode

---

## What I learned

### 1. `claude -p` is the mass amplification engine

The `--print` / `-p` flag transforms Claude Code from an interactive agent into a one-shot query processor. Combined with `--json-schema`, it produces validated structured output. Combined with `--model haiku`, it runs cheap. Combined with `--max-turns`, it limits compute. Combined with `--no-session-persistence`, it avoids disk I/O. This is the exact execution model for OathFish's mass amplification layer (C-05).

The full amplification call signature maps to:

```bash
claude -p \
  --system-prompt "$ARCHETYPE_IDENTITY" \
  --append-system-prompt "$VARIATION_DELTA" \
  --json-schema "$PREDICTION_SCHEMA" \
  --model haiku \
  --max-turns 1 \
  --no-session-persistence \
  --output-format json \
  "Given the following scenario and deliberation context: $CONTEXT. What is your prediction?"
```

### 2. `--system-prompt` vs `--append-system-prompt` enables identity layering

The four system prompt flags create a clean separation:
- `--system-prompt` = archetype identity (the persona core)
- `--append-system-prompt` = variation delta (demographic/contextual variation)

This is exactly what the feature request specifies (line 203-204). The docs confirm these work in both interactive and non-interactive modes. The append flags preserve Claude Code's built-in capabilities while adding custom instructions — but for amplification, OathFish uses `--system-prompt` (replacement) because amplification calls are pure persona responses, not agentic tool-using sessions.

### 3. `--json-schema` guarantees structured output

The docs describe `--json-schema` as: "Get validated JSON output matching a JSON Schema after agent completes its workflow (print mode only)." This eliminates the free-text parsing problem that the research-driven-redesign identified (line 121-123). Every amplification call returns a `PredictionPosition` object (or subset) that the MCP server can ingest directly. No regex parsing, no format errors, no partial responses.

### 4. `--resume SESSION_ID` carries full conversation context

The docs state: "Resume a specific session by ID or name." This is the mechanism the feature request uses for carrying deliberation context into amplification (line 205). BUT spec-audit.md (SPEC-03) identified this as a CRITICAL contradiction with C-21 (statelessness). The CLI reference confirms the contradiction: `--resume` loads a prior conversation, making the call stateful. The resolution (deliberation digest injected via prompt text, not `--resume`) is supported by the CLI: use `--system-prompt` to inject the digest instead of `--resume`.

### 5. `--fallback-model` provides overload resilience

The docs state: "Enable automatic fallback to specified model when default model is overloaded (print mode only)." For mass amplification (500-5000 calls with `--model haiku`), some calls may fail due to rate limits or overload. `--fallback-model sonnet` provides automatic retry with a more available (but more expensive) model. This is not mentioned in the feature request but should be — it prevents amplification batch failures.

### 6. `--max-budget-usd` enables cost control

The docs state: "Maximum dollar amount to spend on API calls before stopping (print mode only)." For mass amplification at scale (1500 calls * $0.01/call = $15 per archetype tier), this flag provides a hard cost ceiling. If amplification costs spike unexpectedly (e.g., Haiku overload causes fallback to Sonnet), the budget cap prevents runaway spending.

### 7. `--max-turns` limits compute per amplification call

The docs state: "Limit the number of agentic turns (print mode only). Exits with an error when the limit is reached." For amplification, `--max-turns 1` ensures each call is a single response — no tool use, no follow-up, no agentic behavior. This enforces the "stateless single-turn response" model described in the architecture table (feature-request.md line 78).

### 8. `--effort` controls response depth per model tier

The docs state: "Set the effort level for the current session. Options: low, medium, high, max (Opus 4.6 only). Session-scoped and does not persist to settings." This maps to OathFish's tiered archetype model:
- Opus thought-leader archetypes: `--effort max`
- Sonnet standard archetypes: `--effort high`
- Haiku follower archetypes: `--effort medium`

This allows cost-quality tuning without changing models — a Sonnet call with `--effort high` vs `--effort low` produces different depth of reasoning at the same model cost.

### 9. `--agents` enables dynamic subagent definitions

The docs state: "Define custom subagents dynamically via JSON. Uses the same field names as subagent frontmatter, plus a prompt field." This means OathFish can define archetype subagents at runtime:

```bash
claude --agents '{
  "archetype-cautious-vc": {
    "description": "Embodies the Cautious VC perspective",
    "prompt": "You are The Cautious VC, representing institutional investors...",
    "tools": ["Read", "SendMessage"],
    "model": "opus",
    "maxTurns": 5
  }
}'
```

This is more flexible than pre-defined Markdown files — archetypes are generated per-topic in the UNDERSTAND phase, so their definitions must be dynamic.

### 10. `--worktree` enables isolated parallel work

The docs state: "Start Claude in an isolated git worktree at `<repo>/.claude/worktrees/<name>`." This maps to the A/B baseline amplification (C-26): run the baseline in a worktree so its state is isolated from the main deliberation flow. Combined with `--fork-session`, the baseline amplification gets a clean execution environment.

### 11. `--no-session-persistence` reduces overhead for stateless calls

The docs state: "Disable session persistence so sessions are not saved to disk and cannot be resumed (print mode only)." For 1500 amplification calls, each creating a session file would produce 1500 session files. `--no-session-persistence` avoids this overhead entirely. This flag directly supports C-21 (stateless mass layer).

### 12. `--strict-mcp-config` ensures amplification calls use the right MCP server

The docs state: "Only use MCP servers from --mcp-config, ignoring all other MCP configurations." For amplification calls that should only use the oathfish-engine MCP server (not any user-configured servers), `--strict-mcp-config --mcp-config ./engine/.mcp.json` ensures a clean MCP environment.

---

## What maps to OathFish

### Mass amplification call signature (C-05, C-17, C-21)

The full `claude -p` call for each amplification persona variation:

```bash
claude -p \
  --system-prompt "$ARCHETYPE_PERSONA" \
  --append-system-prompt "$VARIATION_DELTA" \
  --json-schema "$PREDICTION_SCHEMA" \
  --model haiku \
  --fallback-model sonnet \
  --max-turns 1 \
  --max-budget-usd 0.05 \
  --no-session-persistence \
  --output-format json \
  --effort medium \
  "$SCENARIO_PROMPT"
```

**Flag-to-constraint mapping:**

| Flag | Constraint | Purpose |
|------|-----------|---------|
| `-p` | C-05 | Non-interactive mode for mass amplification |
| `--system-prompt` | C-08, C-30 | Archetype identity + superforecaster methodology |
| `--append-system-prompt` | C-09 | Per-variation demographic/contextual delta |
| `--json-schema` | C-05 | Structured output eliminates parsing (PredictionPosition schema) |
| `--model haiku` | C-05, C-17 | Cheap model for 500-5000 calls |
| `--fallback-model sonnet` | (NEW) | Overload resilience during mass amplification |
| `--max-turns 1` | C-21 | Single-turn stateless response |
| `--max-budget-usd 0.05` | (NEW) | Per-call cost ceiling prevents runaway |
| `--no-session-persistence` | C-21 | No disk writes for stateless calls |
| `--output-format json` | C-05 | Machine-readable output for MCP aggregation |
| `--effort medium` | (NEW) | Appropriate depth for mass-layer haiku calls |

### Baseline amplification call signature (C-26)

The baseline runs BEFORE deliberation with pre-deliberation archetype stances:

```bash
claude -p \
  --system-prompt "$INITIAL_ARCHETYPE_PERSONA" \
  --json-schema "$PREDICTION_SCHEMA" \
  --model haiku \
  --fallback-model sonnet \
  --max-turns 1 \
  --no-session-persistence \
  --output-format json \
  --effort medium \
  "$SCENARIO_PROMPT_NO_DELIBERATION_CONTEXT"
```

Note: NO `--resume` (per SPEC-03 resolution), NO `--append-system-prompt` with deliberation digest (baseline must be uncontaminated).

### Deliberation session flags (C-04, C-07)

The coordinator's interactive session uses different flags:

```bash
claude \
  --agent deliberation-coordinator \
  --model opus \
  --effort max \
  --mcp-config ./engine/.mcp.json \
  --teammate-mode in-process \
  --name "oathfish-run-{RUN_ID}" \
  --allowedTools "Bash(claude -p *)" "Write" "Edit" "SendMessage" \
  --worktree "oathfish-run-{RUN_ID}"
```

### Archetype subagent definition via `--agents` (C-08, C-20)

Dynamic archetype definitions generated by the UNDERSTAND phase:

```bash
claude --agents "$(cat archetypes-agents.json)"
```

Where `archetypes-agents.json` is generated during UNDERSTAND:

```json
{
  "archetype-cautious-vc": {
    "description": "Cautious VC perspective — institutional investors",
    "prompt": "You are 'The Cautious VC'...[superforecaster methodology]...",
    "tools": ["Read", "SendMessage"],
    "model": "opus",
    "maxTurns": 5,
    "memory": "project"
  },
  "archetype-tech-optimist": {
    "description": "Tech Optimist perspective — early adopters",
    "prompt": "You are 'The Tech Optimist'...[superforecaster methodology]...",
    "tools": ["Read", "SendMessage"],
    "model": "sonnet",
    "maxTurns": 4,
    "memory": "project"
  }
}
```

### Session continuity via `--resume` (SPEC-03 resolution)

The spec audit identified `--resume` in amplification as contradicting C-21 (statelessness). The resolution uses `--resume` ONLY for the INTERACT phase (post-synthesis user Q&A), NOT for amplification:

```bash
# INTERACT phase: resume the deliberation session for archetype interviews
claude -r "oathfish-run-{RUN_ID}" "Ask the Cautious VC about their round 4 position shift"
```

For amplification, deliberation context is injected via prompt text (deliberation digest), not `--resume`.

---

## What maps to the research

### Paper 2305.14325 (Multi-Agent Debate) — `--max-turns` enforces debate structure

The debate paper found that "stubborn prompts produce better outcomes" and "longer debates produce better final solutions." The `--max-turns` flag maps to this:
- FREE_FORM rounds: `maxTurns: 3` per archetype (brief initial reasoning)
- STRUCTURED_DEBATE rounds: `maxTurns: 5` per archetype (deeper engagement with opponent)
- SCENARIO_INJECTION rounds: `maxTurns: 3` (focused second-order reasoning)
- INDEPENDENT_PREDICTION round: `maxTurns: 1` (single structured prediction, no deliberation)

This graduated turn count implements "structured stubbornness" — debate rounds get more turns for deeper engagement, while prediction rounds are single-shot for independence.

### Paper 2402.19379 (Silicon Crowd) — `--json-schema` + `--no-session-persistence` enforce independence

The ensemble paper's core finding: "simple averaging beats LLM updating (p=0.011)." The CLI flags enforce this:
- `--json-schema` guarantees each call produces a structured prediction (no free-text drift)
- `--no-session-persistence` ensures no call leaves traces for subsequent calls
- `--max-turns 1` prevents any multi-turn updating behavior
- No `--resume` means no shared context between amplification calls

Each amplification call is mathematically independent: same schema, same persona variant, same scenario, but no shared state. The median of 1500 independent structured predictions implements the "simple averaging" baseline that the paper validated.

### Paper 2409.19839 (ForecastBench) — `--output-format json` enables submission pipeline

ForecastBench requires structured prediction submissions. The `--output-format json` flag produces machine-readable output that can be directly transformed into ForecastBench submission format. The `--json-schema` ensures the output matches the required fields (prediction, confidence, timeframe). This eliminates the parsing step between OathFish's output and ForecastBench's input format.

### Paper 2411.10109 (Generative Agents) — `--system-prompt` + `--append-system-prompt` enable grounding

The persona paper's grounding ladder (Rung 2: 3-5 real public sources) maps to the system prompt layering:
- `--system-prompt`: Core archetype identity (persona, values, incentives, blind spots, communication style) + curated real-world source excerpts (interview quotes, published frameworks, hearing testimony)
- `--append-system-prompt`: Variation delta (demographic shift, contextual variation, scenario-specific framing)

The separation means grounding sources are baked into the core identity (persistent across variations) while demographic variations change between calls. This implements the paper's finding that even modest grounding produces "step-function improvement" in persona fidelity.

### Paper 2602.19520 (Calibration Decomposition) — `--max-budget-usd` prevents calibration cost spiral

The calibration paper identified resolution latency as a risk: most predictions take 3-12 months to resolve. During this period, OathFish runs accumulate API costs without calibration feedback. `--max-budget-usd` provides a per-call and per-session cost ceiling that prevents spending from outpacing calibration value. If the system is producing uncalibrated predictions (year 1), the budget constraint forces cost discipline.

---

## What 10x the outcome

### 1. Add `--fallback-model` to every amplification call

The feature request does not mention `--fallback-model`. But at 1500 amplification calls per run, even a 1% failure rate means 15 failed predictions. `--fallback-model sonnet` provides automatic retry with a different model if Haiku is overloaded:

```bash
claude -p --model haiku --fallback-model sonnet --json-schema "$SCHEMA" "$PROMPT"
```

This is critical for mass amplification reliability. The fallback model is slightly more expensive but ensures batch completion. The Python SDK amplification engine should set this as default.

**Impact**: Eliminates amplification batch failures. At 1500 calls, even 99% reliability means 15 missing predictions per run. With fallback, reliability approaches 100%.

### 2. Use `--effort` to implement tiered archetype depth

The feature request specifies tiered models (Opus for thought leaders, Sonnet for standard, Haiku for followers). But `--effort` adds a second dimension:

| Archetype tier | Model | Effort | Purpose |
|---------------|-------|--------|---------|
| Thought leaders (5-8) | Opus | max | Deepest reasoning, most context, highest cost |
| Standard (15-20) | Sonnet | high | Solid reasoning, good cost-quality balance |
| Followers (5-8) | Haiku | medium | Adequate reasoning, lowest cost |
| Mass amplification | Haiku | medium | Statistical breadth, minimal per-call cost |

`--effort max` is Opus 4.6 only, providing the deepest reasoning for the 5-8 most central archetypes. This aligns with the centrality-based tiering in the feature request (line 659) without adding complexity — it is just a flag.

### 3. Use `--no-session-persistence` for ALL amplification calls

The feature request does not explicitly mention this flag, but it is essential for C-21 (statelessness):

- 1500 amplification calls without `--no-session-persistence` = 1500 session files on disk
- Each session file contains the full prompt + response (potentially 10KB+)
- Total: 15MB+ of ephemeral session data per run, accumulating across runs

`--no-session-persistence` eliminates this entirely. The amplification results are captured by the Python SDK and recorded via MCP tools. No session files needed.

**Impact**: Eliminates disk I/O bottleneck and storage accumulation for mass amplification.

### 4. Use `--strict-mcp-config` for amplification to prevent tool leakage

Mass amplification calls should not have access to arbitrary MCP tools — they should only produce structured predictions. But if the user has other MCP servers configured (e.g., GitHub, Slack), those tools would be available in `claude -p` calls by default.

```bash
claude -p \
  --strict-mcp-config \
  --mcp-config ./engine/.mcp.json \
  --tools "" \
  --json-schema "$SCHEMA" \
  "$PROMPT"
```

`--strict-mcp-config` ensures only the oathfish-engine MCP server is available. `--tools ""` disables all built-in tools. The call produces pure structured output with no tool access — exactly what the mass layer needs.

**Impact**: Prevents amplification calls from accidentally using tools (Bash, WebFetch, etc.) that would add cost and non-determinism.

### 5. Use `--tools ""` with `--json-schema` for pure prediction calls

The `--tools ""` flag disables ALL built-in tools. Combined with `--json-schema`, this creates a pure prediction pipeline:

```bash
claude -p --tools "" --json-schema "$PREDICTION_SCHEMA" --system-prompt "$PERSONA" "$SCENARIO"
```

The model can only produce a JSON response matching the schema. No tool calls, no side effects, no agentic behavior. This is the purest implementation of "stateless single-turn response" (feature-request.md line 78).

**Impact**: Eliminates any possibility of amplification calls using tools, reducing cost and ensuring deterministic behavior.

### 6. Use `--disallowedTools` to enforce archetype tool restrictions at the CLI level

For archetype subagents defined via `--agents`, the `tools` field restricts available tools. But as defense-in-depth, also use `--disallowedTools` at the session level:

```bash
claude --disallowedTools "Write" "Edit" "Bash" "WebFetch" "WebSearch"
```

This removes dangerous tools from the model's context entirely for the entire session. Even if a bug in archetype configuration accidentally grants Write access, the session-level disallow overrides it.

### 7. Use `--mcp-config` with inline JSON for dynamic MCP server configuration

The feature request assumes a static `.mcp.json` file. But the CLI supports dynamic MCP configuration:

```bash
claude -p --mcp-config '{"oathfish-engine": {"type": "stdio", "command": "python", "args": ["-m", "engine.server", "--run-id", "RUN_001"]}}' "$PROMPT"
```

This allows the Python SDK amplification engine to pass the run ID as a command-line argument to the MCP server, dynamically binding each amplification batch to a specific run. No static configuration file needed.

### 8. Use `--fork-session` for A/B testing without session contamination

The `--fork-session` flag creates a new session ID when resuming. For A/B baseline testing:

```bash
# After UNDERSTAND phase, fork the session for baseline
claude --resume "oathfish-run-001" --fork-session -p "Run baseline amplification"
```

The forked session has full UNDERSTAND context but diverges before DELIBERATE. This creates a clean baseline without the state machine conflict identified in SPEC-02.

---

## Why?

The CLI reference reveals that `claude -p` is not just "non-interactive mode" — it is a complete structured prediction API. The combination of `--system-prompt` (identity), `--append-system-prompt` (variation), `--json-schema` (structure), `--model` (cost), `--max-turns` (compute), `--no-session-persistence` (statelessness), `--effort` (depth), `--fallback-model` (resilience), and `--max-budget-usd` (cost control) provides 9 independent knobs for tuning each amplification call.

The feature request uses 4 of these knobs (system-prompt, append-system-prompt, json-schema, model). The analysis identifies 5 more that should be used:

1. `--fallback-model` — prevents batch failures during 1500-call runs
2. `--no-session-persistence` — eliminates 15MB+ ephemeral disk writes per run
3. `--effort` — adds cost-quality tuning without changing models
4. `--max-budget-usd` — prevents runaway cost during uncalibrated year 1
5. `--tools ""` — disables all built-in tools for pure prediction calls

Together, these 9 flags transform `claude -p` into a precisely controlled prediction engine where every dimension (identity, variation, structure, cost, compute, statelessness, depth, resilience, ceiling) is explicitly specified. No defaults, no surprises, no side effects.

---

## Reality check?

### `--json-schema` validation may reject valid but non-conforming responses

If the schema is too strict (e.g., requires `confidence` as a float between 0.0 and 1.0, but the model outputs 0.95 as a string "0.95"), the validation may fail and return an error instead of a prediction. The amplification engine needs robust error handling for schema validation failures, not just API errors.

### `--fallback-model` cost implications at scale

If Haiku experiences sustained overload during a 1500-call batch, and 30% of calls fall back to Sonnet, costs increase 3-5x for those calls. At 1500 calls with 30% fallback:
- 1050 Haiku calls * ~$0.003 = $3.15
- 450 Sonnet calls * ~$0.015 = $6.75
- Total: ~$9.90 (vs $4.50 all-Haiku)

The `--max-budget-usd` flag per call mitigates this, but the batch-level cost control needs to be in the Python SDK, not the CLI.

### `--max-turns 1` may be too restrictive for complex scenarios

Some amplification prompts may require the model to reason through a multi-step scenario before producing a prediction. With `--max-turns 1`, the model must produce the prediction in a single response. For complex scenarios with long context (deliberation digest + persona + variation + scenario), this may truncate reasoning. Consider `--max-turns 2` as a fallback for complex scenarios.

### `--no-session-persistence` means no retry with context

If an amplification call fails (API error, schema validation error), `--no-session-persistence` means the failed attempt is gone — no session to resume, no context to retry with. The Python SDK must handle retries with the full prompt, not session continuation.

### `--effort` is Opus 4.6 only for `max` level

The docs state `max` effort requires Opus 4.6. If OathFish's thought-leader archetypes use `--model opus --effort max`, they must be using Opus 4.6 specifically. If the user's account has a different Opus version, `--effort max` may fail silently or produce an error.

### `--agents` JSON size limits

Defining 30 archetype subagents via `--agents` JSON could produce a very large command-line string (30 * ~500 chars = ~15KB). Some shells have command-line length limits (typically 128KB on macOS, but still). The safer approach is to generate archetype Markdown files in `.claude/agents/` during the UNDERSTAND phase, not pass them all via `--agents`.

### The `--resume` contradiction (SPEC-03) is real and unresolved in the CLI

The CLI reference confirms that `--resume` loads a full conversation. There is no "partial resume" or "summary resume" mode. The resolution (deliberation digest) must be implemented in the Python SDK, not the CLI. The CLI provides no built-in way to inject a conversation summary — it is either full resume or fresh start.

### `--worktree` requires a git repository

The `--worktree` flag requires the project to be a git repository. The env context shows "Is directory a git repo: No" for the current OathFish project. This flag cannot be used until OathFish is initialized as a git repo.

---

## Citations from the reference document

> "claude -p 'query': Query via SDK, then exit"
— CLI Reference, commands table

> "--json-schema: Get validated JSON output matching a JSON Schema after agent completes its workflow (print mode only)"
— CLI Reference, flags table

> "--system-prompt: Replace the entire system prompt with custom text"
— CLI Reference, flags table

> "--append-system-prompt: Append custom text to the end of the default system prompt"
— CLI Reference, flags table

> "--system-prompt and --system-prompt-file are mutually exclusive. The append flags can be combined with either replacement flag."
— CLI Reference, system prompt flags section

> "For most use cases, use an append flag. Appending preserves Claude Code's built-in capabilities while adding your requirements. Use a replacement flag only when you need complete control over the system prompt."
— CLI Reference, system prompt flags section

> "--resume, -r: Resume a specific session by ID or name, or show an interactive picker to choose a session"
— CLI Reference, flags table

> "--model: Sets the model for the current session with an alias for the latest model (sonnet or opus) or a model's full name"
— CLI Reference, flags table

> "--fallback-model: Enable automatic fallback to specified model when default model is overloaded (print mode only)"
— CLI Reference, flags table

> "--no-session-persistence: Disable session persistence so sessions are not saved to disk and cannot be resumed (print mode only)"
— CLI Reference, flags table

> "--max-turns: Limit the number of agentic turns (print mode only). Exits with an error when the limit is reached. No limit by default"
— CLI Reference, flags table

> "--max-budget-usd: Maximum dollar amount to spend on API calls before stopping (print mode only)"
— CLI Reference, flags table

> "--effort: Set the effort level for the current session. Options: low, medium, high, max (Opus 4.6 only). Session-scoped and does not persist to settings"
— CLI Reference, flags table

> "--tools: Restrict which built-in tools Claude can use. Use '' to disable all, 'default' for all, or tool names like 'Bash,Edit,Read'"
— CLI Reference, flags table

> "--allowedTools: Tools that execute without prompting for permission. See permission rule syntax for pattern matching. To restrict which tools are available, use --tools instead"
— CLI Reference, flags table

> "--disallowedTools: Tools that are removed from the model's context and cannot be used"
— CLI Reference, flags table

> "--agents: Define custom subagents dynamically via JSON. Uses the same field names as subagent frontmatter, plus a prompt field for the agent's instructions"
— CLI Reference, flags table

> "--agent: Specify an agent for the current session (overrides the agent setting)"
— CLI Reference, flags table

> "--worktree, -w: Start Claude in an isolated git worktree at <repo>/.claude/worktrees/<name>. If no name is given, one is auto-generated"
— CLI Reference, flags table

> "--mcp-config: Load MCP servers from JSON files or strings (space-separated)"
— CLI Reference, flags table

> "--strict-mcp-config: Only use MCP servers from --mcp-config, ignoring all other MCP configurations"
— CLI Reference, flags table

> "--fork-session: When resuming, create a new session ID instead of reusing the original (use with --resume or --continue)"
— CLI Reference, flags table

> "--teammate-mode: Set how agent team teammates display: auto (default), in-process, or tmux"
— CLI Reference, flags table

> "--output-format: Specify output format for print mode (options: text, json, stream-json)"
— CLI Reference, flags table

> "--permission-prompt-tool: Specify an MCP tool to handle permission prompts in non-interactive mode"
— CLI Reference, flags table

> "--add-dir: Add additional working directories for Claude to access (validates each path exists as a directory)"
— CLI Reference, flags table

> "--verbose: Enable verbose logging, shows full turn-by-turn output"
— CLI Reference, flags table
