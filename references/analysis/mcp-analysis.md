# MCP Servers — OathFish Analysis

**Source**: https://code.claude.com/docs/en/mcp
**Date fetched**: 2026-03-18

---

## Reading the Document

The Claude Code MCP documentation describes the Model Context Protocol integration layer — the mechanism by which Claude Code connects to external tools, databases, and APIs through a standardized server interface. The documentation covers:

**Transport types**: Three transport mechanisms exist. **stdio** runs local processes on the user's machine, ideal for tools needing direct system access. **HTTP (streamable-http)** is the recommended remote transport for cloud-based services. **SSE** (Server-Sent Events) is explicitly deprecated in favor of HTTP. stdio servers are configured with a `command` and `args`; HTTP/SSE servers are configured with a `url` and optional `headers`.

**Configuration scopes**: Three levels of MCP server configuration exist with clear precedence (local > project > user):
- **Local** (default): Stored in `~/.claude.json` under the project's path. Private to the user, current project only.
- **Project**: Stored in `.mcp.json` at the project root. Designed for version control. All team members share the same tools.
- **User**: Stored in `~/.claude.json` globally. Available across all projects for a single user.

**Plugin MCP servers**: Plugins can bundle MCP servers via `.mcp.json` at the plugin root or inline in `plugin.json`. Key variables:
- `${CLAUDE_PLUGIN_ROOT}` — references bundled plugin files (code, configs, scripts)
- `${CLAUDE_PLUGIN_DATA}` — references persistent state that survives plugin updates
- Plugin MCP servers auto-start when the plugin is enabled and auto-stop when disabled.
- `/reload-plugins` reconnects MCP servers mid-session.

**Environment variable expansion**: `.mcp.json` supports `${VAR}` and `${VAR:-default}` syntax in `command`, `args`, `env`, `url`, and `headers` fields. If a required variable is unset and has no default, the config fails to parse.

**Dynamic tool updates**: Claude Code supports `list_changed` notifications from MCP servers, allowing servers to add/remove/modify tools, prompts, and resources at runtime without requiring a reconnect. This is a push mechanism — the server notifies, Claude Code refreshes.

**MCP Tool Search (deferred loading)**: When MCP tool descriptions exceed 10% of the context window, Claude Code automatically defers tool loading. Tools are discovered on demand via a search tool rather than preloaded. Configurable via `ENABLE_TOOL_SEARCH`: `true` (always on), `auto` (10% threshold), `auto:<N>` (custom threshold), `false` (all tools loaded upfront). Requires Sonnet 4+ or Opus 4+ models. Server instructions become critical for discoverability when Tool Search is active.

**Output limits**: Tool output triggers a warning at 10,000 tokens. Default maximum is 25,000 tokens. Configurable via `MAX_MCP_OUTPUT_TOKENS` environment variable. Large outputs from database queries, reports, or log processing can be accommodated.

**MCP Resources**: Servers can expose addressable resources via `@server:protocol://resource/path` syntax. Resources are fuzzy-searchable in the @ mention autocomplete and auto-fetched as attachments when referenced.

**MCP Prompts as Commands**: Servers can expose prompts accessible as `/mcp__servername__promptname` commands with space-separated arguments.

**`claude mcp serve`**: Claude Code can itself become an MCP server, exposing its own tools (View, Edit, LS, etc.) to other MCP clients.

**Security model**: Project-scoped servers from `.mcp.json` require user approval before use. Managed `managed-mcp.json` allows IT administrators to enforce exclusive control over which servers are available. Allowlists/denylists provide policy-based control by server name, command, or URL pattern.

**Startup timeout**: Configurable via `MCP_TIMEOUT` environment variable (e.g., `MCP_TIMEOUT=10000` for 10 seconds).

**OAuth 2.0**: Supported for HTTP servers, with token storage, auto-refresh, and browser-based login flow.

---

## What I Learned

1. **stdio is the right transport for OathFish and it is fully supported as a first-class citizen.** The documentation shows stdio servers are configured with `command` + `args` in `.mcp.json` — exactly the pattern OathFish uses (`"command": "python", "args": ["${CLAUDE_PLUGIN_ROOT}/engine/server.py"]`). No HTTP overhead, no network latency, no authentication complexity. The MCP server runs as a child process of Claude Code.

