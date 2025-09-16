from __future__ import annotations
import json, os, posixpath, urllib.parse, shutil, subprocess, sys, time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(os.getenv("MAPSERVER_REPO_ROOT", ".")).resolve()
MAP_DIR = REPO_ROOT / ".mapserver"
FRONTEND_DIR = (Path(__file__).resolve().parents[1] / "frontend" / "dist").resolve()

UI_HOST = os.getenv("MAPSERVER_UI_HOST", "127.0.0.1")
UI_PORT = int(os.getenv("MAPSERVER_UI_PORT", "5174"))
TASKMASTER_CLI = os.getenv("TASKMASTER_CLI") or shutil.which("task-master")

def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _compute_next_task(tasks: List[Dict[str, Any]]):
    by_id = {t.get("id"): t for t in tasks if isinstance(t.get("id"), int)}
    # If any in-progress, prefer it
    inprog = [t for t in tasks if t.get("status") == "in-progress"]
    if inprog:
        return inprog[0]
    # Otherwise find a pending task whose dependencies are all done
    done_ids = {t["id"] for t in tasks if t.get("status") == "done"}
    pending = [t for t in tasks if t.get("status") == "pending"]
    for t in sorted(pending, key=lambda x: x.get("id", 0)):
        deps = set(t.get("dependencies") or [])
        if deps.issubset(done_ids):
            return t
    # Fallback: first pending
    return pending[0] if pending else None

def _taskmaster_next_via_cli():
    if not TASKMASTER_CLI:
        return None
    try:
        # Try to run in the repo root and parse stdout
        proc = subprocess.run([TASKMASTER_CLI, "next"], cwd=str(REPO_ROOT), check=False,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out = proc.stdout.strip()
        # Heuristic parse: if JSON present, parse; else return as text
        try:
            data = json.loads(out)
            return data
        except Exception:
            return {"text": out}
    except Exception as e:
        return None

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        if path.startswith("/api/"):
            return str(REPO_ROOT / "404")
        if FRONTEND_DIR.exists():
            path = posixpath.normpath(urllib.parse.unquote(path))
            words = [w for w in path.split("/") if w]
            p = FRONTEND_DIR
            for w in words: p = p / w
            if p.is_dir(): p = p / "index.html"
            return str(p)
        return super().translate_path(path)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self.handle_api_get()
        try:
            return super().do_GET()
        except Exception:
            index = FRONTEND_DIR / "index.html"
            if index.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(index.read_bytes())
            else:
                self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self.handle_api_post()
        self.send_error(404, "Not Found")

    def _send_json(self, obj, code=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return {}

    # ---- API implementation ----
    def handle_api_get(self):
        m = self.path
        if m == "/api/status":
            # Check if map server index exists and return status
            has_index = MAP_DIR.exists() and (MAP_DIR / "export" / "tasks.json").exists()
            return self._send_json({
                "status": "ready" if has_index else "not_initialized",
                "repo_root": str(REPO_ROOT),
                "has_index": has_index,
                "taskmaster_available": TASKMASTER_CLI is not None
            })
        if m == "/api/tasks": return self._send_json(_read_json(MAP_DIR / "export" / "tasks.json", []))
        if m == "/api/graphs/module": return self._send_json(_read_json(MAP_DIR / "graphs" / "module_graph.json", {"nodes": [], "edges": []}))
        if m == "/api/graphs/routes": return self._send_json(_read_json(MAP_DIR / "graphs" / "routes.json", []))
        if m == "/api/domains": return self._send_json(_read_json(MAP_DIR / "domains" / "clusters.json", {"domains": []}))
        if m == "/api/rules": return self._send_json(_read_json(MAP_DIR / "rules" / "business_rules.json", []))
        if m == "/api/schemas": return self._send_json(_read_json(MAP_DIR / "schemas" / "canonical.json", {}))
        if m == "/api/integrations": return self._send_json(_read_json(MAP_DIR / "schemas" / "external.json", []))
        if m == "/api/next":
            tasks = _read_json(MAP_DIR / "export" / "tasks.json", [])
            nxt = _compute_next_task(tasks)
            return self._send_json({"next": nxt})
        if m == "/api/progress":
            tasks = _read_json(MAP_DIR / "export" / "tasks.json", [])
            done = sum(1 for t in tasks if t.get("status") == "done")
            inprog = sum(1 for t in tasks if t.get("status") == "in-progress")
            total = len(tasks)
            pct = int(round((done / total) * 100)) if total else 0
            return self._send_json({"done": done, "in_progress": inprog, "total": total, "percent": pct})
        return self._send_json({"error": "Not found"}, 404)

    def handle_api_post(self):
        if self.path.startswith("/api/tasks/") and self.path.endswith("/status"):
            try:
                parts = self.path.strip("/").split("/")
                task_id = int(parts[2])
            except Exception:
                return self._send_json({"error": "Invalid task id"}, 400)
            payload = self._read_body()
            new_status = payload.get("status")
            if new_status not in {"pending", "in-progress", "done", "deferred"}:
                return self._send_json({"error": "Invalid status"}, 400)
            tasks_path = MAP_DIR / "export" / "tasks.json"
            tasks = _read_json(tasks_path, [])
            updated = False
            for t in tasks:
                if t.get("id") == task_id:
                    t["status"] = new_status
                    updated = True
                    break
            if not updated:
                return self._send_json({"error": "Task not found"}, 404)
            _write_json(tasks_path, tasks)
            return self._send_json({"ok": True, "id": task_id, "status": new_status})

        # Begin/complete next task (Task Master bridge or local fallback)
        if self.path == "/api/next/begin":
            tasks_path = MAP_DIR / "export" / "tasks.json"
            tasks = _read_json(tasks_path, [])
            nxt = _compute_next_task(tasks)
            if not nxt: return self._send_json({"error": "No next task"}, 400)
            nxt["status"] = "in-progress"
            _write_json(tasks_path, tasks)
            return self._send_json({"ok": True, "id": nxt["id"], "status": "in-progress"})

        if self.path == "/api/next/complete":
            tasks_path = MAP_DIR / "export" / "tasks.json"
            tasks = _read_json(tasks_path, [])
            nxt = _compute_next_task(tasks)
            if not nxt: return self._send_json({"error": "No next task"}, 400)
            nxt["status"] = "done"
            _write_json(tasks_path, tasks)
            return self._send_json({"ok": True, "id": nxt["id"], "status": "done"})

        # Optional: delegate to Task Master CLI if available
        if self.path == "/api/taskmaster/next":
            res = _taskmaster_next_via_cli()
            return self._send_json({"taskmaster": bool(res), "result": res or None})

        return self._send_json({"error": "Not found"}, 404)

def main():
    host = UI_HOST
    port = UI_PORT
    # No longer need loopback alias since we're using 127.0.0.1
    httpd = HTTPServer((host, port), Handler)
    print(f"Map Server UI running at http://{host}:{port}  (repo={REPO_ROOT})")
    print("API: /api/tasks /api/next /api/progress /api/graphs/module /api/graphs/routes /api/domains /api/rules /api/schemas /api/integrations")
    httpd.serve_forever()

if __name__ == "__main__":
    main()
