#!/usr/bin/env python3
"""Trackpy tool pack entrypoint for bioimage-mcp."""

from __future__ import annotations

import contextlib
import importlib
import inspect
import io
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from bioio import BioImage

# Path setup: add tools/trackpy/ to sys.path for local imports
BASE_DIR = Path(__file__).resolve().parent
TRACKPY_TOOL_ROOT = BASE_DIR.parent
if str(TRACKPY_TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(TRACKPY_TOOL_ROOT))

REPO_ROOT = TRACKPY_TOOL_ROOT.parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))


from bioimage_mcp_trackpy.introspect import (  # noqa: E402
    get_trackpy_version,
    introspect_function,
)

TOOL_VERSION = "0.1.0"
TOOL_ENV_NAME = "bioimage-mcp-trackpy"

# Global memory artifact storage
_MEMORY_ARTIFACTS: dict[str, Any] = {}
_SESSION_ID: str | None = None
_ENV_ID: str | None = None
_WORK_DIR: Path = Path.cwd()


def _initialize_worker(session_id: str, env_id: str, work_dir: str | None = None) -> None:
    """Initialize worker identity."""
    global _SESSION_ID, _ENV_ID, _WORK_DIR
    _SESSION_ID = session_id
    _ENV_ID = env_id
    if work_dir:
        _WORK_DIR = Path(work_dir)
    else:
        _WORK_DIR = Path(os.environ.get("BIOIMAGE_MCP_WORK_DIR", Path.cwd()))
    _WORK_DIR.mkdir(parents=True, exist_ok=True)


def _find_project_root(start: Path) -> Path | None:
    """Find project root by looking for envs/ or pyproject.toml."""
    curr = start
    for _ in range(5):
        if (curr / "envs").exists() or (curr / "pyproject.toml").exists():
            return curr
        curr = curr.parent
    return None


def handle_meta_list(params: dict) -> dict:
    """Out-of-process function discovery for trackpy."""
    import hashlib

    import yaml

    from bioimage_mcp.registry.dynamic.cache import IntrospectionCache
    from bioimage_mcp.registry.dynamic.discovery import discover_functions
    from bioimage_mcp.registry.manifest_schema import ToolManifest
    from bioimage_mcp_trackpy.dynamic_discovery import TrackpyAdapter

    manifest_path = TRACKPY_TOOL_ROOT / "manifest.yaml"
    try:
        raw = manifest_path.read_bytes()
        manifest_data = yaml.safe_load(raw)
        checksum = hashlib.sha256(raw).hexdigest()

        manifest = ToolManifest.model_validate(
            {
                **manifest_data,
                "manifest_path": manifest_path,
                "manifest_checksum": checksum,
            }
        )

        project_root = _find_project_root(manifest_path.parent)
        cache_dir = Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / manifest.tool_id
        cache = IntrospectionCache(cache_dir)

        discovered = discover_functions(
            manifest, {"trackpy": TrackpyAdapter()}, cache=cache, project_root=project_root
        )

        functions = []
        for meta in discovered:
            summary = meta.description.split("\n")[0] if meta.description else ""

            functions.append(
                {
                    "fn_id": meta.fn_id,
                    "name": meta.name,
                    "module": meta.module,
                    "summary": summary,
                    "io_pattern": meta.io_pattern.value,
                }
            )

        return {
            "ok": True,
            "result": {
                "functions": functions,
                "tool_version": get_trackpy_version(),
                "introspection_source": "dynamic_discovery",
            },
        }
    except Exception as exc:
        return {"ok": False, "error": f"Discovery failed: {exc}"}


def handle_meta_describe(params: dict) -> dict:
    """Detailed schema introspection using numpydoc."""
    target_fn = params.get("target_fn")
    if not target_fn:
        return {"ok": False, "error": "target_fn required"}

    # Strip tool prefix if present (e.g. tools.trackpy.locate -> trackpy.locate)
    if target_fn.startswith("tools.trackpy."):
        target_fn = target_fn[14:]
    elif target_fn.startswith("trackpy.") and not target_fn.startswith("trackpy.trackpy."):
        # Already correct format for introspect_function
        pass

    try:
        result = introspect_function(target_fn)
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": f"Introspection failed: {e}"}


