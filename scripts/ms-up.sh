#!/usr/bin/env bash
set -euo pipefail

# Repo root = current working directory unless MAPSERVER_REPO_ROOT is set
REPO_ROOT="${MAPSERVER_REPO_ROOT:-$PWD}"

# Compute deterministic /24 octet from path hash (2..201)
if command -v shasum >/dev/null 2>&1; then
  h="$(printf %s "$REPO_ROOT" | shasum | cut -c1-2)"
else
  h="$(printf %s "$REPO_ROOT" | sha1sum | cut -c1-2)"
fi
oct=$(( (16#$h % 200) + 2 ))
HOST="127.0.0.$oct"

# Compute deterministic port in 5300-6299
phex="$(echo -n "$REPO_ROOT" | tr -d '\n' | (command -v shasum >/dev/null 2>&1 && shasum || sha1sum) | cut -c1-4)"
pdec=$(( 16#$phex ))
PORT=$(( 5300 + (pdec % 1000) ))

# Check loopback alias (skip sudo to avoid hangs in Claude Code)
if [[ "$(uname -s)" == "Darwin" ]]; then
  if ! ifconfig lo0 | grep -q "$HOST"; then
    echo "Note: Loopback alias $HOST not configured."
    echo "To add it manually, run: sudo ifconfig lo0 alias $HOST up"
    echo "Using 127.0.0.1 as fallback..."
    HOST="127.0.0.1"
  fi
elif [[ "$(uname -s)" == "Linux" ]]; then
  if ! ip addr show lo | grep -q "$HOST"; then
    echo "Note: Loopback alias $HOST not configured."
    echo "To add it manually, run: sudo ip addr add $HOST/8 dev lo"
    echo "Using 127.0.0.1 as fallback..."
    HOST="127.0.0.1"
  fi
fi

# Global venv under ~/.map-server/venv (single venv for all projects)
VENV="${MAPSERVER_VENV:-$HOME/.map-server/venv}"
if [[ ! -d "$VENV" ]]; then
  echo "Creating global venv at $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip
fi

# Install/upgrade the local package into the venv (editable if inside source tree)
if [[ -f "pyproject.toml" ]]; then
  echo "Installing map-server (editable) into $VENV"
  "$VENV/bin/pip" install -e .
fi

# Start MCP (optional) in background if --with-mcp
WITH_MCP="${1:-}"
if [[ "$WITH_MCP" == "--with-mcp" ]]; then
  echo "Starting MCP server for $REPO_ROOT ..."
  (cd "$REPO_ROOT" && MAPSERVER_REPO_ROOT="$REPO_ROOT" "$VENV/bin/python" -m map_server.server >/tmp/ms-mcp-$oct.log 2>&1 &)
fi

# Start UI server (bind to project-specific host:port)
echo "Starting UI on http://$HOST:$PORT  (repo=$REPO_ROOT)"
MAPSERVER_REPO_ROOT="$REPO_ROOT" MAPSERVER_UI_HOST="$HOST" MAPSERVER_UI_PORT="$PORT" "$VENV/bin/python" -m map_server.ui