2. **Plugin MCP servers are a distinct, well-defined integration path.** The `.mcp.json` at the plugin root is not the same as the project-scope `.mcp.json` at the project root. Plugin MCP servers have their own lifecycle (auto-start with plugin enable, reconnect via `/reload-plugins`), their own variable namespace (`${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`), and automatic tool registration. This is the path OathFish must use — not manual `claude mcp add` commands.

3. **`${CLAUDE_PLUGIN_DATA}` is distinct from `${CLAUDE_PLUGIN_ROOT}` and is designed for persistent state that survives plugin updates.** This is architecturally significant. OathFish's run data (the `docs/runs/` directory with all deliberation artifacts, amplification results, calibration history) should live under `${CLAUDE_PLUGIN_DATA}`, not `${CLAUDE_PLUGIN_ROOT}`. Plugin code updates should never destroy run history. The current `.mcp.json` in the feature request uses `"OATHFISH_DATA_DIR": "${CLAUDE_PLUGIN_ROOT}/docs/runs"` — this is WRONG. It should be `${CLAUDE_PLUGIN_DATA}/runs`.

4. **Dynamic tool updates via `list_changed` enable runtime tool evolution.** The MCP server can notify Claude Code when its tool set changes. OathFish could theoretically register phase-specific tools dynamically (e.g., only expose `amplify_*` tools when in the AMPLIFY phase), but this adds complexity with marginal benefit since tool search already handles deferred loading.

5. **Tool Search is automatically triggered and affects how tools should be documented.** With ~28 tools across 6 engines, OathFish's tool descriptions could consume significant context. At 28 tools with moderately detailed descriptions (say ~200 tokens each), that is ~5,600 tokens of tool definitions. Whether this triggers the 10% threshold depends on the model's context window. With a 200K context window, 10% = 20,000 tokens — OathFish stays comfortably below. But if other MCP servers are also loaded (GitHub, Sentry, internal tools), the combined tool count could push past the threshold. When Tool Search activates, clear server instructions in the MCP server's metadata become essential for discoverability.

6. **The 25,000 token output limit is a constraint on MCP tool responses.** The `amplify_aggregate()` tool returns per-archetype distributions, overall statistics, and network effects for 30 archetypes. The `deliberation_get_position_map()` tool returns all 30 archetypes with their full evolution history across 6 rounds. These could easily exceed 10,000 tokens. The feature request must account for paginated or summarized MCP responses, or set `MAX_MCP_OUTPUT_TOKENS` higher in the plugin's environment.

7. **MCP Resources are a read-only attachment mechanism, not a tool invocation mechanism.** Resources are fetched and attached to context when referenced via `@server:protocol://`. This is conceptually different from tool calls. OathFish could expose resources like `@oathfish-engine:run://current/position-map` for easy reference, but the primary interaction will be through tool calls, not resource references.

8. **MCP Prompts as Commands could create natural shortcuts.** OathFish could expose MCP prompts like `/mcp__oathfish-engine__status` for quick state checks, though the existing `/oathfish` command system is more natural for user interaction.

---

## What Maps to OathFish

### Direct Mapping: Plugin MCP Server Configuration (C-01, C-06)

The `.mcp.json` at the plugin root is the exact mechanism specified by C-01 (Claude Code plugin) and C-06 (MCP stdio transport). The documentation confirms:

```json
{
  "mcpServers": {
    "oathfish-engine": {
      "type": "stdio",
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/engine/server.py"],
      "env": {
        "OATHFISH_DATA_DIR": "${CLAUDE_PLUGIN_DATA}/runs"
      }
    }
  }
}
```

Note the correction from the feature request: `${CLAUDE_PLUGIN_DATA}` replaces `${CLAUDE_PLUGIN_ROOT}` for the data directory. This ensures run data survives plugin updates, which is critical for cross-run calibration (C-27, C-34).

### Direct Mapping: All State Mutations Through MCP (C-12, C-23)

