# Image Handling Guide

This document provides guidance for tool developers on how to handle image data within the `bioimage-mcp` framework. To ensure consistency and reproducibility across different tools and environments, `bioimage-mcp` standardizes on specific libraries and formats.

## Overview

`bioimage-mcp` standardizes on [bioio](https://github.com/bioio-dev/bioio) for all image I/O operations. `bioio` provides a unified interface for reading various microscopy formats and consistently returns data in a 5D **TCZYX** (Time, Channel, Z-stack, Y, X) format.

All tool functions that accept or return image data MUST use `BioImageRef` or `LabelImageRef` artifact types, which are backed by files compatible with `bioio`.

## Standard Loading Pattern

The recommended way to load images in tool functions is to use the `BioImage` class from the `bioio` package.

### 5D Normalization (Legacy/Compatibility)
By default, `img.data` returns a 5D **TCZYX** array. This is useful for tools that expect a fixed input structure.

```python
from bioio import BioImage
img = BioImage(path)
data = img.data  # Always 5D TCZYX
```

### Native Dimension Preservation (Recommended)
For modern tools that support varying dimensionality (2D, 3D, etc.), use `img.reader.data` to access the data in its native dimensions. This avoids unnecessary 5D expansion and allows tools to operate on the actual data shape.

```python
from bioio import BioImage
img = BioImage(path)
data = img.reader.data  # Native dimensions (e.g., YX or ZYX)
dims = img.reader.dims.order  # e.g., "YX"
```

## Dimension Preservation Patterns

### When to use Native Dimensions
- **Dimension-reducing ops**: Squeeze, projection, or slicing should always return native-dimension artifacts.
- **2D-only tools**: If a tool only supports 2D, it should accept native 2D artifacts directly.
- **Z-stack/3D tools**: If a tool supports 3D, it should accept native 3D artifacts.

### `expand_if_required` Helper
When creating adapters or tools that might need to interface with legacy 5D tools, use the `expand_if_required` logic. This is typically handled by the adapter layer (e.g., `XarrayAdapter` or `SkimageAdapter`).

```python
def expand_if_required(
    data: np.ndarray, dims: str, requirement: DimensionRequirement | None
) -> tuple[np.ndarray, str]:
    """Expand to 5D only if tool manifest requires it."""
    if requirement and requirement.min_ndim == 5 and data.ndim < 5:
        missing = "TCZYX"[: 5 - data.ndim]
        for _ in missing:
            data = np.expand_dims(data, axis=0)
        dims = missing + dims
    return data, dims
```

1.  **Check Manifest**: Does the function metadata specify `dimension_requirements`?
2.  **Expand if needed**: If the tool requires 5D (e.g., `min_ndim: 5`) but the artifact is 2D, expand it.
3.  **Preserve otherwise**: If no 5D requirement exists, pass the native array.

### Squeezing Singleton Dimensions
To convert a 5D image to 2D/3D for processing, use `base.xarray.squeeze`. The resulting artifact will preserve these reduced dimensions in its metadata.

## InterchangeFormat Values

When defining tool manifests or creating artifact references, use the following canonical format values to describe image artifacts:

| Format Value | Description |
| :--- | :--- |
| `OME-TIFF` | **Default** for small to medium-sized images. Highly compatible and contains standard metadata. |
| `OME-Zarr` | **Preferred** for large, multi-scale, or chunked datasets. Ideal for cloud storage and interactive visualization. |

Tools SHOULD be capable of reading both formats via `bioio`, but may choose one as their primary output format based on the data characteristics.

## Manifest Port.format Rules

The `manifest.yaml` file defines the input and output ports for each function. The `format` field in these definitions must follow these rules:

1.  **For `BioImageRef` and `LabelImageRef`**:
    *   The `format` field MUST be either `OME-TIFF` or `OME-Zarr`.
    *   Example:
        ```yaml
        outputs:
          - name: mask
            artifact_type: LabelImageRef
            format: OME-TIFF
            summary: Segmentation mask
        ```

2.  **For `NativeOutputRef` and other artifact types**:
    *   The `format` field can use any descriptive string appropriate for the data (e.g., `JSON`, `CSV`, `PNG` for thumbnails, `NumPy`).
    *   Example:
        ```yaml
        outputs:
          - name: stats
            artifact_type: TableRef
            format: CSV
            summary: Object measurements
        ```

## Metadata Access

One of the primary advantages of using `bioio` is easy access to physical metadata, which is crucial for many bioimage analysis tasks (e.g., calculating volumes, scaling filters).

```python
img = BioImage(path)

# Physical pixel sizes (Z, Y, X) in micrometers (if available)
pixel_sizes = img.physical_pixel_sizes  

# List of channel names
channels = img.channel_names

# Dimensions as a dictionary or named tuple
dims = img.dims  # e.g., Dims(T=1, C=3, Z=1, Y=1024, X=1024)

# Coordinate system and metadata
metadata = img.metadata
```

## Migration Guide for Tool Authors

If you are migrating an existing tool or wrapping a library that uses other I/O methods (like `tifffile` or `scikit-image`), follow these steps:

### 1. Replace legacy I/O
Replace `tifffile.imread(path)` or `skimage.io.imread(path)` with `BioImage(path).data`. 

### 2. Handle 5D Normalization
Since `BioImage.data` always returns 5D TCZYX, you must ensure your implementation handles these extra dimensions correctly.
*   **Squeeze**: If your tool only works on 2D images, use `np.squeeze(data)` or specific slicing like `data[0, 0, 0, :, :]`.
*   **Expand**: If you are creating a result to be saved as an artifact, ensure it is wrapped back into a 5D array or use a helper that handles the OME-TIFF/Zarr writing with proper dimensions.

### 3. Update manifest.yaml
Ensure your `manifest.yaml` uses the canonical `OME-TIFF` or `OME-Zarr` format values for all image-related ports.

### 4. Use physical units
Instead of assuming pixel units, check `img.physical_pixel_sizes` and use them in your calculations to ensure your tool works correctly across different datasets.

## Anti-Patterns to Avoid

### ❌ Don't Create I/O Wrapper Functions

BioImage auto-detects formats correctly when plugins are installed. Custom wrappers that force specific readers cause compatibility issues:

```python
# BAD - Don't do this
def get_bioimage(path, format_hint=None):
    if format_hint == "OME-TIFF":
        return BioImage(path, reader=bioio_ome_tiff.Reader)
    return BioImage(path)

# GOOD - Use BioImage directly
img = BioImage(path)  # Auto-detects format
```

### ❌ Don't Use Raw Zarr for OME-Zarr Output

Raw zarr stores lack OME-Zarr multiscales metadata and aren't readable by compliant tools:

```python
# BAD - Creates invalid OME-Zarr
import zarr
root = zarr.open_group(out_dir, mode="w")
root.create_array("0", data=data)

# GOOD - Use bioio-ome-zarr writer
from bioio_ome_zarr.writers import OMEZarrWriter
writer = OMEZarrWriter(store=out_dir, level_shapes=[data.shape], dtype=data.dtype)
writer.write_full_volume(data)
```

### ❌ Don't Use tifffile or skimage.io for Artifacts

These libraries don't preserve OME metadata or ensure consistent 5D normalization:

```python
# BAD - Loses metadata, no dimension normalization
import tifffile
data = tifffile.imread(path)

# GOOD - Consistent 5D TCZYX, preserves metadata  
from bioio import BioImage
data = BioImage(path).data
```
