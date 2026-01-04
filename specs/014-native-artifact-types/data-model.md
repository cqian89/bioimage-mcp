# Data Model: Native Artifact Types and Dimension Preservation

**Feature Branch**: `014-native-artifact-types`  
**Date**: 2026-01-04  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

This document defines the entity models, field specifications, and validation rules for the native artifact types feature.

---

## Entity Definitions

### 1. ArtifactRef (Enhanced)

**Location**: `src/bioimage_mcp/artifacts/models.py`

The core artifact reference model is extended with first-class dimension fields.

```python
class ArtifactRef(BaseModel):
    """Typed, file-backed pointer for all inter-tool I/O.
    
    Enhanced with native dimension fields for dimension-preserving workflows.
    """
    
    # Existing fields (unchanged)
    ref_id: str
    type: str  # BioImageRef, LabelImageRef, TableRef, ScalarRef, LogRef, NativeOutputRef, PlotRef
    uri: str
    format: str
    storage_type: str = "file"  # file, zarr-temp, memory
    mime_type: str
    size_bytes: int
    checksums: list[ArtifactChecksum] = Field(default_factory=list)
    created_at: str
    schema_version: str | None = None
    
    # Enhanced metadata with dimension fields
    metadata: dict = Field(default_factory=dict)
    # Expected metadata keys for image artifacts:
    # - shape: list[int]           # [512, 512] or [1, 3, 10, 512, 512]
    # - ndim: int                  # 2, 3, 4, or 5
    # - dims: list[str]            # ["Y", "X"] or ["T", "C", "Z", "Y", "X"]
    # - dtype: str                 # "float32", "uint16", etc.
    # - axes: str                  # Legacy: "YX" or "TCZYX"
    # - physical_pixel_sizes: dict # {"X": 0.5, "Y": 0.5, "Z": 1.0}
    # - channel_names: list[str]   # ["DAPI", "GFP"]
```

#### New Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `shape` | `list[int]` | Yes (images) | Actual array shape, e.g., `[512, 512]` |
| `ndim` | `int` | Yes (images) | Number of dimensions (2, 3, 4, 5) |
| `dims` | `list[str]` | Yes (images) | Dimension labels in order, e.g., `["Y", "X"]` |
| `dtype` | `str` | Yes (images) | NumPy dtype string |
| `physical_pixel_sizes` | `dict[str, float]` | Optional | Pixel sizes in microns keyed by axis |
| `channel_names` | `list[str]` | Optional | Channel identifiers |

#### Validation Rules

```python
@model_validator(mode="after")
def validate_dimension_metadata(self) -> ArtifactRef:
    """Validate dimension metadata consistency."""
    if self.type in ("BioImageRef", "LabelImageRef"):
        meta = self.metadata
        shape = meta.get("shape")
        ndim = meta.get("ndim")
        dims = meta.get("dims")
        
        if shape and ndim and len(shape) != ndim:
            raise ValueError(f"shape length ({len(shape)}) != ndim ({ndim})")
        
        if shape and dims and len(shape) != len(dims):
            raise ValueError(f"shape length ({len(shape)}) != dims length ({len(dims)})")
    
    return self
```

---

### 2. ScalarRef (New)

**Location**: `src/bioimage_mcp/artifacts/models.py`

New artifact type for single-value outputs (thresholds, statistics, etc.).

```python
class ScalarMetadata(BaseModel):
    """Metadata for scalar artifacts."""
    
    value: float | int | bool
    dtype: str  # "float64", "int64", "bool"
    unit: str | None = None
    computed_from: str | None = None  # fn_id that produced this value
    source_ref_id: str | None = None  # Input artifact ref_id


class ScalarRef(ArtifactRef):
    """Reference to a scalar value artifact."""
    
    type: Literal["ScalarRef"] = "ScalarRef"
    format: Literal["json"] = "json"
    mime_type: Literal["application/json"] = "application/json"
```

#### Storage Format

Scalars are stored as JSON files:

```json
{
  "value": 127.5,
  "dtype": "float64",
  "unit": null,
  "computed_from": "skimage.filters.threshold_otsu",
  "source_ref_id": "abc123",
  "created_at": "2026-01-04T12:00:00Z"
}
```

---

### 3. TableRef (Enhanced)

**Location**: `src/bioimage_mcp/artifacts/models.py`

TableRef metadata is enhanced with column type information.

```python
class ColumnMetadata(BaseModel):
    """Metadata for a single table column."""
    
    name: str
    dtype: str  # "int64", "float64", "string", "bool"


class TableMetadata(BaseModel):
    """Metadata for table artifacts."""
    
    columns: list[ColumnMetadata]
    row_count: int
    source_fn_id: str | None = None


# TableRef uses standard ArtifactRef with enhanced metadata:
# metadata = {
#     "columns": [{"name": "label", "dtype": "int64"}, ...],
#     "row_count": 42,
#     "source_fn_id": "skimage.measure.regionprops_table"
# }
```

---

### 4. DimensionRequirement (Existing, Reference)

**Location**: `src/bioimage_mcp/api/schemas.py`

Already exists; documented here for reference.

```python
class DimensionRequirement(BaseModel):
    """Requirements for image dimensions and axes."""
    
    min_ndim: int | None = None
    max_ndim: int | None = None
    expected_axes: list[str] | None = None
    spatial_axes: list[str] = ["Y", "X"]
    squeeze_singleton: bool = True
    slice_strategy: str | None = None
    preprocessing_instructions: list[str] | None = None
```

---

## Native Loading Pattern

The standard pattern for loading images with native dimensions preserved:

