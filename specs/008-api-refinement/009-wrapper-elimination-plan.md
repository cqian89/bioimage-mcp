# Plan: Wrapper Elimination & Enhanced Dynamic Discovery

**Created**: 2025-12-29  
**Status**: Draft  
**Parent Spec**: 008-api-refinement  

## Executive Summary

This plan addresses the following issues identified during code review:

1. **Function naming mismatch**: Spec says `base.skimage.filters.gaussian`, implementation uses `base.bioimage_mcp_base.preprocess.gaussian`
2. **Thin wrapper duplication**: 18 functions are near-identical wrappers (~10-15 lines of I/O boilerplate)
3. **Essential wrappers obscured**: High-value functions (phasor, axis ops) buried among thin wrappers
4. **Dynamic discovery underutilized**: System is built but not fully integrated

### Proposed Changes

1. **Remove 18 thin wrappers** from static manifest
2. **Keep 10 essential wrappers** renamed to `base.wrapper.<module>.<func>`
3. **Enable full dynamic discovery** for `base.skimage.*`, `base.scipy.*`, `base.phasorpy.*`
4. **Add manifest overlay system** for enriching dynamically discovered functions

---

## Current State Analysis

### Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │              MCP Server                  │
                    │  ┌─────────────┐  ┌──────────────────┐  │
                    │  │ RegistryIndex│  │ DiscoveryService │  │
                    │  └──────┬──────┘  └────────┬─────────┘  │
                    │         │                  │            │
                    │         ▼                  ▼            │
                    │  ┌─────────────────────────────────┐    │
                    │  │      load_manifest_file()       │    │
                    │  │  ┌───────────┐ ┌─────────────┐  │    │
                    │  │  │  Static   │ │  Dynamic    │  │    │
                    │  │  │ Functions │ │ Discovery   │  │    │
                    │  │  └───────────┘ └─────────────┘  │    │
                    │  └─────────────────────────────────┘    │
                    └────────────────────┬────────────────────┘
                                         │ JSON over stdin/stdout
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │        Tool Environment (subprocess)     │
                    │  ┌─────────────────────────────────┐    │
                    │  │         entrypoint.py           │    │
                    │  │  ┌───────────┐ ┌─────────────┐  │    │
                    │  │  │  FN_MAP   │ │  Dynamic    │  │    │
                    │  │  │ (static)  │ │  Dispatch   │  │    │
                    │  │  └───────────┘ └─────────────┘  │    │
                    │  └─────────────────────────────────┘    │
                    └─────────────────────────────────────────┘
```

### Dynamic Discovery Flow (Current)

1. `manifest.yaml` declares `dynamic_sources` with adapters (skimage, scipy, phasorpy)
2. `loader.py::load_manifest_file()` calls `discover_functions()` for each source
3. Adapters introspect library modules and return `FunctionMetadata`
4. Discovered functions are converted to `Function` objects and appended to manifest
5. Functions are indexed in SQLite and exposed via `list_tools`, `search_functions`

### Dynamic Execution Flow (Current)

1. `run_function(fn_id="base.skimage.filters.gaussian")` called
2. Server invokes tool subprocess via `execute_tool()`
3. `entrypoint.py::main()` receives request on stdin
4. If `fn_id` not in `FN_MAP`, falls through to `dispatch_dynamic()`
5. `dynamic_dispatch.py` finds adapter by prefix and calls `adapter.execute()`
6. Adapter handles: load image → call library function → save result → return ref

### Current Naming Analysis

| Category | Current Name | Proposed Name |
|----------|--------------|---------------|
| **Static (wrapper)** | `base.bioimage_mcp_base.transforms.phasor_from_flim` | `base.wrapper.phasor.phasor_from_flim` |
| **Static (thin)** | `base.bioimage_mcp_base.preprocess.gaussian` | *REMOVE* (use dynamic) |
| **Dynamic** | `base.skimage.filters.gaussian` | `base.skimage.filters.gaussian` ✓ |

---

## Design: Manifest Overlay System

### Problem

Dynamic discovery generates function schemas from docstrings, but:
- Descriptions may be too technical for LLM agents
- No `hints` for workflow guidance
- I/O types inferred heuristically, may be wrong
- No curated tags for searchability

### Solution: Function Overlays

Add a new `function_overlays` section to `manifest.yaml` that merges with dynamically discovered functions:

```yaml
# manifest.yaml
dynamic_sources:
  - adapter: skimage
    prefix: skimage
    modules:
      - skimage.filters
      - skimage.morphology

