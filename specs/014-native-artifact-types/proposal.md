# Proposal: Spec 014: Native Artifact Types and Dimension Preservation

**Branch**: `014-native-artifact-types` | **Date**: 2026-01-04 | **Spec**: `specs/014-native-artifact-types/proposal.md`

## Summary

This proposal addresses a fundamental limitation in the current bioimage-mcp architecture where all multi-dimensional outputs are forced into a 5D (TCZYX) OME-TIFF representation. This "everything-is-5D" constraint nullifies dimension-reducing operations (like `squeeze`, `max_projection`, or `slice`) and causes failures in downstream tools that expect 2D or 3D inputs (e.g., `regionprops`). We propose a shift to a "Native Artifact" model where artifacts preserve their native dimensionality, data types, and metadata both in-memory and during cross-environment interchange.

## Technical Context

- **Language/Version**: Python 3.13
- **Primary Dependencies**: `zarr`, `numpy`, `xarray`, `pandas`, `bioio`
- **Current State**: Adapters (e.g., `XarrayAdapter`) explicitly re-expand all outputs to 5D TCZYX before saving or returning.
- **Target State**: Artifacts retain their natural dimensionality (e.g., 2D for a single slice) and type (e.g., `pandas.DataFrame` for tables).

## Constitution Check

- **Principle III: Artifact References Only**: This proposal reinforces Principle III by making artifact references more descriptive (richer metadata) and using OME-Zarr for flexible intermediate storage as recommended.
- **Principle IV: Reproducibility & Provenance**: Preserving native types and dimensions ensures that tool outputs are exactly what the underlying library produced, improving the fidelity of recorded workflows.
- **Principle VI: Test-Driven Development**: Implementation will start with contract tests for the new `ArtifactRef` fields and integration tests for dimension-reducing pipelines.

## Problem Statement

The core issue is NOT that specific tools (like `regionprops`) cannot handle 5D data, but that the **system re-expands all outputs back to 5D**, which nullifies dimension-reducing operations.

Evidence from `src/bioimage_mcp/registry/dynamic/adapters/xarray.py` (Lines 119-124):

```python
# Ensure result is 5D for OmeTiffWriter (Standard: TCZYX)
standard_order = "TCZYX"
for d in standard_order:
    if d not in result_da.dims:
        result_da = result_da.expand_dims(d)
```

### Impact:
1.  **Broken Pipelines**: A user calls `base.xarray.squeeze` to get a 2D image. The adapter correctly squeezes it, but then immediately expands it back to `(1, 1, 1, Y, X)` to satisfy the OME-TIFF writer.
2.  **Tool Failures**: When this 5D image is passed to `skimage.measure.regionprops_table`, the tool fails because scikit-image expects a 2D or 3D array, and even singleton dimensions can trigger errors or incorrect behavior in geometry-sensitive functions.
3.  **Semantic Loss**: Forcing a threshold value (scalar) or a table into a "BioImage" container is counter-intuitive and loses the semantic structure of the data.

## Proposed Solution

### Part 1: Native In-Memory Artifacts

In-memory artifacts (used within a session or between tools in the same environment) must retain the native Python object returned by the function.

The `ArtifactRef` model will be updated to include rich metadata that reflects the actual state of the data:

```json
{
  "ref_id": "mem-abc123",
  "uri": "mem://session/base/mem-abc123",
  "type": "BioImageRef",
  "data_type": "numpy.ndarray",
  "metadata": {
    "shape": [512, 512],
    "dtype": "float32",
    "ndim": 2,
    "dims": ["Y", "X"],
    "physical_pixel_sizes": [1.0, 1.0],
    "channel_names": ["DAPI"]
  }
}
```

#### Metadata Preservation
For types that don't natively support microscopy metadata (like raw `numpy.ndarray`), we will:
1.  Store metadata in the `ArtifactRef.metadata` dictionary.
2.  Use a lightweight internal wrapper if needed within the tool execution environment to carry both data and metadata (e.g., an `xarray.DataArray` with `.attrs`).

### Part 2: Cross-Environment Export Strategy

