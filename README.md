# Map Server with UI (MCP + React) — GitHub-ready

## One-line install (when hosted on GitHub)
```bash
curl -fsSL https://raw.githubusercontent.com/<your-org>/map-server/main/install.sh | bash
```
> Replace `<your-org>` once you push this repo.

### Local install (from a zip or clone)
```bash
# From inside the extracted repo folder:
bash install.sh
# or
REPO_URL=https://github.com/<your-org>/map-server.git bash install.sh
```

### What the installer does
- Installs to `~/.map-server/repo` and creates a global Python venv at `~/.map-server/venv`.
- Builds the frontend (if `npm` is available).
- Registers MCP servers with **Claude Code** (if `claude` CLI is available):
  - `map-server` (our MCP)
  - `taskmaster-ai` (via `npx -y --package=task-master-ai task-master-ai`) — per Task Master docs.
- Patches `~/.claude/settings.json` (adds Bash permissions; enables project MCP servers).
- Creates the **`/show-ms`** slash command at `~/.claude/commands/show-ms.md`.

### Multi-project support
- Deterministic host & port derived from repo path (e.g., `127.0.0.X:53xx`).
- UI autostarts whenever MCP server is invoked by Claude.
- Manual launcher: `./scripts/ms-up.sh --with-mcp`

### Uninstall
Remove `~/.map-server`, and delete `~/.claude/commands/show-ms.md`. Use `claude mcp remove map-server taskmaster-ai` to deregister.
