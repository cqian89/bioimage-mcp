# Spec 011: Wrapper Consolidation and xarray-Based Image Handling

## Status
- **Status**: Draft
- **Date**: 2025-12-31
- **Branch**: `011-wrapper-consolidation`

## 1. Executive Summary

This proposal aims to eliminate all `base.wrapper.*` tools, moving toward a **zero-wrapper** architecture where library functions are called directly and axis preservation is handled by a unified `base.xarray.*` adapter.

1. **Zero-Wrapper Goal**: All existing `base.wrapper.*` functions (including I/O and axis ops) will be deleted. They are replaced by direct library exposure or a curated subset of `xarray.DataArray` methods exposed via individual tools in the `base.xarray.*` namespace.

2. **Persistent Workers & Memory Artifacts**: To eliminate redundant disk I/O, the server maintains persistent worker processes per MCP session/environment. These workers hold data in memory, referenced by a new URI scheme: `mem://<session_id>/<env_id>/<artifact_id>`.

3. **Axis-Aware Library Calls via `apply_ufunc`**: For libraries that do not natively support `xarray` (e.g., `scikit-image`), we introduce a declarative `apply_ufunc` mechanism in the manifest. This allows running numpy operations while automatically preserving dimensions.

4. **Cross-Env I/O Bridge & Handoff**: Cross-environment data transfer is handled transparently via negotiated interchange formats (defaulting to OME-TIFF unless otherwise declared). The target environment declares required format (env defaults + per-function overrides); the source environment exports/materializes via `bioio`, and the target environment imports via `bioio` (and may re-materialize to `mem://`).

5. **Attribute-Driven Dispatch**: Tool manifests use `input_mode: xarray` to request labeled data. The runtime resolves artifact references (file or `mem://`) to `xarray.DataArray` before execution.

## 2. Correctness Review (Skeptical)

This proposal was reviewed against the current codebase and web research on downstream library behavior. Key findings:

### 2.1 Architectural Decision: Persistent Workers & Memory-Backed Artifacts
- **Decision**: To support efficient data manipulation, `bioimage-mcp` adopts a **Persistent Worker Model**. Workers are started lazily per environment and reused across calls within the same MCP session.
- **Memory Artifacts**: Tools in the `base.xarray.*` namespace produce managed session-memory artifacts (`mem://`). These artifacts exist only in the worker's memory.
- **Isolation & Safety**: Subprocess isolation is maintained (one worker process per env). No explicit memory cap is enforced; the system relies on OS OOM.
- **Resilience**: If a worker crashes, the server restarts it and invalidates all `mem://` references for that environment.
- **Handoff**: Cross-env data transfer triggers negotiated materialization to a file-backed interchange format (default OME-TIFF unless otherwise declared). The source env exports/materializes via `bioio`; the target env imports via `bioio` and may re-materialize to `mem://`. An explicit `base.bioio.export` tool is provided for agent-driven materialization.

### 2.2 Library Compatibility
- **Assumption**: xarray metadata propagates through library calls.
- **Reality**: Most libraries (`scikit-image`, `scipy.ndimage`, `cellpose`) do not natively support xarray. They call `np.asarray()` or `.values` internally, stripping dimension names. `phasorpy` accepts axis names but its core computation logic also converts to numpy. 
- **Correction**: xarray is a powerful *metadata helper* for the adapter layer, but it is not a universal interchange format for the tool logic itself.

### 2.3 Existing Codebase Reality
- **Wrappers**: There are currently 16 wrappers registered in `tools/base/manifest.yaml` (e.g., `squeeze`, `relabel_axes`). These are implemented in `tools/base/bioimage_mcp_base/wrapper/`.
- **Data Access**: The codebase currently uses `BioImage.data` (numpy) exclusively. Transitioning to `.xarray_data` requires updates to all tool adapters.
- **Artifacts**: The server uses a SQLite-backed index for artifacts. "Memory-only" artifacts would require a new volatile index or an extension to the current schema.

## 3. xarray as Metadata Helper

### Current Problem

The current axis wrappers (`relabel_axes`, `squeeze`, `moveaxis`, etc.) exist because:
- `numpy.ndarray` has no dimension names - only integer indices
- Each operation requires manual axis metadata tracking
- Wrappers must read, transform, and write OME-TIFF with updated metadata

### Solution: BioImage.xarray_data

`bioio.BioImage.xarray_data` returns an `xarray.DataArray` with named dimensions:

