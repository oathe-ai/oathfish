#!/bin/bash
# SessionStart (compact) hook: re-inject critical OathFish state after compaction
set -euo pipefail

DATA_DIR="${CLAUDE_PLUGIN_DATA:-/tmp}/runs"
ACTIVE_RUN_FILE="${CLAUDE_PLUGIN_DATA:-/tmp}/.active_run"

if [ ! -f "$ACTIVE_RUN_FILE" ]; then
  exit 0
fi

RUN_ID=$(cat "$ACTIVE_RUN_FILE")
STATE_FILE="$DATA_DIR/$RUN_ID/_meta/run.json"

if [ ! -f "$STATE_FILE" ]; then
  exit 0
fi

STATE=$(jq -r '.state // "UNKNOWN"' "$STATE_FILE")
ROUND=$(jq -r '.current_round // 0' "$STATE_FILE")
TOPIC=$(jq -r '.config.topic // "unknown"' "$STATE_FILE")

cat <<EOF
[OathFish State Recovery After Compaction]
Run: $RUN_ID
Phase: $STATE
Current Round: $ROUND
Topic: $TOPIC

IMPORTANT: Context was compacted. Re-query MCP tools for full state:
- Call state_get() for complete run state
- Call deliberation_get_position_map() for current archetype positions
- Call metrics_get_trend("diversity", 6) for diversity trajectory
- Resume deliberation from round $ROUND
EOF

exit 0