function_overlays:
  base.skimage.filters.gaussian:
    # These fields OVERRIDE dynamic discovery
    description: "Apply Gaussian blur to smooth an image"
    tags: [preprocessing, filter, smoothing]
    hints:
      inputs:
        image:
          expected_axes: ["Y", "X"]
          preprocessing_hint: "Works best on normalized images"
      success_hints:
        next_steps:
          - fn_id: base.skimage.filters.threshold_otsu
            reason: "Segment after smoothing"
    
  base.skimage.morphology.remove_small_objects:
    # Override I/O pattern if heuristic was wrong
    io_pattern: labels_to_labels  # Not image_to_image
    description: "Remove small connected components from a label image"
```

### Merge Semantics

When `describe_function(fn_id="base.skimage.filters.gaussian")` is called:

1. Fetch base schema from dynamic discovery (params from introspection)
2. Look up overlay in manifest's `function_overlays` by fn_id
3. **Deep merge**: Overlay fields override discovered fields
4. Return merged result

```python
def merge_function_overlay(discovered: dict, overlay: dict) -> dict:
    """Deep merge overlay into discovered function schema."""
    result = copy.deepcopy(discovered)
    
    # Override simple fields
    for key in ["description", "tags", "io_pattern"]:
        if key in overlay:
            result[key] = overlay[key]
    
    # Deep merge hints
    if "hints" in overlay:
        result["hints"] = deep_merge(
            result.get("hints", {}), 
            overlay["hints"]
        )
    
    # Override params if specified (rarely needed)
    if "params_override" in overlay:
        for param_name, param_override in overlay["params_override"].items():
            if param_name in result.get("params_schema", {}).get("properties", {}):
                result["params_schema"]["properties"][param_name].update(param_override)
    
    return result
```

---

## Design: Artifact I/O for Dynamic Functions

### Current Approach

Thin wrappers exist because:
1. Library functions expect `ndarray`, not `{"uri": "file://...", "metadata": {...}}`
2. Library functions return `ndarray`, not artifact references
3. OME metadata (axes, pixel sizes) must be propagated

Adapters (e.g., `SkimageAdapter`) already handle this:
- `_load_image(artifact)` → `ndarray`
- `func(*args, **kwargs)` → `ndarray`
- `_save_image(result, work_dir, axes)` → `{"type": "BioImageRef", ...}`

### Enhancement: Metadata Propagation

Current adapters infer output axes from input axes. We should enhance this:

```python
class SkimageAdapter(BaseAdapter):
    def execute(self, fn_id: str, inputs: list, params: dict, work_dir: Path):
        # ... existing code ...
        
        # NEW: Propagate metadata more carefully
        input_metadata = self._extract_full_metadata(primary_input)
        output_metadata = self._compute_output_metadata(
            input_metadata=input_metadata,
            func_name=func_name,
            params=params,
            result_shape=result.shape,
        )
        
        return self._save_image(
            result, 
            work_dir=work_dir, 
            metadata=output_metadata,  # Full metadata, not just axes
        )
    
    def _compute_output_metadata(self, input_metadata, func_name, params, result_shape):
        """Compute output metadata based on function semantics."""
        meta = dict(input_metadata)
        meta["shape"] = list(result_shape)
        
        # Handle axis-changing functions
        if func_name == "rescale" and "scale" in params:
            # Rescale changes spatial dimensions
            pass  # axes order unchanged
        elif func_name == "rotate" and params.get("resize"):
            # Rotation with resize changes shape
            pass  # axes order unchanged
        
        return meta
```

### Alternative: Same-Environment In-Memory Pipeline

For functions running in the same environment, consider an optimization:

```python
# Instead of save → load → save → load for each step,
# keep intermediate arrays in memory within a pipeline