```python
from bioio import BioImage

img = BioImage('image.tif')
xr_data = img.xarray_data
# dims=('T', 'C', 'Z', 'Y', 'X'), shape=(1, 1, 56, 512, 512)
```

**All xarray operations automatically preserve dimension names:**

```python
# Dimension names propagate through operations
squeezed = xr_data.squeeze()              # dims=('Z', 'Y', 'X')
summed = xr_data.sum(dim='Z')             # dims=('T', 'C', 'Y', 'X')
renamed = xr_data.rename({'Z': 'bins'})   # dims=('T', 'C', 'bins', 'Y', 'X')
transposed = xr_data.transpose('Z', 'T', 'C', 'Y', 'X')  # reordered dims
cropped = xr_data.isel(Y=slice(10, 50))   # dims unchanged, shape reduced
```

### xarray Equivalents for All Wrappers

| Current Wrapper | xarray Equivalent | Artifact Created? |
|----------------|-------------------|-------------------|
| `relabel_axes` | `DataArray.rename({'old': 'new'})` | No (in-memory) |
| `squeeze` | `DataArray.squeeze()` | No (in-memory) |
| `expand_dims` | `DataArray.expand_dims('dim', axis=n)` | No (in-memory) |
| `moveaxis` | `DataArray.transpose(*order)` | No (in-memory) |
| `swap_axes` | `DataArray.transpose(...)` | No (in-memory) |
| `project_sum` | `DataArray.sum(dim='axis')` | No (in-memory) |
| `project_max` | `DataArray.max(dim='axis')` | No (in-memory) |
| `crop` | `DataArray.isel(Y=slice(a,b))` | No (in-memory) |
| `flip` | `DataArray.isel(Y=slice(None,None,-1))` | No (in-memory) |
| `pad` | `DataArray.pad({'Y': (before, after)})` | No (in-memory) |

## 4. In-Memory Operation Model (Internal Optimization)

### Current Problem

Every wrapper function currently:
1. Reads artifact from disk
2. Performs operation
3. Writes new artifact to disk
4. Returns artifact reference

This creates excessive I/O for simple axis manipulations and metadata updates.

### 4.1 Persistent Worker & Memory-Backed Artifacts

**NEW ARCHITECTURE**: The runtime executes tool functions in persistent subprocesses per environment.
- **Persistent Workers**: A hot process is maintained for each environment used in a session. It keeps loaded `BioImage` and `DataArray` objects in memory.
- **Memory Artifacts**: Results of axis operations are stored as `mem://` references. These references are ephemeral and tied to the session/worker lifecycle.
- **Materialization**: 
    1. **Cross-Env**: Automatic materialization to OME-TIFF when a `mem://` artifact from one environment is passed to another.
    2. **Explicit**: User calls `base.bioio.export` to save a `mem://` artifact to disk.
    3. **Final**: Workflow results are materialized for persistence.

### 4.2 Implementation: BioImage with ArrayLikeReader

`bioio.BioImage` natively supports in-memory arrays via `ArrayLikeReader`. We can wrap intermediate results without writing to disk:

```python
def run_op(fn_id, inputs, params):
    # Inputs are already BioImage objects (resolved from refs)
    # Perform computation
    data = inputs['image'].xarray_data
    result_data = data.squeeze() 
    
    # Wrap back into BioImage WITHOUT writing to disk
    # BioImage(result_data) uses ArrayLikeReader
    return BioImage(result_data) 
```

## 5. Total Wrapper Elimination & The xarray Adapter

### 5.1 The "Zero Wrapper" Goal
We will delete all `base.wrapper.*` tools. Axis manipulation and transformations are now provided by individual tools in the `base.xarray.*` namespace, which operate on and produce `mem://` artifacts by default.

### 5.2 Wrappers to Delete and Replacement Mechanism

| Wrapper `fn_id` | Status | Replacement Mechanism |
|-----------------|--------|-----------------------|
| `base.wrapper.io.convert_to_ome_zarr` | **Delete** | Decentralized Handoff (Automatic) |
| `base.wrapper.io.export_ome_tiff` | **Delete** | `base.bioio.export` |
| `base.wrapper.axis.*` (squeeze, rename, etc.) | **Delete** | `base.xarray.*` tools |
| `base.wrapper.transform.*` (crop, project, flip, pad) | **Delete** | `base.xarray.*` tools |
| `base.wrapper.denoise.*`, `base.wrapper.preprocess.*` | **Delete** | Direct library calls via `apply_ufunc` |
| `base.wrapper.phasor.*` | **Delete** | Direct `phasorpy` calls via `input_mode: xarray` |

