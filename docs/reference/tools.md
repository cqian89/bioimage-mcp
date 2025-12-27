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
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `axis_mapping` (object, required): Mapping from existing axis names to new axis names (applied atomically).
Outputs:
*   `output` (BioImageRef)
Example usage:
```
base.relabel_axes(image=<BioImageRef>, axis_mapping={"Z": "T", "T": "Z"})
```

#### `base.squeeze`
Description: Remove singleton (size=1) dimensions from an image.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `axis` (string | integer, optional): Axis name or index to squeeze. Omit or set null to squeeze all singleton axes.
Outputs:
*   `output` (BioImageRef)
Example usage:
```
base.squeeze(image=<BioImageRef>, axis="Z")
```

#### `base.expand_dims`
Description: Add a new dimension at a specified position.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `axis` (integer, required): Position to insert new axis (0=first, -1=before last).
*   `new_axis_name` (string, required): Name for new axis (single uppercase letter).
Outputs:
*   `output` (BioImageRef)
Example usage:
```
base.expand_dims(image=<BioImageRef>, axis=0, new_axis_name="T")
```

#### `base.moveaxis`
Description: Move an axis from one position to another.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `source` (string | integer, required): Source axis name or index.
*   `destination` (integer, required): Destination position (index).
Outputs:
*   `output` (BioImageRef)
Example usage:
```
base.moveaxis(image=<BioImageRef>, source="C", destination=0)
```

#### `base.swap_axes`
Description: Swap two axes in an image.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `axis1` (string | integer, required): First axis name or index.
*   `axis2` (string | integer, required): Second axis name or index.
Outputs:
*   `output` (BioImageRef)
Example usage:
```
base.swap_axes(image=<BioImageRef>, axis1="Z", axis2="T")
```

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
