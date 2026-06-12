"""
server.py — minimal MCP server (stdio, JSON-RPC 2.0), zero external MCP SDK.

Implements: initialize, tools/list, tools/call, ping. stdout = protocol only,
so all logging goes to stderr (a classic stdio-MCP footgun).

Run:  python -m mysetterbot_claw
"""
from __future__ import annotations

import json
import sys

from .tools import dispatch, list_tools

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "mysetterbot-claw", "version": "0.1.0"}


def _log(*a):
    print(*a, file=sys.stderr, flush=True)


def _send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _ok(req_id, result):
    _send({"jsonrpc": "2.0", "id": req_id, "result": result})


def _err(req_id, code, message):
    _send({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


def _handle(req: dict) -> None:
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}

    # notifications (no id) — nothing to answer
    if method == "notifications/initialized":
        return

    if method == "initialize":
        _ok(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })
        return

    if method == "ping":
        _ok(req_id, {})
        return

    if method == "tools/list":
        _ok(req_id, {"tools": list_tools()})
        return

    if method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        result = dispatch(name, arguments)
        is_error = isinstance(result, dict) and result.get("ok") is False
        _ok(req_id, {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
            "isError": bool(is_error),
        })
        return

    if req_id is not None:
        _err(req_id, -32601, f"Method not found: {method}")


def main() -> int:
    _log("mysetterbot-claw MCP server ready (stdio).")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            _handle(req)
        except Exception as e:  # noqa: BLE001
            _log("handler error:", e)
            if isinstance(req, dict) and req.get("id") is not None:
                _err(req["id"], -32603, f"Internal error: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
