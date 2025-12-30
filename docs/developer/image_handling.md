# Image Handling Guide

This document provides guidance for tool developers on how to handle image data within the `bioimage-mcp` framework. To ensure consistency and reproducibility across different tools and environments, `bioimage-mcp` standardizes on specific libraries and formats.

## Overview

`bioimage-mcp` standardizes on [bioio](https://github.com/bioio-dev/bioio) for all image I/O operations. `bioio` provides a unified interface for reading various microscopy formats and consistently returns data in a 5D **TCZYX** (Time, Channel, Z-stack, Y, X) format.

All tool functions that accept or return image data MUST use `BioImageRef` or `LabelImageRef` artifact types, which are backed by files compatible with `bioio`.

## Standard Loading Pattern

The recommended way to load images in tool functions is to use the `BioImage` class from the `bioio` package. This ensures that regardless of the underlying file format (TIFF, CZI, LIF, etc.), the data is accessed consistently.

```python
from bioio import BioImage

def my_tool_function(image_ref: dict):
    # Extract the local file path from the URI
    path = image_ref["uri"].replace("file://", "")
    
    # Load the image using BioImage
    img = BioImage(path)
    
    # Access the raw data
    # data is always 5D TCZYX (Time, Channel, Z, Y, X)
    data = img.data
    
    # Example: Processing the data
    # If your algorithm expects 2D (Y, X), you may need to squeeze or slice
    # processed = my_algorithm(data[0, 0, 0, :, :])
```

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
