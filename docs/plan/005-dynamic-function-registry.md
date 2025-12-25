# 005: Dynamic Function Registry

**Status**: Draft  
**Created**: 2025-12-25  
**Context**: Expanding tool availability without manual manifest entries

## Problem Statement

The current bioimage-mcp architecture requires **static manifest definitions** for every exposed function. This creates friction when:

1. Libraries like phasorpy, scikit-image, and scipy.ndimage have dozens of useful functions
2. Each function requires manual YAML entry + Python wrapper code
3. New library versions add functions that remain inaccessible until manually added
4. The FLIM phasor workflow is incomplete because calibration functions aren't exposed

### Immediate Gap: FLIM Calibration

The `test_flim_phasor_e2e.py` test is missing critical calibration steps:

| Current Workflow | Required Workflow |
|------------------|-------------------|
| 1. `base.phasor_from_flim` | 1. Load reference file (known lifetime) |
| 2. Segment intensity | 2. Compute reference phasor coordinates |
| | 3. Load sample file |
| | 4. Compute sample phasor coordinates |
| | 5. **Calibrate** using `phasor_transform` |
| | 6. Segment intensity |

The FLUTE dataset README specifies calibration files:

| Sample File | Calibration Reference | Known Lifetime |
|-------------|----------------------|----------------|
| `Embryo.tif` | `Fluorescein_Embryo.tif` | 4ns |
| `hMSC control.tif` | `Fluorescein_hMSC.tif` | 4ns |
| `ZF-1100_*.tif` | `starch SHG-IRF.tif` | 0ns (IRF) |

## Research Findings

### Available Libraries in Base Environment

```
Module                          Version     Functions
─────────────────────────────────────────────────────
skimage                         v0.26.0     (via submodules)
scipy.ndimage                   v1.x        76 functions
numpy                           v2.4.0      390 functions
phasorpy                        v0.8        (via submodules)
bioio                           v3.2.0      7 functions
tifffile                        v2025.12.20 38 functions
zarr                            v3.1.5      33 functions
skimage.morphology              -           50 functions
skimage.segmentation            -           20 functions
skimage.measure                 -           31 functions
skimage.filters                 -           46 functions
skimage.transform               -           29 functions
skimage.exposure                -           10 functions
skimage.restoration             -           17 functions
```

### PhasorPy API (v0.8)

#### phasorpy.phasor (Core Operations)

| Function | Description | Use Case |
|----------|-------------|----------|
| `phasor_from_signal` | Compute G/S from FLIM signal | Raw phasor computation |
| `phasor_transform` | Rotate and scale phasor coordinates | **Calibration** |
| `phasor_from_polar` | Convert phase/modulation to G/S | Reference phasor from known lifetime |
| `phasor_to_polar` | Convert G/S to phase/modulation | Lifetime analysis |
| `phasor_threshold` | Mask values outside interval (NaN) | Intensity thresholding |
| `phasor_center` | Find center of phasor cloud | Analysis |
| `phasor_normalize` | Normalize phasor coordinates | Preprocessing |
| `phasor_combine` | Linear combination of two phasors | Unmixing |
| `phasor_multiply` | Complex multiplication | Advanced operations |
| `phasor_divide` | Complex division | Advanced operations |

#### phasorpy.io (File I/O)

| Function | Description | Formats |
|----------|-------------|---------|
| `signal_from_sdt` | Load Becker & Hickl SDT | `.sdt` |
| `signal_from_ptu` | Load PicoQuant PTU | `.ptu` |
| `signal_from_lif` | Load Leica LIF | `.lif` |
| `signal_from_pqbin` | Load PicoQuant BIN | `.bin` |
| `signal_from_fbd` | Load FLIMbox FBD | `.fbd` |
| `phasor_to_ometiff` | Save phasor as OME-TIFF | `.ome.tiff` |
| `phasor_from_ometiff` | Load phasor from OME-TIFF | `.ome.tiff` |

#### phasorpy.cluster (Analysis)

