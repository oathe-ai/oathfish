"""OathFish MCP Server -- Deterministic computation core.

stdio transport. 27 tools across 6 engines (21 core + 6 calibration/competence).
All state mutations flush to disk before returning (C-23).
All computation is deterministic (C-02).
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Server-level instructions for Tool Search discoverability
SERVER_INSTRUCTIONS = (
    "OathFish Engine: Deterministic computation core for swarm-based predictive intelligence. "
    "Use these tools for: state management (run lifecycle, checkpoints, resume), "
    "deliberation tracking (round recording, position evolution, convergence detection), "
    "graph operations (entity/relationship CRUD, centrality computation), "
    "mass amplification aggregation (batch recording, statistical distributions), "
    "metrics computation (round metrics, keyword sentiment, trend analysis), "
    "calibration tracking (prediction recording, outcome resolution, domain/archetype bias, ensemble metrics), "
    "question competence classification (domain routing, complexity assessment). "
    "NEVER compute these deterministically yourself -- always delegate to oathfish-engine tools."
)

app = FastMCP("oathfish-engine", instructions=SERVER_INSTRUCTIONS)

# Data directory from environment
# OATHFISH_DATA_DIR should be set to ${CLAUDE_PLUGIN_DATA}/runs by plugin.json
# Fallback: if CLAUDE_PLUGIN_DATA didn't resolve (literal $ in path), use
# ~/.oathfish/runs as a stable location outside the plugin cache
_raw_data_dir = os.environ.get("OATHFISH_DATA_DIR", "")
if not _raw_data_dir or "${" in _raw_data_dir:
    # Env var didn't resolve — use home directory fallback
    DATA_DIR = Path.home() / ".oathfish" / "runs"
else:
    DATA_DIR = Path(_raw_data_dir)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Import and register tool handlers from each engine module
from .state_machine import register_tools as register_state_tools
from .deliberation_engine import register_tools as register_deliberation_tools
from .graph_engine import register_tools as register_graph_tools
from .amplification_engine import register_tools as register_amplification_tools
from .metrics_engine import register_tools as register_metrics_tools
from .calibration_engine import register_tools as register_calibration_tools

register_state_tools(app, DATA_DIR)
register_deliberation_tools(app, DATA_DIR)
register_graph_tools(app, DATA_DIR)
register_amplification_tools(app, DATA_DIR)
register_metrics_tools(app, DATA_DIR)
register_calibration_tools(app, DATA_DIR)


def main() -> None:
    """Run MCP server via stdio transport."""
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
