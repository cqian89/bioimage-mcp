# Data Model: Dynamic Function Registry

## Configuration Models

### DynamicSource
Configuration for a library to be dynamically exposed. Added to `ToolManifest`.

| Field | Type | Description |
|---|---|---|
| `adapter` | `str` | Name of the adapter implementation to use (e.g., "skimage", "phasorpy", "scipy_ndimage"). |
| `prefix` | `str` | The fn_id namespace prefix for tools (e.g., "skimage", "phasorpy", "scipy"). May differ from adapter. |
| `modules` | `List[str]` | List of python module paths to inspect (e.g., "skimage.filters"). |
| `include_patterns` | `List[str]` | Glob patterns for functions to include (default: `["*"]`). |
| `exclude_patterns` | `List[str]` | Glob patterns for functions to exclude. |

### Manifest Update
Existing `ToolManifest` is updated to include `dynamic_sources`.

```python
class ToolManifest(BaseModel):
    # ... existing fields ...
    dynamic_sources: List[DynamicSource] = Field(default_factory=list)
```

## Introspection Models

### ParameterSchema
JSON Schema definition for a function parameter.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Parameter name. |
| `type` | `str` | JSON schema type (string, number, integer, boolean, array). |
| `description` | `str` | Description from docstring. |
| `default` | `Any` | Default value if optional. |
| `required` | `bool` | Whether the parameter is required. |

### FunctionMetadata
Result of introspecting a single function.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Function name. |
| `module` | `str` | Module path. |
| `qualified_name` | `str` | Full ID (module + name). |
| `docstring` | `str` | Raw or parsed docstring summary. |
| `parameters` | `Dict[str, ParameterSchema]` | Parameter definitions. |
| `io_pattern` | `str` | Inferred I/O pattern (e.g., "image_to_image"). |

## Adapter Models

### IOPattern (Enum)
Categorization of function I/O behavior. Must match patterns defined in `plan.md`.

| Value | Inputs | Outputs | Description |
|---|---|---|---|
| `IMAGE_TO_IMAGE` | `[BioImageRef]` | `[BioImageRef]` | Standard image filters/transforms |
| `IMAGE_TO_LABELS` | `[BioImageRef]` | `[LabelImageRef]` | Segmentation, labeling |
| `LABELS_TO_TABLE` | `[LabelImageRef]` | `[TableRef]` | Region property extraction |
| `SIGNAL_TO_PHASOR` | `[BioImageRef]` | `[BioImageRef, BioImageRef, BioImageRef]` | FLIM signal to (intensity, G, S) |
| `PHASOR_TRANSFORM` | `[BioImageRef, BioImageRef]` | `[BioImageRef, BioImageRef]` | (G, S) -> (G', S') calibration |
| `PHASOR_TO_OTHER` | `[BioImageRef, BioImageRef]` | varies | Phasor to polar/signal conversion |
| `ARRAY_TO_ARRAY` | `[BioImageRef]` | `[BioImageRef]` | Generic array transform |
| `ARRAY_TO_SCALAR` | `[BioImageRef]` | `[NativeOutputRef]` | Threshold computation, etc. |
| `FILE_TO_SIGNAL` | `[str]` | `[BioImageRef]` | File path to signal array |
