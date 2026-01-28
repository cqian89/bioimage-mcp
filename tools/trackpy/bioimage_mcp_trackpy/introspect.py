"""Introspection helpers for trackpy functions.

Runs inside the trackpy env to support out-of-process discovery.
"""

from __future__ import annotations

import importlib
import inspect
import logging
from typing import Any

from numpydoc.docscrape import NumpyDocString

logger = logging.getLogger(__name__)

TRACKPY_MODULES = [
    "trackpy",  # Top-level: locate, batch, link, annotate, etc.
    "trackpy.linking",  # Linking algorithms
    "trackpy.motion",  # Motion analysis (msd, etc.)
    "trackpy.predict",  # Predictors (NearestVelocityPredict, etc.)
    "trackpy.filtering",  # Filters for feature/trajectory refinement
    "trackpy.plots",  # Plotting functions
    "trackpy.diag",  # Diagnostics (subpx_bias, etc.)
    "trackpy.feature",  # Feature finding internals
    "trackpy.refine",  # Refinement functions
    "trackpy.masks",  # Mask utilities
    "trackpy.preprocessing",  # Preprocessing utilities
    "trackpy.artificial",  # Synthetic data generation
]

# Params that are artifact inputs, not scalar params
ARTIFACT_INPUT_PARAMS = {
    "image",
    "raw_image",
    "frames",
    "f",
    "features",
    "t",
    "tracks",
    "traj",
    "label_image",
    "mask",
    "reader",
}


def introspect_module(module_name: str) -> list[dict]:
    """Discover all public functions in a module."""
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        logger.warning(f"Failed to import {module_name}: {e}")
        return []

    functions = []
    # Use __all__ if available, else dir() filtered by public names
    names = getattr(module, "__all__", [n for n in dir(module) if not n.startswith("_")])

    for name in names:
        obj = getattr(module, name)
        # Only interested in functions
        if not callable(obj) or inspect.isclass(obj):
            continue

        # Ensure it belongs to this module (not imported)
        # Note: trackpy often exposes functions in top-level that are defined in submodules
        # We allow this if module_name is "trackpy"
        if module_name != "trackpy" and getattr(obj, "__module__", "") != module_name:
            continue

        fn_id = f"{module_name}.{name}"
        summary = _extract_summary(obj)
        io_pattern = _determine_io_pattern(module_name, name)

        functions.append(
            {
                "fn_id": fn_id,
                "name": name,
                "summary": summary,
                "module": module_name,
                "io_pattern": io_pattern,
            }
        )

    return functions


def introspect_function(fn_id: str) -> dict:
    """Get detailed schema for a single function."""
    parts = fn_id.rsplit(".", 1)
    if len(parts) == 2:
        module_name, func_name = parts
    else:
        module_name, func_name = "trackpy", parts[0]

    module = importlib.import_module(module_name)
    func = getattr(module, func_name)

    sig = inspect.signature(func)
    doc_str = func.__doc__ or ""
    doc = NumpyDocString(doc_str)

    # Parse docstring params for descriptions and types
    doc_params = {}
    for p in doc.get("Parameters", []):
        p_name = p.name.split(":")[0].strip()
        p_desc = " ".join(p.desc).strip()
        p_type = p.type if hasattr(p, "type") and p.type else ""
        doc_params[p_name] = {"description": p_desc, "type": p_type}

    # Build params schema
    properties = {}
    required = []

    # Try to get manual overrides
    try:
        from bioimage_mcp_trackpy.descriptions import DESCRIPTION_OVERRIDES

        overrides = DESCRIPTION_OVERRIDES.get(fn_id, {})
    except ImportError:
        overrides = {}

    for param_name, param in sig.parameters.items():
        if param_name in ARTIFACT_INPUT_PARAMS:
            continue  # Filter artifact inputs
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue  # Skip *args and **kwargs

        # Get description
        description = overrides.get(param_name)
        if not description:
            description = doc_params.get(param_name, {}).get("description", "")

        # Get type
        has_default = param.default is not inspect.Parameter.empty
        annotation = param.annotation

        # Infer from default if no annotation
        if annotation is inspect.Parameter.empty or annotation is Any:
            if has_default and isinstance(param.default, (bool, int, float, str)):
                annotation = type(param.default)
            else:
                annotation = doc_params.get(param_name, {}).get("type", "")

        json_type = _map_type_to_json_schema(annotation, param.default if has_default else None)

        prop = {
            "type": json_type,
            "description": description,
        }

        if has_default:
            prop["default"] = _make_json_serializable(param.default)
        else:
            required.append(param_name)

        properties[param_name] = prop

    return {
        "fn_id": fn_id,
        "params_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
        "tool_version": get_trackpy_version(),
        "summary": _extract_summary(func),
        "introspection_source": "numpydoc",
    }


def get_trackpy_version() -> str:
    """Get the version of the installed trackpy library."""
    try:
        import importlib.metadata

        return importlib.metadata.version("trackpy")
    except Exception:
        return "unknown"


def _extract_summary(func) -> str:
    doc = func.__doc__ or ""
    return doc.strip().split("\n")[0].strip()


def _determine_io_pattern(module_name: str, func_name: str) -> str:
    # locate, batch, refine -> image_to_table (features DataFrame)
    if func_name in ("locate", "batch", "refine", "local_maxima", "locate_brightfield"):
        return "image_to_table"
    # link, link_df -> table_to_table (trajectories DataFrame)
    if func_name in ("link", "link_df", "link_iter", "link_partial"):
        return "table_to_table"
    # motion analysis -> table_to_table
    if func_name in ("msd", "imsd", "emsd", "vanhove", "compute_drift", "subtract_drift"):
        return "table_to_table"
    # plots -> image_to_image (roughly, as they produce plots)
    if func_name in ("annotate", "plot_traj", "annotate3d"):
        return "image_to_image"
    return "generic"


def _map_type_to_json_schema(annotation: Any, default_value: Any = None) -> str:
    if annotation is int or annotation == "int":
        return "integer"
    elif annotation is str or annotation == "str":
        return "string"
    elif annotation is float or annotation == "float":
        return "number"
    elif annotation is bool or annotation == "bool":
        return "boolean"
    elif annotation in (list, tuple) or annotation in ("list", "tuple"):
        return "array"

    if isinstance(annotation, str):
        low = annotation.lower()
        if "int" in low:
            return "integer"
        if "float" in low or "number" in low:
            return "number"
        if "bool" in low:
            return "boolean"
        if "str" in low:
            return "string"
        if "list" in low or "tuple" in low or "array" in low:
            return "array"

    if default_value is not None:
        if isinstance(default_value, bool):
            return "boolean"
        if isinstance(default_value, int):
            return "integer"
        if isinstance(default_value, float):
            return "number"
        if isinstance(default_value, (list, tuple)):
            return "array"

    return "string"


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