C-12 (all state mutations flow through MCP tools) and C-23 (all state changes flush to disk immediately) are enabled by the stdio transport's synchronous request-response model. Every tool call returns a response; the server can guarantee disk flush before responding. The documentation confirms that stdio servers run as local processes with direct filesystem access — no network latency between state mutation and disk write.

### Direct Mapping: Deterministic Core (C-02) vs Creative Shell (C-03)

The MCP documentation's entire architecture validates the OathFish split:
- **MCP server (C-02)**: Handles all deterministic computation — state transitions, convergence detection, graph operations, statistical aggregation, keyword sentiment, calibration tracking. Same inputs always produce same outputs.
- **Claude agents (C-03)**: Handle all creative work — archetype reasoning, persona generation, debate facilitation, report writing. Non-deterministic by design.

The MCP protocol enforces this boundary architecturally: agents invoke MCP tools for deterministic work, and the MCP server never invokes agents. Information flows in one direction for computation, the opposite direction for creative output.

### Direct Mapping: 28 Tools Across 6 Engines

The feature request specifies ~28 tools across 6 engines. The MCP documentation imposes no limit on tool count per server. Each tool is registered with a name, description, and input schema. The 6-engine organization (State Machine, Deliberation, Graph, Amplification, Metrics, Calibration) maps cleanly to Python module structure:

| Engine | Tool Count | Feature Request Section |
|--------|-----------|------------------------|
| State Machine | 5 | 4.1.1 (state_init, state_transition, state_get, state_checkpoint, state_resume) |
| Deliberation | 5 | 4.1.2 (deliberation_init, deliberation_record_round, deliberation_track_evolution, deliberation_check_convergence, deliberation_get_position_map) |
| Graph | 5 | 4.1.3 (graph_init, graph_add_node, graph_add_edge, graph_query, graph_compute_centrality) |
| Amplification | 3 | 4.1.4 (amplify_init, amplify_record_batch, amplify_aggregate) |
| Metrics | 3 | 4.1.5 (metrics_compute_round, metrics_sentiment_keyword, metrics_get_trend) |
| Calibration | 5 | 4.1.6 implied (calibration_record_prediction, calibration_record_outcome, calibration_get_domain_bias, calibration_get_archetype_bias, calibration_get_ensemble_metrics) |
| **Total** | **26** | (Plus 2 possible utility tools: health_check, get_run_summary) |

### Direct Mapping: Auto-Start Lifecycle

The documentation states: "At session startup, servers for enabled plugins connect automatically." This means the OathFish MCP server starts when the user opens Claude Code in a project where the OathFish plugin is enabled. No manual `claude mcp add` needed. The SessionStart hook in `hooks.json` can then query `state_get()` to detect active runs and offer resume — a clean startup sequence.

### Direct Mapping: Environment Variable Expansion

The `.mcp.json` uses `${CLAUDE_PLUGIN_ROOT}` for the server script path and `${CLAUDE_PLUGIN_DATA}` for the data directory. The documentation confirms these variables are expanded at server startup. Additional variables like `${OATHFISH_LOG_LEVEL}` or `${OATHFISH_MAX_ARCHETYPES}` could be exposed via the `env` block with `${VAR:-default}` fallback syntax.

---

## What Maps to the Research

### Calibration Engine Requires MCP Determinism (2602.19520, C-27, C-28)

The calibration decomposition paper (2602.19520) shows that calibration is structured across 4 components: universal horizon effect (30.2% R^2), domain intercept (14.6% R^2), domain-by-horizon interaction (26.0% R^2), and scale effect (16.5% R^2). Together these explain 87.3% of calibration variance. For OathFish, the Calibration Engine's 5 MCP tools (`calibration_record_prediction`, `calibration_record_outcome`, `calibration_get_domain_bias`, `calibration_get_archetype_bias`, `calibration_get_ensemble_metrics`) must compute these structured decompositions deterministically.