### 5.3 The `input_mode` & `apply_ufunc` Mechanism

The function manifest specifies how the tool expects to receive image data and how to handle numpy-only libraries.

- **`input_mode: numpy` (Default)**: Passes `BioImage.data` (5D TCZYX).
- **`input_mode: xarray`**: Passes `BioImage.xarray_data`.

#### 5.3.1 Declarative `apply_ufunc` for NumPy Libraries
For libraries like `scikit-image` that are axis-unaware, the manifest can include an `apply_ufunc` block. The runtime/adapter uses `xarray.apply_ufunc` to wrap the call, preserving dimensions and enabling parallelization.

**Manifest Configuration:**
- `input_core_dims`: Dimensions that should not be broadcasted (e.g., `[['Y', 'X']]` for a 2D filter).
- `output_core_dims`: Expected dimensions of the output.
- `vectorize=True`: Automatically loops the function over non-core dimensions (e.g., looping a 2D filter over T, C, Z).
- `dask='parallelized'`: Allows automatic parallel execution if the input is a Dask array.
- `output_dtypes`: The dtype of the result.
- `dask_gufunc_kwargs/output_sizes`: Required for operations that change core dimension sizes.

#### 5.3.2 Code Examples

**1. Per-plane YX filter (e.g., Gaussian Blur)**
Using `vectorize=True` to apply a 2D filter to every Z-slice, channel, and timepoint.
```python
# Internal adapter logic triggered by manifest
result = xr.apply_ufunc(
    skimage.filters.gaussian,
    input_xr_data,
    input_core_dims=[['Y', 'X']],
    output_core_dims=[['Y', 'X']],
    vectorize=True,
    dask='parallelized',
    output_dtypes=[input_xr_data.dtype]
)
```

**2. 3D ZYX filter (e.g., 3D Median)**
```python
# Internal adapter logic for 3D operations
result = xr.apply_ufunc(
    scipy.ndimage.median_filter,
    input_xr_data,
    input_core_dims=[['Z', 'Y', 'X']],
    output_core_dims=[['Z', 'Y', 'X']],
    kwargs={'size': (3, 3, 3)},
    dask='parallelized'
)
```

**Note on Projections**: Standard reductions (sum, max, mean) should use native `xarray.DataArray` methods (e.g., `img.max(dim='Z')`) via the adapter rather than `apply_ufunc`.

**Multi-output handling**: For functions returning multiple arrays (e.g., `phasor_from_signal` returning G and S), the adapter handles the tuple return by wrapping each element into a named artifact or a multi-channel image.

### 5.4 Curated xarray Allowlist

The xarray adapter provides direct access to these methods, replacing the manual `base.wrapper` implementations.

| Wrapper Operation | xarray Method | Example Usage | Doc Link |
|-------------------|---------------|---------------|----------|
| `relabel_axes` | `rename` | `data.rename({'Z': 'T'})` | [rename](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.rename.html) |
| `squeeze` | `squeeze` | `data.squeeze()` | [squeeze](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.squeeze.html) |
| `expand_dims` | `expand_dims` | `data.expand_dims('C', axis=1)` | [expand_dims](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.expand_dims.html) |
| `moveaxis` / `swap_axes` | `transpose` | `data.transpose('C', 'Z', 'Y', 'X')` | [transpose](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.transpose.html) |
| `crop` / `flip` | `isel` | `data.isel(Y=slice(10,50))` | [isel](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.isel.html) |
| `pad` | `pad` | `data.pad({'Y': (10, 10)})` | [pad](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.pad.html) |
| `project_sum` | `sum` | `data.sum(dim='Z')` | [sum](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.sum.html) |
| `project_max` | `max` | `data.max(dim='Z')` | [max](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.max.html) |

### 5.5 Extended Allowlist (Optional)

The following methods are candidates for inclusion to provide advanced analysis capabilities:

- `sel`: Coordinate-based selection (e.g., selecting specific channel names). [sel](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.sel.html)
- `coarsen`: Block-wise reduction (downsampling). [coarsen](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.coarsen.html)
- `rolling`: Moving window operations (e.g., local mean). [rolling](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.rolling.html)
- `where`: Masking and conditional replacement. [where](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.where.html)
- `clip`: Value range limiting. [clip](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.clip.html)
- `astype`: Type conversion (e.g., float to uint16). [astype](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.astype.html)
- `chunk`: Explicit re-chunking for Dask performance. [chunk](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.chunk.html)

