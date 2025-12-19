# `meta.describe` Protocol Specification

**Date**: 2025-12-19  
**Status**: Draft  
**Related**: `specs/001-cellpose-pipeline/research.md` Section 11

This document specifies the `meta.describe` protocol for dynamic parameter schema extraction in bioimage-mcp tool packs.

## Overview

The `meta.describe` protocol enables tool packs to expose their parameter schemas at runtime, combining automatic introspection with curated descriptions. This reduces maintenance burden and allows users to upgrade tool versions without waiting for manifest updates.

## Protocol Definition

### Request Format

The core server invokes `meta.describe` using the standard tool entrypoint protocol (JSON over stdin):

```json
{
  "fn_id": "meta.describe",
  "params": {
    "target_fn": "cellpose.segment"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `fn_id` | string | Always `"meta.describe"` |
| `params.target_fn` | string | The `fn_id` of the function to describe |

### Response Format

```json
{
  "ok": true,
  "result": {
    "params_schema": {
      "type": "object",
      "properties": {
        "diameter": {
          "type": "number",
          "default": 30.0,
          "description": "Estimated cell diameter in pixels. Use 0 for automatic estimation."
        },
        "flow_threshold": {
          "type": "number",
          "default": 0.4,
          "description": "Flow error threshold for mask reconstruction (0.0-1.0)."
        }
      },
      "required": []
    },
    "tool_version": "4.0.1",
    "introspection_source": "python_api"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | Success indicator |
| `result.params_schema` | object | JSON Schema for function parameters |
| `result.tool_version` | string | Version of the underlying tool (e.g., Cellpose version) |
| `result.introspection_source` | string | How schema was derived: `python_api`, `argparse`, `manual` |

### Error Response

```json
{
  "ok": false,
  "error": "Unknown function: cellpose.unknown"
}
```

## Shared Introspection Utilities

Tool packs can use shared utilities to reduce boilerplate. These should be implemented in a helper module (e.g., `src/bioimage_mcp/runtimes/introspect.py` or bundled with each tool pack).

### Python API Introspection

```python
"""Introspect Python function signatures to generate JSON Schema."""

import inspect
from typing import Any, Callable, get_type_hints


# Map Python types to JSON Schema types
TYPE_MAP = {
    int: "integer",
    float: "number",
    str: "string",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def introspect_python_api(
    func: Callable,
    descriptions: dict[str, str],
    exclude_params: set[str] | None = None,
) -> dict[str, Any]:
    """
    Generate JSON Schema from a Python function signature.
    
    Args:
        func: The function to introspect (e.g., CellposeModel.eval)
        descriptions: Curated parameter descriptions {param_name: description}
        exclude_params: Parameter names to exclude (e.g., {'self', 'x'})
    
    Returns:
        JSON Schema dict with 'type', 'properties', and 'required' fields
    """
    exclude = exclude_params or {"self"}
    sig = inspect.signature(func)
    
    # Try to get type hints (may fail for some functions)
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}
    
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    
    for name, param in sig.parameters.items():
        if name in exclude:
            continue
        
        # Skip *args and **kwargs
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        
        prop: dict[str, Any] = {}
        
        # Add description (curated or fallback)
        if name in descriptions:
            prop["description"] = descriptions[name]
        else:
            prop["description"] = f"See {func.__module__} documentation."
        
        # Add default value
        if param.default is not inspect.Parameter.empty:
            # Handle numpy types and other non-JSON-serializable defaults
            default = param.default
            if hasattr(default, "item"):  # numpy scalar
                default = default.item()
            if default is not None:
                prop["default"] = default
        else:
            # No default = required parameter
            schema["required"].append(name)
        
        # Map type annotation to JSON Schema type
        type_hint = hints.get(name, param.annotation)
        if type_hint is not inspect.Parameter.empty:
            origin = getattr(type_hint, "__origin__", type_hint)
            if origin in TYPE_MAP:
                prop["type"] = TYPE_MAP[origin]
        
        schema["properties"][name] = prop
    
    return schema
```

### Argparse Introspection (for Python CLIs)

```python
"""Introspect argparse parsers to generate JSON Schema."""

import argparse
from typing import Any


def introspect_argparse(
    parser: argparse.ArgumentParser,
    descriptions: dict[str, str],
    exclude_dests: set[str] | None = None,
) -> dict[str, Any]:
    """
    Generate JSON Schema from an argparse ArgumentParser.
    
    Args:
        parser: The argument parser to introspect
        descriptions: Curated parameter descriptions {dest_name: description}
        exclude_dests: Destination names to exclude (e.g., {'help', 'version'})
    
    Returns:
        JSON Schema dict with 'type', 'properties', and 'required' fields
    """
    exclude = exclude_dests or {"help", "version"}
    
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    
    for action in parser._actions:
        if action.dest in exclude:
            continue
        
        # Skip positional arguments that are typically file paths
        if not action.option_strings:
            continue
        
        prop: dict[str, Any] = {}
        
        # Add description (curated takes precedence, then argparse help)
        if action.dest in descriptions:
            prop["description"] = descriptions[action.dest]
        elif action.help and action.help != argparse.SUPPRESS:
            prop["description"] = action.help
        else:
            prop["description"] = f"See tool documentation."
        
        # Add default value
        if action.default is not None and action.default != argparse.SUPPRESS:
            prop["default"] = action.default
        
        # Add choices as enum
        if action.choices:
            prop["enum"] = list(action.choices)
        
        # Map argparse type to JSON Schema type
        if action.type is not None:
            if action.type in (int,):
                prop["type"] = "integer"
            elif action.type in (float,):
                prop["type"] = "number"
            elif action.type in (str,):
                prop["type"] = "string"
        elif isinstance(action, argparse._StoreTrueAction):
            prop["type"] = "boolean"
            prop["default"] = False
        elif isinstance(action, argparse._StoreFalseAction):
            prop["type"] = "boolean"
            prop["default"] = True
        
        # Check if required
        if action.required:
            schema["required"].append(action.dest)
        
        schema["properties"][action.dest] = prop
    
    return schema
```

## Tool Pack Implementation Example: Cellpose

### Directory Structure

```
tools/
  cellpose/
    bioimage_mcp_cellpose/
      __init__.py
      entrypoint.py
      descriptions.py    # Curated parameter descriptions
      ops/
        segment.py
    manifest.yaml
```

### Curated Descriptions (`descriptions.py`)

```python
"""Curated parameter descriptions for Cellpose functions."""

SEGMENT_DESCRIPTIONS = {
    # Core parameters
    "diameter": (
        "Estimated cell diameter in pixels. "
        "Use 0 for automatic diameter estimation. "
        "Critical for accurate segmentation."
    ),
    "flow_threshold": (
        "Flow error threshold for mask reconstruction (0.0-1.0). "
        "Lower values = stricter, fewer masks. "
        "Higher values = more permissive, more masks."
    ),
    "cellprob_threshold": (
        "Cell probability threshold (-6.0 to 6.0). "
        "Lower values = larger cells. "
        "Higher values = smaller, more confident detections."
    ),
    "model_type": (
        "Pretrained model to use. Options include 'cyto3' (cells), "
        "'nuclei' (nuclei), or path to custom model."
    ),
    
    # GPU/performance
    "gpu": (
        "Use GPU acceleration if available. "
        "Significantly faster for large images."
    ),
    "batch_size": (
        "Number of tiles to process in parallel on GPU. "
        "Increase for faster processing if GPU memory allows."
    ),
    
    # 3D parameters
    "do_3D": (
        "Run 3D segmentation. Input must have Z dimension. "
        "More computationally intensive than 2D."
    ),
    "stitch_threshold": (
        "Threshold for stitching 2D masks into 3D (0.0-1.0). "
        "Only used when do_3D=False on 3D data."
    ),
    
    # Advanced
    "min_size": (
        "Minimum mask size in pixels. "
        "Masks smaller than this are removed."
    ),
    "normalize": (
        "Normalize image intensities. "
        "Set to False if image is already normalized."
    ),
}
```

### Entrypoint with `meta.describe` (`entrypoint.py`)

```python
#!/usr/bin/env python3
"""Cellpose tool pack entrypoint for bioimage-mcp."""

import json
import sys
from typing import Any

# Import after ensuring we're in the right environment
def handle_meta_describe(params: dict[str, Any]) -> dict[str, Any]:
    """Handle meta.describe requests."""
    target_fn = params.get("target_fn", "")
    
    if target_fn == "cellpose.segment":
        return describe_segment()
    else:
        return {"ok": False, "error": f"Unknown function: {target_fn}"}


def describe_segment() -> dict[str, Any]:
    """Generate schema for cellpose.segment function."""
    import inspect
    
    import cellpose
    from cellpose.models import CellposeModel
    
    from .descriptions import SEGMENT_DESCRIPTIONS
    
    # Use shared utility (inline here for clarity)
    sig = inspect.signature(CellposeModel.eval)
    
    schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    
    exclude = {"self", "x", "batch_size", "channels"}  # x is the image input
    
    for name, param in sig.parameters.items():
        if name in exclude:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        
        prop = {}
        
        # Curated description or fallback
        prop["description"] = SEGMENT_DESCRIPTIONS.get(
            name,
            "See Cellpose documentation."
        )
        
        # Default value
        if param.default is not inspect.Parameter.empty:
            default = param.default
            if hasattr(default, "item"):
                default = default.item()
            if default is not None:
                prop["default"] = default
        
        schema["properties"][name] = prop
    
    return {
        "ok": True,
        "result": {
            "params_schema": schema,
            "tool_version": cellpose.__version__,
            "introspection_source": "python_api",
        },
    }


def handle_segment(params: dict[str, Any]) -> dict[str, Any]:
    """Execute cellpose.segment."""
    from .ops.segment import run_segment
    return run_segment(params)


def main() -> None:
    """Entrypoint: read JSON from stdin, dispatch, write JSON to stdout."""
    request = json.load(sys.stdin)
    fn_id = request.get("fn_id", "")
    params = request.get("params", {})
    
    if fn_id == "meta.describe":
        result = handle_meta_describe(params)
    elif fn_id == "cellpose.segment":
        result = handle_segment(params)
    else:
        result = {"ok": False, "error": f"Unknown fn_id: {fn_id}"}
    
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
```

### Manifest (`manifest.yaml`)

```yaml
manifest_version: "0.1"
tool_id: tools.cellpose
tool_version: "0.1.0"
name: Cellpose Segmentation
description: Cell and nucleus segmentation using Cellpose

env_id: bioimage-mcp-cellpose
entrypoint: bioimage_mcp_cellpose/entrypoint.py
python_version: "3.10"
platforms_supported:
  - linux-64
  - osx-arm64
  - win-64

functions:
  - fn_id: cellpose.segment
    tool_id: tools.cellpose
    name: Cellpose Segment
    description: Segment cells or nuclei using Cellpose deep learning models.
    tags: [segmentation, deep-learning, cells, nuclei]
    inputs:
      - name: image
        artifact_type: BioImageRef
        required: true
    outputs:
      - name: labels
        artifact_type: LabelImageRef
        format: OME-TIFF
        required: true
      - name: cellpose_bundle
        artifact_type: NativeOutputRef
        format: cellpose-seg-npy
        required: false
        description: Tool-native Cellpose output bundle (_seg.npy) for full-fidelity access to flows, masks, and metadata.
    # params_schema can be minimal here; full schema comes from meta.describe
    params_schema:
      type: object
      properties: {}
    resource_hints:
      gpu_recommended: true
      memory_mb: 4096

  - fn_id: meta.describe
    tool_id: tools.cellpose
    name: Describe Function
    description: Return parameter schema for a function.
    tags: [meta]
    inputs: []
    outputs: []
    params_schema:
      type: object
      properties:
        target_fn:
          type: string
          description: "The fn_id to describe"
      required:
        - target_fn
```

## Core Server Integration

### Registry Enhancement

The `ToolRegistry` should call `meta.describe` during discovery to populate full parameter schemas:

```python
# In src/bioimage_mcp/registry/index.py

async def _enrich_function_schemas(self, manifest: ToolManifest) -> None:
    """
    Call meta.describe for each function to get full parameter schemas.
    
    This runs during registry initialization, after manifests are loaded.
    """
    # Check if tool pack supports meta.describe
    meta_fn = next(
        (f for f in manifest.functions if f.fn_id == "meta.describe"),
        None,
    )
    if not meta_fn:
        return  # Tool doesn't support dynamic schemas
    
    for func in manifest.functions:
        if func.fn_id == "meta.describe":
            continue  # Don't describe the describe function
        
        try:
            result = await self._executor.run(
                manifest=manifest,
                fn_id="meta.describe",
                params={"target_fn": func.fn_id},
                timeout_seconds=30,
            )
            if result.get("ok") and "result" in result:
                # Merge introspected schema with manifest schema
                introspected = result["result"].get("params_schema", {})
                func.params_schema = _merge_schemas(
                    func.params_schema,
                    introspected,
                )
        except Exception as e:
            # Log warning but don't fail; fall back to manifest schema
            logger.warning(
                f"Failed to introspect {func.fn_id}: {e}"
            )


def _merge_schemas(base: dict, introspected: dict) -> dict:
    """
    Merge manifest schema with introspected schema.
    
    Manifest takes precedence for explicit overrides.
    """
    merged = introspected.copy()
    
    # Manifest properties override introspected
    if "properties" in base:
        merged.setdefault("properties", {})
        merged["properties"].update(base["properties"])
    
    # Manifest required list is authoritative if present
    if "required" in base and base["required"]:
        merged["required"] = base["required"]
    
    return merged
```

## Caching Strategy

To avoid calling `meta.describe` on every server startup:

1. **Cache by tool version**: Store introspected schemas in SQLite alongside the tool version.
2. **Invalidate on version change**: If `tool_version` or underlying library version changes, re-introspect.
3. **Fallback to manifest**: If cache is cold and introspection fails, use manifest schema.

```python
# Schema cache table
CREATE TABLE IF NOT EXISTS schema_cache (
    fn_id TEXT PRIMARY KEY,
    tool_version TEXT NOT NULL,
    params_schema TEXT NOT NULL,  -- JSON
    introspected_at TEXT NOT NULL
);
```

## Testing

### Unit Test: Introspection Utilities

```python
def test_introspect_python_api():
    """Test that Python API introspection extracts correct schema."""
    def sample_func(
        x: int,
        name: str = "default",
        threshold: float = 0.5,
    ) -> None:
        pass
    
    descriptions = {"x": "The input value", "threshold": "A threshold"}
    schema = introspect_python_api(
        sample_func,
        descriptions,
        exclude_params=set(),
    )
    
    assert schema["properties"]["x"]["type"] == "integer"
    assert schema["properties"]["x"]["description"] == "The input value"
    assert "x" in schema["required"]
    
    assert schema["properties"]["name"]["default"] == "default"
    assert schema["properties"]["threshold"]["default"] == 0.5
```

### Integration Test: Cellpose meta.describe

```python
@pytest.mark.integration
async def test_cellpose_meta_describe(executor, cellpose_manifest):
    """Test that cellpose.segment schema is correctly introspected."""
    result = await executor.run(
        manifest=cellpose_manifest,
        fn_id="meta.describe",
        params={"target_fn": "cellpose.segment"},
        timeout_seconds=60,
    )
    
    assert result["ok"] is True
    schema = result["result"]["params_schema"]
    
    # Check key parameters are present
    assert "diameter" in schema["properties"]
    assert "flow_threshold" in schema["properties"]
    
    # Check descriptions are curated
    assert "pixel" in schema["properties"]["diameter"]["description"].lower()
    
    # Check version is reported
    assert "tool_version" in result["result"]
```

## Migration Path

For existing tool packs without `meta.describe`:

1. **No change required**: Manifest `params_schema` continues to work.
2. **Opt-in enhancement**: Add `meta.describe` function when ready.
3. **Gradual rollout**: Core server falls back to manifest if introspection fails.

## Future Extensions

1. **Validation constraints**: Extend introspection to extract `minimum`, `maximum`, `pattern` from docstrings or decorators.
2. **Dynamic outputs**: Allow `meta.describe` to report output schemas based on input parameters.
3. **Dependency graph**: Introspect parameter dependencies (e.g., "if `do_3D` is true, `stitch_threshold` is relevant").