| Function | Description |
|----------|-------------|
| `phasor_cluster_gmm` | GMM clustering in phasor space |

### Calibration Workflow (phasor_transform)

From phasorpy documentation:

```python
phasor_transform(
    real: ArrayLike,      # G coordinates to transform
    imag: ArrayLike,      # S coordinates to transform  
    phase: ArrayLike = 0.0,      # Rotation angle in radians
    modulation: ArrayLike = 1.0  # Scale factor
) -> tuple[NDArray, NDArray]
```

> "This function rotates and uniformly scales phasor coordinates around the origin. It can be used, for example, to calibrate phasor coordinates."

**Calibration procedure:**
1. Compute phasor from reference (known lifetime fluorophore)
2. Compute expected reference position using `phasor_from_polar` with known lifetime
3. Calculate phase shift and modulation correction
4. Apply `phasor_transform` to sample data

### Bioimage-Relevant Functions (78 total)

#### skimage.filters (10 functions)
- `gaussian`, `median`, `sobel`, `threshold_otsu`, `threshold_yen`
- `unsharp_mask`, `frangi`, `meijering`, `sato`, `hessian`

#### skimage.morphology (11 functions)
- `binary_erosion`, `binary_dilation`, `binary_opening`, `binary_closing`
- `remove_small_objects`, `remove_small_holes`, `skeletonize`
- `label`, `disk`, `ball`, `cube`

#### skimage.segmentation (6 functions)
- `watershed`, `clear_border`, `find_boundaries`, `mark_boundaries`
- `expand_labels`, `relabel_sequential`

#### skimage.measure (7 functions)
- `label`, `regionprops`, `regionprops_table`, `find_contours`
- `moments`, `centroid`, `perimeter`

#### skimage.transform (7 functions)
- `resize`, `rescale`, `rotate`, `warp`, `downscale_local_mean`
- `pyramid_gaussian`, `pyramid_laplacian`

#### skimage.exposure (6 functions)
- `equalize_hist`, `equalize_adapthist`, `rescale_intensity`
- `adjust_gamma`, `adjust_log`, `adjust_sigmoid`

#### skimage.restoration (6 functions)
- `denoise_nl_means`, `denoise_bilateral`, `denoise_tv_chambolle`
- `denoise_wavelet`, `rolling_ball`, `wiener`

#### scipy.ndimage (11 functions)
- `gaussian_filter`, `median_filter`, `uniform_filter`
- `maximum_filter`, `minimum_filter`, `label`, `find_objects`
- `binary_fill_holes`, `distance_transform_edt`, `zoom`, `rotate`

## Current Architecture (Static)

