#!/usr/bin/env python3
"""Base tool pack entrypoint for bioimage-mcp."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
TOOLS_ROOT = BASE_DIR.parent
REPO_ROOT = TOOLS_ROOT.parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from bioimage_mcp_base import io as io_ops
from bioimage_mcp_base import transforms as transform_ops

TOOL_VERSION = "0.1.0"
TOOL_ENV_NAME = "bioimage-mcp-base"
DYNAMIC_FN_PREFIXES = ("base.", f"{TOOL_ENV_NAME}.")


FN_MAP = {
    "base.bioio.export": (io_ops.export, {}),
    "base.bioimage_mcp_base.transforms.phasor_from_flim": (
        transform_ops.phasor_from_flim,
        {},
    ),
    "base.bioimage_mcp_base.transforms.phasor_calibrate": (
        transform_ops.phasor_calibrate,
        {},
    ),
}

LEGACY_REDIRECTS = {}


def handle_meta_describe(params: dict[str, Any]) -> dict[str, Any]:
    target_fn = params.get("target_fn", "")
    if target_fn not in FN_MAP:
        return {"ok": False, "error": f"Unknown function: {target_fn}"}

    func, descriptions = FN_MAP[target_fn]

    # Import introspect_python_api only when needed (for meta.describe)
    try:
        from bioimage_mcp.runtimes.introspect import introspect_python_api
    except ImportError:
        return {"ok": False, "error": "Introspection not available in this environment"}

    schema = introspect_python_api(
        func, descriptions, exclude_params={"inputs", "params", "work_dir"}
    )

    return {
        "ok": True,
        "result": {
            "params_schema": schema,
            "tool_version": TOOL_VERSION,
            "introspection_source": "python_api",
        },
    }


def process_execute_request(request: dict[str, Any]) -> dict[str, Any]:
    """Process a single execute request (new format or legacy format).

    Args:
        request: Either ExecuteRequest format (with command="execute") or legacy format

    Returns:
        ExecuteResponse format dict with command="execute_result"
    """
    fn_id = request.get("fn_id")
    params = request.get("params") or {}
    inputs = request.get("inputs") or {}
    work_dir = Path(request.get("work_dir") or ".").absolute()
    work_dir.mkdir(parents=True, exist_ok=True)
    ordinal = request.get("ordinal")

    warnings = []
    if fn_id in LEGACY_REDIRECTS:
        new_fn_id = LEGACY_REDIRECTS[fn_id]
        warnings.append(
            f"DEPRECATED: {fn_id} is deprecated and will be removed in v1.0.0. "
            f"Use {new_fn_id} instead."
        )
        fn_id = new_fn_id

    try:
        if fn_id == "meta.describe":
            result_response = handle_meta_describe(params)
            # handle_meta_describe returns {"ok": bool, "result": ...} or {"ok": False, "error": ...}
            if result_response.get("ok"):
                response = {
                    "command": "execute_result",
                    "ok": True,
                    "ordinal": ordinal,
                    "outputs": {"result": result_response.get("result")},
                    "log": "ok",
                }
            else:
                response = {
                    "command": "execute_result",
                    "ok": False,
                    "ordinal": ordinal,
                    "error": {"message": result_response.get("error", "Unknown error")},
                    "log": "failed",
                }
        elif fn_id in FN_MAP:
            func, _descriptions = FN_MAP[fn_id]
            result = func(inputs=inputs, params=params, work_dir=work_dir)
            if isinstance(result, dict):
                outputs = result.get("outputs")
                if outputs is None:
                    raise ValueError(f"{fn_id} did not return outputs")
                response = {
                    "command": "execute_result",
                    "ok": True,
                    "ordinal": ordinal,
                    "outputs": outputs,
                    "log": result.get("log", "ok"),
                }
                # Combine tool-specific warnings with redirect warnings
                response["warnings"] = warnings + result.get("warnings", [])
                if "provenance" in result:
                    response["provenance"] = result["provenance"]
            else:
                out_path = result
                fmt = "OME-Zarr"
                response = {
                    "command": "execute_result",
                    "ok": True,
                    "ordinal": ordinal,
                    "outputs": {
                        "output": {
                            "type": "BioImageRef",
                            "format": fmt,
                            "path": str(out_path),
                        }
                    },
                    "log": "ok",
                    "warnings": warnings,
                }
        else:
            # Dynamic dispatch for functions not in FN_MAP
            from bioimage_mcp_base.dynamic_dispatch import dispatch_dynamic

            dynamic_fn_id = fn_id or ""
            for prefix in DYNAMIC_FN_PREFIXES:
                if dynamic_fn_id.startswith(prefix):
                    dynamic_fn_id = dynamic_fn_id[len(prefix) :]
                    break

            result = dispatch_dynamic(
                fn_id=dynamic_fn_id,
                inputs=inputs,
                params=params,
                work_dir=work_dir,
            )
            response = {
                "command": "execute_result",
                "ok": True,
                "ordinal": ordinal,
                "outputs": result.get("outputs", {}),
                "log": "ok (dynamic dispatch)",
            }
    except Exception as exc:  # noqa: BLE001
        error = {"message": str(exc)}
        error_code = getattr(exc, "code", None)
        if error_code:
            error["code"] = error_code
        response = {
            "command": "execute_result",
            "ok": False,
            "ordinal": ordinal,
            "error": error,
            "outputs": {},
            "log": "failed",
        }

    return response


def main() -> int:
    """Main entrypoint that processes NDJSON requests from stdin.

    Supports both:
    1. New NDJSON loop format: multiple requests with command field (execute, shutdown)
    2. Legacy single-request format: single JSON blob without command field

    Returns:
        0 on success, 1 on failure
    """
    # Try to detect if we're in legacy mode (single JSON blob) or NDJSON loop mode
    # Legacy mode: stdin.read() until EOF (no newline in first request)
    # NDJSON mode: read line-by-line with explicit commands

    # Read first line to detect mode
    first_line = sys.stdin.readline()
    if not first_line:
        # Empty stdin, exit cleanly
        return 0

    first_line = first_line.strip()
    if not first_line:
        # Empty line, continue to NDJSON loop
        pass
    else:
        try:
            request = json.loads(first_line)

            # Check if this is new format (has "command" field) or legacy format
            if "command" in request:
                # NDJSON loop mode
                # Process first request
                if request.get("command") == "execute":
                    response = process_execute_request(request)
                    print(json.dumps(response), flush=True)
                elif request.get("command") == "shutdown":
                    response = {
                        "command": "shutdown_ack",
                        "ok": True,
                        "ordinal": request.get("ordinal"),
                    }
                    print(json.dumps(response), flush=True)
                    return 0

                # Continue processing subsequent lines
                for line in sys.stdin:
                    line = line.strip()
                    if not line:
                        continue

                    request = json.loads(line)

                    if request.get("command") == "execute":
                        response = process_execute_request(request)
                        print(json.dumps(response), flush=True)
                    elif request.get("command") == "shutdown":
                        response = {
                            "command": "shutdown_ack",
                            "ok": True,
                            "ordinal": request.get("ordinal"),
                        }
                        print(json.dumps(response), flush=True)
                        break
                    else:
                        # Unknown command
                        response = {
                            "command": "error",
                            "ok": False,
                            "error": {"message": f"Unknown command: {request.get('command')}"},
                        }
                        print(json.dumps(response), flush=True)

                return 0
            else:
                # Legacy format: single request without "command" field
                # Read the rest of stdin (backward compatibility)
                rest = sys.stdin.read()
                if rest:
                    # If there's more data, it was a multi-line JSON blob
                    first_line = first_line + rest
                    request = json.loads(first_line)

                # Process as legacy request
                response = process_execute_request(request)

                # Legacy format doesn't have "command" field in response
                # Remove it for backward compatibility
                legacy_response = {
                    k: v for k, v in response.items() if k != "command" and k != "ordinal"
                }
                print(json.dumps(legacy_response))
                return 0 if response.get("ok") else 1

        except json.JSONDecodeError:
            # Invalid JSON
            response = {
                "command": "error",
                "ok": False,
                "error": {"message": "Invalid JSON in request"},
            }
            print(json.dumps(response), flush=True)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
