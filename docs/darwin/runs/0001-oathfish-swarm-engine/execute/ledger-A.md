# Execution Ledger - Worker A: MCP Core Engines

## Batch 1: Foundation (Phase A)
- [x] A.1: Create engine/models.py -- All ~30 Pydantic models
  - VERIFIED: 13 PredictionPosition fields, 9 RunPhase states, Position union works
- [x] A.2: Create engine/persistence.py -- atomic_write_json, read_json, ensure_run_dir
  - VERIFIED: imports clean, used in all engine smoke tests
- [x] G.2: Create engine/__init__.py -- Package init
  - VERIFIED: engine importable
- [x] G.3: Create engine/requirements.txt
  - VERIFIED: uv pip install succeeded (mcp>=1.0.0, pydantic>=2.0.0)

## Batch 2: State Machine (Phase B)
- [x] B.1: Create engine/state_machine.py -- 5 MCP tools
  - VERIFIED: 9 states in transition table, illegal transitions rejected, ERROR resume works, state persists to disk

## Batch 3: Deliberation Engine (Phase C)
- [x] C.1: Create engine/deliberation_engine.py -- 5 MCP tools
  - VERIFIED: Polymorphic round recording (C-33 enforcement), Jaccard evolution, diversity index with low-N guard, INJECT_CONTRARIAN fires on premature consensus

## Batch 4: Graph + Amplification + Metrics + Sentiment (Phases D, E, F)
- [x] D.1: Create engine/graph_engine.py -- 5 MCP tools
  - VERIFIED: CRUD, temporal filtering (expired edges excluded), centrality ranking
- [x] E.1: Create engine/amplification_engine.py -- 3 MCP tools
  - VERIFIED: Batch recording, aggregation with distributions, debiasing graceful degradation (no corrections file = no error)
- [x] F.1: Create engine/metrics_engine.py -- 3 MCP tools
  - VERIFIED: Round metrics with diversity/engagement/stability/coalitions, sentiment keyword, trend analysis
- [x] F.2: Create engine/sentiment.py -- Keyword word lists + compute_sentiment()
  - VERIFIED: Deterministic (same input = same output), ~200 positive + ~200 negative words, score range [-1.0, 1.0]

## Batch 5: Server Entry Point (Phase G)
- [x] G.1: Create engine/server.py -- MCP stdio entry point, register all 21 tools
  - VERIFIED: 27 tools registered (21 core + 6 calibration from Worker B), FastMCP with stdio transport
- [x] G.4: MCP env requirements documented -- Worker C's .mcp.json must include OATHFISH_DATA_DIR=${CLAUDE_PLUGIN_DATA}/runs and MAX_MCP_OUTPUT_TOKENS=50000

## Cross-Worker Notifications
- [x] Worker B already integrated: calibration_engine.py imported in server.py (27 total tools)
- [x] Worker B already integrated: server.py modified to register 6 calibration tools
- [ ] Notify executor-c when all core engines are ready

## Post-Implementation Fix
- [x] Fixed enum serialization: all .model_dump() calls changed to .model_dump(mode="json") for proper JSON output

## Smoke Test Results (20/20 passed)
1. state_init, state_transition, illegal rejection, error/resume, state_get
2. deliberation_init, record_round, C-33 enforcement, track_evolution, convergence
3. Prediction round recording, position map
4. Sentiment (positive/negative/neutral + determinism)
5. Graph CRUD, temporal filtering, centrality
6. Amplification batch recording, aggregation, debiasing graceful degradation
