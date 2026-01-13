#!/usr/bin/env python3
"""Base tool pack entrypoint for bioimage-mcp."""

from __future__ import annotations

import importlib
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import numpy as np

BASE_DIR = Path(__file__).resolve().parent
TOOLS_ROOT = BASE_DIR.parent
REPO_ROOT = TOOLS_ROOT.parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from datetime import UTC  # noqa: E402

from bioimage_mcp_base.ops import io as io_ops  # noqa: E402

from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE  # noqa: E402

# Deprecated: use OBJECT_CACHE instead
_OBJECT_CACHE = OBJECT_CACHE

TOOL_VERSION = "0.2.0"
TOOL_ENV_NAME = "bioimage-mcp-base"
DYNAMIC_FN_PREFIXES = ("base.", f"{TOOL_ENV_NAME}.")

# ==============================================================================
# Global memory artifact storage (T032)
# ==============================================================================

# Global memory store in worker process
# artifact_id -> numpy array
_MEMORY_ARTIFACTS: dict[str, Any] = {}

# Worker identity (set by initialization handshake or env vars)
_SESSION_ID: str | None = None
_ENV_ID: str | None = None


FN_MAP = {
    "base.io.bioimage.load": (io_ops.load, {}),
    "base.io.bioimage.inspect": (io_ops.inspect, {}),
    "base.io.bioimage.slice": (io_ops.slice_image, {}),
    "base.io.bioimage.validate": (io_ops.validate, {}),
    "base.io.bioimage.get_supported_formats": (io_ops.get_supported_formats, {}),
    "base.io.bioimage.export": (io_ops.export, {}),
    "base.io.table.load": (io_ops.table_load, {}),
    "base.io.table.export": (io_ops.table_export, {}),
}

LEGACY_REDIRECTS = {}


# ==============================================================================
# Memory artifact helpers (T032-T034)
# ==============================================================================


def _initialize_worker(session_id: str, env_id: str) -> None:
    """Initialize worker identity for memory artifact URIs."""
    global _SESSION_ID, _ENV_ID
    _SESSION_ID = session_id
    _ENV_ID = env_id


def _store_in_memory(data: np.ndarray) -> tuple[str, str]:
    """Store data in memory, return (artifact_id, mem:// URI).

    Args:
        data: Numpy array to store

    Returns:
        Tuple of (artifact_id, mem://session/env/artifact_id URI)

    Raises:
        RuntimeError: If worker identity not initialized
    """
    if _SESSION_ID is None or _ENV_ID is None:
        raise RuntimeError("Worker identity not initialized. Cannot create mem:// URI.")

    artifact_id = uuid.uuid4().hex
    _MEMORY_ARTIFACTS[artifact_id] = data

    mem_uri = f"mem://{_SESSION_ID}/{_ENV_ID}/{artifact_id}"
    return artifact_id, mem_uri


def _load_from_memory(uri: str) -> np.ndarray:
    """Load data from memory by mem:// URI.

    Args:
        uri: mem://session/env/artifact_id URI

    Returns:
        Numpy array

    Raises:
        ValueError: If URI is invalid or artifact not found
    """
    if not uri.startswith("mem://"):
        raise ValueError(f"Invalid memory URI: {uri}")

    # Parse mem:// URI
    parts = uri[6:].split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid memory URI format: {uri}")

    session_id, env_id, artifact_id = parts

    # Verify this URI belongs to this worker
    if session_id != _SESSION_ID or env_id != _ENV_ID:
        raise ValueError(
            f"Memory artifact {uri} belongs to different worker (current: {_SESSION_ID}/{_ENV_ID})"
        )

    # Retrieve from memory
    if artifact_id not in _MEMORY_ARTIFACTS:
        raise KeyError(f"Memory artifact not found: {artifact_id}")

    return _MEMORY_ARTIFACTS[artifact_id]


def _load_input_data(input_ref: str | dict) -> np.ndarray:
    """Load input data from file or memory.

    Args:
        input_ref: Either a file path string or a dict with 'uri' key

    Returns:
        Numpy array (5D TCZYX from bioio)
    """
    from bioio import BioImage

    # Handle dict refs (artifact references)
    if isinstance(input_ref, dict):
        uri = input_ref.get("uri", "")
        if uri.startswith("mem://"):
            # Load from worker memory
            return _load_from_memory(uri)
        else:
            # Load from file URI
            path_str = uri.replace("file://", "")
            img = BioImage(path_str)
            return img.data
    else:
        # Load from file path string
        img = BioImage(str(input_ref))
        return img.data


