# Base Toolkit Function Catalog

This catalog describes the base toolkit functions added for common image I/O,
transforms, and preprocessing operations using scikit-image and related
libraries. The goal is to provide a stable, discoverable set of primitives
for workflows without requiring specialized tool packs.

## Scope & Selection Rationale

The functions below were selected because they are:
- broadly useful across microscopy workflows
- stable and well-documented in scikit-image/numpy
- composable for larger workflows
- compatible with file-backed artifact I/O

All functions accept `BioImageRef` inputs and emit `BioImageRef` outputs unless
otherwise noted. Detailed parameter schemas are fetched on-demand via
`meta.describe` and cached locally.

## Image I/O

- `base.convert_to_ome_zarr`
  - Convert an input image to OME-Zarr for file-backed workflows.
  - Useful for intermediate data exchange between tool packs.
- `base.export_ome_tiff`
  - Export an input image to OME-TIFF for compatibility.

## Projections

- `base.project_sum`
  - Sum projection along a selected axis (e.g., Z).
- `base.project_max`
  - Max projection along a selected axis (e.g., Z).

## Transforms

- `base.resize`
  - Resize an image to a target shape.
- `base.rescale`
  - Rescale an image by a scalar factor.
- `base.rotate`
  - Rotate an image by an angle.
- `base.flip`
  - Flip an image along a selected axis.
- `base.crop`
  - Crop an image using start/stop coordinates.
- `base.pad`
  - Pad an image with a configurable padding mode.

## Pre-processing

- `base.normalize_intensity`
  - Percentile-based intensity normalization.
- `base.gaussian`
  - N-D Gaussian filter.
- `base.median`
  - Median filtering using a structuring footprint.
- `base.bilateral`
  - Edge-preserving bilateral filter.
- `base.denoise_nl_means`
  - Non-local means denoising.
- `base.unsharp_mask`
  - Sharpen using unsharp mask.
- `base.equalize_adapthist`
  - Adaptive histogram equalization (CLAHE).
- `base.sobel`
  - Sobel edge magnitude.
- `base.threshold_otsu`
  - Otsu thresholding (optionally apply threshold).
- `base.threshold_yen`
  - Yen thresholding (optionally apply threshold).
- `base.morph_opening`
  - Morphological opening.
- `base.morph_closing`
  - Morphological closing.
- `base.remove_small_objects`
  - Remove connected components below a size threshold.

## Known Limitations

- Some transforms may perform implicit floating-point conversions depending on
  scikit-image defaults. Parameter schemas document `preserve_range` where
  relevant to mitigate this.
- The base toolkit operates on file-backed artifacts; array payloads are not
  supported in MCP messages.
- OME-Zarr and OME-TIFF support depends on installed bioio plugins in the
  `bioimage-mcp-base` environment.
