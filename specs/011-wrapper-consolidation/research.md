# Research: Wrapper Consolidation (Spec 011)

This document details the research findings and architectural decisions for consolidating wrapper tools into the core server and xarray-based adapters.

## 1. Current Wrapper Inventory

**Decision**: 16 wrapper tools identified for deletion.
**Rationale**: All can be replaced by xarray methods or `apply_ufunc` patterns.
**Findings**:
- **I/O wrappers (2)**: `convert_to_ome_zarr`, `export_ome_tiff` → Replaced by Server-side I/O bridge.
- **Axis wrappers (5)**: `relabel_axes`, `squeeze`, `expand_dims`, `moveaxis`, `swap_axes` → Replaced by xarray adapter.
- **Transform wrappers (6)**: `crop`, `normalize_intensity`, projections, `flip`, `pad` → Replaced by xarray adapter.
- **Phasor wrappers (2)**: Keep as direct `phasorpy` calls with `input_mode: xarray`.
- **Denoise wrapper (1)**: Replace with `apply_ufunc` pattern for skimage filters.

## 2. Tool Execution Architecture: Persistent Workers

**Decision**: Shift from transient subprocesses to **Persistent Worker processes** per session/environment.
**Rationale**: The Bioimage-MCP Constitution requires isolated execution; persistent workers satisfy this while allowing in-memory data persistence across sequential tool calls in the same environment.
**Key Insight**: Lazily starting a worker process and keeping it alive allows the server to reference in-memory objects via `mem://` URIs, eliminating redundant disk I/O for multi-step workflows within a single environment.

## 3. xarray Integration Pattern

**Decision**: Use `BioImage.xarray_data` for dimension-aware processing.
**Rationale**: xarray preserves dimension names (T, C, Z, Y, X) through operations, reducing errors compared to raw numpy arrays.
**Implementation Strategy**:
- Add `input_mode: xarray` field to the tool manifest schema.
- Runtime resolves `BioImageRef` to `BioImage.xarray_data` before passing it to the tool.
- The tool operates on labeled dimensions directly.
- Output is written via `bioio.writers.OmeTiffWriter` (or Zarr writer) with preserved `dim_order`.

## 4. apply_ufunc Pattern for numpy Libraries

**Decision**: Use declarative `apply_ufunc` configuration in the manifest for libraries like `scikit-image` and `scipy`.
**Rationale**: These libraries do not support xarray natively. `xr.apply_ufunc` provides a bridge that handles dimension mapping.
**Example Configuration**:
```yaml
apply_ufunc:
  input_core_dims: [["Y", "X"]]
  output_core_dims: [["Y", "X"]]
  vectorize: true
  dask: parallelized
```

## 5. xarray Adapter Allowlist

**Decision**: Expose a curated subset of `xarray.DataArray` methods through a dedicated adapter tool.
**Rationale**: Prevent unsafe operations (e.g., `.values`, `.load()`) that force immediate memory materialization and bypass dask's lazy loading.

**Allowed methods (Priority 1)**:
- `rename({'old': 'new'})` - Replaces `relabel_axes`
- `squeeze()` - Replaces `squeeze`
- `expand_dims('dim', axis=n)` - Replaces `expand_dims`
- `transpose(*order)` - Replaces `moveaxis`, `swap_axes`
- `isel(Y=slice(a,b))` - Replaces `crop`, `flip`
- `pad({'Y': (before, after)})` - Replaces `pad`
- `sum(dim='axis')` - Replaces `project_sum`
- `max(dim='axis')` - Replaces `project_max`

**Forbidden methods**:
- `.values`, `.to_numpy()` - Force full materialization.
- `.load()`, `.compute()` - Force Dask execution (managed by runtime).

## 6. Decentralized Handoff & Materialization

**Decision**: The core server coordinates cross-env negotiation where the source environment materializes data for the target.
**Rationale**: Simplifies workflows by removing the need for manual format conversion calls while maintaining strict environment isolation.
**Implementation**:
- Target tool manifest declares required input formats (e.g., `required_format: ome-tiff`).
- Server checks the actual artifact (file format or `mem://`).
- If a mismatch or cross-env boundary occurs: The server instructs the source environment to export/materialize to a compatible file-backed format (defaulting to OME-TIFF) via `bioio`.
- The target environment then imports the file-backed artifact.
- Log the handoff/materialization step in the workflow provenance for reproducibility.

## 7. Memory Management & Lifecycle

**Key Finding**: `mem://` artifacts are ephemeral and tied to the worker process lifecycle.
**Impact**: If a worker process crashes or the server restarts, all `mem://` references for that environment are invalidated.
**Resilience**: The system relies on OS-level OOM handling. On worker crash, the server restarts the worker and informs the agent/user of the reference loss.
**Implication**: Any data required for long-term persistence or cross-session use MUST be explicitly exported to a file-backed artifact via `base.bioio.export`.
