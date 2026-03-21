#!/bin/bash
# SessionStart hook: detect active OathFish runs, inject resume context
set -euo pipefail

DATA_DIR="${CLAUDE_PLUGIN_DATA:-/tmp}/runs"

if [ ! -d "$DATA_DIR" ]; then
  exit 0
fi

# Find runs with non-COMPLETE state
ACTIVE_RUNS=""
for RUN_DIR in "$DATA_DIR"/*/; do
  STATE_FILE="$RUN_DIR/_meta/run.json"
  if [ -f "$STATE_FILE" ]; then
    STATE=$(jq -r '.state // "UNKNOWN"' "$STATE_FILE" 2>/dev/null)
    RUN_ID=$(jq -r '.run_id // "unknown"' "$STATE_FILE" 2>/dev/null)
    if [ "$STATE" != "COMPLETE" ] && [ "$STATE" != "UNKNOWN" ]; then
      PHASE=$(jq -r '.state // "?"' "$STATE_FILE" 2>/dev/null)
      ROUND=$(jq -r '.current_round // "?"' "$STATE_FILE" 2>/dev/null)
      ACTIVE_RUNS="${ACTIVE_RUNS}Active OathFish run: ${RUN_ID} at phase ${PHASE}"
      if [ "$ROUND" != "?" ]; then
        ACTIVE_RUNS="${ACTIVE_RUNS}, round ${ROUND}"
      fi
      ACTIVE_RUNS="${ACTIVE_RUNS}. Resume with /oathfish --resume ${RUN_ID}\n"
    fi
  fi
done

if [ -n "$ACTIVE_RUNS" ]; then
  echo -e "$ACTIVE_RUNS"
fi

exit 0