```
┌─────────────────────────────────────────────────────────────────┐
│  tools/base/manifest.yaml                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  functions:                                              │    │
│  │    - fn_id: base.phasor_from_flim   # Manually defined  │    │
│  │    - fn_id: base.gaussian           # Manually defined  │    │
│  │    - fn_id: base.median             # Manually defined  │    │
│  │    ...                                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  tools/base/bioimage_mcp_base/entrypoint.py                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  FN_MAP = {                                              │    │
│  │      "base.phasor_from_flim": (phasor_from_flim, ...),  │    │
│  │      "base.gaussian": (gaussian, ...),                   │    │
│  │      ...                                                 │    │
│  │  }  # Hardcoded routing                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  src/bioimage_mcp/registry/loader.py                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  - Scans manifest YAML files                             │    │
│  │  - Indexes functions in SQLite                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  src/bioimage_mcp/api/discovery.py                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  - search_functions(query, tags, io_in, io_out)         │    │
│  │  - describe_function(fn_id) -> schema                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Limitations

1. **Manual effort**: Each function requires YAML + wrapper + descriptions
2. **Incomplete coverage**: Only 26 functions exposed vs. 78+ available
3. **Version lag**: New library functions not automatically available
4. **Calibration gap**: `phasor_transform` not exposed, breaking FLIM workflow

## Proposed Architecture (Dynamic)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Dynamic Library Function Registry                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  1. LIBRARY ADAPTER REGISTRY                                     │    │
│  │     Each library has an adapter that knows how to:               │    │
│  │     - Discover functions (which to expose)                       │    │
│  │     - Infer I/O types (image, labels, table, scalar)            │    │
│  │     - Map artifact refs ↔ numpy/library-native types            │    │
│  │     - Generate curated descriptions (from docstrings)            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  2. MANIFEST: dynamic_sources configuration                      │    │
│  │                                                                   │    │
│  │  dynamic_sources:                                                 │    │
│  │    - adapter: skimage                                             │    │
│  │      modules:                                                     │    │
│  │        - skimage.filters                                          │    │
│  │        - skimage.morphology                                       │    │
│  │        - skimage.measure                                          │    │
│  │      include_patterns: ["*"]                                      │    │
│  │      exclude_patterns: ["_*", "test_*"]                          │    │
│  │                                                                   │    │
│  │    - adapter: phasorpy                                            │    │
│  │      modules:                                                     │    │
│  │        - phasorpy.phasor                                          │    │
│  │        - phasorpy.io                                              │    │
│  │        - phasorpy.cluster                                         │    │
│  │                                                                   │    │
│  │    - adapter: scipy_ndimage                                       │    │
│  │      modules:                                                     │    │
│  │        - scipy.ndimage                                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  3. INTROSPECTION ENGINE (at startup/discovery time)             │    │
│  │                                                                   │    │
│  │  For each (adapter, module, function):                           │    │
│  │    1. Get function signature + type hints                        │    │
│  │    2. Parse numpy-style docstring for param descriptions         │    │
│  │    3. Infer input artifact types from first positional args      │    │
│  │    4. Infer output artifact types from return annotation         │    │
│  │    5. Generate JSON Schema for params                            │    │
│  │    6. Register as: {prefix}.{module_leaf}.{func_name}            │    │
│  │       e.g., "skimage.filters.gaussian"                           │    │
│  │            "phasorpy.phasor.phasor_transform"                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  4. WRAPPER/ADAPTER LAYER (at execution time)                    │    │
│  │                                                                   │    │
│  │  class LibraryAdapter(Protocol):                                  │    │
│  │      def load_input(ref: ArtifactRef) -> Any                     │    │
│  │      def save_output(data: Any, work_dir: Path) -> ArtifactRef   │    │
│  │      def adapt_params(params: dict) -> dict                      │    │
│  │      def call_function(fn, inputs, params) -> dict               │    │
│  │                                                                   │    │
│  │  Adapters handle library-specific quirks:                         │    │
│  │  - skimage: image as first positional, kwargs for rest           │    │
│  │  - phasorpy: (real, imag) tuple patterns                         │    │
│  │  - scipy.ndimage: input/output array patterns                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  5. DYNAMIC ENTRYPOINT ROUTER                                    │    │
│  │                                                                   │    │
│  │  def dispatch(fn_id: str, inputs: dict, params: dict):           │    │
│  │      if fn_id in STATIC_FN_MAP:                                  │    │
│  │          return STATIC_FN_MAP[fn_id](...)                        │    │
│  │                                                                   │    │
│  │      # Dynamic dispatch                                           │    │
│  │      adapter_name, *path = fn_id.split(".")                      │    │
│  │      adapter = ADAPTERS[adapter_name]                            │    │
│  │      module_path = ".".join(path[:-1])                           │    │
│  │      func_name = path[-1]                                        │    │
│  │      func = getattr(import_module(module_path), func_name)       │    │
│  │      return adapter.call_function(func, inputs, params)          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Function ID Naming Convention

| Library | Module | Function | MCP fn_id |
|---------|--------|----------|-----------|
| scikit-image | filters | gaussian | `skimage.filters.gaussian` |
| scikit-image | measure | regionprops_table | `skimage.measure.regionprops_table` |
| scikit-image | morphology | watershed | `skimage.morphology.watershed` |
| phasorpy | phasor | phasor_transform | `phasorpy.phasor.phasor_transform` |
| phasorpy | io | signal_from_sdt | `phasorpy.io.signal_from_sdt` |
| scipy | ndimage | gaussian_filter | `scipy.ndimage.gaussian_filter` |

## Library Adapter Protocol

```python
from typing import Any, Protocol
from pathlib import Path

