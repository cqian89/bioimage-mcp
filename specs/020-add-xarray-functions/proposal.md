# Feature Specification: Dynamic xarray Function Discovery

**Feature Branch**: `020-add-xarray-functions`  
**Created**: 2026-01-10  
**Status**: Proposal  
**Input**: Expand xarray function coverage from 9 static methods to 135+ dynamically discovered functions covering top-level functions, universal functions, and comprehensive DataArray methods.

## Executive Summary

The current xarray implementation in bioimage-mcp exposes only 9 statically-defined functions (rename, squeeze, expand_dims, transpose, isel, pad, sum, max, mean). This proposal expands coverage to 135+ functions through dynamic discovery, enabling:

1. **Top-Level Functions** (`xr.concat`, `xr.merge`, `xr.where`, etc.) - Essential for tile stitching, channel merging
2. **Universal Functions** (ufuncs) - Element-wise math operations via numpy dispatch
3. **Comprehensive DataArray Methods** - All reduction, selection, interpolation, and transform operations

## Problem Statement

### Current Limitations

1. **Only 9 functions exposed** - Missing critical operations like `min`, `std`, `median`, `quantile`, `concat`, `clip`
2. **No concatenation/merging** - Cannot stitch tiles or merge channels without custom code
3. **No math operations** - No element-wise add, subtract, multiply, log, exp, etc.
4. **Static manifest definitions** - Every new function requires manual manifest entry
5. **No ufunc support** - Cannot apply numpy-style universal functions

### Impact on Bioimage Workflows

| Workflow | Missing Functions | Current Workaround |
|:---------|:------------------|:-------------------|
| Max Intensity Projection | ✓ `max` exists | - |
| Min Intensity Projection | ✗ `min` missing | Must use scipy |
| Tile stitching | ✗ `concat` missing | Cannot do |
| Channel merging | ✗ `merge` missing | Cannot do |
| Intensity normalization | ✗ `clip`, math ops missing | Cannot do |
| Background subtraction | ✗ `subtract` missing | Cannot do |
| Percentile thresholds | ✗ `quantile` missing | Cannot do |

## Proposed Solution

### Architecture Overview

Implement dynamic discovery for four xarray function groups:

```
xarray Functions (140+ total)
├── Top-Level Functions (base.xarray.*)              [~15 functions]
│   ├── Combining: concat, merge, combine_by_coords, combine_nested
│   ├── Alignment: align, broadcast
│   ├── Creation: zeros_like, ones_like, full_like
│   └── Computation: where, dot, cov, corr, apply_ufunc
├── Universal Functions (base.xarray.ufuncs.*)       [~50 functions]
│   ├── Arithmetic: add, subtract, multiply, divide, power
│   ├── Math: sqrt, square, abs, log, exp, sin, cos
│   ├── Comparison: maximum, minimum, greater, less, equal
│   └── Logical: logical_and, logical_or, logical_not
├── DataArray Class (base.xarray.DataArray)          [1 constructor]
│   └── Constructor returns ObjectRef for stateful operations
└── DataArray Methods (base.xarray.DataArray.*)      [~70 functions]
    ├── Dimension: rename, squeeze, expand_dims, transpose, stack, unstack
    ├── Selection: isel, sel, head, tail, thin, where
    ├── Reduction: max, min, mean, sum, std, var, median, quantile, argmax, argmin
    ├── Transform: pad, shift, roll, diff, clip, astype, fillna
    ├── Interpolation: interp, interp_like, reindex, ffill, bfill
    └── Window: rolling, coarsen (accessor patterns)
```

### Key Design Decision: Dual-Input Pattern for DataArray Methods

All xarray functions that operate on DataArray data accept **both** input types:

1. **`ObjectRef`** - DataArray object already in memory (from prior `base.xarray.DataArray` call)
2. **`BioImageRef`** - Image artifact loaded via `bioio.BioImage.reader.xarray_data`

This provides maximum flexibility:
- **Direct usage**: Pass BioImageRef directly to any method (no explicit DataArray construction needed)
- **Stateful chaining**: Use ObjectRef for efficient multi-step pipelines without disk I/O
- **Backward compatibility**: Existing workflows using BioImageRef continue to work

#### Input Resolution Logic

```python
def _resolve_dataarray_input(self, artifact: Artifact) -> xr.DataArray:
    """Resolve input artifact to xarray.DataArray.
    
    Supports both ObjectRef (in-memory DataArray) and BioImageRef (load from file).
    """
    if isinstance(artifact, dict):
        artifact_type = artifact.get("type")
        uri = artifact.get("uri", "")
    else:
        artifact_type = getattr(artifact, "type", None)
        uri = getattr(artifact, "uri", "")
    
    # Case 1: ObjectRef with obj:// URI - load from memory cache
    if artifact_type == "ObjectRef" and uri.startswith("obj://"):
        da = self._load_object_from_cache(uri)
        if not isinstance(da, xr.DataArray):
            raise TypeError(f"ObjectRef does not contain DataArray: {type(da)}")
        return da
    
    # Case 2: BioImageRef - load via bioio.BioImage.reader.xarray_data
    if artifact_type == "BioImageRef":
        img = self._load_bioimage(artifact)
        return img.reader.xarray_data
    
    raise ValueError(f"Unsupported input type: {artifact_type}. Expected ObjectRef or BioImageRef.")
```

#### Example Workflows

**Workflow A: Direct BioImageRef (simple, one-off operations)**
```python
# No explicit DataArray construction - BioImageRef loaded automatically
result = run("base.xarray.DataArray.mean", 
    inputs={"da": image_ref},  # BioImageRef
    params={"dim": "Z"}
)
# Returns ObjectRef (can be passed to next operation or serialized)
```

