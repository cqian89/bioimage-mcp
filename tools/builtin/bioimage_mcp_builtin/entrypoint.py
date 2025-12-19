from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from typing import Any

from bioimage_mcp_builtin.ops.convert_to_ome_zarr import convert_to_ome_zarr
from bioimage_mcp_builtin.ops.gaussian_blur import gaussian_blur

# Version of the builtin tool pack
TOOL_VERSION = "0.1.0"

# Curated descriptions for function parameters
GAUSSIAN_BLUR_DESCRIPTIONS = {
    "sigma": "Standard deviation for Gaussian kernel. Higher values = more blur.",
}

CONVERT_TO_OME_ZARR_DESCRIPTIONS = {
    "chunk_size": "Chunk size for Zarr array. Affects I/O performance.",
}


def _introspect_function(func: Any, descriptions: dict[str, str]) -> dict[str, Any]:
    """Generate JSON Schema from a function signature."""
    sig = inspect.signature(func)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    # Exclude common internal parameters
    exclude = {"inputs", "params", "work_dir", "self"}

    for name, param in sig.parameters.items():
        if name in exclude:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        prop: dict[str, Any] = {}

        if name in descriptions:
            prop["description"] = descriptions[name]
        else:
            prop["description"] = "See documentation."

        if param.default is not inspect.Parameter.empty and param.default is not None:
            prop["default"] = param.default
        elif param.default is inspect.Parameter.empty:
            schema["required"].append(name)

        schema["properties"][name] = prop

    return schema


def handle_meta_describe(params: dict[str, Any]) -> dict[str, Any]:
    """Handle meta.describe requests for builtin functions."""
    target_fn = params.get("target_fn", "")

    fn_schemas = {
        "builtin.gaussian_blur": (gaussian_blur, GAUSSIAN_BLUR_DESCRIPTIONS),
        "builtin.convert_to_ome_zarr": (convert_to_ome_zarr, CONVERT_TO_OME_ZARR_DESCRIPTIONS),
    }

    if target_fn not in fn_schemas:
        return {"ok": False, "error": f"Unknown function: {target_fn}"}

    func, descriptions = fn_schemas[target_fn]
    schema = _introspect_function(func, descriptions)

    return {
        "ok": True,
        "result": {
            "params_schema": schema,
            "tool_version": TOOL_VERSION,
            "introspection_source": "python_api",
        },
    }


def main() -> int:
    request = json.loads(sys.stdin.read() or "{}")

    fn_id = request.get("fn_id")
    params = request.get("params") or {}
    inputs = request.get("inputs") or {}
    work_dir = Path(request.get("work_dir") or ".").absolute()
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Handle meta.describe protocol
        if fn_id == "meta.describe":
            response = handle_meta_describe(params)
        elif fn_id == "builtin.convert_to_ome_zarr":
            out_path = convert_to_ome_zarr(inputs=inputs, params=params, work_dir=work_dir)
            response = {
                "ok": True,
                "outputs": {
                    "output": {
                        "type": "BioImageRef",
                        "format": "OME-Zarr",
                        "path": str(out_path),
                    }
                },
                "log": "ok",
            }
        elif fn_id == "builtin.gaussian_blur":
            out_path = gaussian_blur(inputs=inputs, params=params, work_dir=work_dir)
            response = {
                "ok": True,
                "outputs": {
                    "output": {
                        "type": "BioImageRef",
                        "format": "OME-Zarr",
                        "path": str(out_path),
                    }
                },
                "log": "ok",
            }
        else:
            raise ValueError(f"Unknown fn_id: {fn_id}")

    except Exception as exc:  # noqa: BLE001
        response = {"ok": False, "error": {"message": str(exc)}, "outputs": {}, "log": "failed"}

    print(json.dumps(response))
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
