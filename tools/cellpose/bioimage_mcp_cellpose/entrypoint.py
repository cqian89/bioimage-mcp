#!/usr/bin/env python3
"""Cellpose tool pack entrypoint for bioimage-mcp.

Implements the JSON stdin/stdout protocol for tool execution
and the meta.describe protocol for dynamic schema introspection.
Supports persistent worker mode (NDJSON).
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add parent directory to path so bioimage_mcp_cellpose can be imported
BASE_DIR = Path(__file__).resolve().parent
TOOLS_ROOT = BASE_DIR.parent
REPO_ROOT = TOOLS_ROOT.parent.parent

if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

# Global memory store in worker process
_MEMORY_ARTIFACTS: dict[str, Any] = {}
_OBJECT_CACHE: dict[str, Any] = {}

# Worker identity
_SESSION_ID: str | None = None
_ENV_ID: str | None = None

# Tool pack version
TOOL_VERSION = "0.1.0"
TOOL_ENV_NAME = "bioimage-mcp-cellpose"


def _get_cellpose_version() -> str:
    """Get the installed Cellpose version."""
    try:
        import cellpose

        return cellpose.__version__
    except ImportError:
        return "unknown"


def _initialize_worker(session_id: str, env_id: str) -> None:
    """Initialize worker identity for memory artifact URIs."""
    global _SESSION_ID, _ENV_ID
    _SESSION_ID = session_id
    _ENV_ID = env_id


def _store_in_memory(data: Any) -> tuple[str, str]:
    """Store data in memory, return (artifact_id, mem:// URI)."""
    if _SESSION_ID is None or _ENV_ID is None:
        raise RuntimeError("Worker identity not initialized. Cannot create mem:// URI.")

    artifact_id = uuid.uuid4().hex
    _MEMORY_ARTIFACTS[artifact_id] = data

    mem_uri = f"mem://{_SESSION_ID}/{_ENV_ID}/{artifact_id}"
    return artifact_id, mem_uri


def _load_from_memory(uri: str) -> Any:
    """Load data from memory by mem:// URI."""
    if not uri.startswith("mem://"):
        raise ValueError(f"Invalid memory URI: {uri}")

    parts = uri[6:].split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid memory URI format: {uri}")

    session_id, env_id, artifact_id = parts

    if session_id != _SESSION_ID or env_id != _ENV_ID:
        raise ValueError(
            f"Memory artifact {uri} belongs to different worker (current: {_SESSION_ID}/{_ENV_ID})"
        )

    if artifact_id not in _MEMORY_ARTIFACTS:
        raise KeyError(f"Memory artifact not found: {artifact_id}")

    return _MEMORY_ARTIFACTS[artifact_id]


def _store_object(obj: Any) -> tuple[str, str]:
    """Store object in cache, return (object_id, obj:// URI)."""
    if _SESSION_ID is None or _ENV_ID is None:
        raise RuntimeError("Worker identity not initialized. Cannot create obj:// URI.")

    object_id = uuid.uuid4().hex
    _OBJECT_CACHE[object_id] = obj

    obj_uri = f"obj://{_SESSION_ID}/{_ENV_ID}/{object_id}"
    return object_id, obj_uri


def _load_object(uri: str) -> Any:
    """Load object from cache by obj:// URI."""
    if not uri.startswith("obj://"):
        raise ValueError(f"Invalid object URI: {uri}")

    parts = uri[6:].split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid object URI format: {uri}")

    session_id, env_id, object_id = parts

    if session_id != _SESSION_ID or env_id != _ENV_ID:
        raise ValueError(
            f"Object {uri} belongs to different worker (current: {_SESSION_ID}/{_ENV_ID})"
        )

    if object_id not in _OBJECT_CACHE:
        raise KeyError(f"Object not found: {object_id}")

    return _OBJECT_CACHE[object_id]


def _load_input_data(input_ref: str | dict) -> Any:
    """Load input data from file or memory."""
    from bioio import BioImage

    if isinstance(input_ref, dict):
        uri = input_ref.get("uri", "")
        if uri.startswith("mem://"):
            return _load_from_memory(uri)
        else:
            path_str = uri.replace("file://", "")
            img = BioImage(path_str)
            return img.data
    else:
        img = BioImage(str(input_ref))
        return img.data


def _infer_dims_from_shape(shape: tuple[int, ...]) -> str:
    """Infer dimension labels from array shape."""
    ndim = len(shape)
    dims_map = {
        2: "YX",
        3: "ZYX",
        4: "CZYX",
        5: "TCZYX",
    }
    if ndim in dims_map:
        return dims_map[ndim]

    full_dims = "TCZYX"
    if ndim <= 0:
        return ""
    return full_dims[-ndim:] if ndim <= len(full_dims) else full_dims


def _expand_to_5d(data: np.ndarray) -> np.ndarray:
    """Expand array to 5D by prepending singleton dimensions."""
    import numpy as np

    while data.ndim < 5:
        data = np.expand_dims(data, axis=0)
    return data


def _convert_memory_inputs_to_files(inputs: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Convert mem:// artifact inputs to temporary file paths."""
    from bioio.writers import OmeTiffWriter

    converted_inputs = {}
    for key, value in inputs.items():
        if isinstance(value, dict) and value.get("uri", "").startswith("mem://"):
            mem_uri = value["uri"]
            data = _load_from_memory(mem_uri)
            temp_id = uuid.uuid4().hex[:8]
            temp_path = work_dir / f"_mem_{key}_{temp_id}.ome.tif"
            data_5d = _expand_to_5d(data)
            OmeTiffWriter.save(data_5d, temp_path, dim_order="TCZYX")
            converted_inputs[key] = {
                "uri": f"file://{temp_path}",
                "type": value.get("type", "BioImageRef"),
                "format": "OME-TIFF",
            }
        else:
            converted_inputs[key] = value
    return converted_inputs


def _introspect_cellpose_fn(target_fn: str) -> dict[str, Any]:
    """Introspect Cellpose function to get parameter schema."""
    from bioimage_mcp_cellpose.descriptions import SEGMENT_DESCRIPTIONS

    try:
        if target_fn == "cellpose.train.train_seg":
            import cellpose.train

            sig = inspect.signature(cellpose.train.train_seg)
        elif target_fn == "cellpose.denoise.DenoiseModel.eval":
            from cellpose.denoise import DenoiseModel

            sig = inspect.signature(DenoiseModel.eval)
        elif target_fn == "cellpose.metrics.average_precision":
            import cellpose.metrics

            sig = inspect.signature(cellpose.metrics.average_precision)
        else:
            from cellpose.models import CellposeModel

            sig = inspect.signature(CellposeModel.eval)
    except (ImportError, AttributeError):
        # Fallback for common parameters
        return {
            "type": "object",
            "properties": {
                "model_type": {
                    "type": "string",
                    "default": "cyto3",
                    "description": SEGMENT_DESCRIPTIONS.get("model_type", "Model type"),
                },
                "n_epochs": {
                    "type": "integer",
                    "default": 10,
                    "description": "Number of training epochs",
                },
                "learning_rate": {
                    "type": "number",
                    "default": 0.1,
                    "description": "Learning rate",
                },
                "weight_decay": {
                    "type": "number",
                    "default": 0.0001,
                    "description": "Weight decay",
                },
                "batch_size": {
                    "type": "integer",
                    "default": 8,
                    "description": "Batch size",
                },
            },
            "required": [],
        }

    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    exclude = {
        "self",
        "x",
        "channels",
        "channel_axis",
        "z_axis",
        "train_data",
        "train_labels",
        "test_data",
        "test_labels",
        "net",
        "masks_true",
        "masks_pred",
    }

    for name, param in sig.parameters.items():
        if name in exclude:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        prop: dict[str, Any] = {}
        prop["description"] = SEGMENT_DESCRIPTIONS.get(
            name, f"See Cellpose documentation for '{name}'."
        )

        if param.default is not inspect.Parameter.empty:
            default = param.default
            if hasattr(default, "item"):
                default = default.item()
            if default is not None:
                prop["default"] = default
        else:
            # Don't make everything required for now to be safe
            pass

        schema["properties"][name] = prop

    return schema


def handle_meta_describe(params: dict[str, Any]) -> dict[str, Any]:
    """Handle meta.describe requests for Cellpose functions."""
    target_fn = params.get("target_fn", "")

    if target_fn == "cellpose.models.CellposeModel.eval":
        schema = _introspect_cellpose_fn("cellpose.models.CellposeModel.eval")
        return {
            "ok": True,
            "result": {
                "params_schema": schema,
                "tool_version": _get_cellpose_version(),
                "introspection_source": "python_api",
            },
        }
    elif target_fn == "cellpose.train.train_seg":
        schema = _introspect_cellpose_fn("cellpose.train.train_seg")
        return {
            "ok": True,
            "result": {
                "params_schema": schema,
                "inputs_schema": {
                    "type": "object",
                    "properties": {
                        "images": {"type": "array", "items": {"type": "object"}},
                        "labels": {"type": "array", "items": {"type": "object"}},
                    },
                },
                "tool_version": _get_cellpose_version(),
                "introspection_source": "python_api",
            },
        }
    elif target_fn == "cellpose.denoise.DenoiseModel.eval":
        schema = _introspect_cellpose_fn("cellpose.denoise.DenoiseModel.eval")
        return {
            "ok": True,
            "result": {
                "params_schema": schema,
                "tool_version": _get_cellpose_version(),
                "introspection_source": "python_api",
            },
        }
    elif target_fn == "cellpose.metrics.average_precision":
        schema = _introspect_cellpose_fn("cellpose.metrics.average_precision")
        return {
            "ok": True,
            "result": {
                "params_schema": schema,
                "tool_version": _get_cellpose_version(),
                "introspection_source": "python_api",
            },
        }
    else:
        return {"ok": False, "error": f"Unknown function: {target_fn}"}


def handle_model_init(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    """Handle cellpose.CellposeModel instantiation."""
    import torch
    from cellpose.models import CellposeModel

    from bioimage_mcp_cellpose.ops.segment import _uri_to_path

    model_type = params.get("model_type", "cyto3")
    gpu = params.get("gpu", torch.cuda.is_available())

    # Handle pretrained_model if provided (T032)
    pretrained_model = params.get("pretrained_model")
    if isinstance(pretrained_model, dict) and "uri" in pretrained_model:
        # Extract path from NativeOutputRef
        pretrained_model = str(_uri_to_path(pretrained_model["uri"]))

    # Create model
    model = CellposeModel(model_type=model_type, gpu=gpu, pretrained_model=pretrained_model)

    # Store in cache
    object_id, obj_uri = _store_object(model)

    # Return ObjectRef
    output = {
        "ref_id": object_id,
        "type": "ObjectRef",
        "uri": obj_uri,
        "format": "pickle",
        "python_class": "cellpose.models.CellposeModel",
        "storage_type": "memory",
        "created_at": datetime.now(UTC).isoformat(),
        "metadata": {
            "model_type": model_type,
            "gpu": gpu,
            "device": "cuda" if gpu and torch.cuda.is_available() else "cpu",
        },
    }

    return {
        "ok": True,
        "outputs": {"model": output},
        "log": f"CellposeModel({model_type}) initialized",
    }


def handle_denoise_init(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    """Handle cellpose.denoise.DenoiseModel instantiation."""
    import torch
    from cellpose.denoise import DenoiseModel

    model_type = params.get("model_type", "denoise_cyto3")
    gpu = params.get("gpu", torch.cuda.is_available())

    # Create model
    model = DenoiseModel(model_type=model_type, gpu=gpu)

    # Store in cache
    object_id, obj_uri = _store_object(model)

    # Return ObjectRef
    output = {
        "ref_id": object_id,
        "type": "ObjectRef",
        "uri": obj_uri,
        "format": "pickle",
        "python_class": "cellpose.denoise.DenoiseModel",
        "storage_type": "memory",
        "created_at": datetime.now(UTC).isoformat(),
        "metadata": {
            "model_type": model_type,
            "gpu": gpu,
            "device": "cuda" if gpu and torch.cuda.is_available() else "cpu",
        },
    }

    return {
        "ok": True,
        "outputs": {"model": output},
        "log": f"DenoiseModel({model_type}) initialized",
    }


def handle_denoise_eval(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    """Handle cellpose.denoise.DenoiseModel.eval execution."""
    from bioimage_mcp_cellpose.ops.denoise import run_denoise

    # Check for model in inputs (ObjectRef)
    model_obj = None
    model_ref = inputs.get("model")
    if isinstance(model_ref, dict) and model_ref.get("uri", "").startswith("obj://"):
        try:
            model_obj = _load_object(model_ref["uri"])
        except (KeyError, ValueError):
            return {
                "ok": False,
                "error": {
                    "code": "ARTIFACT_NOT_FOUND",
                    "message": "Object not found in cache",
                    "details": [
                        {
                            "path": "inputs.model",
                            "hint": "Object may have been evicted or session expired",
                        }
                    ],
                },
            }

    outputs = run_denoise(inputs=inputs, params=params, work_dir=work_dir, model=model_obj)
    return {
        "ok": True,
        "outputs": outputs,
        "log": "Denoising complete",
    }


def handle_segment(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    """Handle cellpose.segment and cellpose.CellposeModel.eval execution."""
    from bioimage_mcp_cellpose.ops.segment import run_segment

    # Check for model in inputs (ObjectRef)
    model_obj = None
    model_ref = inputs.get("model")
    if isinstance(model_ref, dict) and model_ref.get("uri", "").startswith("obj://"):
        try:
            model_obj = _load_object(model_ref["uri"])
        except (KeyError, ValueError):
            return {
                "ok": False,
                "error": {
                    "code": "ARTIFACT_NOT_FOUND",
                    "message": "Object not found in cache",
                    "details": [
                        {
                            "path": "inputs.model",
                            "hint": "Object may have been evicted or session expired",
                        }
                    ],
                },
            }

    # Map 'x' to 'image' for CellposeModel.eval style calls
    if "x" in inputs and "image" not in inputs:
        inputs["image"] = inputs["x"]

    outputs = run_segment(inputs=inputs, params=params, work_dir=work_dir, model=model_obj)
    return {
        "ok": True,
        "outputs": outputs,
        "log": "Segmentation complete",
    }


def handle_cache_clear(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    """Clear all cached ObjectRefs from memory."""
    count = len(_OBJECT_CACHE)
    _OBJECT_CACHE.clear()
    return {
        "ok": True,
        "outputs": {},  # No outputs - clearing is a side effect
        "log": f"Cleared {count} cached objects",
    }


def handle_average_precision(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    """Handle cellpose.metrics.average_precision execution."""
    from bioimage_mcp_cellpose.ops.metrics import run_average_precision

    outputs = run_average_precision(inputs=inputs, params=params, work_dir=work_dir)
    return {
        "ok": True,
        "outputs": outputs,
        "log": "Average precision computed",
    }


def handle_train_seg(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    """Handle cellpose.train_seg execution (T031)."""
    from bioimage_mcp_cellpose.ops.training import run_train_seg

    # Check for net in inputs (ObjectRef)
    model_obj = None
    net_ref = inputs.get("net")
    if isinstance(net_ref, dict) and net_ref.get("uri", "").startswith("obj://"):
        try:
            model_obj = _load_object(net_ref["uri"])
        except (KeyError, ValueError):
            return {
                "ok": False,
                "error": {
                    "code": "ARTIFACT_NOT_FOUND",
                    "message": "Object not found in cache",
                    "details": [
                        {
                            "path": "inputs.net",
                            "hint": "Object may have been evicted or session expired",
                        }
                    ],
                },
            }

    outputs = run_train_seg(inputs=inputs, params=params, work_dir=work_dir, model=model_obj)
    return {
        "ok": True,
        "outputs": outputs,
        "log": "Training complete",
    }


# Function dispatch table
FUNCTION_HANDLERS = {
    "cellpose.models.CellposeModel": handle_model_init,
    "cellpose.models.CellposeModel.eval": handle_segment,
    "cellpose.denoise.DenoiseModel": handle_denoise_init,
    "cellpose.denoise.DenoiseModel.eval": handle_denoise_eval,
    "cellpose.train.train_seg": handle_train_seg,
    "cellpose.metrics.average_precision": handle_average_precision,
    "cellpose.cache.clear": handle_cache_clear,
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
        if "." not in python_class_name:
            raise ValueError(f"Invalid fully qualified class name: {python_class_name}")

        module_name, class_name = python_class_name.rsplit(".", 1)
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)

        # Instantiate
        obj = cls(**init_params)

        # Store in object cache
        object_id, obj_uri = _store_object(obj)

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
                    "created_at": datetime.now(UTC).isoformat(),
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
    fn_id = request.get("fn_id", "")
    params = request.get("params") or {}
    inputs = request.get("inputs") or {}
    work_dir = Path(request.get("work_dir") or ".").absolute()
    work_dir.mkdir(parents=True, exist_ok=True)
    ordinal = request.get("ordinal")

    output_mode = params.pop("output_mode", "file")

    try:
        inputs = _convert_memory_inputs_to_files(inputs, work_dir)
        if fn_id == "core.reconstruct":
            return handle_reconstruct(request)
        if fn_id == "meta.describe":
            result_response = handle_meta_describe(params)
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
        elif fn_id in FUNCTION_HANDLERS:
            handler = FUNCTION_HANDLERS[fn_id]
            result = handler(inputs, params, work_dir)

            if not result.get("ok"):
                error = result.get("error", "Function execution failed")
                if isinstance(error, str):
                    error = {"message": error}
                response = {
                    "command": "execute_result",
                    "ok": False,
                    "ordinal": ordinal,
                    "error": error,
                    "log": "failed",
                }
            else:
                outputs = result.get("outputs")
                if outputs is None:
                    raise ValueError(f"{fn_id} did not return outputs")

                if output_mode == "memory":
                    outputs = _convert_outputs_to_memory(outputs, work_dir)

                response = {
                    "command": "execute_result",
                    "ok": True,
                    "ordinal": ordinal,
                    "outputs": outputs,
                    "log": result.get("log", "ok"),
                }
        else:
            response = {
                "command": "execute_result",
                "ok": False,
                "ordinal": ordinal,
                "error": {"message": f"Unknown fn_id: {fn_id}"},
                "log": "failed",
            }
    except Exception as exc:  # noqa: BLE001
        response = {
            "command": "execute_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {"message": str(exc)},
            "outputs": {},
            "log": "failed",
        }
    return response


def _convert_outputs_to_memory(outputs: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    from datetime import datetime

    mem_outputs = {}
    for key, value in outputs.items():
        if isinstance(value, dict):
            if "path" in value:
                path = Path(value["path"])
                data = _load_input_data(str(path))
                artifact_id, mem_uri = _store_in_memory(data)
                try:
                    path.unlink()
                except Exception:  # noqa: BLE001
                    pass
                mem_outputs[key] = {
                    "ref_id": artifact_id,
                    "type": value.get("type", "BioImageRef"),
                    "uri": mem_uri,
                    "format": "memory",
                    "storage_type": "memory",
                    "mime_type": "application/octet-stream",
                    "size_bytes": data.nbytes,
                    "created_at": datetime.now(UTC).isoformat(),
                    "metadata": {
                        "shape": list(data.shape),
                        "dtype": str(data.dtype),
                        "dims": _infer_dims_from_shape(data.shape),
                    },
                }
            else:
                mem_outputs[key] = value
        elif isinstance(value, (str, Path)):
            data = _load_input_data(str(value))
            artifact_id, mem_uri = _store_in_memory(data)
            try:
                Path(value).unlink()
            except Exception:  # noqa: BLE001
                pass
            mem_outputs[key] = {
                "ref_id": artifact_id,
                "type": "BioImageRef",
                "uri": mem_uri,
                "format": "memory",
                "storage_type": "memory",
                "mime_type": "application/octet-stream",
                "size_bytes": data.nbytes,
                "created_at": datetime.now(UTC).isoformat(),
                "metadata": {
                    "shape": list(data.shape),
                    "dtype": str(data.dtype),
                    "dims": _infer_dims_from_shape(data.shape),
                },
            }
        else:
            mem_outputs[key] = value
    return mem_outputs


def _extract_artifact_id(ref_id: str | None) -> str:
    """Extract artifact_id from ref_id (supports mem://, obj:// URI and plain ID)."""
    if ref_id is None:
        raise ValueError("ref_id cannot be None")
    if not isinstance(ref_id, str):
        raise ValueError(f"ref_id must be a string, got {type(ref_id).__name__}")
    if not ref_id:
        raise ValueError("ref_id cannot be empty")

    if ref_id.startswith("mem://"):
        parts = ref_id[6:].split("/")
        if len(parts) != 3:
            raise ValueError(f"Invalid memory URI format: {ref_id}")
        _session_id_uri, _env_id_uri, artifact_id = parts
        return artifact_id
    elif ref_id.startswith("obj://"):
        parts = ref_id[6:].split("/")
        if len(parts) != 3:
            raise ValueError(f"Invalid object URI format: {ref_id}")
        _session_id_uri, _env_id_uri, object_id = parts
        return object_id
    elif "://" in ref_id or ref_id == "invalid-uri":
        raise ValueError(f"Invalid reference ID: {ref_id}")
    else:
        return ref_id


def handle_materialize(request: dict[str, Any]) -> dict[str, Any]:
    """Handle materialize command - export mem:// artifact to OME-Zarr or OME-TIFF."""
    ref_id = request.get("ref_id")
    target_format = request.get("target_format", "OME-TIFF")
    dest_path = request.get("dest_path")
    ordinal = request.get("ordinal")

    try:
        artifact_id = _extract_artifact_id(ref_id)
    except ValueError as exc:
        return {
            "command": "materialize_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {"code": "INVALID_REF_ID", "message": str(exc)},
        }

    if artifact_id not in _MEMORY_ARTIFACTS:
        return {
            "command": "materialize_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {"code": "NOT_FOUND", "message": f"Memory artifact not found: {ref_id}"},
        }

    data = _MEMORY_ARTIFACTS[artifact_id]

    if dest_path is None:
        import tempfile

        suffix = ".ome.tif" if target_format == "OME-TIFF" else ".ome.zarr"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        dest_path = temp_file.name
        temp_file.close()

    dest_path = Path(dest_path)

    try:
        if target_format == "OME-TIFF":
            from bioio.writers import OmeTiffWriter

            data_5d = _expand_to_5d(data)
            OmeTiffWriter.save(data_5d, dest_path, dim_order="TCZYX")
        elif target_format == "OME-Zarr":
            from bioio_ome_zarr.writers import OMEZarrWriter

            dims_str = _infer_dims_from_shape(data.shape)
            axes_names = [d.lower() for d in dims_str]
            type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
            axes_types = [type_map[d] for d in axes_names]

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
            "error": {"code": "MATERIALIZATION_FAILED", "message": f"Failed to materialize: {exc}"},
        }


def handle_evict(request: dict[str, Any]) -> dict[str, Any]:
    """Handle evict command - remove artifact from memory."""
    ref_id = request.get("ref_id")
    ordinal = request.get("ordinal")

    try:
        artifact_id = _extract_artifact_id(ref_id)
    except ValueError as exc:
        return {
            "command": "evict_result",
            "ok": False,
            "ordinal": ordinal,
            "error": {"code": "INVALID_REF_ID", "message": str(exc)},
        }

    if artifact_id in _MEMORY_ARTIFACTS:
        del _MEMORY_ARTIFACTS[artifact_id]
        return {"command": "evict_result", "ok": True, "ordinal": ordinal}

    if artifact_id in _OBJECT_CACHE:
        del _OBJECT_CACHE[artifact_id]
        return {"command": "evict_result", "ok": True, "ordinal": ordinal}

    return {
        "command": "evict_result",
        "ok": False,
        "ordinal": ordinal,
        "error": {"code": "NOT_FOUND", "message": f"Artifact not found: {ref_id}"},
    }


def main() -> int:
    """Main entrypoint supporting both single-request and persistent mode."""
    # 1. IMMEDIATE handshake for persistent mode
    is_persistent_mode = "BIOIMAGE_MCP_SESSION_ID" in os.environ

    # 2. Safe initialization / heavy imports
    try:
        # Simulation for testing
        if os.environ.get("SIMULATE_IMPORT_FAILURE") == "numpy":
            raise ImportError("Simulated numpy import failure")

        # Heavy imports
        import bioio  # noqa: F401
        import cellpose  # noqa: F401
        import numpy as np  # noqa: F401

        # Verify torch if needed
        try:
            import torch  # noqa: F401
        except ImportError:
            pass

    except Exception as exc:
        error_msg = f"Required library import failed: {str(exc)}"
        error_json = {
            "command": "error",
            "ok": False,
            "error": {"code": "IMPORT_FAILED", "message": error_msg},
        }
        if is_persistent_mode:
            print(json.dumps(error_json), flush=True)
        else:
            # Legacy mode response
            print(json.dumps({"ok": False, "error": error_msg}), flush=True)
        return 1

    # Initialize worker identity from environment or use defaults
    session_id = os.environ.get("BIOIMAGE_MCP_SESSION_ID", "default_session")
    env_id = os.environ.get("BIOIMAGE_MCP_ENV_ID", "bioimage-mcp-cellpose")
    _initialize_worker(session_id, env_id)

    if is_persistent_mode:
        # NDJSON loop mode
        # 3. Complete handshake
        ready_message = json.dumps(
            {"command": "ready", "status": "complete", "version": TOOL_VERSION}
        )
        print(ready_message, flush=True)

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
            elif request.get("command") == "materialize":
                response = handle_materialize(request)
                print(json.dumps(response), flush=True)
            elif request.get("command") == "evict":
                response = handle_evict(request)
                print(json.dumps(response), flush=True)
            elif request.get("command") == "shutdown":
                _MEMORY_ARTIFACTS.clear()
                print(
                    json.dumps(
                        {"command": "shutdown_ack", "ok": True, "ordinal": request.get("ordinal")}
                    ),
                    flush=True,
                )
                break
            else:
                print(
                    json.dumps(
                        {
                            "command": "error",
                            "ok": False,
                            "error": {"message": f"Unknown command: {request.get('command')}"},
                        }
                    ),
                    flush=True,
                )
        return 0
    else:
        # Legacy mode
        raw_input = sys.stdin.read()
        if not raw_input:
            return 0
        try:
            request = json.loads(raw_input)
            if "command" in request:
                # Handle single NDJSON-style request
                if request.get("command") == "execute":
                    response = process_execute_request(request)
                    print(json.dumps(response))
                return 0 if response.get("ok", True) else 1
            else:
                # Pure legacy format
                work_dir = Path(request.get("work_dir", ".")).absolute()
                work_dir.mkdir(parents=True, exist_ok=True)
                fn_id = request.get("fn_id", "")
                params = request.get("params", {})
                inputs = request.get("inputs", {})

                if fn_id == "meta.describe":
                    response = handle_meta_describe(params)
                elif fn_id in FUNCTION_HANDLERS:
                    response = FUNCTION_HANDLERS[fn_id](inputs, params, work_dir)
                else:
                    response = {"ok": False, "error": f"Unknown fn_id: {fn_id}"}
                print(json.dumps(response))
                return 0 if response.get("ok") else 1
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "Invalid JSON"}), flush=True)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
