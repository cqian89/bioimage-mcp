#!/usr/bin/env python3
"""Cellpose tool pack entrypoint for bioimage-mcp.

Implements the JSON stdin/stdout protocol for tool execution
and the meta.describe protocol for dynamic schema introspection.
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path so bioimage_mcp_cellpose can be imported
BASE_DIR = Path(__file__).resolve().parent
TOOLS_ROOT = BASE_DIR.parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))


# Tool pack version
TOOL_VERSION = "0.1.0"


def _get_cellpose_version() -> str:
    """Get the installed Cellpose version."""
    try:
        import cellpose

        return cellpose.__version__
    except ImportError:
        return "unknown"


def _introspect_cellpose_eval() -> dict[str, Any]:
    """Introspect CellposeModel.eval() to get parameter schema."""
    from bioimage_mcp_cellpose.descriptions import SEGMENT_DESCRIPTIONS

    try:
        from cellpose.models import CellposeModel

        sig = inspect.signature(CellposeModel.eval)
    except ImportError:
        # Return minimal schema if cellpose not installed
        return {
            "type": "object",
            "properties": {
                "model_type": {
                    "type": "string",
                    "default": "cyto3",
                    "description": SEGMENT_DESCRIPTIONS.get("model_type", "Model type"),
                },
                "diameter": {
                    "type": "number",
                    "default": 30.0,
                    "description": SEGMENT_DESCRIPTIONS.get("diameter", "Cell diameter"),
                },
            },
            "required": [],
        }

    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    # Parameters to exclude (internal or handled separately)
    exclude = {"self", "x", "batch_size", "channels", "channel_axis", "z_axis"}

    for name, param in sig.parameters.items():
        if name in exclude:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        prop: dict[str, Any] = {}

        # Use curated description or fallback
        prop["description"] = SEGMENT_DESCRIPTIONS.get(
            name, f"See Cellpose documentation for '{name}'."
        )

        # Add default value
        if param.default is not inspect.Parameter.empty:
            default = param.default
            # Handle numpy types
            if hasattr(default, "item"):
                default = default.item()
            if default is not None:
                prop["default"] = default
        else:
            schema["required"].append(name)

        schema["properties"][name] = prop

    return schema


def handle_meta_describe(params: dict[str, Any]) -> dict[str, Any]:
    """Handle meta.describe requests for Cellpose functions."""
    target_fn = params.get("target_fn", "")

    if target_fn == "cellpose.segment":
        schema = _introspect_cellpose_eval()
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


def handle_segment(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    """Handle cellpose.segment execution."""
    from bioimage_mcp_cellpose.ops.segment import run_segment

    outputs = run_segment(inputs=inputs, params=params, work_dir=work_dir)
    return {
        "ok": True,
        "outputs": outputs,
        "log": "Segmentation complete",
    }


def main() -> int:
    """Entrypoint: read JSON from stdin, dispatch, write JSON to stdout."""
    request = json.loads(sys.stdin.read() or "{}")

    fn_id = request.get("fn_id", "")
    params = request.get("params", {})
    inputs = request.get("inputs", {})
    work_dir = Path(request.get("work_dir", ".")).absolute()
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        if fn_id == "meta.describe":
            response = handle_meta_describe(params)
        elif fn_id == "cellpose.segment":
            response = handle_segment(inputs, params, work_dir)
        else:
            response = {"ok": False, "error": f"Unknown fn_id: {fn_id}"}
    except Exception as exc:  # noqa: BLE001
        response = {
            "ok": False,
            "error": {"message": str(exc)},
            "outputs": {},
            "log": f"Error: {exc}",
        }

    print(json.dumps(response))
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
