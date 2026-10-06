"""
Health & Smoke MCP server (local, stdio JSON-RPC).

Exposes resources:
- mcp://health/smoke  — runs Flask test_client smoke checks and returns a structured report
- mcp://health/routes — lists application routes

Protocol: minimal JSON-RPC 2.0 over stdin/stdout.
Methods implemented:
- initialize
- listResources
- readResource
- ping
- shutdown

Note: This is a lightweight, pragmatic implementation aimed at opencode MCP integration.
It does not cover the full MCP spec; only a minimal surface needed for resources.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional, Tuple
import os

# Ensure repository root is on sys.path so implicit namespace package 'practices' resolves
_here = os.path.abspath(os.path.dirname(__file__))
_root = os.path.abspath(os.path.join(_here, os.pardir))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Import Flask app from the practice project
try:
    from practices.practice_04.project.server import app  # type: ignore
except Exception:
    # As a last resort, import by file path
    import importlib.util

    server_path = os.path.join(_root, "practices", "practice_04", "project", "server.py")
    spec = importlib.util.spec_from_file_location("practice4_server", server_path)
    if spec is None or spec.loader is None:  # pragma: no cover (defensive)
        raise
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    app = getattr(mod, "app")


def _ok(step: str) -> Dict[str, Any]:
    return {"step": step, "status": "ok"}


def _fail(step: str, error: str) -> Dict[str, Any]:
    return {"step": step, "status": "fail", "error": error}


def run_smoke() -> Dict[str, Any]:
    """Run basic smoke checks via Flask test_client.

    Returns a dict with overall status and step details.
    """
    details: List[Dict[str, Any]] = []
    overall_ok = True

    app.config.update(TESTING=True)
    client = app.test_client()

    # 1) GET /
    step = "GET /"
    try:
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Имя студента" in html and "Описание" in html and "/report" in html
        details.append(_ok(step))
    except AssertionError as e:
        overall_ok = False
        details.append(_fail(step, str(e)))

    # 2) POST /report
    step = "POST /report -> 302 /thanks"
    try:
        resp = client.post(
            "/report",
            data={
                "name": "MCP User",
                "details": "Smoke via MCP",
                "group": "K3140",
                "vibe_level": "high",
            },
        )
        assert resp.status_code == 302
        assert resp.headers.get("Location", "").endswith("/thanks")
        details.append(_ok(step))
    except AssertionError as e:
        overall_ok = False
        details.append(_fail(step, str(e)))

    # 3) GET /thanks
    step = "GET /thanks"
    try:
        resp = client.get("/thanks")
        assert resp.status_code == 200
        assert "Спасибо" in resp.get_data(as_text=True)
        details.append(_ok(step))
    except AssertionError as e:
        overall_ok = False
        details.append(_fail(step, str(e)))

    # 4) GET /reports
    step = "GET /reports contains last report"
    try:
        resp = client.get("/reports")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "MCP User" in html and "K3140" in html and "высокий" in html
        details.append(_ok(step))
    except AssertionError as e:
        overall_ok = False
        details.append(_fail(step, str(e)))

    # 5) Export JSON
    step = "GET /reports/export?format=json"
    try:
        resp = client.get("/reports/export", query_string={"format": "json"})
        assert resp.status_code == 200
        assert resp.mimetype.startswith("application/json")
        data = resp.get_json()
        assert isinstance(data, list) and len(data) >= 1
        assert data[-1]["name"] == "MCP User"
        details.append(_ok(step))
    except AssertionError as e:
        overall_ok = False
        details.append(_fail(step, str(e)))

    # 6) Export CSV
    step = "GET /reports/export?format=csv"
    try:
        resp = client.get("/reports/export", query_string={"format": "csv"})
        assert resp.status_code == 200
        assert resp.mimetype.startswith("text/csv")
        csv_text = resp.get_data(as_text=True)
        assert "name,group,vibe_level,details" in csv_text
        assert "MCP User" in csv_text and "K3140" in csv_text
        details.append(_ok(step))
    except AssertionError as e:
        overall_ok = False
        details.append(_fail(step, str(e)))

    # 7) Filter high vibe
    step = "GET /reports?vibe_level=high"
    try:
        resp = client.get("/reports", query_string={"vibe_level": "high"})
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "MCP User" in html
        details.append(_ok(step))
    except AssertionError as e:
        overall_ok = False
        details.append(_fail(step, str(e)))

    return {"ok": overall_ok, "details": details}


def list_routes() -> List[Dict[str, Any]]:
    routes: List[Dict[str, Any]] = []
    for rule in app.url_map.iter_rules():
        # Skip static if present
        if rule.endpoint == "static":
            continue
        routes.append({
            "rule": str(rule),
            "methods": sorted(m for m in rule.methods or [] if m in {"GET", "POST", "PUT", "DELETE", "PATCH"}),
            "endpoint": rule.endpoint,
        })
    return routes


def _send(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _response(id_: Any, result: Any) -> None:
    _send({"jsonrpc": "2.0", "id": id_, "result": result})


def _error(id_: Any, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})


def main() -> None:
    # Announce ready (optional)
    # Process incoming JSON-RPC messages line by line
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception as e:
            # No id to respond to
            _send({"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {e}"}})
            continue

        jsonrpc = msg.get("jsonrpc")
        method = msg.get("method")
        id_ = msg.get("id")
        params = msg.get("params") or {}

        if jsonrpc != "2.0":
            _error(id_, -32600, "Invalid Request: jsonrpc must be '2.0'")
            continue

        try:
            if method == "initialize":
                # Follow MCP initialize result shape
                _response(id_, {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "health-smoke-mcp",
                        "version": "0.1.0"
                    },
                    "capabilities": {
                        "resources": {}
                    }
                })
            elif method in ("resources/list", "listResources"):
                # Advertise available resources
                _response(id_, {
                    "resources": [
                        {
                            "uri": "mcp://health/smoke",
                            "name": "Smoke Report",
                            "description": "Run Flask smoke checks and return a JSON report"
                        },
                        {
                            "uri": "mcp://health/routes",
                            "name": "Routes",
                            "description": "List Flask application routes"
                        }
                    ]
                })
            elif method in ("resources/read", "readResource"):
                uri = params.get("uri")
                if uri == "mcp://health/smoke":
                    result = run_smoke()
                    _response(id_, {
                        "contents": [{
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(result, ensure_ascii=False)
                        }]
                    })
                elif uri == "mcp://health/routes":
                    routes = list_routes()
                    _response(id_, {
                        "contents": [{
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(routes, ensure_ascii=False)
                        }]
                    })
                else:
                    _error(id_, -32602, f"Unknown resource: {uri}")
            elif method == "ping":
                _response(id_, {"ok": True})
            elif method == "shutdown":
                _response(id_, {"ok": True})
                break
            else:
                _error(id_, -32601, f"Method not found: {method}")
        except Exception as e:
            _error(id_, -32000, f"Server error: {e}")


if __name__ == "__main__":
    # If invoked directly without MCP, support a quick debug: print smoke JSON
    if len(sys.argv) > 1 and sys.argv[1] == "--print-smoke":
        print(json.dumps(run_smoke(), ensure_ascii=False, indent=2))
    else:
        main()
