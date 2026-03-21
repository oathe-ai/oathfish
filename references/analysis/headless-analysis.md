# Headless / Agent SDK — OathFish Analysis

**Source**: https://code.claude.com/docs/en/headless
**Date fetched**: 2026-03-18

---

## <reading document>

The Claude Code Headless / Agent SDK documentation describes three interfaces for programmatic Claude Code usage:

**CLI (`claude -p` mode):**
- `claude -p "prompt"` runs non-interactively, prints response, exits
- `--output-format text|json|stream-json` controls response shape
- `--json-schema '{...}'` enforces validated JSON output; response includes `structured_output` field (requires `--output-format json`)
- `--system-prompt "text"` fully replaces the default system prompt
- `--append-system-prompt "text"` adds to default prompt (preserves built-in capabilities)
- `--system-prompt-file` and `--append-system-prompt-file` load from files
- `--continue` resumes the most recent conversation in the current directory
- `--resume SESSION_ID` resumes a specific conversation by UUID
- `--fork-session` (with `--resume` or `--continue`) branches into a new session preserving history
- `--allowedTools "Bash,Read,Edit"` auto-approves tools using permission rule syntax (e.g., `Bash(git diff *)` for prefix matching)
- `--disallowedTools` removes tools from the model's context entirely
- `--tools` restricts which built-in tools are available (empty string disables all)
- `--max-turns N` limits agentic turns (print mode only, exits with error at limit)
- `--max-budget-usd N.NN` caps dollar spend on API calls (print mode only)
- `--fallback-model sonnet` enables automatic fallback when the default model is overloaded (print mode only)
- `--model MODEL` sets model (aliases: `sonnet`, `opus`, `haiku`, or full name like `claude-sonnet-4-6`)
- `--effort low|medium|high|max` sets reasoning effort level (Opus 4.6 only for `max`)
- `--verbose` enables full turn-by-turn output
- `--include-partial-messages` streams token-level events (requires `--output-format stream-json`)
- `--no-session-persistence` disables writing sessions to disk (print mode only)
- `--session-id UUID` forces a specific session ID
- `--name "label"` sets a display name for the session (resumable by name)
- `--add-dir ../apps ../lib` adds additional working directories
- `--mcp-config ./mcp.json` loads MCP server configurations
- `--strict-mcp-config` ignores all MCP configs except `--mcp-config`
- `--dangerously-skip-permissions` bypasses all permission prompts
- `--permission-mode default|acceptEdits|plan|bypassPermissions`
- `--betas interleaved-thinking` enables beta API features
- `--agents '{"name":{...}}'` defines custom subagents dynamically via JSON
- `--input-format text|stream-json` for structured input in print mode
- `--worktree` / `-w` runs in an isolated git worktree
- Input via pipe: `cat file | claude -p "analyze this"`
- Session ID capture: `claude -p "..." --output-format json | jq -r '.session_id'`

**Streaming events (`--output-format stream-json`):**
- Each line is a JSON object: `{type, subtype, ...}`
- Text deltas: `select(.type == "stream_event" and .event.delta.type? == "text_delta") | .event.delta.text`
- Retry events: `system/api_retry` with `attempt`, `max_retries`, `retry_delay_ms`, `error_status`, `error` (categories: `authentication_failed`, `billing_error`, `rate_limit`, `invalid_request`, `server_error`, `max_output_tokens`, `unknown`)

**Python SDK (`claude-agent-sdk` package):**
- `query()` — async generator, single session, no memory between calls
- `ClaudeSDKClient` — persistent client with automatic session continuity across `client.query()` calls
- `ClaudeAgentOptions` dataclass with all configuration: `allowed_tools`, `disallowed_tools`, `system_prompt`, `max_turns`, `max_budget_usd`, `model`, `fallback_model`, `output_format`, `resume`, `fork_session`, `continue_conversation`, `effort`, `thinking`, `hooks`, `agents`, `mcp_servers`, `cwd`, `add_dirs`, `env`, `sandbox`, `permission_mode`, `can_use_tool` callback, `plugins`, `setting_sources`, `include_partial_messages`
- Structured output via `output_format={"type": "json_schema", "schema": {...}}`; response `ResultMessage.structured_output` contains validated data
- Pydantic integration: `FeaturePlan.model_json_schema()` generates schema, `FeaturePlan.model_validate(msg.structured_output)` parses response
- `ResultMessage` contains: `result`, `structured_output`, `session_id`, `duration_ms`, `duration_api_ms`, `total_cost_usd`, `usage` (input/output/cache tokens), `num_turns`, `is_error`, `stop_reason`, `subtype` (`success` or `error_max_structured_output_retries`)
- `AgentDefinition(description, prompt, tools, model)` for programmatic subagents
- `HookMatcher(matcher, hooks, timeout)` with 10 hook events: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `PreCompact`, `Notification`, `SubagentStart`, `PermissionRequest`
- `CanUseTool` callback: `async (tool_name, input_data, context) -> PermissionResultAllow | PermissionResultDeny`
- `@tool()` decorator for custom tools with type-safe input schemas
- `create_sdk_mcp_server()` to embed MCP servers inline
- `Transport` abstract class for custom communication layers
- Error types: `ClaudeSDKError`, `CLINotFoundError`, `CLIConnectionError`, `ProcessError` (with `exit_code`, `stderr`), `CLIJSONDecodeError`
- Session functions: `list_sessions()`, `get_session_messages()`
- MCP configs: `McpStdioServerConfig`, `McpSSEServerConfig`, `McpHttpServerConfig`, `McpSdkServerConfig`
- Sandbox: `SandboxSettings` with network config, excluded commands, violation ignoring