This is exactly why the MCP boundary exists. If a Claude agent computed calibration corrections, the non-deterministic reasoning would introduce noise into the correction signal. The MCP server computes domain-specific bias as a pure mathematical function: for each domain d, compute the mean signed error across all resolved predictions in that domain, apply additive correction. The same resolved outcomes + same prediction history always produces the same correction. C-02 (deterministic MCP) is not an architectural preference — it is a mathematical requirement for calibration to converge.

The persistent data concern is real: calibration history must survive across runs (C-27: track from run 1, apply from run 3+). `${CLAUDE_PLUGIN_DATA}` ensures this data persists through plugin updates. The MCP server loads calibration history from `${OATHFISH_DATA_DIR}/calibration/` at startup and appends to it after each `calibration_record_outcome()` call. C-34 (holdout 20%) is implemented as a deterministic partition at recording time — every 5th resolved prediction is flagged as holdout, never fed back into the correction model.

### Acquiescence Correction Requires Deterministic Aggregation (2402.19379, C-26, C-27)

The silicon crowd paper (2402.19379) demonstrated that LLMs exhibit 57% acquiescence bias (mean predictions significantly above 50%, t(1006)=86.20, p<0.001). More critically, when LLMs see others' predictions and update, the updated predictions are WORSE than simple averaging (GPT-4: updated=0.14, simple avg=0.13, p=0.011; Claude 2: updated=0.15, simple avg=0.14, p=0.001).

This maps to two MCP requirements:

1. **`amplify_aggregate()` must compute median aggregation, not ask Claude to synthesize results.** The aggregation is a deterministic function: collect all 1,500 amplification responses, compute per-archetype action distributions, compute cross-archetype adoption curves, apply domain-specific debiasing corrections. If a Claude agent "summarized" 1,500 responses, it would introduce acquiescence into the summary itself.

2. **The A/B test infrastructure (C-26) requires deterministic comparison.** Baseline amplification runs BEFORE deliberation. Deliberation-informed amplification runs AFTER. The MCP server stores both result sets and computes the delta deterministically. The report analyst (C-03, creative) interprets the delta, but the delta itself is MCP-computed.

The `amplify_aggregate()` output — per-archetype distributions, overall adoption rates, polarization indices — is structured data that could easily exceed the 10,000 token warning threshold when 30 archetypes each have action distributions, confidence distributions, and theme clusters. The plugin should set `MAX_MCP_OUTPUT_TOKENS` to at least 50,000, or implement pagination in the MCP tool (e.g., `amplify_aggregate(archetype_ids=["cautious-vc", "scrappy-founder"])` for per-archetype detail).

### Diversity Tracking Must Be Deterministic (2305.14325, 2402.19379, C-32)

The multiagent debate paper (2305.14325) warns that debates "typically converged into single final answers [that] were not necessarily correct." The ensemble paper (2402.19379) shows acquiescence drives this convergence. C-32 mandates tracking a diversity index per round and injecting contrarian scenarios when diversity drops below 0.15 before round 5.

The diversity index computation is a pure function of archetype positions: standard deviation of argument theme embeddings, or simpler — the count of distinct argument clusters divided by total arguments. This MUST be MCP-computed (`metrics_compute_round()`) because a Claude agent asked "is there enough diversity?" will tend to answer "yes" (acquiescence again). The MCP server returns a number; the coordinator acts on it.

### Independent Predictions in Round 6 Need Schema Enforcement (2402.19379, C-33)

C-33 mandates no numeric predictions shared until the final independent round. Round 6 uses `--json-schema` enforcement so each archetype produces structured JSON (`{prediction, decision, stance, confidence, base_rate_anchor, ...}`). The MCP server's `deliberation_record_round()` must accept two distinct position formats:
- Rounds 1-5: `ArgumentPosition` (qualitative: position_text, key_arguments, concerns, influenced_by)
- Round 6: `PredictionPosition` (quantitative: stance, confidence, timeframe, falsification_criteria)

This was identified as SPEC-01 in the spec audit — a critical contradiction where the data model assumed numeric fields every round. The MCP tool API must be polymorphic: `deliberation_record_round()` detects the round type and validates against the appropriate Pydantic model.

---

## What 10x the Outcome

### 1. Use `${CLAUDE_PLUGIN_DATA}` for Cross-Run Calibration State