```python
def load_native(path: Path) -> tuple[np.ndarray, str, dict]:
    """Load image with native dimensions preserved.
    
    Uses img.reader.data to bypass bioio's 5D normalization.
    Metadata is accessed from the BioImage wrapper for safe defaults.
    
    Returns:
        (data, dims, metadata) where dims is e.g. "ZYX" not "TCZYX"
    """
    from bioio import BioImage
    
    img = BioImage(path)
    reader = img.reader
    
    # Get native data (not normalized to 5D)
    data = reader.data
    if hasattr(data, "compute"):
        data = data.compute()
    
    # Get native dimension labels
    dims = reader.dims.order  # e.g., "ZYX"
    
    # Get metadata from wrapper (safe defaults)
    metadata = {
        "physical_pixel_sizes": img.physical_pixel_sizes,
        "channel_names": img.channel_names,
        "dtype": str(data.dtype),
        "shape": list(data.shape),
        "dims": dims,
        "ndim": data.ndim,
    }
    
    return data, dims, metadata
```

### Conditional Expansion

A helper for conditional 5D expansion:

```python
def expand_if_required(
    data: np.ndarray, 
    dims: str, 
    requirement: DimensionRequirement | None
) -> tuple[np.ndarray, str]:
    """Expand to 5D only if tool manifest requires it."""
    if requirement and requirement.min_ndim == 5 and data.ndim < 5:
        missing = "TCZYX"[:5 - data.ndim]
        for _ in missing:
            data = np.expand_dims(data, axis=0)
        dims = missing + dims
    return data, dims
```

## Loading Pattern Comparison

| Use Case | Pattern | Why |
|----------|---------|-----|
| Native dimension workflows | `img.reader.data` | Preserves 2D, 3D, etc. |
| Legacy 5D-expecting tools | `img.data` | When tool truly needs 5D |
| Metadata access | `img.physical_pixel_sizes`, `img.channel_names` | Safe defaults |
| Dimension labels | `img.reader.dims.order` | Native axis labels |

---

## State Transitions

### Artifact Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Created   │────▶│  In-Memory  │────▶│   Exported  │
│  (mem://)   │     │  (session)  │     │  (file://)  │
└─────────────┘     └─────────────┘     └─────────────┘
      │                    │                   │
      │                    │                   │
      ▼                    ▼                   ▼
   metadata            metadata            metadata
   populated           preserved           preserved
   (native dims        (native dims       (format may
    via reader)        via reader.data)    require 5D)
```

### Dimension States

| State | Description | Example |
|-------|-------------|---------|
| Native 2D | Pure 2D array (Y, X) | After squeeze of singleton dims |
| Native 3D | 3D array (Z, Y, X) or (C, Y, X) | Z-stack or multi-channel |
| Native 4D | 4D array (T, Z, Y, X) or similar | Time-lapse Z-stack |
| Native 5D | Full 5D (T, C, Z, Y, X) | Input microscopy file |
| Exported 5D | 5D for OME-TIFF compatibility | At export boundary only |

---

## Relationships

```
┌───────────────────────────────────────────────────────────────┐
│                        ArtifactRef                            │
│  (base class for all artifact references)                     │
└───────────────────────────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┬───────────────┐
    ▼               ▼               ▼               ▼
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│BioImage │   │ Label   │   │ Table   │   │ Scalar  │
│  Ref    │   │ImageRef │   │  Ref    │   │  Ref    │
└─────────┘   └─────────┘   └─────────┘   └─────────┘
    │               │               │           │
    └───────────────┼───────────────┘           │
                    ▼                           │
           ┌──────────────┐                     │
           │   metadata   │◀────────────────────┘
           │   (shape,    │
           │   ndim, dims)│
           └──────────────┘
```

---

## Interchange Formats

| Artifact Type | Internal Format | Cross-Env Format | Export Formats |
|---------------|-----------------|------------------|----------------|
| BioImageRef | xarray.DataArray | OME-Zarr | OME-TIFF, OME-Zarr, PNG, TIFF, NPY |
| LabelImageRef | numpy.ndarray | OME-Zarr | OME-TIFF, TIFF, NPY |
| TableRef | dict[str, ndarray] | CSV | CSV, TSV |
| ScalarRef | float/int/bool | JSON | JSON |
| PlotRef | matplotlib.Figure | PNG/SVG | PNG, SVG |

---

## Migration Notes

### From Current to Native Model

1. **No schema version bump required** - changes are additive
2. **Existing artifacts remain valid** - missing `ndim`/`dims` fields inferred from `shape`/`axes`
3. **Backward compatibility**:
    ```python
    def get_ndim(metadata: dict) -> int:
        """Get ndim with fallback for legacy artifacts."""
        if "ndim" in metadata:
            return metadata["ndim"]
        if "shape" in metadata:
            return len(metadata["shape"])
        if "axes" in metadata:
            return len(metadata["axes"])
        return 5  # Legacy default
    ```

### Adapter Migration

| Adapter | Current | After Migration |
|---------|---------|-----------------|
| XarrayAdapter | `img.data` (5D) | `img.reader.data` (native) |
| SkimageAdapter | `img.data` (5D) | `img.reader.data` (native) |
| CellposeAdapter | Squeezes after 5D load | Native load, expand only if required |

---

## ARTIFACT_TYPES Registry Update

```python
ARTIFACT_TYPES = {
    "BioImageRef": "Multi-dimensional bioimaging data (input/intermediate)",
    "LabelImageRef": "Instance segmentation labels (integer-valued image)",
    "TableRef": "Measurement/feature tables (CSV format)",
    "ScalarRef": "Single numeric values (thresholds, statistics)",  # NEW
    "LogRef": "Execution log output",
    "NativeOutputRef": "Tool-native output bundle (format is tool-dependent)",
    "PlotRef": "Visualization plots (PNG/SVG)",
}
```
