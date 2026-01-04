# Data Model: Bioimage I/O Functions

**Feature**: 015-bioio-functions  
**Date**: 2026-01-04

## Entities

### 1. BioImageRef (Existing)

Reference to a microscopy image artifact. No changes required.

```yaml
BioImageRef:
  ref_id: string          # Unique identifier (UUID)
  type: "BioImageRef"
  uri: string             # file:// or mem:// URI
  format: string          # OME-TIFF, OME-Zarr, CZI, LIF, etc.
  storage_type: string    # "file" or "memory"
  mime_type: string       # e.g., "image/tiff"
  size_bytes: integer
  created_at: string      # ISO 8601 timestamp
  ndim: integer           # Number of dimensions
  dims: array[string]     # Dimension labels ["T", "C", "Z", "Y", "X"]
  physical_pixel_sizes:
    X: number             # microns
    Y: number
    Z: number | null
  metadata:
    shape: array[integer]
    dtype: string
    channel_names: array[string] | null
    source_ref_id: string | null  # Provenance
```

### 2. TableRef (Existing)

Reference to tabular data. Used for metadata inspection output.

```yaml
TableRef:
  ref_id: string
  type: "TableRef"
  uri: string
  format: "CSV"
  storage_type: string
  mime_type: "text/csv"
  size_bytes: integer
  created_at: string
  metadata:
    columns: array[{name: string, dtype: string}]
    row_count: integer
    source_fn_id: string | null
```

### 3. ImageMetadata (New - Response Object)

Structured response from `inspect` and `validate` functions. Not persisted as artifact.

```yaml
ImageMetadata:
  path: string              # Input file path
  format: string            # Detected format
  reader: string            # Reader plugin used
  shape: array[integer]     # e.g., [1, 3, 50, 512, 512]
  dims: string              # e.g., "TCZYX"
  dtype: string             # e.g., "uint16"
  ndim: integer             # Number of dimensions
  physical_pixel_sizes:
    X: number | null
    Y: number | null
    Z: number | null
  channel_names: array[string] | null
  scene_count: integer      # Number of scenes (1 for single images)
  is_valid: boolean         # Validation result
  issues: array[string]     # List of issues found (empty if valid)
```

### 4. SliceSpec (New - Parameter Object)

Specification for dimension slicing.

```yaml
SliceSpec:
  # Map of dimension name to index or range
  # Examples:
  #   {"C": 0}              - Select first channel
  #   {"T": {"start": 0, "stop": 5}}  - First 5 timepoints
  #   {"Z": {"start": 10, "stop": 20, "step": 2}}  - Z-planes 10-20, step 2
  
  type: object
  additionalProperties:
    oneOf:
      - type: integer       # Single index
      - type: object        # Range
        properties:
          start: integer
          stop: integer
          step: integer     # Optional, default 1
```

### 5. FormatList (New - Response Object)

Response from `get_supported_formats`.

```yaml
FormatList:
  formats: array[string]    # e.g., ["OME-TIFF", "CZI", "LIF", "ND2", "PNG"]
  readers:                  # Optional detailed info
    - name: string          # e.g., "bioio-ome-tiff"
      formats: array[string]
      version: string
```

### 6. ValidationReport (New - Response Object)

Response from `validate` function.

```yaml
ValidationReport:
  path: string
  is_valid: boolean
  reader_selected: string   # e.g., "bioio-ome-tiff"
  format_detected: string   # e.g., "OME-TIFF"
  issues: array[ValidationIssue]
  metadata_summary:
    shape: array[integer]
    dims: string
    dtype: string

ValidationIssue:
  severity: "error" | "warning"
  code: string              # e.g., "MISSING_PIXEL_SIZE"
  message: string
  field: string | null      # Affected metadata field
```

## State Transitions

### Image Loading State

```
[File Path] --load--> [BioImageRef (file-backed)]
[BioImageRef] --slice--> [BioImageRef (new artifact, file-backed)]
[BioImageRef] --export--> [BioImageRef (new format)]
```

### Artifact Lifecycle

1. **load**: Creates new BioImageRef from file path
2. **inspect**: Reads metadata, returns JSON (no new artifact)
3. **slice**: Creates new BioImageRef with subset data
4. **validate**: Reads metadata, returns JSON (no new artifact)
5. **get_supported_formats**: Returns JSON (no artifacts)
6. **export**: Creates new BioImageRef in requested format

## Validation Rules

| Field | Rule |
|-------|------|
| `path` (load/validate) | Must exist and be in `filesystem.allowed_read` |
| `path` (export) | Directory must be in `filesystem.allowed_write` |
| `slices` keys | Must be valid dimension names (T, C, Z, Y, X) |
| `slices` indices | Must be within array bounds |
| `format` (export) | Must be one of: OME-TIFF, OME-Zarr, PNG, CSV, NPY |
