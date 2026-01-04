# Research: Native Artifact Types and Dimension Preservation

**Feature Branch**: `014-native-artifact-types`  
**Date**: 2026-01-04  
**Status**: Complete

This document resolves all NEEDS CLARIFICATION items from the implementation plan and documents technical decisions with rationale.

---

## 0. Critical Finding: bioio Dimension Normalization

`BioImage.data` ALWAYS normalizes to 5D TCZYX. This is a deliberate design choice in `bioio` to provide a consistent interface, but it conflicts with our goal of preserving native dimensions for non-microscopy or specialized tasks.

- `BioImage.data` ALWAYS normalizes to 5D TCZYX
- `img.reader.data` and `img.reader.xarray_data` preserve native dimensions

### Comparison Table: Data Access

| Access Pattern | Behavior | Preserves Native Dims? |
|----------------|----------|------------------------|
| `BioImage(path).data` | Forces 5D TCZYX | ❌ No |
| `BioImage(path).xarray_data` | Forces 5D TCZYX | ❌ No |
| `img.reader.data` | Native dimensions | ✅ Yes |
| `img.reader.xarray_data` | Native dimensions with labels | ✅ Yes |

### Metadata Comparison

| Property | Wrapper (`img.*`) | Reader (`img.reader.*`) |
|----------|-------------------|------------------------|
| physical_pixel_sizes | ✅ Safe defaults | ✅ Same (pass-through) |
| channel_names | ✅ Synthesizes defaults | ⚠️ May be None |
| dims | Forced TCZYX | Native (e.g., ZYX) |

**Resolution**: Constitution III is amended/clarified to specify that while `BioImage` is the standard loader, tools seeking native dimension preservation MUST use `img.reader.data` or `img.reader.xarray_data`.

---

## 1. OME-Zarr Writer for Native Dimensions

### Question
Which bioio-ome-zarr writer API supports N-dimensional arrays (not forced to 5D)?

### Research Findings

#### bioio_ome_zarr.writers.OMEZarrWriter
The `OMEZarrWriter` from bioio-ome-zarr accepts arrays of any dimensionality and allows explicit axis specification through `axes_names` and `axes_types`.

### Decision: Use bioio_ome_zarr.writers.OMEZarrWriter

**Rationale**:
- Constitution III requires use of `bioio` writers for all artifact I/O to ensure ecosystem compatibility and plugin-based extensibility.
- Using `ome-zarr-py` directly would violate the requirement to avoid custom I/O wrappers that bypass the bioio plugin system.
- `OMEZarrWriter` supports native N-D arrays when provided with correct axis metadata.

### Implementation Pattern

```python
from bioio_ome_zarr.writers import OMEZarrWriter

def save_native_ome_zarr(
    data: np.ndarray,
    path: Path,
    dims: list[str],
    physical_pixel_sizes: dict[str, float] | None = None,
) -> None:
    """Save array as OME-Zarr preserving native dimensionality using bioio."""
    axis_type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
    axes_names = [d.lower() for d in dims]
    axes_types = [axis_type_map.get(d.lower(), "space") for d in dims]
    
    writer = OMEZarrWriter(
        store=str(path),
        level_shapes=[data.shape],
        dtype=data.dtype,
        axes_names=axes_names,
        axes_types=axes_types,
        zarr_format=2,
    )
    writer.write_full_volume(data)
```

---

## 2. Backward Compatibility for 5D Tools

### Question
How should tools that genuinely require 5D input declare this requirement?

### Research Findings

The `DimensionRequirement` model in `src/bioimage_mcp/api/schemas.py` already supports this:

```python
class DimensionRequirement(BaseModel):
    min_ndim: int | None = None
    max_ndim: int | None = None
    expected_axes: list[str] | None = None
    spatial_axes: list[str] = ["Y", "X"]
    squeeze_singleton: bool = True
    preprocessing_instructions: list[str] | None = None
```

### Decision: Use Existing DimensionRequirement Model

Tools requiring 5D input declare this in their manifest:

```yaml
function_overlays:
  base.bioio.export:
    hints:
      inputs:
        image:
          dimension_requirements:
            min_ndim: 5
            max_ndim: 5
            expected_axes: ["T", "C", "Z", "Y", "X"]
            squeeze_singleton: false
            preprocessing_instructions:
              - "This tool requires full 5D TCZYX input"
              - "Use base.xarray.expand_dims if dimensions are missing"
```

**Adapter Behavior Change**:

| Current | New |
|---------|-----|
| Adapter always expands to 5D before saving | Adapter preserves native dimensions |
| `expand_dims` called unconditionally | `expand_dims` called ONLY if output format requires it (OME-TIFF) or tool manifest declares `min_ndim: 5` |

### Implementation Pattern

```python
def should_expand_to_5d(output_format: str, output_hints: DimensionRequirement | None) -> bool:
    """Determine if output should be expanded to 5D."""
    # OME-TIFF writer requires 5D
    if output_format == "OME-TIFF":
        return True
    
    # Tool explicitly requires 5D output
    if output_hints and output_hints.min_ndim == 5:
        return True
    
    # Default: preserve native dimensions
    return False
```

---

## 3. Default Export Format Inference

### Question
What heuristics determine PNG vs OME-TIFF vs OME-Zarr when no format is specified?

### Decision: Inference Based on Data Characteristics

| Condition | Inferred Format | Rationale |
|-----------|-----------------|-----------|
| `ndim == 2` AND `dtype in (uint8, uint16)` AND no rich metadata | **PNG** | Simple 2D grayscale, universal compatibility |
| `ndim == 2` AND `dtype == uint8` AND 3 channels | **PNG** | RGB image |
| `ndim >= 3` OR has physical_pixel_sizes OR has channel_names | **OME-TIFF** | Preserves microscopy metadata |
| `size_bytes > 4GB` | **OME-Zarr** | Chunked format for large files |
| `artifact_type == "LabelImageRef"` | **OME-TIFF** | Labels should be integer-preserving |
| `artifact_type == "TableRef"` | **CSV** | Tabular data |
| Default | **OME-TIFF** | Safe default with metadata preservation |

### Implementation Pattern

```python
def infer_export_format(
    artifact: ArtifactRef,
    data_shape: tuple[int, ...] | None = None,
    data_dtype: str | None = None,
) -> str:
    """Infer the best export format based on artifact characteristics."""
    metadata = artifact.metadata or {}
    ndim = metadata.get("ndim", len(data_shape) if data_shape else 5)
    dtype = metadata.get("dtype", data_dtype or "float32")
    
    # Table artifacts -> CSV
    if artifact.type == "TableRef":
        return "CSV"
    
    # Large files -> OME-Zarr
    if artifact.size_bytes > 4 * 1024**3:
        return "OME-Zarr"
    
    # Simple 2D uint8 -> PNG
    if ndim == 2 and dtype in ("uint8", "uint16"):
        has_rich_metadata = bool(
            metadata.get("physical_pixel_sizes") or 
            metadata.get("channel_names")
        )
        if not has_rich_metadata:
            return "PNG"
    
    # Default: OME-TIFF for microscopy data
    return "OME-TIFF"
```

---

## 4. Memory Artifact Dimension Preservation

### Question
How do mem:// artifacts carry dimension metadata between operations?

### Research Findings

Memory artifacts are stored in `MemoryArtifactStore` (referenced in `src/bioimage_mcp/artifacts/store.py`) with `ArtifactRef` metadata. The current metadata extraction happens at import time via `extract_image_metadata()`.

### Decision: Inline Metadata in ArtifactRef

For memory artifacts, the `ArtifactRef.metadata` dict carries all dimension information directly:

```json
{
  "ref_id": "mem-abc123",
  "uri": "mem://session/base/mem-abc123",
  "type": "BioImageRef",
  "storage_type": "memory",
  "format": "xarray.DataArray",
  "metadata": {
    "shape": [512, 512],
    "ndim": 2,
    "dims": ["Y", "X"],
    "dtype": "float32",
    "physical_pixel_sizes": {"Y": 0.5, "X": 0.5}
  }
}
```

**Key Changes**:
1. Add `ndim` and `dims` as first-class fields (not just extracted from file)
2. Adapters populate metadata when creating memory artifacts
3. Memory artifacts never lose dimension info (no file re-reading)