class InMemoryPipeline:
    """Optimized execution for same-env function chains."""
    
    def __init__(self, session_id: str):
        self._cache: dict[str, np.ndarray] = {}
        self._metadata: dict[str, dict] = {}
    
    def execute_step(self, fn_id: str, inputs: dict, params: dict) -> dict:
        # Check if inputs are in cache
        resolved_inputs = {}
        for name, ref in inputs.items():
            ref_id = ref.get("ref_id")
            if ref_id in self._cache:
                resolved_inputs[name] = self._cache[ref_id]
            else:
                resolved_inputs[name] = self._load_from_disk(ref)
        
        # Execute
        result = self._execute_function(fn_id, resolved_inputs, params)
        
        # Cache result with ephemeral ref_id
        ephemeral_id = f"mem:{uuid4()}"
        self._cache[ephemeral_id] = result
        
        return {"ref_id": ephemeral_id, "storage": "memory"}
    
    def materialize(self, ref_id: str, work_dir: Path) -> dict:
        """Write cached array to disk when pipeline completes."""
        if ref_id in self._cache:
            return self._save_to_disk(self._cache[ref_id], work_dir)
        raise KeyError(f"No cached result: {ref_id}")
```

**Decision**: This is an optimization for later. Current disk-based approach works correctly.

---

## Implementation Plan

### Phase 1: Manifest Overlay Model (Low Risk)

**Goal**: Add overlay support without changing existing functions

#### Tasks

1. **T001**: Add `FunctionOverlay` Pydantic model to `manifest_schema.py`
   ```python
   class FunctionOverlay(BaseModel):
       fn_id: str  # Target function to overlay
       description: str | None = None
       tags: list[str] | None = None
       io_pattern: str | None = None  # Override IOPattern
       hints: FunctionHints | None = None
       params_override: dict | None = None
   ```

2. **T002**: Add `function_overlays: list[FunctionOverlay]` to `ToolManifest`

3. **T003**: Implement merge logic in `discovery.py::describe_function()`
   - After fetching dynamic schema, check for overlay
   - Deep merge overlay fields into result

4. **T004**: Write contract tests for overlay merging

5. **T005**: Add sample overlays to `tools/base/manifest.yaml` for validation

### Phase 2: Essential Wrapper Reorganization (Medium Risk)

**Goal**: Rename high-value wrappers to `base.wrapper.*` namespace

#### Essential Wrappers to Keep

| Current Name | New Name | Reason |
|--------------|----------|--------|
| `base.bioimage_mcp_base.io.convert_to_ome_zarr` | `base.wrapper.io.convert_to_ome_zarr` | Format bridging |
| `base.bioimage_mcp_base.io.export_ome_tiff` | `base.wrapper.io.export_ome_tiff` | Format bridging + dtype handling |
| `base.bioimage_mcp_base.axis_ops.relabel_axes` | `base.wrapper.axis.relabel_axes` | OME metadata sync |
| `base.bioimage_mcp_base.axis_ops.squeeze` | `base.wrapper.axis.squeeze` | OME metadata sync |
| `base.bioimage_mcp_base.axis_ops.expand_dims` | `base.wrapper.axis.expand_dims` | OME metadata sync |
| `base.bioimage_mcp_base.axis_ops.moveaxis` | `base.wrapper.axis.moveaxis` | OME metadata sync |
| `base.bioimage_mcp_base.axis_ops.swap_axes` | `base.wrapper.axis.swap_axes` | OME metadata sync |
| `base.bioimage_mcp_base.transforms.phasor_from_flim` | `base.wrapper.phasor.phasor_from_flim` | Multi-output orchestration |
| `base.bioimage_mcp_base.transforms.phasor_calibrate` | `base.wrapper.phasor.phasor_calibrate` | Multi-input handling |
| `base.bioimage_mcp_base.preprocess.denoise_image` | `base.wrapper.denoise.denoise_image` | Per-plane processing hub |

#### Tasks

6. **T006**: Create `tools/base/bioimage_mcp_base/wrapper/` package
   - `wrapper/__init__.py`
   - `wrapper/io.py` (move from io.py)
   - `wrapper/axis.py` (move from axis_ops.py)
   - `wrapper/phasor.py` (move from transforms.py)
   - `wrapper/denoise.py` (move from preprocess.py)

7. **T007**: Update `manifest.yaml` with new `fn_id` values

8. **T008**: Update `entrypoint.py::FN_MAP` to use new names

9. **T009**: Add redirects for old names (temporary, remove in v0.3)
   ```python
   # In entrypoint.py
   LEGACY_REDIRECTS = {
       "base.bioimage_mcp_base.transforms.phasor_from_flim": "base.wrapper.phasor.phasor_from_flim",
       # ...
   }
   ```

10. **T010**: Update integration tests to use new names

### Phase 3: Thin Wrapper Removal (Medium Risk)

**Goal**: Remove 18 thin wrappers, rely on dynamic discovery

#### Thin Wrappers to Remove

```
base.bioimage_mcp_base.transforms.project_sum     → base.numpy.sum (with axis)
base.bioimage_mcp_base.transforms.project_max     → base.numpy.max (with axis)
base.bioimage_mcp_base.transforms.resize          → base.skimage.transform.resize
base.bioimage_mcp_base.transforms.rescale         → base.skimage.transform.rescale
base.bioimage_mcp_base.transforms.rotate          → base.skimage.transform.rotate
base.bioimage_mcp_base.transforms.flip            → base.numpy.flip
base.bioimage_mcp_base.transforms.crop            → (manual slicing - keep as wrapper?)
base.bioimage_mcp_base.transforms.pad             → base.numpy.pad
base.bioimage_mcp_base.preprocess.normalize_intensity → (no direct equivalent - keep?)
base.bioimage_mcp_base.preprocess.gaussian        → base.skimage.filters.gaussian
base.bioimage_mcp_base.preprocess.median          → base.skimage.filters.median
base.bioimage_mcp_base.preprocess.bilateral       → base.skimage.restoration.denoise_bilateral
base.bioimage_mcp_base.preprocess.denoise_nl_means → base.skimage.restoration.denoise_nl_means
base.bioimage_mcp_base.preprocess.unsharp_mask    → base.skimage.filters.unsharp_mask
base.bioimage_mcp_base.preprocess.equalize_adapthist → base.skimage.exposure.equalize_adapthist
base.bioimage_mcp_base.preprocess.sobel           → base.skimage.filters.sobel
base.bioimage_mcp_base.preprocess.threshold_otsu  → base.skimage.filters.threshold_otsu
base.bioimage_mcp_base.preprocess.threshold_yen   → base.skimage.filters.threshold_yen
base.bioimage_mcp_base.preprocess.morph_opening   → base.skimage.morphology.opening
base.bioimage_mcp_base.preprocess.morph_closing   → base.skimage.morphology.closing
base.bioimage_mcp_base.preprocess.remove_small_objects → base.skimage.morphology.remove_small_objects
```

#### Edge Cases

| Function | Issue | Resolution |
|----------|-------|------------|
| `project_sum` | numpy.sum needs axis param | Add to `numpy` adapter or keep as wrapper |
| `crop` | No library equivalent | Keep as `base.wrapper.transform.crop` |
| `normalize_intensity` | Custom percentile logic | Keep as `base.wrapper.preprocess.normalize_intensity` |
| `median`/`morph_*` | Auto-footprint selection | Add overlay with default param |

#### Tasks

11. **T011**: Verify dynamic discovery produces correct functions
    - Run validation script listing all `base.skimage.*` functions
    - Compare with current wrapper functionality

12. **T012**: Add overlays for functions needing customization
    ```yaml
    function_overlays:
      base.skimage.filters.median:
        hints:
          inputs:
            image:
              preprocessing_hint: "Auto-selects disk (2D) or ball (3D) footprint"
    ```

13. **T013**: Remove thin wrapper implementations from `preprocess.py`, `transforms.py`

14. **T014**: Remove thin wrapper entries from `manifest.yaml`

15. **T015**: Update `entrypoint.py::FN_MAP` to remove thin wrappers

16. **T016**: Add migration note to README for users of old function names

### Phase 4: Enhanced Adapter I/O (Low Risk)

**Goal**: Improve metadata propagation in adapters

#### Tasks

17. **T017**: Enhance `SkimageAdapter._extract_metadata()` to capture full OME metadata

18. **T018**: Add `_propagate_metadata()` for common transform patterns

19. **T019**: Add axis inference tests for edge cases (3D, 5D images)

20. **T020**: Document metadata propagation rules in adapter docstrings

### Phase 5: Validation & Cleanup

21. **T021**: Run full test suite, fix any regressions

22. **T022**: Update integration tests to use dynamic function names

23. **T023**: Validate `list_tools(path="base.skimage")` returns expected hierarchy

24. **T024**: Performance test: Verify discovery completes in <500ms

25. **T025**: Update documentation with new function naming scheme

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing workflows | Medium | High | Phase 3 adds temporary redirects |
| Dynamic discovery missing functions | Low | Medium | Validate against current wrapper list |
| Metadata loss in adapters | Low | Medium | Enhanced propagation in Phase 4 |
| Performance regression | Low | Low | Cache introspection results |

---

## Success Criteria

1. **Function count**: Static manifest reduced from ~30 to ~12 essential wrappers
2. **Dynamic functions**: `list_tools(path="base.skimage")` returns 50+ functions
3. **Overlay system**: `describe_function("base.skimage.filters.gaussian")` returns merged hints
4. **No test regressions**: All existing tests pass (with updated names)
5. **Naming consistency**: All functions follow `base.<source>.<module>.<func>` pattern

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Overlay Model | 1 day | None |
| Phase 2: Wrapper Reorganization | 2 days | Phase 1 |
| Phase 3: Thin Wrapper Removal | 2 days | Phase 2 |
| Phase 4: Enhanced Adapter I/O | 1 day | Phase 3 |
| Phase 5: Validation | 1 day | Phase 4 |

**Total**: ~7 days

---

## Appendix: Sample Manifest After Changes

```yaml
manifest_version: "0.0"
tool_id: tools.base
tool_version: "0.2.0"
name: Base Image Processing Toolkit
description: Common image I/O, transforms, and pre-processing functions.

