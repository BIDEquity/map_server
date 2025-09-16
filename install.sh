#!/usr/bin/env bash
set -euo pipefail

# --------- Parse command line arguments ----------
OVERWRITE=false
for arg in "$@"; do
  case $arg in
    --overwrite)
      OVERWRITE=true
      shift
      ;;
    --help|-h)
      echo "Map Server installer (macOS/Linux)"
      echo ""
      echo "Usage: bash install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --overwrite    Force overwrite existing installations (MCP servers, commands)"
      echo "  --help, -h     Show this help message"
      echo ""
      echo "Environment variables:"
      echo "  REPO_URL       GitHub repo URL (default: https://github.com/your-org/map-server.git)"
      echo "  MAPSERVER_HOME Installation directory (default: ~/.map-server)"
      echo "  MAPSERVER_VENV Virtual environment directory (default: ~/.map-server/venv)"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

if [[ "$OVERWRITE" == "true" ]]; then
  echo "==> Map Server installer (macOS/Linux) [OVERWRITE MODE]"
else
  echo "==> Map Server installer (macOS/Linux)"
fi

# --------- Inputs & defaults ----------
REPO_URL_DEFAULT="https://github.com/your-org/map-server.git"   # <- Change once you push to GitHub
REPO_URL="${REPO_URL:-$REPO_URL_DEFAULT}"
MAP_HOME="${MAPSERVER_HOME:-$HOME/.map-server}"
REPO_DIR="$MAP_HOME/repo"
VENV="${MAPSERVER_VENV:-$HOME/.map-server/venv}"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
CLAUDE_CMDS="$HOME/.claude/commands"
TASKMASTER_NAME="taskmaster-ai"

mkdir -p "$MAP_HOME"

# Detect if running from a local checkout (install.sh alongside pyproject.toml & map_server/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" >/dev/null 2>&1 && pwd || pwd)"
LOCAL_SRC=""
if [[ -f "$SCRIPT_DIR/pyproject.toml" && -d "$SCRIPT_DIR/map_server" ]]; then
  LOCAL_SRC="$SCRIPT_DIR"
fi

# --------- Sync source into ~/.map-server/repo ----------
if [[ -n "$LOCAL_SRC" ]]; then
  echo "==> Installing from local folder: $LOCAL_SRC"
  mkdir -p "$REPO_DIR"
  rsync -a --delete "$LOCAL_SRC"/ "$REPO_DIR"/
else
  if [[ -d "$REPO_DIR/.git" ]]; then
    echo "==> Updating existing repo at $REPO_DIR"
    git -C "$REPO_DIR" fetch --all -q || true
    git -C "$REPO_DIR" reset -q --hard origin/main || true
  else
    echo "==> Cloning map-server repo to $REPO_DIR"
    mkdir -p "$REPO_DIR"
    if git clone --depth=1 "$REPO_URL" "$REPO_DIR"; then
      echo "==> Clone succeeded"
    else
      echo "ERROR: Git clone failed from $REPO_URL"
      echo "If running from a local zip/checkout, run this script from inside the folder so it can install locally."
      echo "Or set REPO_URL to your GitHub repo before running: REPO_URL=https://github.com/<org>/map-server.git bash install.sh"
      exit 1
    fi
  fi
fi

# --------- Python venv & package install ----------
PY=$(command -v python3 || true)
if [[ -z "${PY}" ]]; then
  echo "ERROR: python3 not found; please install Python 3.10+ and re-run."
  exit 1
fi

if [[ ! -d "$VENV" ]]; then
  echo "==> Creating global venv at $VENV"
  "$PY" -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip >/dev/null
fi

echo "==> Installing map-server into venv"
"$VENV/bin/pip" install -e "$REPO_DIR"

# --------- Build the frontend (best-effort) ----------
if command -v npm >/dev/null 2>&1; then
  echo "==> Building frontend (Vite)"
  (cd "$REPO_DIR/frontend" && (npm ci || npm i) && npm run build) || echo "WARN: UI build failed (continuing)."
else
  echo "WARN: npm not found; skipping UI build (you can run it later)."
fi