**Workflow B: ObjectRef Chaining (efficient multi-step pipelines)**
```python
# 1. Explicit DataArray construction for stateful operations
da_ref = run("base.xarray.DataArray", inputs={"image": image_ref})["outputs"]["da"]

# 2. Chain multiple operations - no disk I/O between steps
da_ref = run("base.xarray.DataArray.squeeze", inputs={"da": da_ref})["outputs"]["da"]
da_ref = run("base.xarray.DataArray.mean", inputs={"da": da_ref}, params={"dim": "Z"})["outputs"]["da"]
da_ref = run("base.xarray.DataArray.clip", inputs={"da": da_ref}, params={"min": 0, "max": 255})["outputs"]["da"]

# 3. Finalize to BioImageRef when done
final = run("base.xarray.DataArray.to_bioimage", inputs={"da": da_ref})["outputs"]["image"]
```

**Workflow C: Mixed (common pattern)**
```python
# Start with BioImageRef, continue with ObjectRef
result1 = run("base.xarray.DataArray.max", inputs={"da": image_ref}, params={"dim": "Z"})
mip_ref = result1["outputs"]["da"]  # ObjectRef

result2 = run("base.xarray.DataArray.clip", inputs={"da": mip_ref}, params={"min": 10, "max": 255})
clipped_ref = result2["outputs"]["da"]  # ObjectRef
```

### Implementation Strategy

#### Phase 1: Expand Allowlist (P0)

Create `src/bioimage_mcp/registry/dynamic/xarray_allowlists.py`:

