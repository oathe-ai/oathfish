#!/bin/bash
# Dynamic context injection: returns current OathFish run state for skill preprocessing
set -euo pipefail

ACTIVE_RUN_FILE="${CLAUDE_PLUGIN_DATA:-/tmp}/.active_run"

if [ ! -f "$ACTIVE_RUN_FILE" ]; then
  echo "No active OathFish run."
  exit 0
fi

RUN_ID=$(cat "$ACTIVE_RUN_FILE")
STATE_FILE="${CLAUDE_PLUGIN_DATA:-/tmp}/runs/$RUN_ID/_meta/run.json"

if [ ! -f "$STATE_FILE" ]; then
  echo "Run $RUN_ID state file not found."
  exit 0
fi

echo "Active run: $RUN_ID"
jq -r '"State: \(.state // "UNKNOWN")\nTopic: \(.config.topic // "unknown")\nRound: \(.current_round // 0)\nArchetypes: \(.config.archetype_count // 30)"' "$STATE_FILE" 2>/dev/null || echo "Could not parse state file."