class IOPattern(Enum):
    """Common I/O patterns for bioimage functions."""
    IMAGE_TO_IMAGE = auto()      # BioImageRef -> BioImageRef
    IMAGE_TO_LABELS = auto()     # BioImageRef -> LabelImageRef
    LABELS_TO_TABLE = auto()     # LabelImageRef -> TableRef
    SIGNAL_TO_PHASOR = auto()    # BioImageRef -> (G, S) images
    PHASOR_TRANSFORM = auto()    # (G, S) -> (G', S')
    PHASOR_TO_OTHER = auto()     # (G, S) -> polar/signal
    ARRAY_TO_ARRAY = auto()      # Generic array transform
    ARRAY_TO_SCALAR = auto()     # Array -> scalar value
    FILE_TO_SIGNAL = auto()      # File path -> signal array


class LibraryAdapter(Protocol):
    """Protocol for library-specific function adapters."""
    
    @property
    def prefix(self) -> str:
        """Prefix for function IDs (e.g., 'skimage', 'phasorpy')."""
        ...
    
    def discover_functions(self, module_path: str) -> list[FunctionInfo]:
        """Discover exportable functions in a module."""
        ...
    
    def infer_io_pattern(self, func: Callable) -> IOPattern:
        """Infer the I/O pattern for a function."""
        ...
    
    def load_inputs(
        self, 
        pattern: IOPattern, 
        inputs: dict[str, ArtifactRef]
    ) -> dict[str, Any]:
        """Load artifact refs into library-native types."""
        ...
    
    def save_outputs(
        self,
        pattern: IOPattern,
        result: Any,
        work_dir: Path,
    ) -> dict[str, ArtifactRef]:
        """Save function results as artifacts."""
        ...
    
    def adapt_params(self, func: Callable, params: dict) -> dict:
        """Adapt MCP params to function kwargs."""
        ...
    
    def call_function(
        self,
        func: Callable,
        inputs: dict[str, ArtifactRef],
        params: dict,
        work_dir: Path,
    ) -> dict[str, Any]:
        """Execute function with full artifact I/O handling."""
        ...
```

## Adapter Implementations

### SkimageAdapter

```python
class SkimageAdapter(LibraryAdapter):
    """Adapter for scikit-image functions."""
    
    prefix = "skimage"
    
    # Submodule -> typical I/O pattern
    MODULE_PATTERNS = {
        "filters": IOPattern.IMAGE_TO_IMAGE,
        "morphology": IOPattern.IMAGE_TO_IMAGE,
        "transform": IOPattern.IMAGE_TO_IMAGE,
        "exposure": IOPattern.IMAGE_TO_IMAGE,
        "restoration": IOPattern.IMAGE_TO_IMAGE,
        "segmentation": IOPattern.IMAGE_TO_LABELS,
        "measure": IOPattern.LABELS_TO_TABLE,
    }
    
    # Function-specific overrides
    FUNCTION_PATTERNS = {
        "label": IOPattern.IMAGE_TO_LABELS,
        "regionprops": IOPattern.LABELS_TO_TABLE,
        "regionprops_table": IOPattern.LABELS_TO_TABLE,
        "threshold_otsu": IOPattern.ARRAY_TO_SCALAR,
        "threshold_yen": IOPattern.ARRAY_TO_SCALAR,
    }
    
    def infer_io_pattern(self, func: Callable) -> IOPattern:
        # Check function-specific first
        if func.__name__ in self.FUNCTION_PATTERNS:
            return self.FUNCTION_PATTERNS[func.__name__]
        
        # Fall back to module pattern
        module = func.__module__
        for submod, pattern in self.MODULE_PATTERNS.items():
            if submod in module:
                return pattern
        
        return IOPattern.ARRAY_TO_ARRAY
