#!/bin/bash
# OathFish setup: install Python dependencies and verify MCP server starts
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$0")")}"

echo "Installing OathFish dependencies..."
pip3 install -r "$PLUGIN_ROOT/engine/requirements.txt" --quiet

echo "Verifying MCP server starts..."
timeout 5 python3 "$PLUGIN_ROOT/engine/server.py" --verify 2>/dev/null || {
  echo "WARNING: MCP server failed to start. Check Python 3.11+ and dependencies."
  exit 1
}

echo "Creating data directory..."
mkdir -p "${CLAUDE_PLUGIN_DATA:-$PLUGIN_ROOT/data}/runs"

echo "OathFish setup complete."
