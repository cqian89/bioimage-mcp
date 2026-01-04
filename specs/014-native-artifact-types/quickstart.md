# Quickstart: Native Artifact Types and Dimension Preservation

**Feature Branch**: `014-native-artifact-types`  
**Date**: 2026-01-04

This guide demonstrates how to use the native dimension preservation features after implementation.

---

## Overview

The native artifact model preserves the actual dimensionality of image data throughout pipelines, eliminating the previous 5D-forcing behavior that broke dimension-reducing operations.

**Key Changes**:
- Artifacts retain their native dimensions (2D, 3D, 4D) instead of being forced to 5D
- Rich metadata (`ndim`, `dims`, `shape`) available without loading data
- Multi-format export with intelligent format inference
- New `ScalarRef` type for threshold/statistic outputs

---

## Example 1: Dimension-Reducing Pipeline

### Before (Broken)
```text
5D Image → squeeze → [internal 5D again] → threshold → FAILS (expects 2D)
```

### After (Working)
```text
5D Image → squeeze → [2D artifact] → threshold → [2D artifact] → regionprops → Table
```

### MCP Tool Calls

```python
# 1. Import a 5D image (T=1, C=1, Z=1, Y=512, X=512)
result = await run_function(
    fn_id="base.bioio.import",
    inputs={"path": "/data/sample.ome.tiff"},
)
image_ref = result["outputs"]["output"]
# image_ref.metadata = {"shape": [1, 1, 1, 512, 512], "ndim": 5, "dims": ["T", "C", "Z", "Y", "X"]}

# 2. Squeeze to 2D
result = await run_function(
    fn_id="base.xarray.squeeze",
    inputs={"image": image_ref},
)
squeezed_ref = result["outputs"]["output"]
# squeezed_ref.metadata = {"shape": [512, 512], "ndim": 2, "dims": ["Y", "X"]}

# 3. Threshold (works because input is 2D!)
result = await run_function(
    fn_id="skimage.filters.threshold_otsu",
    inputs={"image": squeezed_ref},
)
threshold_ref = result["outputs"]["output"]  # ScalarRef with value

# 4. Apply threshold to create binary mask
result = await run_function(
    fn_id="base.numpy.greater",
    inputs={"image": squeezed_ref},
    params={"value": threshold_ref["metadata"]["value"]},
)
mask_ref = result["outputs"]["output"]
# mask_ref.metadata = {"shape": [512, 512], "ndim": 2, "dims": ["Y", "X"], "dtype": "bool"}

# 5. Region property extraction (works because input is 2D!)
result = await run_function(
    fn_id="skimage.measure.regionprops_table",
    inputs={"labels": mask_ref},
    params={"properties": ["label", "area", "centroid"]},
)
table_ref = result["outputs"]["output"]
# table_ref.type = "TableRef"
# table_ref.metadata = {"columns": [...], "row_count": 42}
```

---

## Example 2: Inspecting Artifact Metadata

Agents can inspect artifact dimensions without downloading data:

```python
# Get artifact details
artifact = await get_artifact(ref_id="abc123")

# Access dimension info from metadata
print(f"Dimensions: {artifact['metadata']['ndim']}D")
print(f"Shape: {artifact['metadata']['shape']}")
print(f"Axes: {artifact['metadata']['dims']}")
print(f"Data type: {artifact['metadata']['dtype']}")

# Output:
# Dimensions: 2D
# Shape: [512, 512]
# Axes: ['Y', 'X']
# Data type: float32
```

---

## Example 3: Multi-Format Export

Export artifacts to various formats based on needs:

```python
# Export 2D image as PNG (simple sharing)
await run_function(
    fn_id="base.bioio.export",
    inputs={"image": squeezed_ref},
    params={"format": "PNG", "path": "/output/result.png"},
)

# Export 5D image as OME-TIFF (preserves metadata)
await run_function(
    fn_id="base.bioio.export",
    inputs={"image": original_5d_ref},
    params={"format": "OME-TIFF", "path": "/output/result.ome.tiff"},
)

# Export large image as OME-Zarr (chunked, cloud-ready)
await run_function(
    fn_id="base.bioio.export",
    inputs={"image": large_image_ref},
    params={"format": "OME-Zarr", "path": "/output/result.ome.zarr"},
)

# Let system infer best format
await run_function(
    fn_id="base.bioio.export",
    inputs={"image": some_ref},
    # No format specified - system will infer based on ndim, dtype, size
)
```