```

### PhasorpyAdapter

```python
class PhasorpyAdapter(LibraryAdapter):
    """Adapter for phasorpy functions."""
    
    prefix = "phasorpy"
    
    # Phasorpy has specific conventions
    FUNCTION_PATTERNS = {
        # Core phasor operations
        "phasor_from_signal": IOPattern.SIGNAL_TO_PHASOR,
        "phasor_transform": IOPattern.PHASOR_TRANSFORM,
        "phasor_from_polar": IOPattern.PHASOR_TRANSFORM,
        "phasor_to_polar": IOPattern.PHASOR_TO_OTHER,
        "phasor_threshold": IOPattern.PHASOR_TRANSFORM,
        "phasor_center": IOPattern.ARRAY_TO_SCALAR,
        "phasor_normalize": IOPattern.PHASOR_TRANSFORM,
        "phasor_combine": IOPattern.PHASOR_TRANSFORM,
        
        # I/O functions
        "signal_from_sdt": IOPattern.FILE_TO_SIGNAL,
        "signal_from_ptu": IOPattern.FILE_TO_SIGNAL,
        "signal_from_lif": IOPattern.FILE_TO_SIGNAL,
        "phasor_to_ometiff": IOPattern.PHASOR_TO_OTHER,
        "phasor_from_ometiff": IOPattern.SIGNAL_TO_PHASOR,
        
        # Analysis
        "phasor_cluster_gmm": IOPattern.PHASOR_TO_OTHER,
    }
    
    def load_inputs(self, pattern: IOPattern, inputs: dict) -> dict:
        """Handle phasorpy's (real, imag) tuple convention."""
        if pattern in (IOPattern.PHASOR_TRANSFORM, IOPattern.PHASOR_TO_OTHER):
            # Expect g_image and s_image inputs
            g_data = load_image(inputs["g_image"]["uri"])
            s_data = load_image(inputs["s_image"]["uri"])
            return {"real": g_data, "imag": s_data}
        
        if pattern == IOPattern.SIGNAL_TO_PHASOR:
            signal = load_image(inputs["signal"]["uri"])
            return {"signal": signal}
        
        return {}
    
    def save_outputs(self, pattern: IOPattern, result: Any, work_dir: Path) -> dict:
        """Handle phasorpy's tuple returns."""
        if pattern == IOPattern.SIGNAL_TO_PHASOR:
            # Returns (mean, real, imag)
            mean, g, s = result
            return {
                "intensity": save_image(mean, work_dir, "intensity.ome.tiff"),
                "g_image": save_image(g, work_dir, "phasor_g.ome.tiff"),
                "s_image": save_image(s, work_dir, "phasor_s.ome.tiff"),
            }
        
        if pattern == IOPattern.PHASOR_TRANSFORM:
            # Returns (real, imag)
            g, s = result
            return {
                "g_image": save_image(g, work_dir, "phasor_g.ome.tiff"),
                "s_image": save_image(s, work_dir, "phasor_s.ome.tiff"),
            }
        
        return {}
```

### ScipyNdimageAdapter

```python
class ScipyNdimageAdapter(LibraryAdapter):
    """Adapter for scipy.ndimage functions."""
    
    prefix = "scipy"
    
    FUNCTION_PATTERNS = {
        # Filters
        "gaussian_filter": IOPattern.IMAGE_TO_IMAGE,
        "median_filter": IOPattern.IMAGE_TO_IMAGE,
        "uniform_filter": IOPattern.IMAGE_TO_IMAGE,
        "maximum_filter": IOPattern.IMAGE_TO_IMAGE,
        "minimum_filter": IOPattern.IMAGE_TO_IMAGE,
        
        # Morphology
        "binary_fill_holes": IOPattern.IMAGE_TO_IMAGE,
        "binary_erosion": IOPattern.IMAGE_TO_IMAGE,
        "binary_dilation": IOPattern.IMAGE_TO_IMAGE,
        
        # Labeling
        "label": IOPattern.IMAGE_TO_LABELS,
        "find_objects": IOPattern.LABELS_TO_TABLE,
        
        # Transforms
        "zoom": IOPattern.IMAGE_TO_IMAGE,
        "rotate": IOPattern.IMAGE_TO_IMAGE,
        
        # Distance
        "distance_transform_edt": IOPattern.IMAGE_TO_IMAGE,
    }
