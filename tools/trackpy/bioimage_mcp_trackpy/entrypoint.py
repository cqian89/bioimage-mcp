#!/usr/bin/env python3
"""Trackpy tool pack entrypoint for bioimage-mcp."""

from __future__ import annotations

import importlib
import json
import os
import sys
import traceback
import uuid
from pathlib import Path
from typing import Any

# Path setup: add tools/ to sys.path for local imports
# Tool packs must NOT depend on src/ (core server)
BASE_DIR = Path(__file__).resolve().parent
TOOLS_ROOT = BASE_DIR.parent.parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

TOOL_VERSION = "0.1.0"
TOOL_ENV_NAME = "bioimage-mcp-trackpy"

TRACKPY_MODULES = [
    "trackpy",
    "trackpy.linking",
    "trackpy.motion",
    "trackpy.predict",
    "trackpy.filtering",
    "trackpy.plots",
    "trackpy.diag",
    "trackpy.feature",
    "trackpy.refine",
    "trackpy.masks",
    "trackpy.preprocessing",
    "trackpy.artificial",
]

# Global memory artifact storage
_MEMORY_ARTIFACTS: dict[str, Any] = {}
_SESSION_ID: str | None = None
_ENV_ID: str | None = None

# Static function map (initially minimal)
FN_MAP: dict[str, tuple[Any, dict]] = {}


def _initialize_worker(session_id: str, env_id: str) -> None:
    """Initialize worker identity."""
    global _SESSION_ID, _ENV_ID
    _SESSION_ID = session_id
    _ENV_ID = env_id


def handle_meta_list(params: dict) -> dict:
    """Out-of-process function discovery for trackpy."""
    functions = []
    for module_name in TRACKPY_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue

        for name in dir(module):
            if name.startswith("_"):
                continue
            obj = getattr(module, name)
            if not callable(obj) or not hasattr(obj, "__doc__"):
                continue

            fn_id = f"{module_name}.{name}"
            doc = obj.__doc__ or ""
            summary = doc.split("\n")[0] if doc else ""

            functions.append(
                {
                    "fn_id": fn_id,
                    "name": name,
                    "summary": summary,
                    "module": module_name,
                }
            )

    return {"ok": True, "result": {"functions": functions}}


def handle_meta_describe(params: dict) -> dict:
    """Detailed schema introspection (minimal implementation for now)."""
    target_fn = params.get("target_fn", "")
    # In the future, this will use numpydoc to parse signatures
    return {
        "ok": True,
        "result": {
            "fn_id": target_fn,
            "params_schema": {"type": "object", "properties": {}},
            "tool_version": TOOL_VERSION,
        },
    }


def _handle_request(request: dict) -> dict:
    """Route requests to handlers."""
    command = request.get("command")
    params = request.get("params", {})
    fn_id = request.get("fn_id")
    ordinal = request.get("ordinal")

    try:
        if command == "execute":
            if fn_id == "meta.list":
                res = handle_meta_list(params)
            elif fn_id == "meta.describe":
                res = handle_meta_describe(params)
            elif fn_id in FN_MAP:
                func, _ = FN_MAP[fn_id]
                # Placeholder for actual execution logic
                res = {"ok": True, "result": "executed"}
            else:
                return {
                    "command": "execute_result",
                    "ok": False,
                    "ordinal": ordinal,
                    "error": {"message": f"Unknown function: {fn_id}"},
                }

            if res.get("ok"):
                return {
                    "command": "execute_result",
                    "ok": True,
                    "ordinal": ordinal,
                    "outputs": {"result": res.get("result")},
                }
            else:
                return {
                    "command": "execute_result",
                    "ok": False,
                    "ordinal": ordinal,
                    "error": {"message": res.get("error", "Unknown error")},
                }

        elif command == "shutdown":
            _MEMORY_ARTIFACTS.clear()
            return {"command": "shutdown_ack", "ok": True, "ordinal": ordinal}

        else:
            return {
                "command": "error",
                "ok": False,
                "ordinal": ordinal,
                "error": {"message": f"Unknown command: {command}"},
            }

    except Exception as exc:
        return {
            "command": "execute_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {"message": str(exc)},
            "log": traceback.format_exc(),
        }


def _run_ndjson_loop():
    """Persistent NDJSON command loop."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = _handle_request(request)
            print(json.dumps(response), flush=True)
            if response.get("command") == "shutdown_ack":
                break
        except json.JSONDecodeError:
            print(
                json.dumps(
                    {
                        "command": "error",
                        "ok": False,
                        "error": {"message": "Invalid JSON"},
                    }
                ),
                flush=True,
            )


def main():
    """Dual-mode entrypoint: legacy JSON or persistent NDJSON."""
    import select

    # Initialize identity from environment if present
    _initialize_worker(
        os.environ.get("BIOIMAGE_MCP_SESSION_ID", "default"),
        os.environ.get("BIOIMAGE_MCP_ENV_ID", TOOL_ENV_NAME),
    )

    # Check if stdin is a TTY (usually interactive or spawned persistent)
    if sys.stdin.isatty():
        sys.stdout.write(json.dumps({"command": "ready", "version": TOOL_VERSION}) + "\n")
        sys.stdout.flush()
        _run_ndjson_loop()
    else:
        # Check if data is immediately available (legacy mode)
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            line = sys.stdin.readline()
            if line.strip():
                try:
                    request = json.loads(line)
                    # If it's a persistent command, continue to loop
                    if request.get("command") in ["execute", "shutdown"]:
                        response = _handle_request(request)
                        print(json.dumps(response), flush=True)
                        if request.get("command") != "shutdown":
                            _run_ndjson_loop()
                        return

                    # Otherwise handle as legacy single request
                    response = _handle_request(request)
                    # For legacy compatibility, we might want to strip 'command' and 'ordinal'
                    # but keeping them usually doesn't hurt if the core handles it.
                    print(json.dumps(response), flush=True)
                    return
                except json.JSONDecodeError:
                    pass

        # No immediate data or not legacy - persistent worker mode
        sys.stdout.write(json.dumps({"command": "ready", "version": TOOL_VERSION}) + "\n")
        sys.stdout.flush()
        _run_ndjson_loop()


if __name__ == "__main__":
    main()
