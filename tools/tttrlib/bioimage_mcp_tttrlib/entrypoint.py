#!/usr/bin/env python3
"""Tttrlib tool pack entrypoint for bioimage-mcp.

Implements the JSON stdin/stdout protocol for tool execution.
Supports persistent worker mode (NDJSON).
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Global caches
_TTTR_CACHE: dict[str, Any] = {}  # Stores tttrlib.TTTR objects
_OBJECT_CACHE: dict[str, Any] = {}  # Stores CLSMImage, Correlator, etc. objects

# Worker identity
_SESSION_ID: str | None = None
_ENV_ID: str | None = None

TOOL_VERSION = "0.1.0"
TOOL_ENV_NAME = "bioimage-mcp-tttrlib"


def _initialize_worker(session_id: str, env_id: str) -> None:
    """Initialize worker identity."""
    global _SESSION_ID, _ENV_ID
    _SESSION_ID = session_id
    _ENV_ID = env_id


def _store_tttr(tttr_obj: Any, uri: str) -> tuple[str, str]:
    """Store TTTR object in cache, return (ref_id, file:// URI)."""
    ref_id = uuid.uuid4().hex
    _TTTR_CACHE[ref_id] = {"obj": tttr_obj, "uri": uri}
    return ref_id, uri


def _load_tttr(ref_id_or_uri: str) -> Any:
    """Load TTTR object from cache."""
    # Try direct ref_id lookup
    if ref_id_or_uri in _TTTR_CACHE:
        return _TTTR_CACHE[ref_id_or_uri]["obj"]
    # Try URI lookup
    for _ref_id, data in _TTTR_CACHE.items():
        if data["uri"] == ref_id_or_uri:
            return data["obj"]

    # If it's a file URI but not in cache, try opening it
    if ref_id_or_uri.startswith("file://"):
        import tttrlib

        path = ref_id_or_uri[7:]
        tttr = tttrlib.TTTR(path)
        _store_tttr(tttr, ref_id_or_uri)
        return tttr

    raise KeyError(f"TTTR object not found: {ref_id_or_uri}")


def _store_object(obj: Any, class_name: str) -> dict[str, Any]:
    """Store object (e.g., CLSMImage) in cache and return ObjectRef."""
    if _SESSION_ID is None or _ENV_ID is None:
        raise RuntimeError("Worker not initialized")
    object_id = uuid.uuid4().hex
    _OBJECT_CACHE[object_id] = obj
    obj_uri = f"obj://{_SESSION_ID}/{_ENV_ID}/{object_id}"

    return {
        "ref_id": object_id,
        "type": "ObjectRef",
        "uri": obj_uri,
        "python_class": class_name,
        "storage_type": "memory",
        "created_at": datetime.now(UTC).isoformat(),
    }


def _load_object(uri: str) -> Any:
    """Load object from cache by obj:// URI."""
    if not uri.startswith("obj://"):
        raise ValueError(f"Invalid object URI: {uri}")
    parts = uri[6:].split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid object URI format: {uri}")
    _, _, object_id = parts
    if object_id not in _OBJECT_CACHE:
        raise KeyError(f"Object not found: {object_id}")
    return _OBJECT_CACHE[object_id]


# Function handlers


def handle_tttr_open(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR - open a TTTR file."""
    import tttrlib

    filename = params.get("filename")
    container_type = params.get("container_type")

    if not filename:
        return {"ok": False, "error": {"message": "filename is required"}}

    filepath = Path(filename)
    if not filepath.exists():
        return {
            "ok": False,
            "error": {"code": "FILE_NOT_FOUND", "message": f"File not found: {filename}"},
        }

    # Map container_type to tttrlib format codes
    container_map = {
        "PTU": 0,
        "HT3": 1,
        "SPC-130": 2,
        "SPC-630_256": 3,
        "SPC-630_4096": 4,
        "HDF": 5,
        "CZ-RAW": 6,
        "SM": 7,
    }

    try:
        if container_type and container_type in container_map:
            tttr = tttrlib.TTTR(str(filepath), container_map[container_type])
        else:
            # Auto-detect format
            tttr = tttrlib.TTTR(str(filepath))

        # Store in cache
        file_uri = f"file://{filepath.absolute()}"
        ref_id, uri = _store_tttr(tttr, file_uri)

        # Get metadata
        n_valid = tttr.n_valid_events if hasattr(tttr, "n_valid_events") else None

        output = {
            "ref_id": ref_id,
            "type": "TTTRRef",
            "uri": uri,
            "format": container_type or "auto",
            "storage_type": "file",
            "created_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "n_valid_events": n_valid,
            },
        }

        return {"ok": True, "outputs": {"tttr": output}, "log": f"Opened TTTR file: {filename}"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_tttr_header(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.TTTR.header - extract metadata."""
    import json as json_module

    tttr_ref = inputs.get("tttr", {})
    ref_id = tttr_ref.get("ref_id") or tttr_ref.get("uri", "").split("/")[-1]

    try:
        tttr = _load_tttr(ref_id)
        # Extract header data safely
        header_data = {}
        if hasattr(tttr, "header"):
            try:
                header_data = dict(tttr.header.data)
            except (AttributeError, TypeError):
                # Fallback if .data is not directly dict-convertible
                header_data = {"info": "Header object present but data extraction failed"}

        # Write header to JSON file
        header_path = work_dir / f"header_{ref_id[:8]}.json"
        with open(header_path, "w") as f:
            json_module.dump(header_data, f, indent=2, default=str)

        output = {
            "ref_id": uuid.uuid4().hex,
            "type": "NativeOutputRef",
            "uri": f"file://{header_path.absolute()}",
            "format": "json",
            "mime_type": "application/json",
            "created_at": datetime.now(UTC).isoformat(),
        }

        return {"ok": True, "outputs": {"header": output}, "log": "Header extracted"}

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_clsm_image(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.CLSMImage - reconstruct image from TTTR."""
    import tttrlib

    tttr_ref = inputs.get("tttr", {})
    ref_id = tttr_ref.get("ref_id") or tttr_ref.get("uri", "").split("/")[-1]

    try:
        tttr = _load_tttr(ref_id)

        # CLSMImage constructor arguments
        clsm_kwargs = {
            "tttr": tttr,
        }
        # Add optional params if provided
        for key in [
            "n_frames",
            "n_lines",
            "n_pixel",
            "marker_line_start",
            "marker_line_stop",
            "marker_frame_start",
        ]:
            if key in params:
                clsm_kwargs[key] = params[key]

        clsm = tttrlib.CLSMImage(**clsm_kwargs)

        output = _store_object(clsm, "tttrlib.CLSMImage")

        return {
            "ok": True,
            "outputs": {"clsm": output},
            "log": f"Reconstructed CLSMImage with {clsm.n_frames} frames",
        }

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


def handle_correlator(
    inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Handle tttrlib.Correlator - compute correlation."""
    import numpy as np
    import tttrlib

    tttr_ref = inputs.get("tttr", {})
    ref_id = tttr_ref.get("ref_id") or tttr_ref.get("uri", "").split("/")[-1]

    try:
        tttr = _load_tttr(ref_id)

        # Setup correlator
        correlator = tttrlib.Correlator(
            tttr=tttr,
            method=params.get("method", "react"),
            n_bins=params.get("n_bins", 17),
            n_casc=params.get("n_casc", 25),
        )

        # Store correlator object
        output = _store_object(correlator, "tttrlib.Correlator")

        # If user wants the curve immediately
        results = {}
        if params.get("return_curve", False):
            x = correlator.x
            y = correlator.y

            # Save to CSV
            csv_path = work_dir / f"correlation_{uuid.uuid4().hex[:8]}.csv"
            data = np.column_stack((x, y))
            np.savetxt(csv_path, data, delimiter=",", header="tau,g2", comments="")

            results["curve"] = {
                "ref_id": uuid.uuid4().hex,
                "type": "TableRef",
                "uri": f"file://{csv_path.absolute()}",
                "format": "csv",
                "created_at": datetime.now(UTC).isoformat(),
            }

        return {
            "ok": True,
            "outputs": {"correlator": output, **results},
            "log": "Correlator initialized",
        }

    except Exception as e:
        return {"ok": False, "error": {"message": str(e)}}


# Function dispatch table
FUNCTION_HANDLERS = {
    "tttrlib.TTTR": handle_tttr_open,
    "tttrlib.TTTR.header": handle_tttr_header,
    "tttrlib.CLSMImage": handle_clsm_image,
    "tttrlib.Correlator": handle_correlator,
}


def process_execute_request(request: dict[str, Any]) -> dict[str, Any]:
    """Process an execute request."""
    fn_id = request.get("fn_id", "")
    params = request.get("params") or {}
    inputs = request.get("inputs") or {}
    work_dir = Path(request.get("work_dir") or ".").absolute()
    work_dir.mkdir(parents=True, exist_ok=True)
    ordinal = request.get("ordinal")

    try:
        if fn_id in FUNCTION_HANDLERS:
            handler = FUNCTION_HANDLERS[fn_id]
            result = handler(inputs, params, work_dir)

            if result.get("ok"):
                return {
                    "command": "execute_result",
                    "ok": True,
                    "ordinal": ordinal,
                    "outputs": result.get("outputs", {}),
                    "log": result.get("log", "ok"),
                }
            else:
                return {
                    "command": "execute_result",
                    "ok": False,
                    "ordinal": ordinal,
                    "error": result.get("error", {"message": "Unknown error"}),
                }
        else:
            return {
                "command": "execute_result",
                "ok": False,
                "ordinal": ordinal,
                "error": {"message": f"Unknown fn_id: {fn_id}"},
            }
    except Exception as e:
        return {
            "command": "execute_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {"message": str(e)},
            "log": traceback.format_exc(),
        }


def main() -> int:
    """Main entrypoint."""
    is_persistent_mode = "BIOIMAGE_MCP_SESSION_ID" in os.environ

    # Initialize worker
    session_id = os.environ.get("BIOIMAGE_MCP_SESSION_ID", "default_session")
    env_id = os.environ.get("BIOIMAGE_MCP_ENV_ID", TOOL_ENV_NAME)
    _initialize_worker(session_id, env_id)

    # Verify tttrlib import
    try:
        import tttrlib  # noqa: F401
    except ImportError as e:
        error_json = {
            "command": "error",
            "ok": False,
            "error": {"code": "IMPORT_FAILED", "message": str(e)},
        }
        print(json.dumps(error_json), flush=True)
        return 1

    if is_persistent_mode:
        # NDJSON persistent mode
        print(
            json.dumps({"command": "ready", "status": "complete", "version": TOOL_VERSION}),
            flush=True,
        )

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                print(
                    json.dumps(
                        {"command": "error", "ok": False, "error": {"message": "Invalid JSON"}}
                    ),
                    flush=True,
                )
                continue

            if request.get("command") == "execute":
                response = process_execute_request(request)
                print(json.dumps(response), flush=True)
            elif request.get("command") == "shutdown":
                _TTTR_CACHE.clear()
                _OBJECT_CACHE.clear()
                print(
                    json.dumps(
                        {"command": "shutdown_ack", "ok": True, "ordinal": request.get("ordinal")}
                    ),
                    flush=True,
                )
                break
        return 0
    else:
        # Single request mode
        raw_input = sys.stdin.read()
        if not raw_input:
            return 0
        try:
            request = json.loads(raw_input)
        except json.JSONDecodeError:
            print(
                json.dumps({"command": "error", "ok": False, "error": {"message": "Invalid JSON"}})
            )
            return 1

        if "command" in request and request.get("command") == "execute":
            response = process_execute_request(request)
        else:
            # Legacy format
            response = process_execute_request(
                {
                    "fn_id": request.get("fn_id"),
                    "params": request.get("params"),
                    "inputs": request.get("inputs"),
                    "work_dir": request.get("work_dir"),
                }
            )
        print(json.dumps(response))
        return 0 if response.get("ok") else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
