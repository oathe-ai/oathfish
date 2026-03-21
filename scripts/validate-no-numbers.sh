#!/bin/bash
# C-33 Enforcement: Prevent coordinator from relaying numeric predictions to archetypes
# Runs as PreToolUse hook on Agent tool
# Exit 0 = allow Agent call
# Exit 2 = block Agent call, stderr becomes feedback to coordinator

set -euo pipefail

INPUT=$(cat)

# Only check archetype-related Agent calls
AGENT_TYPE=$(echo "$INPUT" | jq -r '.tool_input.agent_type // .tool_input.type // empty')
if [ -z "$AGENT_TYPE" ] || ! echo "$AGENT_TYPE" | grep -q "archetype"; then
  exit 0
fi

# Read current round from file bridge
ROUND_FILE="${CLAUDE_PLUGIN_DATA:-/tmp}/.current_round"
if [ -f "$ROUND_FILE" ]; then
  CURRENT_ROUND=$(cat "$ROUND_FILE")
else
  # If no round file, assume deliberation not active -- allow
  exit 0
fi

# Round 6+ = prediction round, numbers allowed
if [ "$CURRENT_ROUND" -ge 6 ] 2>/dev/null; then
  exit 0
fi

# Extract the prompt/message being sent to the archetype
PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // .tool_input.task // empty')

if [ -z "$PROMPT" ]; then
  exit 0
fi

# Check if the coordinator is relaying numeric predictions from other archetypes
# This catches the coordinator accidentally including other archetypes' numbers
if echo "$PROMPT" | grep -qiE \
  '(stance[:\s]*-?[0-9]|confidence[:\s]*[0-9]|probability[:\s]*[0-9]|[0-9]+(\.[0-9]+)?%|\b0\.[0-9]+\b|likelihood[:\s]*[0-9]|predict(ion)?[:\s]*[0-9]|estimate[:\s]*[0-9])'; then
  echo "C-33 VIOLATION: The prompt being sent to this archetype contains numeric predictions (stance scores, confidence percentages, or probability estimates). In rounds 1-5, relay QUALITATIVE ARGUMENTS ONLY between archetypes. Remove all numeric predictions from the relay and pass only argument text, reasoning, and concerns." >&2
  exit 2
fi

# Allow if no numeric patterns detected in relay
exit 0