---

## Example 4: Tool Dimension Hints

Query function requirements to understand expected inputs:

```python
# Describe a function to see dimension requirements
func_info = await describe_function(fn_id="skimage.filters.threshold_otsu")

# Output:
{
  "fn_id": "skimage.filters.threshold_otsu",
  "name": "Otsu Thresholding",
  "hints": {
    "inputs": {
      "image": {
        "type": "BioImageRef",
        "dimension_requirements": {
          "min_ndim": 2,
          "max_ndim": 2,
          "expected_axes": ["Y", "X"],
          "squeeze_singleton": true,
          "preprocessing_instructions": [
            "Squeeze singleton T, C, Z dimensions first",
            "If multiple channels, select one channel",
            "Use base.xarray.squeeze for preprocessing"
          ]
        }
      }
    }
  }
}
```

---

## Supported Export Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| OME-TIFF | `.ome.tiff` | Microscopy data with metadata |
| OME-Zarr | `.ome.zarr` | Large data, cloud storage |
| PNG | `.png` | Simple 2D images (uint8/uint16) |
| TIFF | `.tiff` | Standard image format |
| NPY | `.npy` | Raw NumPy arrays |
| CSV | `.csv` | Table data |
| JSON | `.json` | Scalar values, records |

---

## Format Inference Rules

When no format is specified, the system infers:

| Data Characteristics | Inferred Format |
|---------------------|-----------------|
| 2D + uint8/uint16 + no rich metadata | PNG |
| 2D + uint8 + 3 values in last dim | PNG (RGB) |
| Any dimensionality with physical_pixel_sizes | OME-TIFF |
| Size > 4GB | OME-Zarr |
| TableRef | CSV |
| ScalarRef | JSON |
| Default | OME-TIFF |

---

## New Artifact Types

### ScalarRef

For single-value outputs (thresholds, statistics):

```python
# After threshold computation
scalar_ref = {
    "ref_id": "scalar123",
    "type": "ScalarRef",
    "format": "json",
    "metadata": {
        "value": 127.5,
        "dtype": "float64",
        "computed_from": "skimage.filters.threshold_otsu"
    }
}

# Access the value directly
threshold_value = scalar_ref["metadata"]["value"]
```

### Enhanced TableRef

Tables now include column type metadata:

```python
table_ref = {
    "ref_id": "table456",
    "type": "TableRef",
    "format": "CSV",
    "metadata": {
        "columns": [
            {"name": "label", "dtype": "int64"},
            {"name": "area", "dtype": "float64"},
            {"name": "centroid-0", "dtype": "float64"},
            {"name": "centroid-1", "dtype": "float64"}
        ],
        "row_count": 42
    }
}
```

---

## Migration from 5D-Forced Workflows

### Existing Workflows

Existing recorded workflows continue to work. The system maintains backward compatibility:

- Missing `ndim`/`dims` fields are inferred from `shape`/`axes`
- Tools with explicit 5D requirements get expanded inputs automatically
- Export to OME-TIFF still produces 5D output (format requirement)

### Updating Manifests

Add dimension requirements to custom tools:

```yaml
# In manifest.yaml
function_overlays:
  my_custom.tool.process:
    hints:
      inputs:
        image:
          dimension_requirements:
            min_ndim: 2
            max_ndim: 3
            expected_axes: ["Y", "X"]
            preprocessing_instructions:
              - "Squeeze singleton dimensions"
```

---

## Troubleshooting

### "Tool expects 2D but received 5D"

Use `base.xarray.squeeze` to remove singleton dimensions:

```python
# Before calling 2D-only tool
squeezed = await run_function(
    fn_id="base.xarray.squeeze",
    inputs={"image": image_5d},
)
```

### "Cannot export 5D as PNG"

PNG only supports 2D. Either squeeze first or use a different format:

```python
# Option 1: Squeeze then export
squeezed = await run_function(fn_id="base.xarray.squeeze", inputs={"image": img})
await run_function(fn_id="base.bioio.export", inputs={"image": squeezed}, params={"format": "PNG"})

# Option 2: Use OME-TIFF
await run_function(fn_id="base.bioio.export", inputs={"image": img}, params={"format": "OME-TIFF"})
```

### "Missing dimension metadata"

For legacy artifacts, dimension info is inferred. To ensure full metadata:

```python
# Re-import with metadata extraction
result = await run_function(
    fn_id="base.bioio.import",
    inputs={"path": artifact["uri"]},
)
```