def _execute_trackpy_function(fn_id: str, params: dict, inputs: dict) -> dict:
    """Execute a trackpy function with artifact resolution."""
    capture = io.StringIO()
    try:
        func = _resolve_callable(fn_id)
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())

        # Resolve artifact inputs
        resolved_inputs = {}
        for key, value in inputs.items():
            resolved_val = _load_input_artifact(value)
            # Map generic input names back to trackpy-specific ones
            if key == "image":
                if "raw_image" in param_names:
                    resolved_inputs["raw_image"] = resolved_val
                elif "image" in param_names:
                    resolved_inputs["image"] = resolved_val
                elif "frames" in param_names:
                    resolved_inputs["frames"] = resolved_val
                elif param_names:
                    # Fallback: use first parameter if it's likely an image
                    resolved_inputs[param_names[0]] = resolved_val
            elif key == "table":
                if "f" in param_names:
                    resolved_inputs["f"] = resolved_val
                elif "t" in param_names:
                    resolved_inputs["t"] = resolved_val
                elif "features" in param_names:
                    resolved_inputs["features"] = resolved_val
                elif "traj" in param_names:
                    resolved_inputs["traj"] = resolved_val
            else:
                resolved_inputs[key] = resolved_val

        # Combine params and resolved inputs
        call_kwargs = {**params, **resolved_inputs}

        # Execute with stdout/stderr redirection and logging capture
        import logging

        tp_logger = logging.getLogger("trackpy")
        old_propagate = tp_logger.propagate
        old_handlers = tp_logger.handlers[:]

        tp_logger.propagate = False
        for h in old_handlers:
            tp_logger.removeHandler(h)

        log_handler = logging.StreamHandler(capture)
        tp_logger.addHandler(log_handler)
        try:
            with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
                result = func(**call_kwargs)
        finally:
            tp_logger.removeHandler(log_handler)
            for h in old_handlers:
                tp_logger.addHandler(h)
            tp_logger.propagate = old_propagate

        # Serialize outputs
        outputs = {}
        if isinstance(result, pd.DataFrame):
            outputs["table"] = _save_table_artifact(result, f"{fn_id.replace('.', '_')}_output")
        elif isinstance(result, np.ndarray):
            outputs["image"] = _save_image_artifact(result, f"{fn_id.replace('.', '_')}_output")
        else:
            outputs["result"] = _make_json_serializable(result)

        log_content = capture.getvalue()
        return {"ok": True, "outputs": outputs, "_meta": {"log": log_content}}

    except Exception as e:
        log_content = capture.getvalue()
        return {
            "ok": False,
            "error": {"message": str(e)},
            "log": f"{log_content}\n{traceback.format_exc()}",
        }


def _resolve_callable(fn_id: str) -> Any:
    parts = fn_id.rsplit(".", 1)
    if len(parts) == 2:
        module_name, func_name = parts
    else:
        module_name, func_name = "trackpy", parts[0]

    module = importlib.import_module(module_name)
    return getattr(module, func_name)


def _load_input_artifact(artifact_ref: dict) -> Any:
    """Load artifact to in-memory object (numpy/pandas)."""
    ref_type = artifact_ref.get("type") or artifact_ref.get("ref_type")
    # File-backed
    path = artifact_ref.get("path")
    if not path:
        uri = artifact_ref.get("uri")
        if uri and uri.startswith("file://"):
            from urllib.parse import unquote, urlparse

            path = unquote(urlparse(uri).path)
            if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]

    if not path:
        # Check memory
        ref_id = artifact_ref.get("ref_id")
        if ref_id in _MEMORY_ARTIFACTS:
            return _MEMORY_ARTIFACTS[ref_id]
        raise ValueError(f"Artifact not found: {artifact_ref}")

    if ref_type == "BioImageRef":
        img = BioImage(path)
        return img.get_image_data("ZYX")  # Standard trackpy orientation
    elif ref_type == "TableRef":
        return pd.read_csv(path)

    return path  # Fallback to path string


def _save_table_artifact(df: pd.DataFrame, name_hint: str) -> dict:
    import uuid

    ref_id = str(uuid.uuid4())
    filename = f"{name_hint}_{ref_id[:8]}.csv"
    path = _WORK_DIR / filename
    df.to_csv(path, index=False)
    return {
        "type": "TableRef",
        "ref_id": ref_id,
        "path": str(path),
        "format": "csv",
        "shape": list(df.shape),
    }


def _save_image_artifact(arr: np.ndarray, name_hint: str) -> dict:
    import uuid

    from bioio_ome_tiff import Writer

    ref_id = str(uuid.uuid4())
    filename = f"{name_hint}_{ref_id[:8]}.ome.tif"
    path = _WORK_DIR / filename

    # Simple OME-TIFF write
    # bioio-ome-tiff Writer expects [T, C, Z, Y, X] or similar
    # We'll try to be simple for now
    Writer.save(arr, path)

    return {
        "type": "BioImageRef",
        "ref_id": ref_id,
        "path": str(path),
        "format": "ome.tif",
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
    }


def _make_json_serializable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_make_json_serializable(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _make_json_serializable(v) for k, v in value.items()}
    if hasattr(value, "tolist") and not isinstance(value, type):
        try:
            return value.tolist()
        except Exception:  # noqa: BLE001
            pass
    return str(value)


def _handle_request(request: dict) -> dict:
    """Route requests to handlers."""
    global _WORK_DIR
    command = request.get("command")
    params = request.get("params", {})
    inputs = request.get("inputs", {})
    fn_id = request.get("fn_id")
    ordinal = request.get("ordinal")
    work_dir = request.get("work_dir")

    if work_dir:
        _WORK_DIR = Path(work_dir)
        _WORK_DIR.mkdir(parents=True, exist_ok=True)

    try:
        if command == "execute":
            if fn_id == "meta.list":
                res = handle_meta_list(params)
            elif fn_id == "meta.describe":
                res = handle_meta_describe(params)
            else:
                res = _execute_trackpy_function(fn_id, params, inputs)

            if res.get("ok"):
                response = {
                    "command": "execute_result",
                    "ok": True,
                    "ordinal": ordinal,
                    "outputs": res.get("outputs") or {"result": res.get("result")},
                }
                if "_meta" in res:
                    response["_meta"] = res["_meta"]
                return response
            else:
                return {
                    "command": "execute_result",
                    "ok": False,
                    "ordinal": ordinal,
                    "error": res.get("error", {"message": "Unknown error"}),
                    "log": res.get("log"),
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
        os.environ.get("BIOIMAGE_MCP_WORK_DIR"),
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