When an artifact moves between different environment boundaries (e.g., `base` environment to `cellpose` environment), it must be serialized. 

**Decision: Option B - Standard Export Format + Receiver Adapter Conversion**

We will define standard "Interchange Formats" based on the artifact's data type:

| Data Type | Interchange Format | Why? |
| :--- | :--- | :--- |
| **N-D Arrays** | **OME-Zarr** | Supports arbitrary dimensions (2D, 3D, 5D, etc.), preserves metadata, and is chunk-efficient. |
| **Tables** | **CSV** | Human-readable, universal support, sufficient for typical measurement tables. |
| **Plots** | **PNG/SVG** | Standard visualization formats. |

#### External Export Formats

For user-facing export (via `base.bioio.export` or similar), the user/agent should be able to choose from:

| Category | Supported Formats |
| :--- | :--- |
| **Microscopy** | OME-TIFF, OME-Zarr |
| **Standard Images** | TIFF, PNG, JPEG |
| **Raw Arrays** | NumPy (.npy), Zarr |
| **Tables** | CSV, TSV |

The export function should accept a `format` parameter. If not specified, the system should infer a sensible default based on the data type and dimensionality (e.g., PNG for 2D uint8, OME-TIFF for 5D with metadata).

**Rationale for Option B:**
- **Simplicity**: No complex negotiation between sender and receiver.
- **Predictability**: The sender always exports to the most robust format for that data type.
- **Constitution Alignment**: Principle III explicitly mentions OME-Zarr for intermediate storage.
- **Performance**: Zarr is optimized for fast I/O compared to OME-TIFF for large arrays.

The receiving environment's adapter is responsible for loading the standard format and converting it into the specific structure the tool function requires (e.g., squeezing if the tool only supports 2D).

## Key Technical Decisions

1.  **Deprecate 5D-Forced OME-TIFF for Intermediates**: OME-TIFF will remain supported for final export and external input, but internal pipelines will default to OME-Zarr to preserve native dimensionality.
2.  **Explicit `ndim` and `shape` in `ArtifactRef`**: These fields become first-class citizens in the artifact metadata to allow agents to reason about dimensionality without downloading the data.
3.  **Adapter Responsibility Shift**: Adapters must stop calling `expand_dims` by default. They should only expand if the *output format* strictly requires it (like OME-TIFF) and even then, only if the user hasn't explicitly requested a different format.

## Implementation Phases

### Phase 1: Core Model & Storage
- Update `ArtifactRef` and `ArtifactStore` to support native metadata fields.
- Implement OME-Zarr writer for cross-env interchange.
- Extend export functionality to support multiple output formats (PNG, JPEG, TIFF, OME-TIFF, OME-Zarr, npy).

### Phase 2: Adapter Refactoring
- Remove 5D-forcing logic from `XarrayAdapter` and `SkimageAdapter`.
- Update loaders to handle Zarr interchange format.

### Phase 3: Agent & Discovery
- Update tool manifests to include "Dimension Hints" (e.g., "This tool expects 2D inputs").
- Enhance MCP `describe_tool` output with these hints.

## Success Criteria

1.  A pipeline of `squeeze` -> `threshold` -> `regionprops_table` executes successfully without manual dimension manipulation.
2.  `ArtifactRef` objects correctly report `ndim: 2` for 2D outputs.
3.  Table outputs from `regionprops` are stored as CSV files with column type metadata in the artifact reference.

## Risks and Mitigations

| Risk | Mitigation |
| :--- | :--- |
| **Compatibility** | Existing tools expecting 5D might break. | Adapters for those specific tools will include a "Normalization Layer" to expand to 5D if the tool's manifest indicates it. |
| **Complexity** | Managing multiple file formats (Zarr, CSV, TIFF). | Centralize I/O in the `ArtifactStore` and use `bioio` which abstracts much of this complexity. |

## Open Questions

1.  Should we allow users to override the default interchange format?
2.  How do we handle "Mixed" metadata (e.g., a numpy array that originated from a CZI file but lost its metadata during a scikit-image operation)?