### 5.6 Methods Not Exposed

The following methods **MUST NOT** be exposed via the MCP tool surface:

- `.values` and `.to_numpy()`: Forces materialization of the entire array into memory, risking Out-Of-Memory (OOM) for large datasets.
- `.load()` and `.compute()`: Forces Dask graph execution and materialization into memory.

**Rationale**: The core server and tool runtimes should work with lazy Dask arrays as long as possible. Materialization should only happen during final artifact export or when explicitly required by a non-lazy tool implementation.

## 6. Consolidated Tool Surface & Decentralized Handoff

### 6.1 Decentralized Format Handoff
All `base.wrapper.io` functions are deleted. The MCP server's execution layer now coordinates a **Decentralized Handoff** between environments:

1. **Negotiation**: When a target tool (e.g., `cellpose`) requires OME-TIFF but receives a CZI or `mem://` artifact from a different environment.
2. **Materialization**: The source environment exports/materializes the data to a file-backed interchange format (defaulting to OME-TIFF unless otherwise declared) using `bioio` writer backends.
3. **Import**: The target environment imports the file-backed artifact via `bioio` and may re-materialize it to `mem://` for subsequent same-env operations.
4. **Provenance**: The handoff step is automatically logged in the workflow run record.
5. **Caching**: Materialized artifacts are cached to avoid redundant I/O within the same session.

### 6.2 Explicit Export Tool
For agent-driven or final materialization of `mem://` artifacts to disk, an explicit `base.bioio.export` tool is provided. This allows agents to save a persistent file (defaulting to OME-TIFF; OME-Zarr support is optional/TBD).

### 6.3 Implementation via bioio
Generalized format conversion and materialization are performed using the formal `bioio` ecosystem. This ensures that physical units, dimension names, and metadata are preserved during the transition between isolated environments.

## 7. Configuration and Path Handling

### Problem
Defaulting to `~/.bioimage-mcp/artifacts` is problematic for IDEs (Cursor/VSCode) and portable workflows.

### Solution: Relative to Working Directory
Standardize on paths relative to the current working directory (CWD) by default. This ensures that artifacts, logs, and configuration stay within the project context where the MCP server was started.

**Note on Repository Roots**: While CWD is the default for maximum flexibility, in many development scenarios, the repository root (found via `.git` or `.bioimage-mcp` markers) is a more stable anchor. Tools should prefer repo-relative paths when a marker is present, but respect the CWD-based configuration.

**Config Schema Consistency**:
The following keys will support CWD-relative paths (automatically expanded to absolute paths during configuration loading):
- `artifact_store_root`: Path to store artifacts (default: `./.bioimage-mcp/artifacts`)
- `fs_allowlist_read`: List of allowed read paths (defaults include `./`)
- `fs_allowlist_write`: List of allowed write paths (defaults include `./`)

## 8. Implementation Plan

### Phase 1: Attribute-Driven Adapter Selection (Week 1-2)

1. Add `input_mode` (or `input_datatype`) field to function manifest schema and registry models.
2. Implement the `apply_ufunc` config block in the manifest schema.
3. Update the tool execution layer (`run_function`) to check `input_mode` and `apply_ufunc` settings, providing the appropriate data view (`.data` vs `.xarray_data`).
4. Create the `xarray` adapter to expose native `DataArray` methods (rename, squeeze, transpose, etc.) as MCP tools.
5. Create `save_xarray_artifact()` utility for writing with dim preservation using `bioio` writer backends.

### Phase 2: Decentralized Handoff & Export (Week 2-3)

1. Add format compatibility and export metadata to environment manifests.
2. Implement cross-env negotiation and automatic source-env materialization in the server execution layer.
3. Implement the `base.bioio.export` tool for explicit materialization.
4. Ensure handoff and materialization steps are logged in the workflow provenance.
5. Test with `base (CZI)` → `cellpose (OME-TIFF)` workflow.

### Phase 3: Total Wrapper Removal (Week 3-4)

1. Delete all `base.wrapper.*` implementation code and manifest entries.
2. Update agent system prompts to guide them toward library-native functions and the `xarray` adapter.
3. Update documentation and tutorials to reflect the zero-wrapper architecture.

## 10. Success Criteria