The single highest-impact correction from the MCP documentation. The feature request routes run data through `${CLAUDE_PLUGIN_ROOT}/docs/runs`. This means every plugin update wipes calibration history. Since C-27 mandates tracking acquiescence from run 1 and applying corrections from run 3+, and since 2602.19520 shows calibration requires structured historical data across many resolved predictions, losing this history resets the entire calibration trajectory.

**Fix**: `"OATHFISH_DATA_DIR": "${CLAUDE_PLUGIN_DATA}/runs"`. All run artifacts, calibration history, archetype prediction records, and holdout sets live under `${CLAUDE_PLUGIN_DATA}`. The plugin code under `${CLAUDE_PLUGIN_ROOT}` contains only code, prompts, and templates — never state.

This correction touches: C-15 (persistence), C-16 (resumability), C-23 (write-through), C-27 (calibration tracking), C-34 (holdout set).

### 2. MCP Server Instructions for Tool Search Discoverability

When Tool Search activates (due to other MCP servers consuming context), OathFish's 26 tools must be discoverable by description alone. The documentation says: "Server instructions help Claude understand when to search for your tools." The MCP server should include rich server-level instructions:

```
OathFish Engine: Deterministic computation core for swarm-based predictive intelligence.
Use these tools for: state management (run lifecycle, checkpoints, resume),
deliberation tracking (round recording, position evolution, convergence detection),
graph operations (entity/relationship CRUD, centrality computation),
mass amplification aggregation (batch recording, statistical distributions),
metrics computation (round metrics, keyword sentiment, trend analysis),
and calibration (prediction recording, outcome tracking, domain bias, ensemble metrics).
NEVER compute these deterministically yourself — always delegate to oathfish-engine tools.
```

This instruction serves double duty: it helps Tool Search find the right tools, and it reinforces the C-02/C-03 boundary (deterministic MCP vs creative agents) even when the full tool list is deferred.

### 3. Paginated MCP Tool Responses for Large Outputs

The 25,000 token default limit (and 10,000 token warning) means several OathFish tools need output management:

- `deliberation_get_position_map()`: 30 archetypes x full evolution history across 6 rounds. At ~300 tokens per archetype per round, this is ~54,000 tokens uncompressed.
- `amplify_aggregate()`: 30 archetypes x (action_dist + confidence_dist + top_themes) + overall stats + network effects. Easily ~15,000-30,000 tokens.
- `graph_query(depth=2)`: A highly-connected node with 50 edges at depth 2 could return thousands of tokens.

**Solution**: Add optional `detail_level` and `archetype_ids` filter parameters to large-output tools. Default to summary mode; allow the agent to drill into specific archetypes on demand. This is the MCP equivalent of database pagination.

```
deliberation_get_position_map(detail_level="summary")  # 30 archetypes, latest stance only
deliberation_get_position_map(detail_level="full", archetype_ids=["cautious-vc"])  # Full history for one
```

### 4. `list_changed` Notifications for Phase-Aware Tool Visibility

The MCP documentation explicitly supports dynamic tool updates via `list_changed`. While all 26 tools could be registered at startup, a more elegant approach registers only phase-relevant tools:

- INIT/UNDERSTAND: state_*, graph_*
- DELIBERATE: state_*, deliberation_*, metrics_*
- AMPLIFY: state_*, amplify_*, calibration_record_prediction
- SYNTHESIZE: all read-only tools (get_*, query, aggregate)
- INTERACT: all read-only tools + deliberation_get_position_map

When the state machine transitions (via `state_transition()`), the MCP server fires `list_changed` and Claude Code refreshes the tool list. This reduces cognitive load on the agent (fewer irrelevant tools) and reinforces the phase-based pipeline (C-07).

**Caveat**: This adds complexity to the MCP server implementation. The simpler approach — register all tools at startup, rely on Tool Search if needed — may be preferred for the initial implementation. Phase-aware visibility is a v2 optimization.

### 5. MCP Resource Exposure for Context Injection

MCP Resources could expose key run artifacts as referenceable context:

- `@oathfish-engine:run://current/status` — current state, phase, round
- `@oathfish-engine:run://current/archetypes` — archetype list with latest stances
- `@oathfish-engine:run://current/convergence` — convergence metrics
- `@oathfish-engine:calibration://domain-bias` — calibration corrections by domain

This enables the user to type `Tell me about @oathfish-engine:run://current/convergence` without invoking a tool call. Resources are read-only and context-attached, which fits the "monitoring" use case during long deliberation runs. Not critical for v1, but a natural extension.

---

## Why?

The MCP server is not an implementation convenience — it is the **architectural guarantee** that OathFish's predictions improve over time. Without deterministic computation:

1. **Calibration cannot converge.** The calibration engine (2602.19520) requires that the same resolved outcomes produce the same bias corrections across runs. If a Claude agent "estimates" the domain bias, the estimate varies by run, by context window contents, by temperature. The correction signal degrades rather than accumulates. The MCP server computes `mean_signed_error(predictions, outcomes, domain)` — a pure function. Over 5+ runs, the correction converges to the true domain bias (subject to sample size, per 2602.19520's power analysis: 80% power at n=90 for d=0.3).

2. **A/B testing becomes meaningless.** C-26 mandates comparing baseline (pre-deliberation) against deliberation-informed predictions. If aggregation is non-deterministic, the A/B delta is noise. The MCP server computes `brier_score(baseline_predictions, outcomes)` and `brier_score(informed_predictions, outcomes)` — identical functions applied to different input sets. The delta is a true signal.

3. **Acquiescence correction requires exact arithmetic.** 2402.19379 showed 57% acquiescence bias (p<0.001). Correcting this requires subtracting a domain-specific offset from each prediction. If the offset is LLM-estimated, it inherits the very acquiescence it is trying to correct. The MCP server computes the offset from historical data — no LLM in the correction loop.

4. **Diversity monitoring must be independent of the monitored system.** C-32 requires detecting premature consensus during deliberation. If the coordinator (a Claude agent) judges whether consensus is premature, it is susceptible to the same acquiescence that drives the premature consensus. The MCP server computes a diversity index from position data — an external, deterministic measurement. The coordinator acts on the number but does not compute it.

5. **Reproducibility is a prerequisite for scientific credibility.** SC-11 (ForecastBench submission) and SC-12 (debiasing improvement measurement) require that OathFish's quantitative claims are reproducible. If an aggregate metric changes between runs with identical inputs, the claim is unfalsifiable. MCP determinism guarantees that `amplify_aggregate(same_results)` always returns the same distributions.

The `${CLAUDE_PLUGIN_DATA}` correction is the structural expression of this principle: persistent deterministic state must live outside the code deployment lifecycle. Plugin updates change computation logic; they must never change historical data.

---

## Reality Check?

### Concern 1: 28 tools is a lot — will this create context pressure?

At ~200 tokens per tool description (name + description + input schema), 28 tools consume ~5,600 tokens. With a 200K context window, this is 2.8% — well below the 10% Tool Search trigger. But if the user has 5-10 other MCP servers loaded (GitHub, Sentry, a database, internal tools), the combined tool count could reach 80-100 tools at ~16,000-20,000 tokens — approaching 10%. When Tool Search activates, OathFish's server instructions become the primary discovery mechanism. This is a real operational concern that the server instructions recommendation addresses.

### Concern 2: Output limits may truncate critical aggregation data

The `amplify_aggregate()` return for 30 archetypes with full distributions could exceed 25,000 tokens. This is not hypothetical — 30 archetypes x (action_dist + confidence_dist + theme_clusters + 5 top themes per archetype) + overall statistics + network effects is substantial structured JSON. The `MAX_MCP_OUTPUT_TOKENS=50000` setting or paginated response design is not optional — it is required for the system to function as specified.

### Concern 3: `${CLAUDE_PLUGIN_DATA}` persistence model is untested at OathFish scale

The documentation describes `${CLAUDE_PLUGIN_DATA}` as "persistent state that survives plugin updates," but does not specify storage limits, backup mechanisms, or performance characteristics with hundreds of MB of run data. OathFish's `docs/runs/` directory accumulates JSON files across runs — after 10 runs with 30 archetypes and 1,500 amplification results each, this could reach 50-100 MB. The assumption (A-new) is that `${CLAUDE_PLUGIN_DATA}` handles this gracefully.

### Concern 4: stdio transport means single-process, single-threaded MCP server

The Python MCP server runs as a single stdio process. When `amplify_record_batch()` is called with 500 results, the server must parse, validate, aggregate, and persist — blocking all other tool calls until complete. If the coordinator tries to call `state_get()` while a large batch is being processed, it waits. For 28 tools across 6 engines, the single-threaded constraint means all operations are serialized. This is acceptable for most operations (sub-second), but batch recording of amplification results may need to be chunked into smaller batches (50-100 results per call).

### Concern 5: The spec audit identified 3 critical contradictions — MCP alone does not resolve them

SPEC-01 (Position data model assumes numeric fields every round, but C-33 forbids numbers until round 6) is an MCP API design issue. The MCP server must implement polymorphic validation in `deliberation_record_round()` — detecting the round type and applying `ArgumentPosition` (rounds 1-5) vs `PredictionPosition` (round 6). This is solvable but was unresolved at spec audit time.

SPEC-02 (C-26 requires baseline amplification BEFORE deliberation, but the state machine flows UNDERSTAND -> DELIBERATE -> AMPLIFY) requires a state machine redesign: either a BASELINE_AMPLIFY sub-phase before DELIBERATE, or a parallel path. The MCP server's `state_transition()` legal transitions must be updated to accommodate this.

Both are addressable within the MCP architecture but require spec-level resolution before implementation.

---

## Citations from the References Document

### MCP Documentation (https://code.claude.com/docs/en/mcp)

- **stdio transport**: "Stdio servers run as local processes on your machine. They're ideal for tools that need direct system access or custom scripts." — Validates C-06 transport choice.
- **Plugin MCP lifecycle**: "At session startup, servers for enabled plugins connect automatically. If you enable or disable a plugin during a session, run `/reload-plugins` to connect or disconnect its MCP servers." — Confirms auto-start for OathFish engine.
- **`${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}`**: "Use `${CLAUDE_PLUGIN_ROOT}` for bundled plugin files and `${CLAUDE_PLUGIN_DATA}` for persistent state that survives plugin updates." — Critical distinction for calibration data persistence (C-27, C-34).
- **Environment variable expansion**: "`${VAR}` expands to the value of environment variable `VAR`. `${VAR:-default}` expands to `VAR` if set, otherwise uses `default`." — Enables configurable `OATHFISH_DATA_DIR`.
- **Dynamic tool updates**: "Claude Code supports MCP `list_changed` notifications, allowing MCP servers to dynamically update their available tools, prompts, and resources without requiring you to disconnect and reconnect." — Enables phase-aware tool visibility.
- **Tool Search activation**: "Claude Code automatically enables Tool Search when your MCP tool descriptions would consume more than 10% of the context window." — Drives server instructions requirement.
- **Output limits**: "Claude Code will display a warning when MCP tool output exceeds 10,000 tokens. [...] Default maximum is 25,000 tokens. [...] Set the `MAX_MCP_OUTPUT_TOKENS` environment variable." — Constrains amplify_aggregate() and deliberation_get_position_map() output design.
- **MCP Resources**: "Use the format `@server:protocol://resource/path` to reference a resource." — Potential for run status and calibration data exposure.
- **Plugin `.mcp.json` example**: `{"database-tools": {"command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server", "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"], "env": {"DB_URL": "${DB_URL}"}}}` — Template for OathFish `.mcp.json`.
- **Project scope .mcp.json security**: "Claude Code prompts for approval before using project-scoped servers from `.mcp.json` files." — Plugin-bundled servers bypass this (auto-approved with plugin enable).
- **Managed MCP**: "Deploy a fixed set of MCP servers that users cannot modify or extend." — Not relevant for OathFish (plugin distribution, not enterprise lockdown).

### Feature Request (docs/darwin/runs/0001-oathfish-swarm-engine/_meta/feature-request.md)

- **C-01**: "System must be a Claude Code plugin (plugin.json, .mcp.json, agents/, skills/, commands/)" — MCP server is part of the plugin structure.
- **C-02**: "Deterministic operations (metrics, aggregation, convergence, graph, state) handled by Python MCP server" — The core invariant. Same inputs produce same outputs.
- **C-03**: "Creative operations (archetype reasoning, persona generation, reports) handled by Claude agents" — The complementary invariant.
- **C-06**: "MCP server uses stdio transport configured via .mcp.json" — Direct mapping to MCP doc's stdio transport.
- **C-12**: "All state mutations flow through MCP server tools" — Enforced by archetype agents lacking Write tool (C-20).
- **C-15**: "State persists to disk after every MCP mutation" — Write-through caching enabled by stdio's synchronous model.
- **C-22**: "Coordinator never computes metrics — only orchestrates" — The C-02/C-03 boundary at the agent level.
- **C-23**: "All MCP state changes flush to disk immediately" — Guarantees recoverability (C-16).
- **C-27**: "Track per-domain acquiescence rate from run 1; apply corrections from run 3+" — Requires persistent cross-run state (`${CLAUDE_PLUGIN_DATA}`).
- **C-33**: "No numeric predictions shared between archetypes until final independent round" — Drives polymorphic MCP tool API design (SPEC-01).
- **Section 4.7 .mcp.json**: The current `"OATHFISH_DATA_DIR": "${CLAUDE_PLUGIN_ROOT}/docs/runs"` should be corrected to `"${CLAUDE_PLUGIN_DATA}/runs"`.

### Research Papers

- **2602.19520 (Calibration Decomposition)**: "87.3% of calibration variance explained by 4 structured components." Domain-specific bias (14.6% R^2) is the component OathFish can track per run. Power analysis: 80% power at n=90 for d=0.3. Mandates deterministic calibration computation (C-02) and persistent storage (`${CLAUDE_PLUGIN_DATA}`).
- **2402.19379 (Silicon Crowd)**: "Mean model predictions significantly above 50%: M=57.35, t(1006)=86.20, p<0.001." Acquiescence bias is real and large. "Simple average of human+machine predictions BEATS the LLM's own update" (GPT-4: p=0.011). Mandates deterministic aggregation in `amplify_aggregate()` (C-02) and A/B baseline testing (C-26).
- **2305.14325 (Multiagent Debate)**: "Debates typically converged into single final answers [that] were not necessarily correct." Mandates deterministic diversity monitoring (C-32) via `metrics_compute_round()` — the MCP server detects premature consensus, not the coordinator agent.
- **2409.19839 (ForecastBench)**: Superforecasters 0.096 Brier vs best LLM 0.122. Target benchmark for OathFish (SC-11). ForecastBench submission requires reproducible predictions — MCP determinism enables this.
- **2411.10109 (Generative Agent Simulations)**: 85% fidelity with real interview data. Validates archetype grounding (C-29) but raises the persistence question — grounding data should also live under `${CLAUDE_PLUGIN_DATA}` if curated per deployment.

### Spec Audit (docs/darwin/runs/0001-oathfish-swarm-engine/_meta/spec-audit.md)

- **SPEC-01**: "Position data model requires numeric stance/confidence every round, but C-33 forbids numbers until round 6." — Requires polymorphic `deliberation_record_round()` MCP tool accepting ArgumentPosition (rounds 1-5) or PredictionPosition (round 6).
- **SPEC-02**: "C-26 (baseline amplification BEFORE deliberation) contradicts the state machine flow (UNDERSTAND -> DELIBERATE -> AMPLIFY)." — Requires state machine redesign: either a BASELINE_AMPLIFY sub-phase or parallel path. Affects `state_transition()` legal transitions.
- **SPEC-03**: "`--resume SESSION_ID` used in amplification contradicts C-21 (claude -p is stateless)." — `--resume` injects prior context into prompt, does not make the call stateful. Clarification, not contradiction. But the MCP server's `amplify_init()` must generate fully self-contained prompts that embed deliberation context rather than relying on session references.
