# Tool Reference

## Tools.Base (`bioimage-mcp-base`)

General purpose image processing tools for bioimage analysis.

### Image I/O & Export

*   `base.io.bioimage.export`: Export image to file-backed artifact (OME-TIFF or OME-Zarr). Used for explicit materialization or cross-environment handoff.
    *   **Inputs**: `image` (BioImageRef, required)
    *   **Params**:
        *   `format` (string): Output format (`OME-TIFF` or `OME-Zarr`). Default: `OME-TIFF`.
        *   `path` (string, optional): Target file path.
    *   **Outputs**: `output` (BioImageRef, file-backed)

### Axis Manipulation (xarray-based)

> **Note**: These tools produce memory-backed artifacts (`mem://`) by default for efficient chaining within the same tool environment. Use `base.io.bioimage.export` to materialize to disk when needed.

#### `base.xarray.rename`
Description: Rename dimension labels (e.g., Z -> T) while preserving metadata.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `mapping` (object, required): Map of `old_dim` -> `new_dim`.
Outputs:
*   `output` (BioImageRef, mem://)
Example usage:
```
base.xarray.rename(image=<ref>, mapping={"Z": "T"})
```

#### `base.xarray.squeeze`
Description: Remove singleton (size=1) dimensions.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dim` (string, optional): Specific dimension name to squeeze. If omitted, squeezes all singleton dimensions.
Outputs:
*   `output` (BioImageRef, mem://)
Example usage:
```
base.xarray.squeeze(image=<ref>, dim="C")
```

#### `base.xarray.expand_dims`
Description: Add a new dimension at a specified position.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dim` (string, required): Name for the new dimension.
*   `axis` (integer, optional): Position to insert new dimension (0=first, -1=before last).
Outputs:
*   `output` (BioImageRef, mem://)
Example usage:
```
base.xarray.expand_dims(image=<ref>, dim="T", axis=0)
```

#### `base.xarray.transpose`
Description: Reorder dimensions (replaces `base.moveaxis`, `base.swap_axes`).
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dims` (array of strings, required): Ordered list of dimension names.
Outputs:
*   `output` (BioImageRef, mem://)
Example usage:
```
base.xarray.transpose(image=<ref>, dims=["T", "C", "Z", "Y", "X"])
```

### Reductions (xarray-based)

#### `base.xarray.sum`
Description: Reduce along a named dimension using sum projection.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dim` (string, required): Dimension to reduce.
Outputs:
*   `output` (BioImageRef, mem://)

#### `base.xarray.max`
Description: Reduce along a named dimension using maximum projection.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dim` (string, required): Dimension to reduce.
Outputs:
*   `output` (BioImageRef, mem://)

#### `base.xarray.mean`
Description: Reduce along a named dimension using mean average.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dim` (string, required): Dimension to reduce.
Outputs:
*   `output` (BioImageRef, mem://)

### Transforms (xarray-based)

#### `base.xarray.isel`
Description: Select along dimensions by integer indexing or slices (replaces `base.crop`).
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `selections` (kwargs): Dimension names mapped to indices or slices (e.g., `Y={"start": 10, "stop": 50}`).
Outputs:
*   `output` (BioImageRef, mem://)

#### `base.xarray.pad`
Description: Pad along dimensions.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `padding` (kwargs): Dimension names mapped to padding widths (e.g., `Y=[10, 10]`).
Outputs:
*   `output` (BioImageRef, mem://)

### Pre-processing & Filters
*   `base.normalize_intensity`: Normalize intensities.
*   `base.gaussian`: Gaussian filter.
*   `base.median`: Median filter.
*   `base.bilateral`: Bilateral filter.
*   `base.denoise_nl_means`: Non-local means denoising.
*   `base.unsharp_mask`: Unsharp mask sharpening.
*   `base.equalize_adapthist`: Adaptive histogram equalization (CLAHE).
*   `base.sobel`: Sobel edge detection.
*   `base.threshold_otsu`: Otsu thresholding.
*   `base.threshold_yen`: Yen thresholding.
*   `base.morph_opening`: Morphological opening.
*   `base.morph_closing`: Morphological closing.
*   `base.remove_small_objects`: Remove small connected components.
*   `base.denoise_image`: General denoising tool.

### FLIM Analysis
*   `base.phasor_from_flim`: Compute phasor coordinates (G, S) and intensity from FLIM data.
*   `base.phasor_calibrate`: Calibrate phasor coordinates using a known reference lifetime.

### Legacy Tools (Deprecated)

> ⚠️ **DEPRECATED**: The following legacy tools are deprecated and will be removed in v1.0.0. Use the new `base.xarray.*` or `base.io.bioimage.*` tools instead.

*   `base.convert_to_ome_zarr` -> Use `base.io.bioimage.export(format="OME-Zarr")`
*   `base.export_ome_tiff` -> Use `base.io.bioimage.export(format="OME-TIFF")`
*   `base.project_sum` -> Use `base.xarray.sum`
*   `base.project_max` -> Use `base.xarray.max`
*   `base.crop` -> Use `base.xarray.isel`
*   `base.pad` -> Use `base.xarray.pad`
*   `base.relabel_axes` -> Use `base.xarray.rename`
*   `base.squeeze` -> Use `base.xarray.squeeze`
*   `base.expand_dims` -> Use `base.xarray.expand_dims`
*   `base.moveaxis` -> Use `base.xarray.transpose`
*   `base.swap_axes` -> Use `base.xarray.transpose`

---

## Tools.Cellpose (`bioimage-mcp-cellpose`)

Deep learning-based segmentation using the Cellpose framework.

*   `cellpose.segment`: Segment cells or nuclei.
    *   **Inputs**: `BioImageRef`
    *   **Outputs**: `LabelImageRef` (mask), `cellpose_bundle` (npy)
    *   **Params**: `model_type` (e.g., 'cyto3', 'nuclei'), `diameter`, `channels`, `flow_threshold`, `cellprob_threshold`.