def _infer_dims_from_shape(shape: tuple[int, ...]) -> str:
    """Infer dimension labels from array shape.

    Args:
        shape: Array shape tuple

    Returns:
        Dimension string (e.g., "YX", "ZYX", "TCZYX")
    """
    ndim = len(shape)
    dims_map = {
        2: "YX",
        3: "ZYX",
        4: "CZYX",
        5: "TCZYX",
    }
    if ndim in dims_map:
        return dims_map[ndim]

    # Fallback for other dimensions: last N characters of "TCZYX"
    full_dims = "TCZYX"
    if ndim <= 0:
        return ""
    return full_dims[-ndim:] if ndim <= len(full_dims) else full_dims


def _expand_to_5d(data: np.ndarray) -> np.ndarray:
    """Expand array to 5D by prepending singleton dimensions.

    Args:
        data: Numpy array of any dimension

    Returns:
        5D (or higher) numpy array
    """
    while data.ndim < 5:
        data = np.expand_dims(data, axis=0)
    return data


def _convert_memory_inputs_to_files(inputs: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Convert mem:// artifact inputs to temporary file paths.

    This allows functions that expect file paths to work with memory artifacts.

    Args:
        inputs: Dict of input artifacts (may contain mem:// URIs)
        work_dir: Working directory for temporary files

    Returns:
        Dict of inputs with mem:// URIs replaced by file paths
    """
    from bioio.writers import OmeTiffWriter

    converted_inputs = {}

    for key, value in inputs.items():
        if isinstance(value, dict) and value.get("uri", "").startswith("mem://"):
            # Load from memory and save to temp file
            mem_uri = value["uri"]
            data = _load_from_memory(mem_uri)

            # Save to temporary file with unique name
            import uuid

            temp_id = uuid.uuid4().hex[:8]
            temp_path = work_dir / f"_mem_{key}_{temp_id}.ome.tif"
            dims_str = _infer_dims_from_shape(data.shape)
            OmeTiffWriter.save(data, temp_path, dim_order=dims_str)

            # Replace with file URI
            converted_inputs[key] = {
                "ref_id": value.get("ref_id"),
                "uri": f"file://{temp_path}",
                "type": value.get("type", "BioImageRef"),
                "format": "OME-TIFF",
            }
        else:
            # Keep as-is
            converted_inputs[key] = value

    return converted_inputs


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


def _extract_artifact_id(ref_id: str | None) -> str:
    """Extract artifact_id from ref_id (supports both mem:// URI and plain ID).

    Args:
        ref_id: Either "mem://session/env/artifact_id" or just "artifact_id"

    Returns:
        artifact_id portion

    Raises:
        ValueError: If ref_id is None, not a string, or mem:// URI is malformed
    """
    if ref_id is None:
        raise ValueError("ref_id cannot be None")
    if not isinstance(ref_id, str):
        raise ValueError(f"ref_id must be a string, got {type(ref_id).__name__}")
    if not ref_id:
        raise ValueError("ref_id cannot be empty")

    if ref_id.startswith("mem://"):
        # Parse mem:// URI to extract artifact_id
        parts = ref_id[6:].split("/")
        if len(parts) != 3:
            raise ValueError(f"Invalid memory URI format: {ref_id}")
        _session_id, _env_id, artifact_id = parts
        return artifact_id
    else:
        # Already just the artifact_id
        return ref_id


def handle_materialize(request: dict[str, Any]) -> dict[str, Any]:
    """Handle materialize command - export mem:// artifact to OME-Zarr or OME-TIFF.

    Args:
        request: MaterializeRequest dict with ref_id, target_format, dest_path, and ordinal

    Returns:
        MaterializeResponse dict
    """
    ref_id = request.get("ref_id")
    target_format = request.get("target_format", "OME-TIFF")
    dest_path = request.get("dest_path")
    ordinal = request.get("ordinal")

    # Extract artifact_id from ref_id (supports both mem:// URI and plain ID)
    try:
        artifact_id = _extract_artifact_id(ref_id)
    except ValueError as exc:
        return {
            "command": "materialize_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {
                "code": "INVALID_REF_ID",
                "message": str(exc),
            },
        }

    # Get data from memory
    if artifact_id not in _MEMORY_ARTIFACTS:
        return {
            "command": "materialize_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {
                "code": "NOT_FOUND",
                "message": f"Memory artifact not found: {ref_id}",
            },
        }

    data = _MEMORY_ARTIFACTS[artifact_id]

    # Generate destination path if not provided
    if dest_path is None:
        import tempfile

        suffix = ".ome.tif" if target_format == "OME-TIFF" else ".ome.zarr"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        dest_path = temp_file.name
        temp_file.close()

    dest_path = Path(dest_path)

    try:
        # Write to disk using bioio writers
        if target_format == "OME-TIFF":
            from bioio.writers import OmeTiffWriter

            dims_str = _infer_dims_from_shape(data.shape)
            OmeTiffWriter.save(data, dest_path, dim_order=dims_str)
        elif target_format == "OME-Zarr":
            from bioio_ome_zarr.writers import OMEZarrWriter

            dims_str = _infer_dims_from_shape(data.shape)
            axes_names = [d.lower() for d in dims_str]
            type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
            axes_types = [type_map[d] for d in axes_names]

            # OME-Zarr requires specific writer setup
            writer = OMEZarrWriter(
                store=str(dest_path),
                level_shapes=[data.shape],
                dtype=data.dtype,
                axes_names=axes_names,
                axes_types=axes_types,
            )
            writer.write_full_volume(data)
        else:
            return {
                "command": "materialize_result",
                "ok": False,
                "ordinal": ordinal,
                "error": {
                    "code": "INVALID_FORMAT",
                    "message": f"Unsupported target format: {target_format}",
                },
            }

        return {
            "command": "materialize_result",
            "ok": True,
            "ordinal": ordinal,
            "path": str(dest_path),
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "command": "materialize_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {
                "code": "MATERIALIZATION_FAILED",
                "message": f"Failed to materialize artifact: {exc}",
            },
        }


def handle_evict(request: dict[str, Any]) -> dict[str, Any]:
    """Handle evict command - remove artifact from memory.

    Args:
        request: EvictRequest dict with ref_id and ordinal

    Returns:
        EvictResponse dict
    """
    ref_id = request.get("ref_id")
    ordinal = request.get("ordinal")

    # Extract artifact_id from ref_id (supports both mem:// URI and plain ID)
    try:
        artifact_id = _extract_artifact_id(ref_id)
    except ValueError as exc:
        return {
            "command": "evict_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {
                "code": "INVALID_REF_ID",
                "message": str(exc),
            },
        }

    evicted = False
    if artifact_id in _MEMORY_ARTIFACTS:
        del _MEMORY_ARTIFACTS[artifact_id]
        evicted = True

    # Also evict from object cache (try both ID and full URI)
    if OBJECT_CACHE.evict(artifact_id):
        evicted = True
    if ref_id != artifact_id and OBJECT_CACHE.evict(ref_id):
        evicted = True

    if evicted:
        return {
            "command": "evict_result",
            "ok": True,
            "ordinal": ordinal,
        }

    # Artifact not found
    return {
        "command": "evict_result",
        "ok": False,
        "ordinal": ordinal,
        "error": {
            "code": "NOT_FOUND",
            "message": f"Memory artifact not found: {ref_id}",
        },
    }


def handle_reconstruct(request: dict[str, Any]) -> dict[str, Any]:
    """Handle core.reconstruct - instantiate a class and return an ObjectRef.

    Args:
        request: ExecuteRequest dict with class_context

    Returns:
        ExecuteResponse dict
    """
    class_context = request.get("class_context")
    ordinal = request.get("ordinal")

    if not class_context:
        # Fallback: check if python_class and init_params are in params
        params = request.get("params") or {}
        python_class_name = params.get("python_class")
        init_params = params.get("init_params", {})
    else:
        python_class_name = class_context.get("python_class")
        init_params = class_context.get("init_params", {})

    if not python_class_name:
        return {
            "command": "execute_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {
                "code": "INVALID_REQUEST",
                "message": "Missing python_class for reconstruction",
            },
        }

    try:
        # Resolve class
        if "." not in python_class_name:
            raise ValueError(f"Invalid fully qualified class name: {python_class_name}")

        module_name, class_name = python_class_name.rsplit(".", 1)
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)

        # Instantiate
        obj = cls(**init_params)

        # Store in unified object cache
        object_id = uuid.uuid4().hex
        OBJECT_CACHE.set(object_id, obj)

        # Also store by full URI for compatibility
        obj_uri = f"obj://{_SESSION_ID}/{_ENV_ID}/{object_id}"
        OBJECT_CACHE.set(obj_uri, obj)

        # Also store in _MEMORY_ARTIFACTS for compatibility with _load_from_memory
        _MEMORY_ARTIFACTS[object_id] = obj

        return {
            "command": "execute_result",
            "ok": True,
            "ordinal": ordinal,
            "outputs": {
                "model": {
                    "ref_id": object_id,
                    "type": "ObjectRef",
                    "uri": obj_uri,
                    "format": "pickle",
                    "python_class": python_class_name,
                    "storage_type": "memory",
                    "created_at": _now_iso(),
                    "metadata": {"init_params": init_params},
                }
            },
            "log": f"Reconstructed {python_class_name}",
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "command": "execute_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {
                "code": "RECONSTRUCTION_FAILED",
                "message": f"Failed to reconstruct {python_class_name}: {exc}",
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
    hints = request.get("hints") or {}

    work_dir = Path(request.get("work_dir") or ".").absolute()
    work_dir.mkdir(parents=True, exist_ok=True)
    ordinal = request.get("ordinal")

    # Extract output_mode from params (T033)
    output_mode = params.pop("output_mode", "file")  # 'file' or 'memory'

    # Set allowlist in environment for the duration of this request (T041)
    allowlist = request.get("fs_allowlist_read")
    sys.stderr.write(f"DEBUG: Setting allowlist from request: {allowlist}\n")
    sys.stderr.flush()
    if allowlist is not None:
        import os

        os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_READ"] = json.dumps(allowlist)

    # Set write allowlist in environment for the duration of this request
    write_allowlist = request.get("fs_allowlist_write")
    if write_allowlist is not None:
        os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_WRITE"] = json.dumps(write_allowlist)

    warnings = []
    if fn_id in LEGACY_REDIRECTS:
        new_fn_id = LEGACY_REDIRECTS[fn_id]
        warnings.append(
            f"DEPRECATED: {fn_id} is deprecated and will be removed in v1.0.0. "
            f"Use {new_fn_id} instead."
        )
        fn_id = new_fn_id

    try:
        # Convert mem:// inputs to file inputs (T034)
        # This allows functions that expect file paths to work with memory artifacts
        # IMPORTANT: This must be inside try/except to catch evicted artifact errors
        inputs = _convert_memory_inputs_to_files(inputs, work_dir)
        if fn_id == "core.reconstruct":
            return handle_reconstruct(request)
        if fn_id == "meta.describe":
            result_response = handle_meta_describe(params)
            # handle_meta_describe returns {"ok": bool, "result": ...}
            # or {"ok": False, "error": ...}
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

                # Transform outputs to memory artifacts if requested (T033)
                if output_mode == "memory":
                    outputs = _convert_outputs_to_memory(outputs, work_dir)

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

                # Handle memory mode for legacy path return (T033)
                if output_mode == "memory":
                    # Load the file and store in memory
                    data = _load_input_data(str(out_path))
                    artifact_id, mem_uri = _store_in_memory(data)

                    # Clean up the temporary file
                    try:
                        out_path.unlink()
                    except Exception:  # noqa: BLE001
                        pass  # Ignore cleanup errors

                    # Build memory artifact reference
                    ref_id = artifact_id  # Use same ID for both
                    output_ref = {
                        "ref_id": ref_id,
                        "type": "BioImageRef",
                        "uri": mem_uri,
                        "format": "memory",
                        "storage_type": "memory",
                        "mime_type": "application/octet-stream",
                        "size_bytes": data.nbytes,
                        "created_at": _now_iso(),
                        "metadata": {
                            "shape": list(data.shape),
                            "dtype": str(data.dtype),
                            "dims": _infer_dims_from_shape(data.shape),
                        },
                    }

                    response = {
                        "command": "execute_result",
                        "ok": True,
                        "ordinal": ordinal,
                        "outputs": {"output": output_ref},
                        "log": "ok (memory)",
                        "warnings": warnings,
                    }
                else:
                    # File mode (original behavior)
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
                hints=hints,
            )

            outputs = result.get("outputs", {})

            # Transform outputs to memory artifacts if requested (T033)
            if output_mode == "memory":
                outputs = _convert_outputs_to_memory(outputs, work_dir)

            response = {
                "command": "execute_result",
                "ok": True,
                "ordinal": ordinal,
                "outputs": outputs,
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


def _convert_outputs_to_memory(outputs: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Convert file-based outputs to memory artifacts.

    Args:
        outputs: Dict of output artifacts (may contain file paths or refs)
        work_dir: Working directory for loading files

    Returns:
        Dict of memory artifact references
    """
    mem_outputs = {}

    for key, value in outputs.items():
        if isinstance(value, dict):
            # Already an artifact reference
            # If it has a path, load and convert to memory
            if "path" in value:
                path = Path(value["path"])
                data = _load_input_data(str(path))
                artifact_id, mem_uri = _store_in_memory(data)

                # Clean up the temporary file
                try:
                    path.unlink()
                except Exception:  # noqa: BLE001
                    pass  # Ignore cleanup errors

                mem_outputs[key] = {
                    "ref_id": artifact_id,
                    "type": value.get("type", "BioImageRef"),
                    "uri": mem_uri,
                    "format": "memory",
                    "storage_type": "memory",
                    "mime_type": "application/octet-stream",
                    "size_bytes": data.nbytes,
                    "created_at": _now_iso(),
                    "metadata": {
                        "shape": list(data.shape),
                        "dtype": str(data.dtype),
                        "dims": _infer_dims_from_shape(data.shape),
                    },
                }
            else:
                # Already a reference, keep as-is
                mem_outputs[key] = value
        elif isinstance(value, (str, Path)):
            # File path
            data = _load_input_data(str(value))
            artifact_id, mem_uri = _store_in_memory(data)

            # Clean up the temporary file
            try:
                Path(value).unlink()
            except Exception:  # noqa: BLE001
                pass  # Ignore cleanup errors

            mem_outputs[key] = {
                "ref_id": artifact_id,
                "type": "BioImageRef",
                "uri": mem_uri,
                "format": "memory",
                "storage_type": "memory",
                "mime_type": "application/octet-stream",
                "size_bytes": data.nbytes,
                "created_at": _now_iso(),
                "metadata": {
                    "shape": list(data.shape),
                    "dtype": str(data.dtype),
                    "dims": _infer_dims_from_shape(data.shape),
                },
            }
        else:
            # Unknown type, keep as-is
            mem_outputs[key] = value

    return mem_outputs


def _now_iso() -> str:
    """Get current time in ISO format."""
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def main() -> int:
    """Main entrypoint that processes NDJSON requests from stdin.

    Supports both:
    1. New NDJSON loop format: multiple requests with command field (execute, shutdown)
    2. Legacy single-request format: single JSON blob without command field

    Returns:
        0 on success, 1 on failure
    """
    import os
    import sys

    print(f"DEBUG: BASE ENTRYPOINT CALLED with PID {os.getpid()}", file=sys.stderr)

    # Initialize worker identity from environment or use defaults (T032)
    session_id = os.environ.get("BIOIMAGE_MCP_SESSION_ID", "default_session")
    env_id = os.environ.get("BIOIMAGE_MCP_ENV_ID", "bioimage-mcp-base")
    _initialize_worker(session_id, env_id)

    # Detect mode from environment variables:
    # If BIOIMAGE_MCP_SESSION_ID is set, we're spawned by persistent manager (NDJSON mode)
    # Otherwise, we're in legacy mode (single request)
    is_persistent_mode = "BIOIMAGE_MCP_SESSION_ID" in os.environ

    if is_persistent_mode:
        # NDJSON loop mode with persistent worker
        # Send ready handshake immediately to signal worker is initialized
        ready_message = json.dumps({"command": "ready", "version": TOOL_VERSION})
        print(ready_message, flush=True)

        # Process requests in loop
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                response = {
                    "command": "error",
                    "ok": False,
                    "error": {"message": "Invalid JSON in request"},
                }
                print(json.dumps(response), flush=True)
                continue

            if request.get("command") == "execute":
                response = process_execute_request(request)
                print(json.dumps(response), flush=True)
            elif request.get("command") == "materialize":
                response = handle_materialize(request)
                print(json.dumps(response), flush=True)
            elif request.get("command") == "evict":
                response = handle_evict(request)
                print(json.dumps(response), flush=True)
            elif request.get("command") == "shutdown":
                # T073: Release memory artifacts before shutdown
                _MEMORY_ARTIFACTS.clear()
                OBJECT_CACHE.clear()
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
        # Legacy mode: single request without persistent worker
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
                    elif request.get("command") == "materialize":
                        response = handle_materialize(request)
                        print(json.dumps(response), flush=True)
                    elif request.get("command") == "evict":
                        response = handle_evict(request)
                        print(json.dumps(response), flush=True)
                    elif request.get("command") == "shutdown":
                        # T073: Release memory artifacts before shutdown
                        _MEMORY_ARTIFACTS.clear()
                        OBJECT_CACHE.clear()
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
                        elif request.get("command") == "materialize":
                            response = handle_materialize(request)
                            print(json.dumps(response), flush=True)
                        elif request.get("command") == "evict":
                            response = handle_evict(request)
                            print(json.dumps(response), flush=True)
                        elif request.get("command") == "shutdown":
                            # T073: Release memory artifacts before shutdown
                            _MEMORY_ARTIFACTS.clear()
                            OBJECT_CACHE.clear()
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
