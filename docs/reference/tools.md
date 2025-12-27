# Tool Reference

## Tools.Base (`bioimage-mcp-base`)

General purpose image processing tools powered by `scikit-image`.

### Image I/O & Utils
*   `base.convert_to_ome_zarr`: Convert image to OME-Zarr.
*   `base.export_ome_tiff`: Export image to OME-TIFF.

### Transforms
*   `base.project_sum`: Sum projection.
*   `base.project_max`: Max projection.
*   `base.resize`: Resize image.
*   `base.rescale`: Rescale image by factor.
*   `base.rotate`: Rotate image.
*   `base.flip`: Flip image.
*   `base.crop`: Crop image.
*   `base.pad`: Pad image.

### Axis Manipulation

#### `base.relabel_axes`
Description: Relabel axis names (e.g., Z to T) for pipeline compatibility.
Parameters:
*   `axis_mapping` (object): Mapping of existing axis names to new axis names.
Example usage:
```
base.relabel_axes(image=<BioImageRef>, axis_mapping={"Z": "T", "T": "Z"})
```
Common use cases:
*   Align FLIM time/bin axis with downstream tools expecting `T`.
*   Standardize axis labels across datasets before batch processing.

#### `base.squeeze`
Description: Remove singleton (size=1) dimensions from an image.
Parameters:
*   `axis` (string | integer, optional): Axis name or index to squeeze. Omit to squeeze all singleton axes.
Example usage:
```
base.squeeze(image=<BioImageRef>, axis="Z")
```
Common use cases:
*   Remove a trailing singleton Z or C axis before 2D processing.
*   Simplify images exported from microscopy systems with extra length-1 axes.

#### `base.expand_dims`
Description: Add a new dimension at a specified position.
Parameters:
*   `axis` (integer): Axis index where the new dimension is inserted.
*   `new_axis_name` (string): Axis name for the new dimension.
Example usage:
```
base.expand_dims(image=<BioImageRef>, axis=0, new_axis_name="T")
```
Common use cases:
*   Add a time axis for single-frame images before time-series workflows.
*   Insert a channel axis for single-channel images prior to multi-channel tools.

#### `base.moveaxis`
Description: Move an axis from one position to another.
Parameters:
*   `source` (string | integer): Source axis name or index.
*   `destination` (integer): Destination axis index.
Example usage:
```
base.moveaxis(image=<BioImageRef>, source="C", destination=0)
```
Common use cases:
*   Reorder axes to match expected layout for a downstream model.
*   Move channel or time axis to the front for batch operations.

#### `base.swap_axes`
Description: Swap two axes in an image.
Parameters:
*   `axis1` (string | integer): First axis name or index.
*   `axis2` (string | integer): Second axis name or index.
Example usage:
```
base.swap_axes(image=<BioImageRef>, axis1="Z", axis2="T")
```
Common use cases:
*   Exchange Z and T axes when acquisition metadata is reversed.
*   Correct axis order before projection or segmentation tools.

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

---

## Tools.Cellpose (`bioimage-mcp-cellpose`)

Deep learning-based segmentation.

*   `cellpose.segment`: Segment cells or nuclei.
    *   **Inputs**: `BioImageRef`
    *   **Outputs**: `LabelImageRef` (mask), `cellpose_bundle` (npy)
    *   **Params**: `model_type` (e.g., 'cyto3', 'nuclei'), `diameter`, etc.
