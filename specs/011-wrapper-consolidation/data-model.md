# Data Model: Wrapper Consolidation (Spec 011)

This document defines the data models and entities for the Wrapper Consolidation specification. This spec introduces unified I/O bridging, a generic xarray adapter for axis operations, and extended tool manifests to support `xarray.apply_ufunc`.

## Entities

### 1. FunctionManifest (Extended)

The existing manifest schema is extended with new fields to support automated data handling and `apply_ufunc` dispatch. Schema defined in `src/bioimage_mcp/registry/manifest_schema.py`.

```yaml
functions:
  - fn_id: string                    # e.g., "base.xarray.rename"
    tool_id: string                  # Tool pack identifier
    name: string                     # Human-readable name
    description: string              # Function description
    
    # NEW: Input mode configuration
    input_mode: "numpy" | "xarray" | "path"  # Default: "numpy"
    
    # NEW: apply_ufunc configuration for numpy-only libraries
    apply_ufunc:
      input_core_dims: [[string]]    # Core dims per input (e.g., [["Y", "X"]])
      output_core_dims: [[string]]   # Core dims per output
      vectorize: boolean             # Loop over non-core dims
      dask: "forbidden" | "allowed" | "parallelized"
      output_dtypes: [string]        # Optional dtype hints
    
    inputs: [PortDefinition]
    outputs: [PortDefinition]
    params_schema: JSONSchema
```

### 2. Managed Memory Artifacts

Memory-backed artifacts use the `mem://` URI scheme and are ephemeral across server restarts.

```python
class ArtifactRef(BaseModel):
    ref_id: str
    type: str                        # BioImageRef, LabelImageRef, etc.
    uri: str                         # mem://<session_id>/<env_id>/<artifact_id>
    format: str                      # "memory" or negotiated interchange format
    storage_type: str = "memory"     # "file" or "memory"
    # ... other fields ...
    metadata: dict                   # dims, shape, dtype (minimal for mem://)
```

### 3. Persistent Worker State

Persistent workers maintain state for a session.

```python
class WorkerSession(BaseModel):
    session_id: str
    env_id: str
    process_id: int
    started_at: datetime
    active_artifacts: list[str]      # List of ref_ids residing in this worker's memory
```

### 4. IOBridge Cross-Env Handoff

Provenance record of an automatic format conversion or materialization performed by the `IOBridge`.

```python
class IOBridgeHandoff(BaseModel):
    source_ref_id: str               # Original artifact (likely mem://)
    target_ref_id: str               # Materialized artifact (file://)
    source_env: str
    target_env: str
    negotiated_format: str           # e.g., "OME-TIFF"
    timestamp: datetime
```

### 5. MethodAllowlist

Configuration for allowed xarray methods in the adapter.

```python
XARRAY_ALLOWLIST = {
    "rename": {"signature": "(mapping: dict[str, str])", "category": "axis"},
    "squeeze": {"signature": "(dim: str | None = None)", "category": "axis"},
    "expand_dims": {"signature": "(dim: str | dict, axis: int | None = None)", "category": "axis"},
    "transpose": {"signature": "(*dims: str)", "category": "axis"},
    "isel": {"signature": "(**indexers: int | slice)", "category": "selection"},
    "pad": {"signature": "(pad_width: dict[str, tuple[int, int]])", "category": "transform"},
    "sum": {"signature": "(dim: str | list[str] | None = None)", "category": "reduction"},
    "max": {"signature": "(dim: str | list[str] | None = None)", "category": "reduction"},
    "mean": {"signature": "(dim: str | list[str] | None = None)", "category": "reduction"},
}

XARRAY_DENYLIST = {"values", "to_numpy", "load", "compute", "data"}
```

### 6. ArtifactRef (Reference Only)

Existing model, provided here for context. No changes are introduced to this core model in Spec 011.

```python
class ArtifactRef(BaseModel):
    ref_id: str
    type: str                        # BioImageRef, LabelImageRef, etc.
    uri: str
    format: str                      # OME-TIFF, OME-Zarr, etc.
    storage_type: str = "file"       # "file" or "zarr-temp"
    mime_type: str
    size_bytes: int
    checksums: list[ArtifactChecksum]
    created_at: str
    metadata: dict                   # axes, shape, physical_pixel_sizes
    schema_version: str | None
```

## Relationships

- **FunctionManifest** --declares--> `input_mode`, `apply_ufunc`, `io_requirements`
- **XArrayAdapterRequest** --references--> **ArtifactRef** (by `ref_id`)
- **XArrayAdapterResponse** --produces--> **ArtifactRef**
- **IOBridgeConversion** --links--> **ArtifactRef** (source) --> **ArtifactRef** (target)
- **WorkflowRecord** --contains--> **IOBridgeConversion[]** (in provenance logs)

## Validation Rules

1.  **input_mode**: Must be "numpy", "xarray", or "path". Defaults to "numpy" if not specified.
2.  **apply_ufunc**: Only valid and processed when `input_mode` is "xarray".
3.  **XArrayMethod**: Must be present in `XARRAY_ALLOWLIST`.
4.  **XArrayMethod**: Must NOT be in `XARRAY_DENYLIST`.
5.  **output_format**: Must be a format supported by the installed `bioio` writers.
