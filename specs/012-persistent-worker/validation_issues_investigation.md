# Validation Issues Investigation Report

**Date**: 2026-01-02  
**Context**: Investigation of issues from `datasets/FLUTE_FLIM_data_tif/outputs/20260101_2253_test_validation_workflow.md`

---

## Summary

This report investigates three key questions:
1. What decides which functions are listed (is there a whitelist)?
2. What causes the cellpose "No adapter found" error?
3. What causes the skimage rank mismatch errors?

---

## 1. Function Listing Mechanism (Whitelist Analysis)

### How Functions Are Listed

The function listing is controlled by a **multi-layer system**:

#### Layer 1: Manifest-Defined Functions
Static functions are explicitly declared in `tools/<pack>/manifest.yaml`:
- `tools/base/manifest.yaml`: Defines `base.xarray.*`, `base.bioio.export`, `meta.describe`
- `tools/cellpose/manifest.yaml`: Defines `cellpose.segment`, `meta.describe`

#### Layer 2: Dynamic Discovery via Adapters
Dynamic functions are discovered at runtime from `dynamic_sources` in manifests.

**Base manifest dynamic sources** (`tools/base/manifest.yaml:15-51`):
```yaml
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
    include_patterns:
      - "*"
    exclude_patterns:
      - "_*"
      - "test_*"

  - adapter: phasorpy
    prefix: phasorpy
    modules:
      - phasorpy.phasor
      - phasorpy.io
    # ...

  - adapter: scipy
    prefix: scipy
    modules:
      - scipy.ndimage
```

#### Layer 3: Adapter Registry (The "Whitelist")

**Location**: `src/bioimage_mcp/registry/dynamic/adapters/__init__.py:59-82`

The `ADAPTER_REGISTRY` dict controls which prefixes can be dynamically dispatched:

```python
ADAPTER_REGISTRY: dict[str, Any] = {}

def _populate_default_adapters() -> None:
    ADAPTER_REGISTRY["phasorpy"] = PhasorPyAdapter()
    ADAPTER_REGISTRY["scipy"] = ScipyNdimageAdapter()
    ADAPTER_REGISTRY["skimage"] = SkimageAdapter()
    ADAPTER_REGISTRY["xarray"] = XarrayAdapterForRegistry()
```

**Key finding**: Only these 4 prefixes have adapters registered:
- `phasorpy`
- `scipy`
- `skimage`
- `xarray`

**Cellpose is NOT in this registry** - it uses static manifest functions only.

#### Layer 4: Xarray Allowlist (Method-Level Filtering)

**Location**: `src/bioimage_mcp/registry/dynamic/allowlists.py:11-26`

```python
XARRAY_ALLOWLIST: dict[str, dict[str, Any]] = {
    "rename": {...},
    "squeeze": {...},
    "expand_dims": {...},
    "transpose": {...},
    "isel": {...},
    "pad": {...},
    "sum": {...},
    "max": {...},
    "mean": {...},
    # ...
}

XARRAY_DENYLIST: frozenset[str] = frozenset({
    "values", "to_numpy", "load", "compute", "data"
})
```

This prevents memory-unsafe operations on xarray DataArrays.

### Answer: Is There a Whitelist?

**Yes, multiple layers:**

| Layer | Scope | Control |
|-------|-------|---------|
| `ADAPTER_REGISTRY` | Prefix-level | Which library adapters exist |
| `manifest.dynamic_sources.modules` | Module-level | Which modules to introspect |
| `include_patterns`/`exclude_patterns` | Function-level | Glob patterns for function names |
| `XARRAY_ALLOWLIST`/`XARRAY_DENYLIST` | Method-level | Safe xarray operations |

---

## 2. Cellpose "No adapter found for prefix: 'cellpose'" Error

### Root Cause

The error message from the validation report:
> Error: "No adapter found for prefix: 'cellpose'"

This originates from `tools/base/bioimage_mcp_base/dynamic_dispatch.py:40-41`:

```python
if prefix not in ADAPTER_REGISTRY:
    raise ValueError(f"No adapter found for prefix: '{prefix}'")
```

### Why It Happens

1. **Cellpose is NOT in the adapter registry**: The `ADAPTER_REGISTRY` only contains `phasorpy`, `scipy`, `skimage`, `xarray`

2. **Cellpose uses static manifest dispatch, not dynamic dispatch**: The cellpose manifest (`tools/cellpose/manifest.yaml`) defines `cellpose.segment` as a static function, not via `dynamic_sources`.

3. **Routing mismatch**: When `cellpose.segment` is called:
   - `ExecutionService.run_workflow()` searches manifests for `fn_id == "cellpose.segment"`
   - It should find the cellpose manifest and route to `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
   - However, the dynamic dispatch code is being invoked instead

### Investigation of Routing Path

Looking at `src/bioimage_mcp/api/execution.py:140-230`:

```python
def execute_step(...):
    manifests, _diagnostics = load_manifests(config.tool_manifest_roots)
    
    for manifest in manifests:
        for fn in manifest.functions:
            if fn.fn_id != fn_id:
                continue
            # Found! Use this manifest's entrypoint
            entrypoint = manifest.entrypoint
            # ...
    raise KeyError(fn_id)  # Not found in any manifest