```

## Docstring Parsing

Use numpydoc for extracting parameter descriptions:

```python
def parse_numpy_docstring(func: Callable) -> dict[str, str]:
    """Extract parameter descriptions from numpy-style docstrings.
    
    Most scientific Python libraries use numpy docstring format:
    
        Parameters
        ----------
        image : ndarray
            Input image.
        sigma : float, optional
            Standard deviation for Gaussian kernel.
            
    Returns dict mapping param name -> description.
    """
    try:
        from numpydoc.docscrape import FunctionDoc
        doc = FunctionDoc(func)
        descriptions = {}
        for param in doc["Parameters"]:
            name = param.name.split(":")[0].strip()
            desc = " ".join(param.desc).strip()
            if desc:
                descriptions[name] = desc
        return descriptions
    except Exception:
        return {}
```

## Manifest Extension

```yaml
# tools/base/manifest.yaml

manifest_version: "0.1"
tool_id: tools.base
tool_version: "0.2.0"

# Static functions (existing)
functions:
  - fn_id: base.phasor_from_flim
    # ... existing definition

# NEW: Dynamic function sources
dynamic_sources:
  - adapter: skimage
    modules:
      - skimage.filters
      - skimage.morphology
      - skimage.segmentation
      - skimage.measure
      - skimage.transform
      - skimage.exposure
      - skimage.restoration
    include_patterns:
      - "*"
    exclude_patterns:
      - "_*"
      - "test_*"
      - "*_coords"  # Internal helpers

  - adapter: phasorpy
    modules:
      - phasorpy.phasor
      - phasorpy.io
      - phasorpy.cluster
    include_patterns:
      - "phasor_*"
      - "signal_from_*"
      - "*_cluster_*"
    exclude_patterns:
      - "parse_*"  # Internal helpers
      - "number_threads"

  - adapter: scipy_ndimage
    modules:
      - scipy.ndimage
    include_patterns:
      - "*_filter"
      - "binary_*"
      - "label"
      - "find_objects"
      - "distance_transform_*"
      - "zoom"
      - "rotate"
