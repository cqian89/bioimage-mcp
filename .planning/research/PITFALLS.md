# Domain Pitfalls: Scipy Integration

**Domain:** Bioimage-MCP / Scipy Integration (v0.3.0)
**Researched:** 2026-01-25
**Overall Confidence:** HIGH

## Critical Pitfalls (Scipy Specific)

Mistakes that cause system instability, OOM crashes, or data corruption when integrating Scipy.

### Pitfall 1: Memory Exhaustion on Large Volumes
**What goes wrong:** `scipy.ndimage` functions generally require the entire input array to be materialized in RAM. Bioimage datasets (e.g., lightsheet, 4D time-lapse) often exceed available system memory.
**Why it happens:** The current adapter pattern (inherited from early skimage integration) calls `.compute()` on Dask-backed xarrays, forcing a full load of potentially multi-gigabyte files.
**Consequences:** Worker process crashes (OOM), system instability, or failed MCP requests without clear error messages.
**Warning signs:** High RSS memory usage in worker processes; `MemoryError` in logs; worker disconnects during filtering.
**Prevention:** 
1. Implement chunked processing for functions that support it (e.g., via `dask.array.map_blocks`).
2. Add a "memory budget" check before materializing arrays.
3. Provide a `slice` parameter to operate on sub-volumes by default.
**Phase:** **Phase 1 (Integration Hardening)**.

### Pitfall 2: Implicit Dtype Escalation (Memory Doubling)
**What goes wrong:** Many Scipy functions (especially filters like `gaussian_filter`) promote input data to `float64` by default to ensure precision.
**Why it happens:** Scipy's default behavior for most linear filters is to use double-precision floats unless an `output` array or dtype is explicitly provided.
**Consequences:** Doubling of memory usage (e.g., `uint16` -> `float64` is 4x increase). This often triggers the OOM issues described above.
**Warning signs:** Result artifacts are significantly larger than input artifacts; memory spikes during execution.
**Prevention:** 
1. Use the `output` parameter in `ndimage` functions to force a specific dtype (e.g., `float32`).
2. Add a heuristic to the adapter to choose the most memory-efficient safe dtype for the operation.
**Phase:** **Phase 1 (Integration Hardening)**.

### Pitfall 3: Return Type Mismatch (Scalars/Tuples)
**What goes wrong:** The current adapter assumes all `scipy.ndimage` functions return a single image array. However, many functions return scalars (`mean`, `variance`) or tuples (`label`, `extrema`).
**Why it happens:** Simplistic `IMAGE_TO_IMAGE` I/O pattern mapping in the adapter's `execute` method.
**Consequences:** `TypeError` or `AttributeError` when the adapter tries to call `.ndim` or `.dtype` on a scalar/tuple result.
**Warning signs:** "object has no attribute 'ndim'" errors in logs for measurement functions.
**Prevention:** 
1. Implement more granular I/O pattern detection (e.g., `IMAGE_TO_SCALAR`, `IMAGE_TO_LABELS_AND_COUNT`).
2. Update the `execute` logic to handle non-array returns (e.g., returning a `TableRef` or `ObjectRef` instead of a `BioImageRef`).
**Phase:** **Phase 2 (Feature Expansion)**.

## Moderate Pitfalls

### Pitfall 1: Physical Metadata (Voxel Size) Loss
**What goes wrong:** Scipy operations are unaware of physical units (microns, ms). Parameters like `sigma` are interpreted in pixels, not physical units.
**Why it happens:** Scipy works on raw `numpy.ndarray`, stripping away `xarray` coordinates and `bioio` metadata.
**Consequences:** Incorrect biological interpretations (e.g., applying a "2 micron" blur that is actually 2 pixels on an anisotropic volume).
**Prevention:** 
1. Extract physical spacing from `BioImageRef` metadata.
2. If the agent provides physical units, convert them to pixels based on the metadata before calling Scipy.
3. Preserve and propagate physical metadata to output artifacts.
**Phase:** **Phase 3 (Metadata & Units)**.

### Pitfall 2: Multi-Input Handling Failure
**What goes wrong:** Functions requiring multiple images (e.g., `binary_propagation` with a `mask`, `watershed_ift` with `markers`) are not correctly mapped.
**Why it happens:** The current adapter only loads the first input in `execute` and treats all others as scalar parameters.
**Consequences:** Failure to execute advanced morphological or segmentation workflows.
**Prevention:** 
1. Enhance `_normalize_inputs` to identify all `BioImageRef` inputs in the request.
2. Map MCP input names to Scipy argument names based on function signatures.
**Phase:** **Phase 2 (Feature Expansion)**.

## General System Pitfalls (Legacy)

- **Zombie Processes:** Workers remain alive after server crash. *Mitigation: stdin EOF polling.*
- **The "Memory://" Illusion:** Assuming `mem://` URIs are global across workers. *Mitigation: Track worker ownership.*
- **Serialization Overhead:** Passing large lists in JSON. *Mitigation: Use Artifacts for data.*

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Hardening** | Memory OOM | Implement chunking or memory budget checks. |
| **Hardening** | Dtype Bloat | Force `float32` output for linear filters by default. |
| **Expansion** | Scalar Returns | Handle `label`, `mean`, etc. returning non-arrays. |
| **Expansion** | Multi-input | Map multiple `BioImageRef` to function arguments. |
| **Metadata** | Unit Loss | Convert physical units to pixels using image metadata. |

## Sources
- [SciPy ndimage Tutorial](https://scipy.github.io/devdocs/tutorial/ndimage.html)
- [Image.sc Forum: Scipy Pitfalls](https://forum.image.sc/search?q=scipy%20pitfalls)
- [bioimage-mcp: tools/base/bioimage_mcp_base/entrypoint.py](tools/base/bioimage_mcp_base/entrypoint.py)