# --------- Task Master MCP (npx) registration ----------
# We'll prefer npx package 'task-master-ai' and add as MCP via 'claude mcp add' if available.
CLAUDE=$(command -v claude || true)
if [[ -z "$CLAUDE" && "$(command -v npm || true)" != "" ]]; then
  echo "==> Installing Claude Code CLI globally via npm (@anthropic-ai/claude-code)"
  npm install -g @anthropic-ai/claude-code || echo "WARN: Failed to install Claude Code CLI; will continue."
  CLAUDE=$(command -v claude || true)
fi

if [[ -n "$CLAUDE" ]]; then
  if [[ "$OVERWRITE" == "true" ]]; then
    echo "==> Force-registering MCP servers with Claude Code (overwrite mode)"
  else
    echo "==> Registering MCP servers with Claude Code (user scope)"
  fi
  
  # Add Task Master (npx, package task-master-ai)
  if [[ "$OVERWRITE" == "true" ]]; then
    # Force remove and re-add
    set +e
    $CLAUDE mcp remove "$TASKMASTER_NAME" >/dev/null 2>&1
    set -e
    $CLAUDE mcp add "$TASKMASTER_NAME" -- npx -y --package=task-master-ai task-master-ai
  else
    # Check if already exists
    set +e
    if ! $CLAUDE mcp list 2>/dev/null | grep -q "^$TASKMASTER_NAME"; then
      $CLAUDE mcp add "$TASKMASTER_NAME" -- npx -y --package=task-master-ai task-master-ai
    else
      echo "  Task Master MCP server already registered (use --overwrite to force update)"
    fi
    set -e
  fi

  # Add map-server (stdio via Python in our venv) — autostarts UI via env
  if [[ "$OVERWRITE" == "true" ]]; then
    # Force remove and re-add
    set +e
    $CLAUDE mcp remove map-server >/dev/null 2>&1
    set -e
    $CLAUDE mcp add map-server -- "$VENV/bin/python" -m map_server.server
  else
    # Check if already exists
    set +e
    if ! $CLAUDE mcp list 2>/dev/null | grep -q "^map-server"; then
      $CLAUDE mcp add map-server -- "$VENV/bin/python" -m map_server.server
    else
      echo "  map-server MCP server already registered (use --overwrite to force update)"
    fi
    set -e
  fi

  echo "==> MCP servers registered. You may need to restart Claude Code."
else
  echo "WARN: 'claude' CLI not found; skipping MCP registration. Install @anthropic-ai/claude-code and run:"
  echo "      ~/.map-server/repo/scripts/register-with-claude.sh"
fi

# --------- Patch ~/.claude/settings.json (allowed tools) ----------
echo "==> Patching ~/.claude/settings.json"
mkdir -p "$(dirname "$CLAUDE_SETTINGS")"
if [[ ! -s "$CLAUDE_SETTINGS" ]]; then
  echo "{}" > "$CLAUDE_SETTINGS"
fi
# Use Python for a robust JSON merge
"$PY" - "$CLAUDE_SETTINGS" <<'PY'
import json, os, sys
p=sys.argv[1]
try:
  data=json.load(open(p))
except Exception:
  data={}
perms=data.setdefault("permissions",{})
allow=perms.setdefault("allow",[])
for item in ["Bash(open:*)","Bash(xdg-open:*)","Bash(git rev-parse:*)","Bash(python3:*)"]:
  if item not in allow: allow.append(item)
data["enableAllProjectMcpServers"]=True
json.dump(data, open(p,"w"), indent=2)
print(p)
PY

# --------- Install /show-ms slash command ----------
if [[ "$OVERWRITE" == "true" ]]; then
  echo "==> Force-installing /show-ms slash command (overwrite mode)"
  mkdir -p "$CLAUDE_CMDS"
  cat > "$CLAUDE_CMDS/show-ms.md" <<'CMD'
---
allowed-tools: Bash(git rev-parse:*), Bash(python3:*), Bash(open:*), Bash(xdg-open:*), mcp__taskmaster-ai__initialize_project, mcp__map-server__build_index
description: Open the Map Server dashboard for the current repo
---

## Context

