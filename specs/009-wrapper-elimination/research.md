# Research: Wrapper Elimination & Enhanced Dynamic Discovery

**Date**: 2025-12-29  
**Status**: Complete

## Research Questions

### RQ-1: Where should overlay merging occur in the codebase?

**Decision**: Merge overlays in `loader.py::load_manifest_file()` immediately after dynamic function discovery.

**Rationale**:
- Single point of truth for function schemas
- SQLite index receives merged metadata
- `describe_function()` returns consistent data without runtime merging

**Alternatives Considered**:
- Runtime merging in `describe_function()`: Rejected because it requires repeated lookups and inconsistent caching
- Merging during adapter execution: Rejected because overlays are metadata, not runtime behavior

### RQ-2: How should legacy redirects be implemented?

**Decision**: Use `LEGACY_REDIRECTS` dictionary in `entrypoint.py` that maps old fn_id to new fn_id.

**Rationale**:
- Minimal code change
- Logs deprecation warning once per session per function
- Easy to remove in v1.0.0

**Alternatives Considered**:
- Manifest-level aliases: More complex, adds manifest schema burden
- Server-side redirect layer: Would require changes to run_function dispatch

### RQ-3: Which thin wrappers can be safely removed?

**Decision**: Remove 15 thin wrappers that have direct dynamic equivalents.

**Analysis**:
| Thin Wrapper | Dynamic Equivalent | Status |
|--------------|-------------------|--------|
| `preprocess.gaussian` | `skimage.filters.gaussian` | REMOVE |
| `preprocess.median` | `skimage.filters.median` | REMOVE |
| `preprocess.bilateral` | `skimage.restoration.denoise_bilateral` | REMOVE |
| `preprocess.unsharp_mask` | `skimage.filters.unsharp_mask` | REMOVE |
| `preprocess.sobel` | `skimage.filters.sobel` | REMOVE |
| `preprocess.threshold_otsu` | `skimage.filters.threshold_otsu` | REMOVE |
| `preprocess.threshold_yen` | `skimage.filters.threshold_yen` | REMOVE |
| `preprocess.morph_opening` | `skimage.morphology.opening` | REMOVE |
| `preprocess.morph_closing` | `skimage.morphology.closing` | REMOVE |
| `preprocess.remove_small_objects` | `skimage.morphology.remove_small_objects` | REMOVE |
| `preprocess.equalize_adapthist` | `skimage.exposure.equalize_adapthist` | REMOVE |
| `preprocess.denoise_nl_means` | `skimage.restoration.denoise_nl_means` | REMOVE |
| `transforms.resize` | `skimage.transform.resize` | REMOVE |
| `transforms.rescale` | `skimage.transform.rescale` | REMOVE |
| `transforms.rotate` | `skimage.transform.rotate` | REMOVE |

**Edge Cases**:
- `crop`: No direct equivalent -> RETAIN as `base.wrapper.transform.crop`
- `normalize_intensity`: Custom percentile logic -> RETAIN as `base.wrapper.preprocess.normalize_intensity`
- `project_sum/max`: Require axis parameter handling -> RETAIN as `base.wrapper.transform.*`
- `flip/pad`: No existing dynamic adapter -> RETAIN as `base.wrapper.transform.*`

### RQ-4: What overlay fields are needed for dynamic functions?

**Decision**: Support these overlay fields:
- `description`: Override docstring-derived description
- `tags`: Add searchability tags
- `io_pattern`: Override heuristic-detected I/O pattern
- `hints`: Add workflow guidance (expected_axes, next_steps)
- `params_override`: Modify specific parameter constraints

**Rationale**: These are the fields that dynamic discovery cannot reliably extract from library introspection.

### RQ-5: How should the wrapper package be organized?

**Decision**: Create `tools/base/bioimage_mcp_base/wrapper/` with category-based modules:
- `wrapper/io.py`: convert_to_ome_zarr, export_ome_tiff
- `wrapper/axis.py`: relabel_axes, squeeze, expand_dims, moveaxis, swap_axes
- `wrapper/phasor.py`: phasor_from_flim, phasor_calibrate
- `wrapper/denoise.py`: denoise_image
- `wrapper/edge_cases.py`: crop, normalize_intensity, flip, pad, project_sum, project_max (implements these edge cases; exposed via `base.wrapper.transform.*` or `base.wrapper.preprocess.*`)

**Rationale**: Clear separation of essential wrappers from removed thin wrappers; while implementation is grouped by complexity (edge cases), public fn_ids follow category-based naming.

## Technical Findings

### Dynamic Discovery Infrastructure
- **Adapters**: SkimageAdapter, ScipyNdimageAdapter, PhasorPyAdapter in `src/bioimage_mcp/registry/dynamic/adapters/`
- **Introspection**: Uses `inspect.signature` + docstring parsing via numpydoc
- **I/O Patterns**: Heuristic detection based on function/module names
- **Execution**: `dynamic_dispatch.py` routes to correct adapter

### Manifest Schema Structure
- **ToolManifest**: Root model with `functions` list and `dynamic_sources` list
- **Function**: Includes fn_id, inputs, outputs, params_schema, hints
- **DynamicSource**: adapter type, prefix, modules list
- **Overlay target**: Add `function_overlays: dict[str, FunctionOverlay]` to ToolManifest

### Current Wrapper Analysis
- **32 functions** in manifest (31 tools + 1 meta.describe)
- **10 essential wrappers**: Complex logic for metadata sync, multi-output, format bridging
- **15 thin wrappers**: Simple I/O boilerplate around single library calls
- **FN_MAP**: Dictionary mapping fn_id to (impl_func, description_obj) tuple

## Validation Approach

1. **Unit tests**: Overlay merging logic with various field combinations
2. **Contract tests**: Overlay schema validation against manifest
3. **Integration tests**: Execute dynamic functions end-to-end
4. **Migration tests**: Legacy redirect execution with deprecation logging