**Session management:**
- Sessions are conversation histories persisted to disk at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`
- `<encoded-cwd>` replaces every non-alphanumeric character with `-`
- `continue_conversation=True` finds the most recent session in cwd
- `resume=SESSION_ID` loads a specific session; cwd must match
- `fork_session=True` copies history into a new session, original unchanged
- `ClaudeSDKClient` tracks session ID internally across `client.query()` calls — no manual ID management
- `no_session_persistence` keeps sessions in memory only (TypeScript SDK only; Python always persists)
- Cross-host resume requires shipping the `.jsonl` file and matching cwd
- Alternative: capture results as application state, inject into fresh session prompt

---

## <what I learned>

**Structured output is production-ready and schema-validated.** The `--json-schema` flag (CLI) and `output_format={"type": "json_schema", "schema": ...}` (SDK) guarantee the response matches the provided JSON Schema. The validated data lands in the `structured_output` field of the JSON response (CLI) or `ResultMessage.structured_output` (SDK). Pydantic `model_json_schema()` generates the schema; `model_validate()` parses the response. Error handling via `subtype: error_max_structured_output_retries` when the agent cannot produce valid output. This is not aspirational — it is an enforced contract.

**Session continuity works but has specific mechanics.** `--resume SESSION_ID` loads the full conversation transcript from a `.jsonl` file on disk. The session includes all prior messages, tool calls, and results. The cwd must match (sessions are stored under an encoded-cwd directory). This means: (a) resume IS stateful — it loads the entire prior conversation; (b) all calls sharing a session share the same context window; (c) resume across machines requires shipping the session file.

**The Python SDK `query()` function is an async generator.** Each call creates a new session (no memory). `ClaudeSDKClient` maintains session state across calls. Both return `AsyncIterator[Message]`. The `Message` union includes `UserMessage`, `AssistantMessage`, `SystemMessage`, `ResultMessage`, and `StreamEvent`. This means parallel execution is natural via `asyncio.gather()` or `asyncio.Semaphore`.

**Cost control is built-in.** `--max-budget-usd` caps total API spend per invocation. `--max-turns` caps agentic loop iterations. `--fallback-model` handles overload gracefully. `ResultMessage.total_cost_usd` reports actual spend. `ResultMessage.usage` breaks down input/output/cache tokens. These are hard limits, not suggestions.

**System prompt control is dual-mode.** `--system-prompt` fully replaces the default (removes all Claude Code built-in behavior). `--append-system-prompt` adds to the default (preserves tool usage, file reading, etc.). They can be combined: `--system-prompt` sets the base, `--append-system-prompt` layers on top. For archetype agents that need pure persona control without Claude Code's default instructions, `--system-prompt` is the right choice. For variation deltas that modify behavior, `--append-system-prompt` adds to whatever base exists.

**Permission and tool control is granular.** `--allowedTools` auto-approves specific tools with pattern matching. `--disallowedTools` removes tools entirely from context. `--tools` restricts the available tool set. The SDK `CanUseTool` callback enables programmatic approval logic — approve, deny, or modify tool inputs at runtime. `PermissionResultAllow` can include `updated_input` to transform tool arguments.

**Subagents are first-class in the SDK.** `AgentDefinition(description, prompt, tools, model)` defines agents programmatically. Each can have its own model override. Messages from subagent context include `parent_tool_use_id` for tracking. This is separate from Claude Teams — these are single-invocation subagents, not persistent team members.

**Hooks intercept the agent loop at 10 points.** `PreToolUse` can block, modify input, or add context. `PostToolUse` can modify output or add context. `Stop` can prevent the agent from finishing. `SubagentStop` intercepts subagent completion. These are callbacks (SDK) or shell commands (CLI config), not async middleware.

---

## <what maps to OathFish>

### Mass Amplification Layer (BASELINE_AMPLIFY and AMPLIFY phases)

| OathFish Component | Headless Feature | Mapping |
|---|---|---|
| Structured persona responses (C-05, C-17) | `--json-schema` + `--output-format json` | Each `claude -p` call returns validated JSON matching `PredictionPosition` or `AmplificationResult` schema. Response in `structured_output` field eliminates free-text parsing. |
| Archetype identity injection (C-08, C-09) | `--system-prompt $ARCHETYPE_PERSONA` | Fully replaces default prompt with archetype persona. No Claude Code boilerplate — pure persona control. Used for the base archetype identity. |
| Variation delta (persona variation within archetype) | `--append-system-prompt $VARIATION_DELTA` | Adds demographic/personality variation on top of archetype identity. "You are 5 years younger and more optimistic" etc. |
| Deliberation context transfer (C-21 revised) | `--resume $SESSION_ID` (post-deliberation AMPLIFY only) | Loads deliberation conversation into amplification calls. NOT used for BASELINE_AMPLIFY (stateless control). Session ID captured via `--output-format json \| jq -r '.session_id'`. |
| Stateless baseline (C-26) | No `--resume`, no session flags | BASELINE_AMPLIFY calls use only `--system-prompt` + `--append-system-prompt` + `--json-schema`. No session context = uncontaminated A/B control. |
| Cheap fast model (C-05) | `--model haiku` | Haiku for mass amplification. `--fallback-model sonnet` for overload resilience. |
| Rate limiting (C-17: 500-5000 calls) | `--max-budget-usd` per call | Cap individual call cost. Python SDK `asyncio.Semaphore` for concurrency control. |
| Parallel execution | Python SDK `query()` as async generator | `asyncio.gather()` with semaphore for N concurrent calls. Each `query()` is independent — natural parallelism. |
| Error handling | `ResultMessage.is_error`, `ProcessError`, retry events | `system/api_retry` stream events for retry visibility. `ProcessError.exit_code` for crash detection. `error_max_structured_output_retries` for schema validation failures. |
| Cost tracking | `ResultMessage.total_cost_usd` + `ResultMessage.usage` | Per-call cost accounting enables budget management for 1500+ call batches. |
| Turn limiting | `--max-turns 1` | Mass amplification calls should be single-turn (prompt in, structured JSON out). `--max-turns 1` prevents agentic wandering. |
| Tool restriction | `--tools ""` or omit `--allowedTools` | Amplification calls need NO tools — they produce a prediction, not execute actions. Disabling tools prevents wasted tokens on tool-use reasoning. |

### Deep Deliberation Layer (DELIBERATE phase)

| OathFish Component | SDK Feature | Mapping |
|---|---|---|
| Round 6 independent predictions (C-33, C-14) | SDK `output_format={"type": "json_schema", "schema": PredictionPosition.model_json_schema()}` | Each archetype's round 6 prediction enforced as validated JSON via SDK structured output. |
| Deliberation session capture | `ResultMessage.session_id` | Capture the deliberation session ID from the DELIBERATE phase to pass into post-deliberation AMPLIFY calls via `--resume`. |
| Archetype subagent model tiering | `AgentDefinition(model="opus"\|"sonnet"\|"haiku")` | High-centrality archetypes get Opus, standard get Sonnet, followers get Haiku. SDK supports per-agent model override. |
| Diversity monitoring hooks (C-32) | `PostToolUse` hook on `SendMessage` | After each archetype responds, hook fires to check argument diversity. If premature consensus detected, inject contrarian prompt. |
| No-numbers enforcement (C-33) | `PreToolUse` hook on `SendMessage` | Validate that archetype responses in rounds 1-5 contain no numeric stance/confidence. Block if validation fails. |
| Evolution tracking | `PostToolUse` hook collecting archetype responses | After each round's responses collected, trigger MCP `deliberation_track_evolution()`. |

### Python SDK Amplification Engine (replacing amplify.sh)

| Feature | SDK Pattern |
|---|---|
| Async parallel execution | `async for msg in query(prompt=..., options=ClaudeAgentOptions(...))` inside `asyncio.gather()` |
| Semaphore-based rate limiting | `asyncio.Semaphore(max_concurrent)` wrapping each `query()` call |
| Structured result collection | `ResultMessage.structured_output` → `PredictionPosition.model_validate()` |
| Per-call cost accounting | `ResultMessage.total_cost_usd` accumulated across all calls |
| Error retry | `system/api_retry` events + catch `ProcessError` with exponential backoff |
| Session management | `query()` creates new session per call (stateless) for BASELINE; `ClaudeAgentOptions(resume=session_id)` for post-deliberation |
| Batch budget cap | `ClaudeAgentOptions(max_budget_usd=0.05)` per individual call; track cumulative in orchestrator |

---

## <what maps to the research>

### 2402.19379 — LLM Ensemble Prediction (Schoenegger et al.)

**Key finding**: Simple averaging beats LLM updating (GPT-4 p=0.011, Claude 2 p=0.001). Social updating degrades accuracy. 57% acquiescence bias (p<0.001).

**Headless mapping**: The `--json-schema` flag enables independent structured predictions (round 6) that are averaged by the MCP server — NOT by having Claude update predictions based on others' numbers. The `--system-prompt` replacement removes default Claude behavior that might introduce acquiescence (agreeable default persona). `--no-session-persistence` could be used for BASELINE_AMPLIFY calls to ensure zero contamination. `--max-turns 1` prevents multi-turn agentic behavior that could introduce social updating within a single call.

**Constraint link**: C-33 (no numbers until round 6), C-26 (baseline before deliberation), C-21 (stateless baseline calls).

### 2305.14325 — Multiagent Debate (Du et al.)

**Key finding**: Multiagent debate improves factuality 8-15pp. Stubborn prompts produce better outcomes. Debate 81.8% vs majority-vote 69.0%.

**Headless mapping**: `--system-prompt` enables "structured stubbornness" — each archetype's persona prompt encodes domain-specific resistance points. `--append-system-prompt` can add round-specific debate instructions ("Address your opponent's STRONGEST argument"). The `PreToolUse` hook on `SendMessage` enforces the no-numbers rule that prevents premature convergence. `--effort high` could deepen reasoning quality for debate rounds.

**Constraint link**: C-10 (STRUCTURED_DEBATE round type), C-32 (premature consensus detection), C-33 (arguments only).

### 2409.19839 — ForecastBench (Zou et al.)

**Key finding**: LLMs underperform superforecasters (best LLM 0.1352, superforecasters 0.096). Gap widest on combination questions requiring joint-probability reasoning.

**Headless mapping**: `--system-prompt` encodes superforecaster methodology (decompose, base rate, falsify) in every archetype prompt per C-30. `--json-schema` enforces `base_rate_anchor` and `falsification_criteria` as required fields in the `PredictionPosition` schema — not optional niceties but structurally mandated. `--model opus` for high-centrality archetypes on multi-factor questions where deeper reasoning matters most.

**Constraint link**: C-30 (superforecaster methodology), C-35 (ForecastBench submission), SC-11 (Brier target).

### 2411.10109 — Generative Agent Simulations of 1,000 People (Park et al.)

**Key finding**: 85% fidelity with real interview data. Step-function improvement from even modest grounding in real sources.

**Headless mapping**: `--system-prompt` carries the full archetype persona grounded in 3-5 real sources per C-29. The persona is not a thin demographic label — it is a rich system prompt with values, incentives, blind spots, and communication style, anchored in real public statements/interviews. The Python SDK's ability to programmatically construct system prompts from `Archetype.persona_prompt` + grounding sources enables per-call persona assembly.

**Constraint link**: C-29 (ground in real sources), C-09 (topic-customized), C-08 (persistent identity), A-06 (inter-archetype correlation < 0.8).

### 2602.19520 — Calibration Dynamics in Prediction Markets (Karger et al.)

**Key finding**: 87.3% calibration variance explained by 4 components. Domain-specific bias detectable at n=90 (80% power at d=0.3). Universal horizon effect (30.2% R-squared).

**Headless mapping**: `ResultMessage.total_cost_usd` and `ResultMessage.usage` enable per-call cost tracking that feeds into the calibration engine's domain-level bias tracking. The `structured_output` field ensures every prediction has the required fields (`confidence`, `timeframe`, `base_rate_anchor`) needed for calibration computation. `--json-schema` prevents any prediction from missing required calibration fields — the schema IS the calibration contract.

**Constraint link**: C-27 (per-domain acquiescence tracking), C-28 (dual Brier reporting), C-34 (holdout set), SC-12 (debiasing improvement), SC-14 (domain bias detection).

---

## <what 10x the outcome>

### 1. `--json-schema` as the scientific instrument

`--json-schema` is not just a convenience feature — it is the single most important capability for OathFish's quantitative integrity. Without schema enforcement, every one of the 1500+ amplification calls returns free-text that must be parsed, validated, and normalized. With it, every call returns a validated `PredictionPosition` or `AmplificationResult` that goes directly into statistical aggregation. This eliminates an entire category of data quality errors and makes the calibration engine's job deterministic.

The 10x: Schema enforcement means the difference between "1500 noisy text responses that require LLM-based parsing" and "1500 validated structured predictions ready for statistical analysis." This is the foundation for C-28 (dual Brier), C-27 (acquiescence tracking), and C-34 (holdout validation). Without it, the calibration engine cannot function.

### 2. Python SDK async engine replacing bash script

The feature request (line 308) specifies "Python SDK amplification engine (replaces bash script; --json-schema, --resume, async)." The SDK's `query()` as an async generator enables:
- `asyncio.Semaphore(N)` for precise concurrency control (no shell-level parallelism hacks)
- Per-call `ResultMessage.total_cost_usd` for budget tracking
- Per-call `ResultMessage.structured_output` for immediate Pydantic validation
- Per-call error handling (`ProcessError`, `error_max_structured_output_retries`) with retry logic
- Native `asyncio.gather()` for parallel batches with cancellation support

The 10x: An `amplify.sh` bash script with `xargs -P` cannot: track per-call cost, validate structured output, retry individual failures, enforce budget limits, or provide typed results. The Python SDK does all of these natively. At 1500 calls, the difference between "batch succeeded or failed" and "1487 succeeded, 13 retried, total cost $4.23, all results schema-validated" is the difference between a research tool and a script.

### 3. `--system-prompt` + `--append-system-prompt` as the persona architecture

The dual system prompt mechanism maps perfectly to OathFish's two-level persona architecture:
- `--system-prompt $ARCHETYPE_IDENTITY` = core persona (The Cautious VC: values, incentives, blind spots, communication style, grounding sources)
- `--append-system-prompt $VARIATION_DELTA` = demographic/personality variation ("You are 15 years younger, based in Austin instead of SF, with 3 years experience instead of 20")

The 10x: This means persona variation is compositional, not monolithic. One archetype persona prompt serves as the base for 50 variations. The `--system-prompt` replacement removes Claude Code's default system prompt entirely, so the archetype IS the identity — no default "helpful assistant" behavior leaking through. This directly addresses the fidelity finding from 2411.10109: persona richness produces step-function fidelity improvements.

### 4. `--resume SESSION_ID` as the deliberation bridge (with stateless baseline control)

The revised C-21 defines two modes: BASELINE_AMPLIFY is fully stateless (no `--resume`), AMPLIFY uses `--resume` to carry deliberation context. This enables the A/B test (C-26) by construction:
- Baseline: 1500 calls with persona-only prompts → uncontaminated predictions
- Informed: 1500 calls with `--resume $DELIBERATE_SESSION_ID` → deliberation-enriched predictions
- Delta: MCP `amplify_aggregate()` computes the difference → SC-13 measured

The 10x: Without `--resume`, transferring deliberation context requires manually summarizing 6 rounds of multi-archetype deliberation into a text digest (SPEC-03 resolution option 3). With `--resume`, the full conversation history is loaded automatically — every argument, every debate exchange, every scenario reaction. The A/B comparison becomes architecturally clean: same schema, same personas, different context.

**Critical caveat**: This only works if `--resume` does not cause all 1500 calls to share mutable session state. Per the docs, session files are read-only for resume purposes — each call reads the transcript but does not write back to it. This needs verification (see Reality Check).

### 5. `--max-turns 1` + `--tools ""` for mass amplification purity

Amplification calls should be single-turn, tool-free predictions. `--max-turns 1` prevents the agent from entering an agentic loop (reading files, running commands). Combined with `--tools ""` (disable all tools), each call becomes: prompt in → structured JSON out. No intermediate tool calls, no file reads, no wasted tokens.

The 10x: At 1500 calls, every unnecessary agentic turn multiplies cost and latency. A single wasted tool call per amplification call = 1500 wasted tool calls = significant cost. `--max-turns 1` + `--tools ""` guarantees single-turn behavior, making amplification as cheap and fast as possible.

### 6. `--max-budget-usd` as batch-level cost control

At 1500 calls with Haiku at ~$0.003/call, a full amplification batch costs ~$4.50. But with `--resume` loading deliberation context (potentially 100K+ tokens), costs could spike 10-50x per call. `--max-budget-usd` per call caps individual cost, while the Python orchestrator tracks cumulative spend.

The 10x: Prevents a single runaway call from consuming the budget. At scale, one call that enters an agentic loop or hits context limits could cost as much as the other 1499 combined. Per-call budget caps + orchestrator-level tracking = predictable costs at scale.

### 7. `--fallback-model` for production resilience

At 1500 concurrent calls, rate limits and model overload are near-certainties. `--fallback-model sonnet` means individual calls that hit Haiku overload automatically fall back to Sonnet instead of failing. Combined with `system/api_retry` stream events, the Python SDK orchestrator can monitor retry rates and adjust concurrency dynamically.

The 10x: The difference between "75% of calls succeeded, 25% failed due to rate limits" and "100% of calls succeeded, 12% fell back to Sonnet" is the difference between a partial result and a complete dataset.

---

## <why?>

**Schema enforcement eliminates the parsing layer.** Every prediction system that uses LLMs for structured output faces the same problem: LLM output is text, but statistical analysis requires structured data. Without schema enforcement, you need a parsing + validation + normalization layer between the LLM and the aggregation engine. This layer introduces its own errors, requires its own tests, and fails in unpredictable ways. `--json-schema` eliminates this entire layer. The response is either valid structured data or an explicit error (`error_max_structured_output_retries`). There is no "mostly parsed" state.

**Session resume is the only viable deliberation context transfer for post-deliberation amplification.** The alternative (SPEC-03 resolution option 3: "deliberation digest" injected as text) loses information. A 6-round deliberation with 30 archetypes produces a rich conversation history — argument chains, debate exchanges, scenario reactions, position shifts. Summarizing this into a text digest loses the nuance that makes deliberation valuable. `--resume` loads the full transcript. The cost tradeoff (higher per-call token usage vs. information loss from summarization) must be measured empirically, but the capability exists. For BASELINE_AMPLIFY, the absence of `--resume` is equally important — it is what makes the baseline stateless.

**Async Python SDK enables production-grade orchestration.** The bash script (`amplify.sh` with `xargs -P`) is a prototype pattern. It cannot handle: per-call error recovery, structured output validation, cost tracking, dynamic concurrency adjustment, or graceful shutdown. The Python SDK's `query()` as an async generator + `asyncio` primitives provide all of these. At 1500 calls, the difference between shell parallelism and async Python orchestration is the difference between a batch job and a production system.

**`--system-prompt` replacement is essential for persona purity.** Claude Code's default system prompt includes instructions about being helpful, using tools, following safety guidelines, etc. For an archetype agent in mass amplification, this default behavior is noise. The archetype IS the system prompt — The Cautious VC does not need Claude Code's default instructions about file editing. `--system-prompt` strips all defaults and installs the pure persona. This is not optional; it is architecturally required for persona fidelity.

**`--max-turns 1` prevents agentic behavior in mass amplification.** Without turn limiting, Claude may decide to use tools, ask clarifying questions, or perform multi-step reasoning. In amplification, every call should be: read prompt → produce structured prediction → done. Multi-turn behavior in amplification wastes tokens, adds latency, and introduces non-deterministic tool usage that varies between calls. Single-turn enforcement makes each call predictable and cheap.

**Cost control features are not optional at scale.** At 1500 calls per run, with plans for 500-5000 (C-17), every per-call cost multiplier compounds. `--max-budget-usd` per call, `--model haiku`, `--max-turns 1`, and `--tools ""` are all cost-reducing constraints that, together, keep a full amplification batch in the $5-20 range instead of the $50-500 range. The Python SDK's `ResultMessage.total_cost_usd` makes this trackable.

---

## <reality check?>

### SPEC-03 is partially resolved, not fully resolved

The revised C-21 splits amplification into two modes: stateless BASELINE_AMPLIFY and stateful AMPLIFY with `--resume`. This resolves the contradiction for the A/B test design. However, the spec audit (SPEC-03) raised a deeper concern: if `--resume` loads a shared deliberation session, all 1500 post-deliberation calls share the same session context. The docs confirm that `--resume` loads the full conversation history. But the docs do NOT explicitly state whether resuming is read-only (each call reads the transcript independently) or whether concurrent resumes of the same session can interfere. At 1500 concurrent calls all resuming the same session ID, this is a concurrency question the docs do not address.

**Risk**: If session resume involves file locking or mutable state, concurrent resumes will serialize or fail. If session files are read-only for resume, concurrent access is safe. The docs say sessions are stored as `.jsonl` files — reading a `.jsonl` file concurrently is safe on POSIX systems. But the SDK might acquire locks or create temporary state. This needs empirical verification.

**Mitigation**: Test with 10 concurrent `--resume` calls to the same session ID before scaling to 1500.

### `--resume` with deliberation context inflates amplification cost

A 6-round deliberation with 30 archetypes can generate 100K-500K tokens of conversation history. Loading this via `--resume` means every amplification call pays input token costs for the full deliberation transcript. At 1500 calls: 1500 x 100K tokens = 150M input tokens. Even at Haiku's input pricing, this is orders of magnitude more expensive than stateless calls.

**Risk**: Post-deliberation amplification may be 50-100x more expensive than baseline amplification due to context loading. The `--max-budget-usd` per call can cap this, but if the budget is too low, calls fail; if too high, total batch cost explodes.

**Mitigation**: The deliberation digest approach (SPEC-03 option 3) may be more cost-effective: summarize deliberation insights into a 2K-5K token digest, inject via `--append-system-prompt`. Trade information completeness for cost control. The right approach depends on whether the marginal information from the full transcript vs. a digest is worth the 50-100x cost multiplier. Measure empirically.

### `--system-prompt` + `--append-system-prompt` interaction may not work as specified

The docs say `--system-prompt` and `--system-prompt-file` are "mutually exclusive" but "the append flags can be combined with either replacement flag." The feature request specifies: `--system-prompt $ARCHETYPE_IDENTITY` + `--append-system-prompt $VARIATION_DELTA`. This should work: `--system-prompt` sets the base (archetype persona), `--append-system-prompt` adds the variation delta. However, the docs describe `--append-system-prompt` as "append custom text to the end of the default system prompt." If `--system-prompt` replaces the default, does `--append-system-prompt` append to the REPLACEMENT or to the (now-absent) default?

**Risk**: `--append-system-prompt` may be ignored when `--system-prompt` is used, or it may behave unexpectedly. The docs say the append flags "can be combined with either replacement flag," which implies it appends to whatever `--system-prompt` set. But the wording "append to the default prompt" is ambiguous.

**Mitigation**: Test the combination explicitly. If `--append-system-prompt` does not append to `--system-prompt` replacement, concatenate both into a single `--system-prompt` value.

### `--json-schema` retry behavior at scale

The docs mention `error_max_structured_output_retries` as a failure mode. At 1500 calls, even a 1% failure rate = 15 calls that cannot produce valid JSON. The docs do not specify: how many retries before `error_max_structured_output_retries`? What is the retry delay? Does each retry consume additional API credits?

**Risk**: If the retry limit is low (e.g., 3 retries) and the schema is complex, some percentage of calls will fail. If retries are billed, the effective cost per call increases.

**Mitigation**: Keep schemas simple (flat objects, few required fields). Use `PredictionPosition.model_json_schema()` which generates standard JSON Schema from Pydantic — this is well-tested territory. Monitor `error_max_structured_output_retries` rates in early runs and simplify schema if failure rate exceeds 2%.

### Python SDK `query()` vs CLI `claude -p` for mass amplification

The feature request specifies "Python SDK amplification engine (replaces bash script)." The Python SDK's `query()` spawns a Claude Code subprocess per call. At 1500 concurrent calls, this means 1500 subprocess spawns. The SDK documentation does not discuss subprocess pool management, connection reuse, or maximum concurrent subprocess limits.

**Risk**: 1500 concurrent subprocess spawns may overwhelm the system (file descriptor limits, memory, CPU). The OS typically limits concurrent processes to 1024 (default `ulimit -n`).

**Mitigation**: Use `asyncio.Semaphore(50)` or similar to limit concurrency to 50 simultaneous calls. At 50 concurrent with ~2s per call, 1500 calls complete in ~60s. This is the approach the feature request already suggests ("asyncio.Semaphore for rate limiting + retry with backoff"). The key is: the semaphore value must account for both API rate limits AND local resource limits.

### Session persistence for BASELINE_AMPLIFY calls

BASELINE_AMPLIFY runs 1500 stateless calls (no `--resume`). By default, each call creates a session file on disk. 1500 session files = 1500 `.jsonl` files in `~/.claude/projects/<encoded-cwd>/`. These are useless for baseline calls.

**Risk**: Disk clutter, slower `list_sessions()`, potential filesystem performance issues with 1500+ session files per run.

**Mitigation**: Use `--no-session-persistence` for baseline calls (CLI flag) or equivalent SDK option. The TypeScript SDK supports `persistSession: false` but the Python SDK docs note "Python always persists to disk." If Python SDK does not support disabling persistence, need to clean up session files post-batch, or accept the disk overhead.

### `--effort` flag relevance

The `--effort` flag supports `low`, `medium`, `high`, `max` (Opus 4.6 only for `max`). For mass amplification with Haiku, `--effort low` could reduce per-call cost and latency. For deliberation with Opus, `--effort high` or `max` could improve reasoning quality.

**Not a risk but an optimization opportunity** that the feature request does not mention.

### `--fallback-model` only works in print mode

The docs specify `--fallback-model` is "print mode only." Since mass amplification uses `claude -p` (print mode), this works. But if the Python SDK `query()` function does not support `fallback_model` in `ClaudeAgentOptions`, the fallback must be handled in the orchestrator.

**Verification needed**: Confirm `ClaudeAgentOptions.fallback_model` is supported. The Python SDK docs do list `fallback_model: str | None = None` in `ClaudeAgentOptions` — this appears supported.

---

## <citations from the references document>

### CLI Mode

> "Add the `-p` (or `--print`) flag to any `claude` command to run it non-interactively."

> "Use `--output-format` to control how responses are returned: `text` (default): plain text output; `json`: structured JSON with result, session ID, and metadata; `stream-json`: newline-delimited JSON for real-time streaming."

### Structured Output

> "To get output conforming to a specific schema, use `--output-format json` with `--json-schema` and a JSON Schema definition. The response includes metadata about the request (session ID, usage, etc.) with the structured output in the `structured_output` field."

> "The SDK supports standard JSON Schema features including all basic types (object, array, string, number, boolean, null), `enum`, `const`, `required`, nested objects, and `$ref` definitions."

> "Structured output generation can fail when the agent cannot produce valid JSON matching your schema. [...] When an error occurs, the result message has a `subtype` indicating what went wrong: `success` — Output was generated and validated successfully; `error_max_structured_output_retries` — Agent couldn't produce valid output after multiple attempts."

### System Prompt Control

> "`--system-prompt` and `--system-prompt-file` are mutually exclusive. The append flags can be combined with either replacement flag."

> "For most use cases, use an append flag. Appending preserves Claude Code's built-in capabilities while adding your requirements. Use a replacement flag only when you need complete control over the system prompt."

### Session Resume

> "Use `--continue` to continue the most recent conversation, or `--resume` with a session ID to continue a specific conversation."

> "If you're running multiple conversations, capture the session ID to resume a specific one: `session_id=$(claude -p 'Start a review' --output-format json | jq -r '.session_id')`"

> "Sessions persist the **conversation**, not the filesystem. To snapshot and revert file changes the agent made, use file checkpointing."

> "Sessions are stored under `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`, where `<encoded-cwd>` is the absolute working directory with every non-alphanumeric character replaced by `-`."

> "If a `resume` call returns a fresh session instead of the expected history, the most common cause is a mismatched `cwd`."

> "To resume a session on a different host (CI workers, ephemeral containers, serverless), you have two options: Move the session file [...] or Don't rely on session resume. Capture the results you need (analysis output, decisions, file diffs) as application state and pass them into a fresh session's prompt. This is often more robust than shipping transcript files around."

### Python SDK

> "`query()` — Single Session Interaction [...] Creates new session each time. No conversation memory between calls. Best for one-off tasks."

> "`ClaudeSDKClient` — Continuous Conversation [...] Each call to `client.query()` automatically continues the same session."

> "`ResultMessage` contains: `result`, `structured_output`, `session_id`, `duration_ms`, `duration_api_ms`, `total_cost_usd`, `usage`, `num_turns`, `is_error`, `stop_reason`, `subtype`."

### Cost Control

> "`--max-budget-usd`: Maximum dollar amount to spend on API calls before stopping (print mode only)."

> "`--max-turns`: Limit the number of agentic turns (print mode only). Exits with an error when the limit is reached. No limit by default."

> "`--fallback-model`: Enable automatic fallback to specified model when default model is overloaded (print mode only)."

### Tool Control

> "`--allowedTools`: Tools that execute without prompting for permission. See permission rule syntax for pattern matching."

> "The trailing `*` enables prefix matching, so `Bash(git diff *)` allows any command starting with `git diff`. The space before `*` is important: without it, `Bash(git diff*)` would also match `git diff-index`."

> "`--tools`: Restrict which built-in tools Claude can use. Use `\"\"` to disable all, `\"default\"` for all, or tool names like `\"Bash,Edit,Read\"`."

### Hooks (SDK)

> "Available hooks: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `PreCompact`, `Notification`, `SubagentStart`, `PermissionRequest`."

### Agents (SDK)

> "`AgentDefinition`: `description: str`, `prompt: str`, `tools: list[str] | None`, `model: Literal['sonnet', 'opus', 'haiku', 'inherit'] | None`."

### Streaming / Retry Events

> "When an API request fails with a retryable error, Claude Code emits a `system/api_retry` event before retrying."

> "Fields: `attempt` (current attempt number), `max_retries` (total retries permitted), `retry_delay_ms` (milliseconds until next attempt), `error_status` (HTTP status or null), `error` (category: authentication_failed, billing_error, rate_limit, invalid_request, server_error, max_output_tokens, unknown)."