```python
from enum import Enum
from typing import Any

class XarrayFunctionType(Enum):
    TOPLEVEL = "toplevel"       # xr.concat, xr.where
    UFUNC = "ufunc"             # Element-wise operations
    DATAARRAY_CLASS = "class"   # DataArray constructor → ObjectRef
    DATAARRAY_METHOD = "method" # da.mean(), da.transpose()
    ACCESSOR = "accessor"       # da.rolling().mean()

class SignatureType(Enum):
    SINGLE_INPUT = "single"     # One DataArray in, one out
    MULTI_INPUT = "multi"       # Multiple DataArrays (concat, merge)
    BINARY = "binary"           # Two DataArrays (add, subtract)
    CONSTRUCTOR = "constructor" # Returns ObjectRef
    INSTANCE_METHOD = "instance"# Takes ObjectRef, returns artifact
    SPECIAL = "special"         # Complex signatures (apply_ufunc)

# === DATAARRAY CLASS (Constructor) ===
XARRAY_DATAARRAY_CLASS: dict[str, dict[str, Any]] = {
    "DataArray": {
        "category": "constructor",
        "signature_type": SignatureType.CONSTRUCTOR,
        "summary": "Instantiate a DataArray from BioImageRef and return ObjectRef for method chaining",
        "tags": ["initialization", "xarray"],
        "inputs": [
            {"name": "image", "type": "BioImageRef", "required": True}
        ],
        "outputs": [
            {"name": "da", "type": "ObjectRef"}
        ],
        "params": {},
        "bioimage_use": "Load image once for multiple sequential operations without re-serialization",
    },
}

# === TOP-LEVEL FUNCTIONS ===
XARRAY_TOPLEVEL_ALLOWLIST: dict[str, dict[str, Any]] = {
    # Combining Data
    "concat": {
        "category": "combine",
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Concatenate arrays along a new or existing dimension",
        "tags": ["combine", "stitch", "xarray"],
        "params": {"dim": "str", "join": "str?", "fill_value": "Any?"},
        "bioimage_use": "Tile stitching, time-series assembly, Z-stack building",
    },
    "merge": {
        "category": "combine", 
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Merge multiple arrays/datasets into one",
        "tags": ["combine", "merge", "xarray"],
        "bioimage_use": "Combine separate channels into multi-channel image",
    },
    "combine_by_coords": {
        "category": "combine",
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Combine arrays by aligning coordinates automatically",
        "tags": ["combine", "align", "xarray"],
        "bioimage_use": "Automatic tile alignment based on coordinates",
    },
    "combine_nested": {
        "category": "combine",
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Combine arrays arranged in nested list structure",
        "tags": ["combine", "grid", "xarray"],
        "bioimage_use": "Grid-based tile assembly (e.g., 3x3 mosaic)",
    },
    
    # Alignment
    "align": {
        "category": "align",
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Align arrays to common coordinates",
        "tags": ["align", "coordinates", "xarray"],
        "bioimage_use": "Multi-modal registration, co-registration",
    },
    "broadcast": {
        "category": "align",
        "signature_type": SignatureType.MULTI_INPUT,
        "summary": "Broadcast arrays against each other",
        "tags": ["broadcast", "shape", "xarray"],
        "bioimage_use": "Shape matching for arithmetic operations",
    },
    
    # Creation
    "zeros_like": {
        "category": "create",
        "signature_type": SignatureType.SINGLE_INPUT,
        "summary": "Create zero-filled array matching input shape/coords",
        "tags": ["create", "zeros", "xarray"],
        "bioimage_use": "Initialize empty mask or accumulator",
    },
    "ones_like": {
        "category": "create",
        "signature_type": SignatureType.SINGLE_INPUT,
        "summary": "Create ones-filled array matching input shape/coords",
        "tags": ["create", "ones", "xarray"],
        "bioimage_use": "Initialize uniform mask",
    },
    "full_like": {
        "category": "create",
        "signature_type": SignatureType.SINGLE_INPUT,
        "summary": "Create array filled with specified value",
        "tags": ["create", "fill", "xarray"],
        "params": {"fill_value": "scalar"},
        "bioimage_use": "Initialize with background value",
    },
    
    # Computation
    "where": {
        "category": "compute",
        "signature_type": SignatureType.SPECIAL,
        "summary": "Conditional element selection (like np.where)",
        "tags": ["mask", "threshold", "conditional", "xarray"],
        "bioimage_use": "Masking, thresholding, conditional replacement",
    },
    "dot": {
        "category": "compute",
        "signature_type": SignatureType.BINARY,
        "summary": "Generalized dot product",
        "tags": ["linear_algebra", "matrix", "xarray"],
        "bioimage_use": "Spectral unmixing, linear combinations",
    },
    "cov": {
        "category": "compute",
        "signature_type": SignatureType.BINARY,
        "summary": "Compute covariance between arrays",
        "tags": ["statistics", "correlation", "xarray"],
        "bioimage_use": "Channel correlation analysis",
    },
    "corr": {
        "category": "compute",
        "signature_type": SignatureType.BINARY,
        "summary": "Compute Pearson correlation coefficient",
        "tags": ["statistics", "correlation", "xarray"],
        "bioimage_use": "Co-localization analysis between channels",
    },
    "apply_ufunc": {
        "category": "advanced",
        "signature_type": SignatureType.SPECIAL,
        "summary": "Apply NumPy/custom function with dimension handling",
        "tags": ["advanced", "custom", "dask", "xarray"],
        "bioimage_use": "Custom per-pixel operations, Dask-compatible processing",
    },
    "polyval": {
        "category": "compute",
        "signature_type": SignatureType.BINARY,
        "summary": "Evaluate polynomial at points",
        "tags": ["polynomial", "math", "xarray"],
        "bioimage_use": "Intensity calibration curves",
    },
}

# === UNIVERSAL FUNCTIONS (UFUNCS) ===
XARRAY_UFUNC_ALLOWLIST: dict[str, dict[str, Any]] = {
    # Arithmetic (binary)
    "add": {"category": "arithmetic", "arity": 2, "summary": "Element-wise addition"},
    "subtract": {"category": "arithmetic", "arity": 2, "summary": "Element-wise subtraction"},
    "multiply": {"category": "arithmetic", "arity": 2, "summary": "Element-wise multiplication"},
    "divide": {"category": "arithmetic", "arity": 2, "summary": "Element-wise division"},
    "true_divide": {"category": "arithmetic", "arity": 2, "summary": "Element-wise true division"},
    "floor_divide": {"category": "arithmetic", "arity": 2, "summary": "Element-wise floor division"},
    "power": {"category": "arithmetic", "arity": 2, "summary": "Element-wise power"},
    "remainder": {"category": "arithmetic", "arity": 2, "summary": "Element-wise remainder"},
    "mod": {"category": "arithmetic", "arity": 2, "summary": "Element-wise modulo"},
    
    # Unary Math
    "negative": {"category": "unary", "arity": 1, "summary": "Numerical negative"},
    "positive": {"category": "unary", "arity": 1, "summary": "Numerical positive"},
    "absolute": {"category": "unary", "arity": 1, "summary": "Absolute value"},
    "abs": {"category": "unary", "arity": 1, "summary": "Absolute value (alias)"},
    "sqrt": {"category": "unary", "arity": 1, "summary": "Square root"},
    "square": {"category": "unary", "arity": 1, "summary": "Square"},
    "reciprocal": {"category": "unary", "arity": 1, "summary": "Reciprocal (1/x)"},
    "sign": {"category": "unary", "arity": 1, "summary": "Sign of elements"},
    
    # Exponential / Logarithmic
    "exp": {"category": "exp_log", "arity": 1, "summary": "Exponential (e^x)"},
    "exp2": {"category": "exp_log", "arity": 1, "summary": "2^x"},
    "expm1": {"category": "exp_log", "arity": 1, "summary": "exp(x) - 1"},
    "log": {"category": "exp_log", "arity": 1, "summary": "Natural logarithm"},
    "log2": {"category": "exp_log", "arity": 1, "summary": "Base-2 logarithm"},
    "log10": {"category": "exp_log", "arity": 1, "summary": "Base-10 logarithm"},
    "log1p": {"category": "exp_log", "arity": 1, "summary": "log(1 + x)"},
    
    # Trigonometric
    "sin": {"category": "trig", "arity": 1, "summary": "Sine"},
    "cos": {"category": "trig", "arity": 1, "summary": "Cosine"},
    "tan": {"category": "trig", "arity": 1, "summary": "Tangent"},
    "arcsin": {"category": "trig", "arity": 1, "summary": "Inverse sine"},
    "arccos": {"category": "trig", "arity": 1, "summary": "Inverse cosine"},
    "arctan": {"category": "trig", "arity": 1, "summary": "Inverse tangent"},
    "arctan2": {"category": "trig", "arity": 2, "summary": "Two-argument arctangent"},
    "hypot": {"category": "trig", "arity": 2, "summary": "Hypotenuse"},
    "sinh": {"category": "trig", "arity": 1, "summary": "Hyperbolic sine"},
    "cosh": {"category": "trig", "arity": 1, "summary": "Hyperbolic cosine"},
    "tanh": {"category": "trig", "arity": 1, "summary": "Hyperbolic tangent"},
    "deg2rad": {"category": "trig", "arity": 1, "summary": "Degrees to radians"},
    "rad2deg": {"category": "trig", "arity": 1, "summary": "Radians to degrees"},
    
    # Rounding
    "floor": {"category": "rounding", "arity": 1, "summary": "Floor"},
    "ceil": {"category": "rounding", "arity": 1, "summary": "Ceiling"},
    "trunc": {"category": "rounding", "arity": 1, "summary": "Truncate"},
    "rint": {"category": "rounding", "arity": 1, "summary": "Round to nearest int"},
    "round": {"category": "rounding", "arity": 1, "summary": "Round"},
    
    # Comparison (binary, return bool array)
    "maximum": {"category": "comparison", "arity": 2, "summary": "Element-wise maximum"},
    "minimum": {"category": "comparison", "arity": 2, "summary": "Element-wise minimum"},
    "fmax": {"category": "comparison", "arity": 2, "summary": "Element-wise maximum (ignore NaN)"},
    "fmin": {"category": "comparison", "arity": 2, "summary": "Element-wise minimum (ignore NaN)"},
    "greater": {"category": "comparison", "arity": 2, "summary": "Element-wise greater than"},
    "greater_equal": {"category": "comparison", "arity": 2, "summary": "Element-wise greater or equal"},
    "less": {"category": "comparison", "arity": 2, "summary": "Element-wise less than"},
    "less_equal": {"category": "comparison", "arity": 2, "summary": "Element-wise less or equal"},
    "equal": {"category": "comparison", "arity": 2, "summary": "Element-wise equality"},
    "not_equal": {"category": "comparison", "arity": 2, "summary": "Element-wise inequality"},
    
    # Logical
    "logical_and": {"category": "logical", "arity": 2, "summary": "Element-wise logical AND"},
    "logical_or": {"category": "logical", "arity": 2, "summary": "Element-wise logical OR"},
    "logical_xor": {"category": "logical", "arity": 2, "summary": "Element-wise logical XOR"},
    "logical_not": {"category": "logical", "arity": 1, "summary": "Element-wise logical NOT"},
    
    # Special
    "isnan": {"category": "special", "arity": 1, "summary": "Test for NaN"},
    "isinf": {"category": "special", "arity": 1, "summary": "Test for infinity"},
    "isfinite": {"category": "special", "arity": 1, "summary": "Test for finite"},
    "clip": {"category": "special", "arity": 3, "summary": "Clip values to range"},
}

# === DATAARRAY METHODS (take ObjectRef OR BioImageRef, return ObjectRef) ===
# Input "da" accepts both types - resolved at runtime via _resolve_dataarray_input()
# This follows the pattern: methods work on DataArray regardless of how it was obtained
XARRAY_DATAARRAY_ALLOWLIST: dict[str, dict[str, Any]] = {
    # Dimension Manipulation
    "rename": {"category": "axis", "summary": "Rename dimensions", "returns": "ObjectRef", 
               "input_types": ["ObjectRef", "BioImageRef"]},
    "squeeze": {"category": "axis", "summary": "Remove singleton dimensions", "returns": "ObjectRef",
                "input_types": ["ObjectRef", "BioImageRef"]},
    "expand_dims": {"category": "axis", "summary": "Add new dimension", "returns": "ObjectRef",
                    "input_types": ["ObjectRef", "BioImageRef"]},
    "transpose": {"category": "axis", "summary": "Reorder dimensions", "returns": "ObjectRef",
                  "input_types": ["ObjectRef", "BioImageRef"]},
    "stack": {"category": "axis", "summary": "Combine dimensions into MultiIndex", "returns": "ObjectRef",
              "input_types": ["ObjectRef", "BioImageRef"]},
    "unstack": {"category": "axis", "summary": "Decompose MultiIndex dimension", "returns": "ObjectRef",
                "input_types": ["ObjectRef", "BioImageRef"]},
    "swap_dims": {"category": "axis", "summary": "Swap dimension for coordinate", "returns": "ObjectRef",
                  "input_types": ["ObjectRef", "BioImageRef"]},
    "set_index": {"category": "axis", "summary": "Set dimension as index", "returns": "ObjectRef",
                  "input_types": ["ObjectRef", "BioImageRef"]},
    "reset_index": {"category": "axis", "summary": "Reset index to dimension", "returns": "ObjectRef",
                    "input_types": ["ObjectRef", "BioImageRef"]},
    
    # Indexing / Selection
    "isel": {"category": "selection", "summary": "Select by integer index", "returns": "ObjectRef"},
    "sel": {"category": "selection", "summary": "Select by coordinate label", "returns": "ObjectRef"},
    "head": {"category": "selection", "summary": "Select first n elements", "returns": "ObjectRef"},
    "tail": {"category": "selection", "summary": "Select last n elements", "returns": "ObjectRef"},
    "thin": {"category": "selection", "summary": "Subsample every n-th element", "returns": "ObjectRef"},
    "drop_sel": {"category": "selection", "summary": "Drop by coordinate label", "returns": "ObjectRef"},
    "drop_isel": {"category": "selection", "summary": "Drop by integer index", "returns": "ObjectRef"},
    "where": {"category": "selection", "summary": "Filter by condition (method form)", "returns": "ObjectRef"},
    "isin": {"category": "selection", "summary": "Check membership", "returns": "ObjectRef"},
    
    # Reductions (these reduce dimensionality, return ObjectRef or BioImageRef)
    "max": {"category": "reduction", "summary": "Maximum (e.g., MIP)", "returns": "ObjectRef"},
    "min": {"category": "reduction", "summary": "Minimum", "returns": "ObjectRef"},
    "mean": {"category": "reduction", "summary": "Mean", "returns": "ObjectRef"},
    "sum": {"category": "reduction", "summary": "Sum", "returns": "ObjectRef"},
    "prod": {"category": "reduction", "summary": "Product", "returns": "ObjectRef"},
    "std": {"category": "reduction", "summary": "Standard deviation", "returns": "ObjectRef"},
    "var": {"category": "reduction", "summary": "Variance", "returns": "ObjectRef"},
    "median": {"category": "reduction", "summary": "Median", "returns": "ObjectRef"},
    "count": {"category": "reduction", "summary": "Count non-NaN", "returns": "ObjectRef"},
    "all": {"category": "reduction", "summary": "All True", "returns": "ObjectRef"},
    "any": {"category": "reduction", "summary": "Any True", "returns": "ObjectRef"},
    "quantile": {"category": "reduction", "summary": "Quantile (percentile)", "returns": "ObjectRef"},
    "argmax": {"category": "reduction", "summary": "Index of maximum", "returns": "ObjectRef"},
    "argmin": {"category": "reduction", "summary": "Index of minimum", "returns": "ObjectRef"},
    "idxmax": {"category": "reduction", "summary": "Coordinate of maximum", "returns": "ObjectRef"},
    "idxmin": {"category": "reduction", "summary": "Coordinate of minimum", "returns": "ObjectRef"},
    
    # Cumulative
    "cumsum": {"category": "cumulative", "summary": "Cumulative sum", "returns": "ObjectRef"},
    "cumprod": {"category": "cumulative", "summary": "Cumulative product", "returns": "ObjectRef"},
    
    # Transforms
    "pad": {"category": "transform", "summary": "Pad along dimensions", "returns": "ObjectRef"},
    "shift": {"category": "transform", "summary": "Shift data (NaN at edges)", "returns": "ObjectRef"},
    "roll": {"category": "transform", "summary": "Roll data circularly", "returns": "ObjectRef"},
    "diff": {"category": "transform", "summary": "N-th order difference", "returns": "ObjectRef"},
    "clip": {"category": "transform", "summary": "Clip to range", "returns": "ObjectRef"},
    "astype": {"category": "transform", "summary": "Cast to dtype", "returns": "ObjectRef"},
    "fillna": {"category": "transform", "summary": "Fill NaN values", "returns": "ObjectRef"},
    "ffill": {"category": "transform", "summary": "Forward fill NaN", "returns": "ObjectRef"},
    "bfill": {"category": "transform", "summary": "Backward fill NaN", "returns": "ObjectRef"},
    "dropna": {"category": "transform", "summary": "Drop NaN values", "returns": "ObjectRef"},
    "sortby": {"category": "transform", "summary": "Sort by coordinate", "returns": "ObjectRef"},
    "rank": {"category": "transform", "summary": "Rank values", "returns": "ObjectRef"},
    
    # Interpolation
    "interp": {"category": "interpolation", "summary": "Interpolate to new coordinates", "returns": "ObjectRef"},
    "interp_like": {"category": "interpolation", "summary": "Interpolate to match another array", "returns": "ObjectRef"},
    "reindex": {"category": "interpolation", "summary": "Reindex to new coordinates", "returns": "ObjectRef"},
    "reindex_like": {"category": "interpolation", "summary": "Reindex to match another array", "returns": "ObjectRef"},
    "interpolate_na": {"category": "interpolation", "summary": "Interpolate over NaN values", "returns": "ObjectRef"},
    
    # Calculus
    "differentiate": {"category": "calculus", "summary": "Differentiate along coordinate", "returns": "ObjectRef"},
    "integrate": {"category": "calculus", "summary": "Integrate along coordinate", "returns": "ObjectRef"},
    
    # Broadcasting
    "broadcast_like": {"category": "broadcast", "summary": "Broadcast to match another array", "returns": "ObjectRef"},
    
    # Window operations (return accessor objects - special handling)
    "coarsen": {"category": "window", "returns_accessor": True, "summary": "Block coarsening (downsampling)"},
    "rolling": {"category": "window", "returns_accessor": True, "summary": "Rolling window operations"},
    "rolling_exp": {"category": "window", "returns_accessor": True, "summary": "Exponentially weighted rolling"},
    "weighted": {"category": "window", "returns_accessor": True, "summary": "Weighted reductions"},
    
    # GroupBy / Resample (return accessor objects - special handling)
    "groupby": {"category": "group", "returns_accessor": True, "summary": "Group by coordinate values"},
    "groupby_bins": {"category": "group", "returns_accessor": True, "summary": "Group by coordinate bins"},
    "resample": {"category": "group", "returns_accessor": True, "summary": "Resample time dimension"},
    
    # Serialization (finalize ObjectRef back to artifact)
    "to_bioimage": {"category": "serialize", "summary": "Convert ObjectRef to BioImageRef artifact", "returns": "BioImageRef"},
}

# === DENYLIST ===
XARRAY_DENYLIST: frozenset[str] = frozenset({
    # Memory unsafe - loads entire array into RAM
    "values", "to_numpy", "load", "compute", "data", "item",
    "as_numpy", "__array__",
    
    # Conversion to non-artifact formats
    "to_series", "to_dataframe", "to_dict", "to_pandas",
    "to_netcdf", "to_zarr",  # I/O handled separately
    
    # Interactive / Plotting
    "plot", "show", "info", "_repr_html_",
    
    # Deprecated
    "drop",  # Use drop_sel/drop_isel
})
```