```

## Implementation Files

| File | Purpose |
|------|---------|
| `src/bioimage_mcp/registry/dynamic.py` | Dynamic function discovery engine |
| `src/bioimage_mcp/registry/adapters/__init__.py` | Adapter protocol + registry |
| `src/bioimage_mcp/registry/adapters/skimage.py` | scikit-image adapter |
| `src/bioimage_mcp/registry/adapters/phasorpy.py` | phasorpy adapter |
| `src/bioimage_mcp/registry/adapters/scipy_ndimage.py` | scipy.ndimage adapter |
| `src/bioimage_mcp/registry/docstring_parser.py` | Numpy docstring extraction |
| `tools/base/bioimage_mcp_base/dynamic_dispatch.py` | Runtime dispatch in tool env |
| `tests/unit/registry/test_dynamic.py` | Unit tests for introspection |
| `tests/contract/test_dynamic_functions.py` | Contract tests for adapters |

## Discovery Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Startup / Registry Refresh                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Load manifest.yaml                                           │
│     ├── Parse static functions (existing behavior)              │
│     └── Parse dynamic_sources (new)                             │
│                                                                  │
│  2. For each dynamic_source:                                     │
│     ├── Load adapter by name                                    │
│     ├── For each module in modules:                             │
│     │   ├── Import module in tool environment                   │
│     │   ├── Discover functions matching include/exclude         │
│     │   └── For each function:                                  │
│     │       ├── Infer I/O pattern                               │
│     │       ├── Parse docstring for descriptions                │
│     │       ├── Extract signature for params schema             │
│     │       └── Generate FunctionInfo                           │
│     └── Register all discovered functions                       │
│                                                                  │
│  3. Index in SQLite (same as static functions)                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  call_tool(fn_id="skimage.filters.gaussian", inputs, params)    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Entrypoint receives request                                  │
│                                                                  │
│  2. Check STATIC_FN_MAP first (backwards compatible)            │
│     └── Not found, try dynamic dispatch                         │
│                                                                  │
│  3. Parse fn_id: adapter="skimage", path=["filters","gaussian"] │
│                                                                  │
│  4. Load adapter: SkimageAdapter                                 │
│                                                                  │
│  5. Import function: from skimage.filters import gaussian       │
│                                                                  │
│  6. Infer I/O pattern: IMAGE_TO_IMAGE                           │
│                                                                  │
│  7. Load inputs via adapter:                                     │
│     image = load_image(inputs["image"]["uri"])                  │
│                                                                  │
│  8. Adapt params via adapter:                                    │
│     kwargs = {"sigma": params["sigma"], ...}                    │
│                                                                  │
│  9. Call function:                                               │
│     result = gaussian(image, **kwargs)                          │
│                                                                  │
│  10. Save outputs via adapter:                                   │
│      output_ref = save_image(result, work_dir, "output.ome.tiff")│
│                                                                  │
│  11. Return MCP response:                                        │
│      {"outputs": {"output": output_ref}, "log": "ok"}           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Benefits

1. **~80+ functions immediately available** with minimal code
2. **Self-documenting** - descriptions extracted from docstrings
3. **Type-inferred** - I/O types derived from function signatures
4. **Extensible** - add new libraries by writing an adapter
5. **Searchable** - all functions indexed for MCP discovery
6. **Lazy loading** - functions only imported when called
7. **Version-resilient** - new library functions automatically available

## Considerations

### Curated vs. Auto-generated

Some functions need manual curation:
- Complex I/O patterns (multiple images in/out)
- Non-standard return types
- Functions with side effects

Solution: Allow `exclude_patterns` and provide override mechanism in manifest.

### Stability

Library updates could break inferred schemas.

Solution:
- Pin library versions in lockfiles (existing)
- Version-stamped schema cache
- Contract tests for critical functions

### Testing

Need contract tests for dynamic functions.

Solution:
- Test adapter I/O patterns
- Test representative function from each module
- Integration test for FLIM calibration workflow

### Performance

Introspection at startup adds latency.

Solution:
- Cache introspection results
- Lazy introspection on first access
- Background refresh

## Migration Path

1. **Phase 1**: Add dynamic infrastructure (no breaking changes)
   - Implement adapter protocol
   - Add phasorpy adapter (immediate need for calibration)
   - Keep all existing static functions

2. **Phase 2**: Expand coverage
   - Add skimage adapter
   - Add scipy.ndimage adapter
   - Migrate redundant static functions to dynamic

3. **Phase 3**: Optimize
   - Schema caching
   - Lazy loading
   - Performance benchmarks

## Success Criteria

1. `phasorpy.phasor.phasor_transform` available via MCP discovery
2. FLIM calibration workflow works end-to-end
3. `skimage.filters.*` functions searchable and callable
4. No regression in existing static function behavior
5. Contract tests pass for all adapters

## References

- PhasorPy documentation: https://www.phasorpy.org/
- scikit-image API: https://scikit-image.org/docs/stable/api/
- scipy.ndimage: https://docs.scipy.org/doc/scipy/reference/ndimage.html
- Existing introspection: `src/bioimage_mcp/runtimes/introspect.py`
- FLUTE dataset: `datasets/FLUTE_FLIM_data_tif/README.md`