1.  **Zero Wrappers**: No `base.wrapper.*` tools exist in the final registry.
2.  **Axis-Preserving Library Calls**: Library functions like `skimage.filters.gaussian` are called directly, with dimensions preserved via `apply_ufunc` as defined in the manifest.
3.  **Unified xarray Adapter**: A single adapter exposes `xarray.DataArray` methods, replacing over 10 manual axis/transform wrappers.
4.  **Allowlist Coverage**: The xarray adapter covers 100% of the functionality previously provided by `base.wrapper.*` axis and transform tools.
5.  **Resource Safety**: No forbidden materialization methods (`.values`, `.load`, etc.) are exposed via the tool registry.
6.  **Transparent Handoff**: Agent can run a workflow across environments (e.g., loading CZI and passing to Cellpose) without manual I/O conversion calls; the system handles negotiation and materialization.
7.  **Provenance Logging**: Every automatic handoff and materialization is explicitly recorded in the workflow run artifact.
8.  **Agent Success**: Agent successfully performs FLIM analysis using `phasorpy` and axis operations using the `xarray` adapter.

## 11. Migration Guide

### For Agent Workflows

**Before (with wrappers):**
```python
# Load and convert format manually
zarr = run_function('base.wrapper.io.convert_to_ome_zarr', {'image': path})

# Axis manipulation via custom wrapper (disk I/O)
relabeled = run_function('base.wrapper.axis.relabel_axes', 
                         {'image': zarr}, 
                         {'axis_mapping': {'Z': 'T'}})
```

**After (Zero Wrappers):**
```python
# Load directly - persistent worker keeps it in memory
img = run_function('base.bioio.load', {'path': path})

# Axis manipulation via base.xarray.rename (produces mem://)
relabeled = run_function('base.xarray.rename', 
                         {'image': img}, 
                         {'mapping': {'Z': 'T'}})

# Library call - Decentralized Handoff handles cross-env boundary if phasorpy is in different env
phasors = run_function('phasorpy.phasor.phasor_from_signal',
                       {'signal': relabeled},
                       {'axis': 'T', 'harmonic': 1})

# Explicitly save results to disk (defaults to OME-TIFF; OME-Zarr support is TBD)
run_function('base.bioio.export', 
             {'image': phasors, 'path': 'results.ome.tiff'})
```

## 13. References & Citations

- **xarray.apply_ufunc Documentation**: [Generated API Reference](https://docs.xarray.dev/en/stable/generated/xarray.apply_ufunc.html)
- **Vectorizing 1D functions**: [xarray Example](https://docs.xarray.dev/en/stable/examples/apply_ufunc_vectorize_1d.html)
- **Dask Automatic Parallelization**: [xarray User Guide](https://docs.xarray.dev/en/stable/user-guide/dask.html#dask-automatic-parallelization)
- **Wrapping Custom Computation**: [xarray Computation Guide](https://docs.xarray.dev/en/stable/user-guide/computation.html#wrapping-custom-computation)
- **xarray.DataArray.rename**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.rename.html)
- **xarray.DataArray.squeeze**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.squeeze.html)
- **xarray.DataArray.expand_dims**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.expand_dims.html)
- **xarray.DataArray.transpose**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.transpose.html)
- **xarray.DataArray.isel**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.isel.html)
- **xarray.DataArray.pad**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.pad.html)
- **xarray.DataArray.sum**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.sum.html)
- **xarray.DataArray.max**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.max.html)
- **xarray.DataArray.sel**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.sel.html)
- **xarray.DataArray.coarsen**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.coarsen.html)
- **xarray.DataArray.rolling**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.rolling.html)
- **xarray.DataArray.where**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.where.html)
- **xarray.DataArray.clip**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.clip.html)
- **xarray.DataArray.astype**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.astype.html)
- **xarray.DataArray.chunk**: [Doc](https://docs.xarray.dev/en/stable/generated/xarray.DataArray.chunk.html)
- **bioio**: Unified bio-format I/O and xarray integration. [GitHub](https://github.com/bioio-devs/bioio)
- **bioio-ome-tiff**: OME-TIFF writer backend. [GitHub](https://github.com/bioio-devs/bioio-ome-tiff)
- **bioio-ome-zarr**: OME-Zarr writer backend. [GitHub](https://github.com/bioio-devs/bioio-ome-zarr)
- **phasorpy**: Lifetime and spectral phasor analysis. [GitHub](https://github.com/phasorpy/phasorpy)
- **OME-TIFF Specification**: Standard for microscopy metadata. [OME-TIFF](https://docs.openmicroscopy.org/ome-model/latest/ome-tiff/)