#### Phase 2: Implement Dynamic Discovery

Enhance `XarrayAdapterForRegistry.discover()` to introspect:

```python
def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
    """Dynamically discover xarray functions from allowlists."""
    from bioimage_mcp.registry.dynamic.xarray_allowlists import (
        XARRAY_DATAARRAY_CLASS,
        XARRAY_TOPLEVEL_ALLOWLIST,
        XARRAY_UFUNC_ALLOWLIST,
        XARRAY_DATAARRAY_ALLOWLIST,
    )
    
    results = []
    
    # 0. DataArray class constructor (returns ObjectRef)
    for name, info in XARRAY_DATAARRAY_CLASS.items():
        meta = self._create_constructor_metadata(name, info)
        meta.fn_id = f"base.xarray.{name}"  # base.xarray.DataArray
        meta.returns = "ObjectRef"
        results.append(meta)
    
    # 1. Top-level functions (xr.concat, xr.where, etc.)
    for name, info in XARRAY_TOPLEVEL_ALLOWLIST.items():
        func = getattr(xr, name, None)
        if func:
            meta = self._introspect_function(func, f"xr.{name}", info)
            meta.fn_id = f"base.xarray.{name}"
            results.append(meta)
    
    # 2. Universal functions (ufuncs)
    for name, info in XARRAY_UFUNC_ALLOWLIST.items():
        # ufuncs are dispatched via numpy or xr.ufuncs
        meta = self._create_ufunc_metadata(name, info)
        meta.fn_id = f"base.xarray.ufuncs.{name}"
        results.append(meta)
    
    # 3. DataArray methods (take ObjectRef OR BioImageRef, return ObjectRef)
    for name, info in XARRAY_DATAARRAY_ALLOWLIST.items():
        method = getattr(xr.DataArray, name, None)
        if method:
            meta = self._introspect_instance_method(method, name, info)
            meta.fn_id = f"base.xarray.DataArray.{name}"
            # Input "da" accepts BOTH ObjectRef and BioImageRef
            # The adapter resolves at runtime via _resolve_dataarray_input()
            meta.inputs = {
                "da": {
                    "type": ["ObjectRef", "BioImageRef"],  # Union type
                    "required": True,
                    "description": "DataArray (ObjectRef) or image to convert (BioImageRef)"
                },
                **meta.inputs  # Additional inputs if any
            }
            results.append(meta)
    
    return results
```

