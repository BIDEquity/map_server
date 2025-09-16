#!/usr/bin/env bash
set -euo pipefail

CLAUDE=$(command -v claude || true)
if [[ -z "$CLAUDE" ]]; then
  echo "Claude CLI not found. Install it with: npm i -g @anthropic-ai/claude-code"
  exit 1
fi

VENV="${MAPSERVER_VENV:-$HOME/.map-server/venv}"
TASKMASTER_NAME="taskmaster-ai"

set +e
$CLAUDE mcp remove "$TASKMASTER_NAME" >/dev/null 2>&1
$CLAUDE mcp remove map-server >/dev/null 2>&1
set -e

$CLAUDE mcp add "$TASKMASTER_NAME" -- npx -y --package=task-master-ai task-master-ai
$CLAUDE mcp add map-server -- "$VENV/bin/python" -m map_server.server

echo "Registered MCP servers with Claude."