```

The issue is that `cellpose.segment` may not match the fn_id lookup because:
- The manifest defines `fn_id: cellpose.segment`
- But the function ID in the request may be formatted differently (e.g., `tools.cellpose.segment`)

### Diagnosis

The error "No adapter found for prefix: 'cellpose'" suggests the call is reaching `dispatch_dynamic()` in the base entrypoint, which means:

1. The cellpose manifest wasn't loaded (environment not set up correctly), OR
2. The fn_id matching failed, causing fallback to dynamic dispatch

**Most likely cause**: The cellpose environment (`bioimage-mcp-cellpose`) is not installed, so:
- The manifest discovery doesn't find/load it
- The function falls through to dynamic dispatch
- Dynamic dispatch fails because there's no `cellpose` adapter

### Recommended Fixes

1. **Verify cellpose environment installation**:
   ```bash
   micromamba activate bioimage-mcp-cellpose
   python -c "import cellpose; print(cellpose.__version__)"
   ```

2. **Add better error messages**: When a function isn't found, indicate whether:
   - The manifest exists but environment isn't installed
   - The function ID doesn't match any manifest

3. **Optional**: Add a "cellpose" adapter for dynamic dispatch if generic cellpose functions are desired

---

## 3. Skimage Rank Mismatch Errors

### Reported Errors

From the validation report:
- `base.skimage.filters.threshold_otsu`: Workflow validation failed/parameter mismatch
- `base.skimage.segmentation.felzenszwalb`: Rank mismatch error on 5D input

### Root Cause

**bioio always returns 5D TCZYX arrays** (per AGENTS.md specification):

```python
from bioio import BioImage
img = BioImage(path)
data = img.data  # Always 5D TCZYX
```

**Most skimage functions expect 2D or 3D input**:

```python
# skimage.segmentation.felzenszwalb expects:
#   image : (M, N, C) or (M, N) ndarray
#   NOT 5D arrays!
```

### Code Analysis

**Loading in SkimageAdapter** (`src/bioimage_mcp/registry/dynamic/adapters/skimage.py:145-172`):

```python
def _load_image(self, artifact: Artifact) -> np.ndarray:
    # ...
    try:
        from bioio import BioImage
        img = BioImage(path, reader=reader)
        data = img.data.compute() if hasattr(img.data, "compute") else img.data
        if data is not None and data.size > 0:
            return data  # <-- Always 5D TCZYX!
    except Exception:
        pass
    # Fallback to tifffile
    return tifffile.imread(path)
```

**Execution** (`src/bioimage_mcp/registry/dynamic/adapters/skimage.py:316-317`):

```python
# Execute function
result = func(*args, **kwargs, **params)
# No dimension handling before calling func!
```

### Why `threshold_otsu` Fails

`threshold_otsu` returns a scalar threshold value, not an image:

```python
>>> from skimage.filters import threshold_otsu
>>> threshold_otsu(image_2d)  # Returns float, not array
```

The adapter expects image output for `filters` module functions:

```python
def determine_io_pattern(self, module_name: str, func_name: str) -> IOPattern:
    if func_name.startswith("threshold_"):
        return IOPattern.ARRAY_TO_SCALAR  # Correct pattern
```

But the execute path doesn't handle `ARRAY_TO_SCALAR` properly - it tries to save the scalar as an image.

### Why `felzenszwalb` Fails

`felzenszwalb` requires 2D or 3D input:

```python
# From skimage.segmentation.felzenszwalb docstring:
#   image : (M, N, C) or (M, N) ndarray
```

When given 5D `(1, 1, 56, 512, 512)` TCZYX data, skimage raises a rank mismatch error.

### Recommended Fixes

#### Fix 1: Add Dimension Squeezing/Extraction

Add preprocessing in `SkimageAdapter.execute()`:

```python
def _prepare_for_skimage(self, data: np.ndarray, func_name: str) -> np.ndarray:
    """Prepare 5D TCZYX data for skimage functions that expect 2D/3D."""
    if data.ndim <= 3:
        return data
    
    # Squeeze singleton dimensions (T=1, C=1, Z=1)
    squeezed = np.squeeze(data)
    
    # If still >3D, take first slice from each leading dimension
    while squeezed.ndim > 3:
        squeezed = squeezed[0]
    
    return squeezed
```

#### Fix 2: Handle `ARRAY_TO_SCALAR` Pattern

```python
def execute(self, fn_id, inputs, params, work_dir=None):
    # ...
    result = func(*args, **kwargs, **params)
    
    io_pattern = self.determine_io_pattern(module_path, func_name)
    
    if io_pattern == IOPattern.ARRAY_TO_SCALAR:
        # Return scalar result directly, not as image artifact
        return [{"type": "ScalarRef", "value": float(result)}]
```

#### Fix 3: Add Function-Specific Dimension Requirements

Enhance adapter with dimension requirements per function:

```python
SKIMAGE_DIM_REQUIREMENTS = {
    "skimage.segmentation.felzenszwalb": {"max_ndim": 3},
    "skimage.filters.threshold_otsu": {"expected_output": "scalar"},
    # ...
}
```

---

## Summary of Findings

| Issue | Root Cause | Fix Priority |
|-------|------------|--------------|
| Function listing | Multi-layer whitelist system (adapters, modules, patterns) | N/A (documentation) |
| Cellpose adapter error | Cellpose env not installed OR manifest routing mismatch | High |
| Skimage rank mismatch | 5D bioio output passed directly to 2D/3D functions | High |
| threshold_otsu failure | ARRAY_TO_SCALAR pattern not handled in execute() | Medium |

---

## Recommended Actions

1. **Immediate**: Verify cellpose environment installation and manifest loading
2. **Short-term**: Add dimension preprocessing in SkimageAdapter.execute()
3. **Medium-term**: Implement proper ARRAY_TO_SCALAR output handling
4. **Long-term**: Add per-function dimension requirement metadata in adapters