#### Phase 3: Handle Multi-Input Functions

For functions like `concat`, `merge`, `add`, `subtract`:

```python
def execute_multi_input(
    self,
    fn_id: str,
    inputs: list[Artifact],
    params: dict[str, Any],
    work_dir: Path,
) -> list[dict]:
    """Handle functions that take multiple DataArrays."""
    
    # Load all input artifacts as DataArrays
    arrays = [self._load_as_dataarray(art) for art in inputs]
    
    if fn_id == "base.xarray.concat":
        dim = params.get("dim", "concat_dim")
        result = xr.concat(arrays, dim=dim)
    elif fn_id == "base.xarray.merge":
        result = xr.merge([arr.to_dataset(name=f"var_{i}") for i, arr in enumerate(arrays)])
        result = result.to_array()  # Convert back to DataArray
    elif fn_id.startswith("base.xarray.ufuncs."):
        ufunc_name = fn_id.split(".")[-1]
        if len(arrays) == 2:
            result = getattr(np, ufunc_name)(arrays[0], arrays[1])
        else:
            result = getattr(np, ufunc_name)(arrays[0])
    else:
        raise ValueError(f"Unknown multi-input function: {fn_id}")
    
    return self._save_output(result, fn_id.split(".")[-1], work_dir)
```

#### Phase 4: Update Manifest

