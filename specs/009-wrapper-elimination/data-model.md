# Data Model: Wrapper Elimination & Enhanced Dynamic Discovery

**Date**: 2025-12-29  
**Status**: Draft

## Entities

### FunctionOverlay

Configuration object for enriching dynamically discovered functions.

**Location**: `src/bioimage_mcp/registry/manifest_schema.py`

```python
class FunctionOverlay(BaseModel):
    """Override/supplement fields for a dynamically discovered function."""

    # Target function to overlay (must match a dynamically discovered fn_id)
    fn_id: str

    # Override fields (None = use discovered value)
    description: str | None = None
    tags: list[str] | None = None
    io_pattern: str | None = None  # IOPattern enum value as string

    # Deep-merged fields
    hints: FunctionHints | None = None

    # Parameter-specific overrides
    params_override: dict[str, dict[str, Any]] | None = None
```

**Validation Rules**:
- `fn_id` MUST be a valid identifier matching `<tool_id>.<prefix>.<module>.<function>` pattern
- `io_pattern` MUST be a valid IOPattern enum value if provided
- `params_override` keys MUST match existing parameter names in the discovered function

**State Transitions**: Static configuration; no runtime state changes.

### LegacyRedirect

Mapping from deprecated function ID to new function ID.

**Location**: `tools/base/bioimage_mcp_base/entrypoint.py`

```python
LEGACY_REDIRECTS: dict[str, str] = {
    # Old fn_id -> New fn_id
    "base.bioimage_mcp_base.transforms.phasor_from_flim": "base.wrapper.phasor.phasor_from_flim",
    "base.bioimage_mcp_base.transforms.phasor_calibrate": "base.wrapper.phasor.phasor_calibrate",
    "base.bioimage_mcp_base.axis_ops.relabel_axes": "base.wrapper.axis.relabel_axes",
    "base.bioimage_mcp_base.axis_ops.squeeze": "base.wrapper.axis.squeeze",
    "base.bioimage_mcp_base.axis_ops.expand_dims": "base.wrapper.axis.expand_dims",
    "base.bioimage_mcp_base.axis_ops.moveaxis": "base.wrapper.axis.moveaxis",
    "base.bioimage_mcp_base.axis_ops.swap_axes": "base.wrapper.axis.swap_axes",
    "base.bioimage_mcp_base.io.convert_to_ome_zarr": "base.wrapper.io.convert_to_ome_zarr",
    "base.bioimage_mcp_base.io.export_ome_tiff": "base.wrapper.io.export_ome_tiff",
    "base.bioimage_mcp_base.preprocess.denoise_image": "base.wrapper.denoise.denoise_image",
}
```

**Behavior**:
- When old fn_id is called, log deprecation warning with new fn_id
- Route to new fn_id implementation
- Remove in v1.0.0

### DynamicSource (Existing - Reference)

Already defined in `manifest_schema.py`. Documents adapter-based library introspection.

```python
class DynamicSource(BaseModel):
    """Configuration for dynamic function discovery from a library."""

    adapter: str  # Adapter type: "skimage", "scipy_ndimage", "phasorpy"
    prefix: str   # Namespace prefix for discovered functions
    modules: list[str]  # Python modules to introspect
```

### Updated ToolManifest

Add `function_overlays` field to existing ToolManifest.

```python
class ToolManifest(BaseModel):
    manifest_version: str
    tool_id: str
    tool_version: str
    name: str
    description: str
    env_id: str
    entrypoint: str

    # Existing fields
    functions: list[Function] = []
    dynamic_sources: list[DynamicSource] = []

    # NEW: Overlays for dynamic functions
    function_overlays: dict[str, FunctionOverlay] = {}

    # Metadata (set during loading)
    manifest_path: Path | None = None
    manifest_checksum: str | None = None
```

## Relationships

```
ToolManifest
├── functions: list[Function]           # Static function definitions
├── dynamic_sources: list[DynamicSource] # Library introspection configs
└── function_overlays: dict[str, FunctionOverlay]  # Enrichment for dynamic funcs
                                          │
                                          ▼
                              DynamicSource.discover()
                                          │
                                          ▼
                              FunctionMetadata (intermediate)
                                          │
                                          ▼
                              merge_function_overlay()
                                          │
                                          ▼
                              Function (final, indexed in SQLite)
```

## Data Flow

1. **Load manifest**: Parse YAML → ToolManifest
2. **Dynamic discovery**: For each DynamicSource, call adapter.discover() → FunctionMetadata list
3. **Convert to Function**: Map FunctionMetadata → Function objects
4. **Apply overlays**: For each Function, check function_overlays by fn_id, deep merge if exists
5. **Index**: Store merged Function objects in SQLite registry
6. **Serve**: describe_function() returns merged Function schema

## Merge Semantics

```python
def merge_function_overlay(discovered: Function, overlay: FunctionOverlay) -> Function:
    """Deep merge overlay into discovered function."""
    result = discovered.model_copy(deep=True)

    # Simple override fields
    if overlay.description is not None:
        result.description = overlay.description
    if overlay.tags is not None:
        result.tags = overlay.tags
    if overlay.io_pattern is not None:
        result.io_pattern = IOPattern(overlay.io_pattern)

    # Deep merge hints
    if overlay.hints is not None:
        if result.hints is None:
            result.hints = overlay.hints
        else:
            result.hints = deep_merge_hints(result.hints, overlay.hints)

    # Parameter overrides
    if overlay.params_override is not None:
        for param_name, overrides in overlay.params_override.items():
            if param_name in result.params_schema.get("properties", {}):
                result.params_schema["properties"][param_name].update(overrides)

    return result
```