!`python3 - <<'PY'
import os, subprocess, hashlib, platform, json, sys
from pathlib import Path

# Determine repo root
try:
    repo_root = subprocess.run(["git","rev-parse","--show-toplevel"], check=True, text=True, capture_output=True).stdout.strip()
except Exception:
    repo_root = os.getcwd()

repo_path = Path(repo_root)

# Check if Task Master is initialized
taskmaster_dir = repo_path / ".taskmaster"
mapserver_dir = repo_path / ".mapserver"

needs_taskmaster = not taskmaster_dir.exists()
needs_mapserver_index = not mapserver_dir.exists() or not (mapserver_dir / "index.json").exists()

# Calculate deterministic URL
h = hashlib.sha1(repo_root.encode()).hexdigest()
octet = (int(h[:2],16) % 200) + 2
ip = f"127.0.0.{octet}"
phex = int(h[:4],16)
port = 5300 + (phex % 1000)
url = f"http://{ip}:{port}"

# Try to open URL if already initialized
if not needs_taskmaster and not needs_mapserver_index:
    cmd = ["open", url] if platform.system()=="Darwin" else ["xdg-open", url]
    try: subprocess.run(cmd, check=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception: pass

print(json.dumps({
    "repo": repo_root, 
    "url": url,
    "needs_taskmaster": needs_taskmaster,
    "needs_mapserver_index": needs_mapserver_index
}))
PY`

## Your task

1. Check the context above. 
2. If `needs_taskmaster` is true, initialize Task Master using the mcp__taskmaster-ai__initialize_project tool with projectRoot set to the repo path.
3. If `needs_mapserver_index` is true, build the Map Server index using the mcp__map-server__build_index tool with root set to the repo path.
4. Once everything is initialized, reply with **only** the URL to the dashboard for this repo.
CMD
else
  if [[ -f "$CLAUDE_CMDS/show-ms.md" ]]; then
    echo "==> /show-ms slash command already installed (use --overwrite to force update)"
  else
    echo "==> Installing /show-ms slash command"
    mkdir -p "$CLAUDE_CMDS"
    cat > "$CLAUDE_CMDS/show-ms.md" <<'CMD'
---
allowed-tools: Bash(git rev-parse:*), Bash(python3:*), Bash(open:*), Bash(xdg-open:*), mcp__taskmaster-ai__initialize_project, mcp__map-server__build_index
description: Open the Map Server dashboard for the current repo
---

## Context

!`python3 - <<'PY'
import os, subprocess, hashlib, platform, json, sys
from pathlib import Path

# Determine repo root
try:
    repo_root = subprocess.run(["git","rev-parse","--show-toplevel"], check=True, text=True, capture_output=True).stdout.strip()
except Exception:
    repo_root = os.getcwd()

repo_path = Path(repo_root)

# Check if Task Master is initialized
taskmaster_dir = repo_path / ".taskmaster"
mapserver_dir = repo_path / ".mapserver"

needs_taskmaster = not taskmaster_dir.exists()
needs_mapserver_index = not mapserver_dir.exists() or not (mapserver_dir / "index.json").exists()

# Calculate deterministic URL
h = hashlib.sha1(repo_root.encode()).hexdigest()
octet = (int(h[:2],16) % 200) + 2
ip = f"127.0.0.{octet}"
phex = int(h[:4],16)
port = 5300 + (phex % 1000)
url = f"http://{ip}:{port}"

# Try to open URL if already initialized
if not needs_taskmaster and not needs_mapserver_index:
    cmd = ["open", url] if platform.system()=="Darwin" else ["xdg-open", url]
    try: subprocess.run(cmd, check=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception: pass

print(json.dumps({
    "repo": repo_root, 
    "url": url,
    "needs_taskmaster": needs_taskmaster,
    "needs_mapserver_index": needs_mapserver_index
}))
PY`

## Your task

1. Check the context above. 
2. If `needs_taskmaster` is true, initialize Task Master using the mcp__taskmaster-ai__initialize_project tool with projectRoot set to the repo path.
3. If `needs_mapserver_index` is true, build the Map Server index using the mcp__map-server__build_index tool with root set to the repo path.
4. Once everything is initialized, reply with **only** the URL to the dashboard for this repo.
CMD
  fi
fi

echo "==> Install complete."
echo ""
echo "Tips:"
echo " - Start Claude in your legacy repo, then run the slash command:  /show-ms"
echo " - Or launch manually for a repo:  ~/.map-server/repo/scripts/ms-up.sh --with-mcp"
if [[ "$OVERWRITE" != "true" ]]; then
  echo " - To force update existing installations, run:  bash install.sh --overwrite"
fi