Add dynamic source entry:

```yaml
dynamic_sources:
  # ... existing sources ...
  
  - adapter: xarray
    prefix: xarray
    include_patterns:
      - "*"
    exclude_patterns:
      - "_*"
```

## User Scenarios & Testing

### User Story 1 - DataArray ObjectRef Creation (Priority: P0)

A user wants to load an image as a DataArray ObjectRef for efficient method chaining.

**Acceptance Scenarios**:

1. **Given** a BioImageRef, **When** `base.xarray.DataArray` is called, **Then** an ObjectRef is returned with `python_class: "xarray.DataArray"`.

2. **Given** an ObjectRef from step 1, **When** `base.xarray.DataArray.mean` is called with `dim: "Z"`, **Then** a new ObjectRef is returned (reduced dimensionality).

3. **Given** an ObjectRef, **When** `base.xarray.DataArray.to_bioimage` is called, **Then** the DataArray is serialized to a BioImageRef artifact.

### User Story 2 - Tile Stitching with concat (Priority: P0)

A user has multiple image tiles and needs to stitch them into a single volume.

**Acceptance Scenarios**:

1. **Given** 4 BioImageRef artifacts representing tiles, **When** `base.xarray.concat` is called with `dim: "X"`, **Then** output is a single BioImageRef with combined X dimension.

2. **Given** tiles with mismatched coordinates, **When** concat is called with `join: "outer"`, **Then** missing regions are filled with NaN.

### User Story 3 - Background Subtraction (Priority: P0)

A user needs to subtract a background image from a signal image.

**Acceptance Scenarios**:

1. **Given** a signal image and background image, **When** `base.xarray.ufuncs.subtract` is called, **Then** output is signal - background as a BioImageRef.

2. **Given** images with different shapes, **When** subtract is called, **Then** xarray broadcasts correctly and output matches larger shape.

### User Story 4 - Intensity Normalization with ObjectRef (Priority: P0)

A user needs to normalize image intensities to [0, 1] range using method chaining.

**Acceptance Scenarios**:

1. **Given** a BioImageRef, **When** `base.xarray.DataArray` is called, **Then** ObjectRef is returned.

2. **Given** the ObjectRef, **When** `base.xarray.DataArray.min` and `base.xarray.DataArray.max` are called (without dim), **Then** scalar values are computed.

3. **Given** ObjectRef and min/max, **When** subtract and divide operations are chained, **Then** normalized ObjectRef is returned.

4. **Given** normalized ObjectRef, **When** `base.xarray.DataArray.to_bioimage` is called, **Then** BioImageRef with values in [0,1] is returned.

### User Story 5 - Percentile-based Thresholding (Priority: P1)

A user needs to compute 99th percentile for contrast adjustment.

**Acceptance Scenarios**:

1. **Given** an ObjectRef, **When** `base.xarray.DataArray.quantile` is called with `q: 0.99`, **Then** the 99th percentile value is returned as ObjectRef.

2. **Given** quantile ObjectRef, **When** `base.xarray.DataArray.clip` is called, **Then** clipped ObjectRef is returned.

### User Story 6 - Multi-Scale Pyramid (Priority: P1)

A user needs to create a downsampled pyramid level using block averaging.

**Acceptance Scenarios**:

1. **Given** an ObjectRef, **When** `base.xarray.DataArray.coarsen` is called with `{"Y": 2, "X": 2}` and `.mean()`, **Then** a 2x downsampled ObjectRef is returned.

## Technical Design

### BioImageRef to DataArray Loading (Existing Pattern)

The current codebase loads BioImageRef artifacts as xarray DataArrays using `bioio.BioImage.reader.xarray_data`. This pattern is already implemented in `adapters/xarray.py:155`:

```python
from bioio import BioImage

def _load_bioimage(self, artifact: Artifact) -> BioImage:
    """Load BioImage from artifact reference."""
    # ... extract path from artifact URI ...
    
    # Select appropriate reader based on format
    reader = None
    if fmt == "OME-TIFF":
        from bioio_ome_tiff import Reader as OmeTiffReader
        reader = OmeTiffReader
    elif fmt == "OME-Zarr":
        from bioio_ome_zarr import Reader as OmeZarrReader
        reader = OmeZarrReader
    # ... etc ...
    
    return BioImage(str(path), reader=reader)

def _resolve_dataarray_input(self, artifact: Artifact) -> xr.DataArray:
    """Resolve input to DataArray from either ObjectRef or BioImageRef."""
    artifact_type = artifact.get("type") if isinstance(artifact, dict) else getattr(artifact, "type", None)
    uri = artifact.get("uri", "") if isinstance(artifact, dict) else getattr(artifact, "uri", "")
    
    # ObjectRef: Load from in-memory cache
    if artifact_type == "ObjectRef" and uri.startswith("obj://"):
        return self._load_object_from_cache(uri)
    
    # BioImageRef: Load via bioio.BioImage.reader.xarray_data
    if artifact_type == "BioImageRef":
        img = self._load_bioimage(artifact)
        return img.reader.xarray_data  # Native dimensions preserved
    
    raise ValueError(f"Unsupported input type: {artifact_type}")
```

### File Changes

| File | Change Type | Description |
|:-----|:------------|:------------|
| `src/bioimage_mcp/registry/dynamic/xarray_allowlists.py` | NEW | Comprehensive allowlists for all function groups |
| `src/bioimage_mcp/registry/dynamic/adapters/xarray.py` | MODIFY | Implement `discover()`, handle multi-input |
| `src/bioimage_mcp/registry/dynamic/xarray_adapter.py` | MODIFY | Add execution handlers for new function types |
| `tools/base/manifest.yaml` | MODIFY | Add xarray to dynamic_sources |
| `tests/unit/registry/test_xarray_discovery.py` | NEW | Unit tests for discovery |
| `tests/contract/test_xarray_functions.py` | NEW | Contract tests for schemas |
| `tests/integration/test_xarray_workflows.py` | NEW | Integration tests for workflows |

### API Surface

New function IDs exposed:

```
# DataArray Class Constructor (1)
base.xarray.DataArray                    # (image: BioImageRef) → ObjectRef

# Top-level (15)
base.xarray.concat
base.xarray.merge
base.xarray.combine_by_coords
base.xarray.combine_nested
base.xarray.align
base.xarray.broadcast
base.xarray.zeros_like
base.xarray.ones_like
base.xarray.full_like
base.xarray.where
base.xarray.dot
base.xarray.cov
base.xarray.corr
base.xarray.apply_ufunc
base.xarray.polyval

# Ufuncs (50)
base.xarray.ufuncs.add
base.xarray.ufuncs.subtract
base.xarray.ufuncs.multiply
base.xarray.ufuncs.divide
base.xarray.ufuncs.sqrt
base.xarray.ufuncs.log
base.xarray.ufuncs.exp
... (all 50)

# DataArray Methods (71) - accept BOTH ObjectRef and BioImageRef as "da" input
base.xarray.DataArray.mean               # (da: ObjectRef|BioImageRef, dim: str) → ObjectRef
base.xarray.DataArray.max                # (da: ObjectRef|BioImageRef, dim: str) → ObjectRef  
base.xarray.DataArray.min                # (da: ObjectRef|BioImageRef, dim: str) → ObjectRef
base.xarray.DataArray.std                # (da: ObjectRef|BioImageRef, dim: str) → ObjectRef
base.xarray.DataArray.var                # (da: ObjectRef|BioImageRef, dim: str) → ObjectRef
base.xarray.DataArray.median             # (da: ObjectRef|BioImageRef, dim: str) → ObjectRef
base.xarray.DataArray.quantile           # (da: ObjectRef|BioImageRef, q: float) → ObjectRef
base.xarray.DataArray.clip               # (da: ObjectRef|BioImageRef, min, max) → ObjectRef
base.xarray.DataArray.squeeze            # (da: ObjectRef|BioImageRef) → ObjectRef
base.xarray.DataArray.transpose          # (da: ObjectRef|BioImageRef, dims: list) → ObjectRef
base.xarray.DataArray.isel               # (da: ObjectRef|BioImageRef, **indexers) → ObjectRef
base.xarray.DataArray.sel                # (da: ObjectRef|BioImageRef, **indexers) → ObjectRef
base.xarray.DataArray.to_bioimage        # (da: ObjectRef) → BioImageRef
... (all 71)

# Migration: Existing functions move to new namespace
# OLD: base.xarray.mean       → NEW: base.xarray.DataArray.mean
# OLD: base.xarray.max        → NEW: base.xarray.DataArray.max
# OLD: base.xarray.squeeze    → NEW: base.xarray.DataArray.squeeze
# OLD: base.xarray.transpose  → NEW: base.xarray.DataArray.transpose
# OLD: base.xarray.isel       → NEW: base.xarray.DataArray.isel
# OLD: base.xarray.pad        → NEW: base.xarray.DataArray.pad
# OLD: base.xarray.sum        → NEW: base.xarray.DataArray.sum
# OLD: base.xarray.rename     → NEW: base.xarray.DataArray.rename
# OLD: base.xarray.expand_dims→ NEW: base.xarray.DataArray.expand_dims
```