### Implementation Pattern

```python
def create_memory_artifact_ref(
    data: np.ndarray,
    dims: list[str],
    session_id: str,
    env_id: str,
    artifact_id: str,
    **extra_metadata,
) -> ArtifactRef:
    """Create an ArtifactRef for a memory-backed artifact."""
    return ArtifactRef(
        ref_id=artifact_id,
        uri=f"mem://{session_id}/{env_id}/{artifact_id}",
        type="BioImageRef",
        format="numpy.ndarray",
        storage_type="memory",
        mime_type="application/octet-stream",
        size_bytes=data.nbytes,
        checksums=[],
        created_at=ArtifactRef.now(),
        metadata={
            "shape": list(data.shape),
            "ndim": data.ndim,
            "dims": dims,
            "dtype": str(data.dtype),
            **extra_metadata,
        },
    )
```

---

## 5. Additional Research: ScalarRef Implementation

### Question
How should scalar outputs (e.g., computed threshold values) be represented?

### Decision: New ScalarRef Artifact Type

Add `ScalarRef` as a new artifact type for single-value outputs:

```python
class ScalarRef(ArtifactRef):
    """Reference to a scalar value artifact."""
    
    type: Literal["ScalarRef"] = "ScalarRef"
    format: Literal["json"] = "json"
    
    # Value stored directly in metadata for quick access
    # Full value also persisted in JSON file for provenance
```

**Storage Format**: JSON file containing:
```json
{
  "value": 127.5,
  "dtype": "float64",
  "unit": null,
  "computed_from": "skimage.filters.threshold_otsu",
  "source_ref_id": "abc123"
}
```

**Rationale**:
- Consistent with artifact-only I/O model
- Value available in metadata for quick access (no file read)
- Full provenance preserved in file
- Supports typed values (int, float, bool)

---

## 6. TableRef Column Metadata

### Question
How should table artifacts store column type information?

### Decision: Columns List in Metadata

```json
{
  "ref_id": "table-xyz789",
  "type": "TableRef",
  "format": "CSV",
  "metadata": {
    "columns": [
      {"name": "label", "dtype": "int64"},
      {"name": "area", "dtype": "float64"},
      {"name": "centroid-0", "dtype": "float64"},
      {"name": "centroid-1", "dtype": "float64"}
    ],
    "row_count": 42,
    "source_fn_id": "skimage.measure.regionprops_table"
  }
}
```

**Implementation**: Extract column metadata when saving tables:

```python
def save_table_with_metadata(
    table: dict[str, np.ndarray],
    path: Path,
) -> dict:
    """Save table and return artifact reference with column metadata."""
    columns = [
        {"name": name, "dtype": str(arr.dtype)}
        for name, arr in table.items()
    ]
    
    # Save as CSV
    # ... (existing CSV writing logic)
    
    return {
        "type": "TableRef",
        "format": "CSV",
        "path": str(path),
        "metadata": {
            "columns": columns,
            "row_count": len(next(iter(table.values()))) if table else 0,
        },
    }
```

---

## Summary of Decisions

| Topic | Decision | Alternative Rejected |
|-------|----------|---------------------|
| Image loading | `img.reader.data` (native) | `img.data` (forces 5D) |
| OME-Zarr writer | `bioio_ome_zarr.writers.OMEZarrWriter` | ome-zarr-py (violates Constitution) |
| 5D tool declaration | Manifest `dimension_requirements` | Hardcoded adapter logic |
| Format inference | Heuristic based on ndim/dtype/size | User always specifies format |
| Memory artifact metadata | Inline in ArtifactRef.metadata | Separate metadata store |
| Scalar outputs | ScalarRef artifact type | Embed in workflow record |
| Table columns | columns list in metadata | Column types in file header only |

---

## Dependencies Required

No new dependencies for core server. Tool environments require:

```yaml
# Already present in bioimage-mcp-base
- bioio
- bioio-ome-tiff
- bioio-ome-zarr
- zarr
```

**Note**: `bioio-ome-zarr` is sufficient for both reading and writing N-dimensional OME-Zarr files with explicit axis metadata, ensuring compliance with Constitution III.