env_id: bioimage-mcp-base
entrypoint: bioimage_mcp_base/entrypoint.py
python_version: "3.13"

# Dynamic sources - these expose library functions directly
dynamic_sources:
  - adapter: skimage
    prefix: skimage
    modules:
      - skimage.filters
      - skimage.morphology
      - skimage.transform
      - skimage.exposure
      - skimage.restoration
      - skimage.segmentation
      - skimage.measure

  - adapter: phasorpy
    prefix: phasorpy
    modules:
      - phasorpy.phasor
      - phasorpy.io

  - adapter: scipy
    prefix: scipy
    modules:
      - scipy.ndimage

# Essential wrappers only - functions with significant value-add
functions:
  # I/O bridging
  - fn_id: base.wrapper.io.convert_to_ome_zarr
    tool_id: tools.base
    name: Convert to OME-Zarr
    description: Convert any image to OME-Zarr for pipeline processing.
    # ... full definition ...

  - fn_id: base.wrapper.io.export_ome_tiff
    tool_id: tools.base
    name: Export OME-TIFF
    description: Export image to OME-TIFF with dtype conversion and metadata.
    # ... full definition ...

  # Axis operations (OME metadata aware)
  - fn_id: base.wrapper.axis.relabel_axes
    # ...
  
  # FLIM phasor analysis (complex orchestration)
  - fn_id: base.wrapper.phasor.phasor_from_flim
    # ...

# Overlays for dynamic functions
function_overlays:
  base.skimage.filters.gaussian:
    description: "Apply Gaussian blur to smooth an image"
    tags: [preprocessing, filter, smoothing, skimage]
    hints:
      inputs:
        image:
          expected_axes: ["Y", "X"]
      success_hints:
        next_steps:
          - fn_id: base.skimage.filters.threshold_otsu
            reason: "Segment after smoothing"

  base.skimage.morphology.remove_small_objects:
    io_pattern: labels_to_labels
    description: "Remove small connected components from label image"
    tags: [postprocessing, cleanup, labels, skimage]
```