### Example Workflows

#### Direct BioImageRef Usage (Simple, Backward Compatible)
```python
# Pass BioImageRef directly - automatically loaded via bioio.BioImage.reader.xarray_data
result = run("base.xarray.DataArray.mean", 
    inputs={"da": {"ref_id": "img-123", "type": "BioImageRef"}},
    params={"dim": "Z"}
)
mip = result["outputs"]["da"]  # ObjectRef containing reduced DataArray
```

#### ObjectRef Chaining (Efficient Multi-Step Pipelines)
```python
# 1. Explicit construction (optional - enables stateful operations)
result1 = run("base.xarray.DataArray", inputs={"image": img_ref})
da_ref = result1["outputs"]["da"]  # ObjectRef

# 2. Chain operations - no disk I/O between steps
result2 = run("base.xarray.DataArray.squeeze", inputs={"da": da_ref})
da_ref = result2["outputs"]["da"]

result3 = run("base.xarray.DataArray.mean", inputs={"da": da_ref}, params={"dim": "Z"})
da_ref = result3["outputs"]["da"]

result4 = run("base.xarray.DataArray.clip", inputs={"da": da_ref}, params={"min": 0, "max": 255})
da_ref = result4["outputs"]["da"]

# 3. Serialize to BioImageRef when done
result5 = run("base.xarray.DataArray.to_bioimage", inputs={"da": da_ref})
final_image = result5["outputs"]["image"]  # BioImageRef
```

#### Mixed Pattern (Common Usage)
```python
# Start with BioImageRef (loaded once), continue with ObjectRef (no reload)
result1 = run("base.xarray.DataArray.max", 
    inputs={"da": {"ref_id": "img-123", "type": "BioImageRef"}},  # BioImageRef
    params={"dim": "Z"}
)
mip_ref = result1["outputs"]["da"]  # ObjectRef

result2 = run("base.xarray.DataArray.clip", 
    inputs={"da": mip_ref},  # ObjectRef - no disk I/O
    params={"min": 10, "max": 255}
)
clipped_ref = result2["outputs"]["da"]  # ObjectRef
```

## Constitution Compliance

| Principle | How Satisfied |
|:----------|:--------------|
| **1. Stable MCP Surface** | Discovery returns summaries; full schemas via `describe()` |
| **2. Isolated Execution** | All xarray ops run in base tool environment |
| **3. Artifact References Only** | All I/O via BioImageRef, no raw arrays in messages |
| **4. Reproducibility** | Functions introspected from pinned xarray version |
| **5. Safety** | Denylist prevents memory-unsafe operations |
| **6. TDD** | Tests written before implementation |

## Milestones

| Milestone | Deliverable | Estimate |
|:----------|:------------|:---------|
| M1 | Allowlist module with all 135 functions | 2 hours |
| M2 | Dynamic discovery implementation | 3 hours |
| M3 | Multi-input function handling | 2 hours |
| M4 | Ufunc execution via numpy dispatch | 2 hours |
| M5 | Unit + contract tests | 2 hours |
| M6 | Integration tests (concat, subtract, quantile) | 2 hours |
| **Total** | | **13 hours** |

## Open Questions

1. **Accessor patterns**: Should `rolling`, `coarsen`, `groupby` be exposed as single functions with aggregation parameter, or as two-step flows?

2. **Multi-input artifact protocol**: How should `concat` receive multiple images? As a list in `inputs`, or as named inputs `image_0`, `image_1`, etc.?

3. **Migration strategy**: Should old `base.xarray.*` function IDs be deprecated with aliases, or removed entirely? Recommend: Keep aliases for one release cycle.

4. **ObjectRef caching**: Should DataArray ObjectRefs support LRU eviction like Cellpose models? What's the memory limit policy?

## Appendix: Full Function Count

| Group | Namespace | Count | Examples |
|:------|:----------|:------|:---------|
| DataArray Constructor | `base.xarray.DataArray` | 1 | DataArray (→ ObjectRef) |
| Top-Level | `base.xarray.*` | 15 | concat, merge, where, broadcast |
| Ufuncs | `base.xarray.ufuncs.*` | 50 | add, subtract, sqrt, log, sin |
| DataArray Methods | `base.xarray.DataArray.*` | 71 | mean, max, clip, isel, to_bioimage |
| **Total** | | **137** | |

### Migration from Current Functions

| Current fn_id | New fn_id | Breaking Change |
|:--------------|:----------|:----------------|
| `base.xarray.rename` | `base.xarray.DataArray.rename` | Input changes: `image` → `da: ObjectRef` |
| `base.xarray.squeeze` | `base.xarray.DataArray.squeeze` | Input changes: `image` → `da: ObjectRef` |
| `base.xarray.expand_dims` | `base.xarray.DataArray.expand_dims` | Input changes: `image` → `da: ObjectRef` |
| `base.xarray.transpose` | `base.xarray.DataArray.transpose` | Input changes: `image` → `da: ObjectRef` |
| `base.xarray.isel` | `base.xarray.DataArray.isel` | Input changes: `image` → `da: ObjectRef` |
| `base.xarray.pad` | `base.xarray.DataArray.pad` | Input changes: `image` → `da: ObjectRef` |
| `base.xarray.sum` | `base.xarray.DataArray.sum` | Input changes: `image` → `da: ObjectRef` |
| `base.xarray.max` | `base.xarray.DataArray.max` | Input changes: `image` → `da: ObjectRef` |
| `base.xarray.mean` | `base.xarray.DataArray.mean` | Input changes: `image` → `da: ObjectRef` |

**Recommendation**: Keep old function IDs as deprecated aliases for one release cycle, logging warnings when used.
