from __future__ import annotations
from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
import os, subprocess, hashlib, sys, shutil
from pathlib import Path

from .analysis.indexer import build_index as do_build_index
from .analysis.repo import inventory as do_inventory
from .analysis.deps import module_graph as do_module_graph
from .analysis.routes import route_extraction as do_routes
from .analysis.integrations import external_integrations as do_integrations
from .analysis.schemas import schemas_extract as do_schemas
from .analysis.domain import domain_clustering as do_domain
from .analysis.complexity import complexity_and_hotspots as do_hotspots
from .analysis.business_rules import business_rules as do_rules
from .analysis.blueprint import module_blueprint as do_blueprint
from .taskmaster.exporter import export_tasks as do_export_tasks

mcp = FastMCP('map-server')

def _deterministic_host_port(repo_root: Path):
    # Always use localhost to avoid needing sudo for loopback aliases
    host = "127.0.0.1"
    # Port: 5300–6299 from hash of repo path for deterministic but unique ports
    h = hashlib.sha1(str(repo_root).encode("utf-8")).hexdigest()
    port = 5300 + (int(h[:4], 16) % 1000)
    return host, port

def _ensure_ui_started():
    # Best-effort: spawn map_server.ui if desired
    auto = os.environ.get("MAPSERVER_AUTOSTART_UI", "1")
    if auto != "1":
        return
    repo_root = Path(os.environ.get("MAPSERVER_REPO_ROOT", "."))
    repo_root = repo_root.resolve()
    host, port = _deterministic_host_port(repo_root)
    env = os.environ.copy()
    env.setdefault("MAPSERVER_REPO_ROOT", str(repo_root))
    env.setdefault("MAPSERVER_UI_HOST", host)
    env.setdefault("MAPSERVER_UI_PORT", str(port))
    # Try to detect if something already listens there (best-effort, non-fatal)
    try:
        import socket
        with socket.create_connection((host, int(port)), timeout=0.15):
            return  # already up
    except Exception:
        pass
    # Spawn UI
    py = shutil.which("python3") or sys.executable
    try:
        subprocess.Popen([py, "-m", "map_server.ui"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

@mcp.tool
def build_index(root: str = '.') -> dict: return do_build_index(root)

@mcp.tool
def repo_inventory(root: str = '.') -> dict: return do_inventory(root)

@mcp.tool
def module_graph(root: str = '.', include_third_party: bool = False) -> dict: return do_module_graph(root, include_third_party)

@mcp.tool
def route_extraction(root: str = '.', limit: Optional[int] = None) -> list: return do_routes(root, limit)

@mcp.tool
def external_integrations(root: str = '.') -> list: return do_integrations(root)

@mcp.tool
def schemas_extract(root: str = '.', include: Optional[List[str]] = None) -> dict: return do_schemas(root, include)

@mcp.tool
def domain_clustering(root: str = '.', k: Optional[int] = None, algorithm: Optional[str] = None) -> dict: return do_domain(root, k, algorithm)

@mcp.tool
def complexity_and_hotspots(root: str = '.', since: Optional[str] = None) -> list: return do_hotspots(root, since)

@mcp.tool
def business_rules(root: str = '.', module_globs: Optional[List[str]] = None) -> list: return do_rules(root, module_globs)

@mcp.tool
def module_blueprint(module: str, target_stack: Dict[str, Any]) -> dict: return do_blueprint(module, target_stack)

@mcp.tool
def export_taskmaster(strategy: str = 'domains', output: str = '.mapserver/export/tasks.json') -> dict: return do_export_tasks(strategy=strategy, output=output)

def main():
    _ensure_ui_started()
    mcp.run()

if __name__ == '__main__':
    main()
