# Phase 07: Transforms & Measurements - Research

**Researched:** 2026-01-25
**Domain:** Coordinate-aware image transformations and analytical measurements.
**Confidence:** HIGH

## Summary

Phase 07 focuses on extending the `scipy.ndimage` integration within the `bioimage-mcp` framework, specifically addressing geometric transformations (zoom, rotate, affine) and quantitative measurements (labeling, center of mass, intensity statistics). A key requirement is the preservation and adjustment of physical metadata (microns, ms) during transformations and the production of structured JSON artifacts for measurements.

**Primary recommendation:** Use `scipy.ndimage` for core logic, but wrap these in adapters that explicitly handle OME-TIFF metadata updates (especially for `zoom`) and ensure measurement outputs follow a consistent JSON schema keyed by label ID.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `scipy.ndimage` | 1.15+ | Core transformation and measurement logic | Industry standard for N-D image processing in Python. |
| `bioio` | Latest | Metadata-aware image I/O | Standard for bioimage metadata (OME) in this project. |
| `ome-types` | Latest | OME-XML model handling | Used by bioio to represent and manipulate metadata. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `scipy.fft` | 1.15+ | Fourier transforms | Required to prepare data for `ndimage.fourier` filters. |
| `numpy` | 1.26+ | Array manipulation | Base for all image data. |

**Installation:**
```bash
pip install scipy bioio bioio-ome-tiff ome-types
```

## Architecture Patterns

### Recommended Project Structure
Geometric transforms and measurements will live in `tools/base/` under the `scipy.ndimage` adapter, with custom logic for metadata and JSON formatting.

### Pattern 1: Coordinate-Aware Zoom
**What:** Adjusting `PhysicalSize` metadata based on the zoom factor.
**When to use:** Every `zoom` operation on a `BioImageRef`.
**Example:**
```python
# Logic for adapter
zoom_factors = params.get("zoom") # can be scalar or sequence
old_metadata = image.metadata.images[0].pixels
new_pixel_size_x = old_metadata.physical_size_x / zoom_factors[axis_x]
# Update OME model before writing artifact
```

### Pattern 2: Label-Centric Measurements
**What:** Returning a JSON object keyed by label ID for all region-based measurements.
**When to use:** `center_of_mass`, `mean`, `sum`, `extrema`.
**Example:**
```json
{
  "1": {"mean": 120.5, "center_of_mass": [10.5, 20.2]},
  "2": {"mean": 245.1, "center_of_mass": [50.1, 80.8]},
  "metadata": {"unit": "microns", "total_labels": 2}
}
```

### Anti-Patterns to Avoid
- **Discarding Metadata:** Do not return a raw `BioImageRef` without updated physical sizes after a `zoom`.
- **Inconsistent JSON:** Avoid returning lists of values for measurements; always use a dict keyed by label ID to handle missing/discontiguous labels.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connected component labeling | Custom pixel walker | `scipy.ndimage.label` | Performance and handling of high-dimensional connectivity. |
| Interpolation (Bicubic, etc) | Custom kernel convolution | `scipy.ndimage.zoom` | Highly optimized C/C++ implementations for multiple orders. |
| OME-XML generation | Manual string templates | `ome-types` | Prevents schema validation errors in downstream tools. |

## Common Pitfalls

### Pitfall 1: Anisotropic Zoom
**What goes wrong:** Applying a single zoom factor to an image where X/Y/Z have different physical sizes or requiring different scaling.
**How to avoid:** Support `zoom` as a sequence mapping to dimensions (C, Z, Y, X). Ensure metadata updates match the correct dimension.

### Pitfall 2: Fourier Complex Mapping
**What goes wrong:** `scipy.ndimage.fourier` filters expect the input to be the result of a Fourier transform (complex).
**How to avoid:** Tools should expect/return `complex64/128` data. Since OME-TIFF doesn't natively support complex, save as a 2-channel image ("Real", "Imag") and provide a helper to recombine them.

### Pitfall 3: Inverse Affine Matrix
**What goes wrong:** `scipy.ndimage.affine_transform` uses an *inverse* mapping by default (mapping output coordinates to input).
**How to avoid:** Clearly document the expected matrix in the tool description or provide a `forward=True` flag that inverts the matrix before calling Scipy.

## Code Examples

### Physical Metadata Update (Conceptual)
```python
# Source: Internal project logic
from ome_types import OME

def update_pixel_sizes(ome: OME, zoom_factors: list[float], axes: str):
    pixels = ome.images[0].pixels
    for factor, axis in zip(zoom_factors, axes):
        if axis == 'X' and pixels.physical_size_x:
            pixels.physical_size_x /= factor
        elif axis == 'Y' and pixels.physical_size_y:
            pixels.physical_size_y /= factor
        elif axis == 'Z' and pixels.physical_size_z:
            pixels.physical_size_z /= factor
    return ome
```

### Fourier Filter Workflow
```python
# Source: SciPy Documentation
import numpy as np
from scipy import ndimage

# 1. FFT
input_fft = np.fft.fftn(image)
# 2. Filter
filtered_fft = ndimage.fourier_gaussian(input_fft, sigma=2)
# 3. IFFT (Handle transition)
result = np.fft.ifftn(filtered_fft).real
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `scipy.ndimage.measurements` | `scipy.ndimage` (flat) | SciPy 1.6.0 | Functions moved to main `ndimage` namespace. |
| `tifffile` for OME | `bioio` + `ome-types` | 2023 | Better abstraction of multi-reader/writer plugins and Pydantic-based metadata. |

## Open Questions

1. **Affine Metadata:** How should we update physical metadata for an arbitrary affine transform?
   - *Recommendation:* If the transform is a pure rotation/translation, keep pixel sizes. For scaling/shearing, warn the user that metadata may no longer be accurate or calculate the determinant of the sub-matrix.
2. **Complex OME-TIFF Type:** Should we use a custom metadata annotation for "Complex Image"?
   - *Recommendation:* Use standard multi-channel OME-TIFF with channel names "Real" and "Imaginary".

## Sources

### Primary (HIGH confidence)
- `scipy.ndimage` documentation - Interpolation, Measurements, Fourier filters.
- `bioio-ome-tiff` / `ome-types` - Metadata structures.

### Secondary (MEDIUM confidence)
- `cupy` / `dask-image` implementations - Verification of Fourier logic and real/imag transitions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Core libraries are stable.
- Architecture: HIGH - Fits existing adapter patterns.
- Pitfalls: HIGH - Common in bioimage processing.

**Research date:** 2026-01-25
**Valid until:** 2026-07-25 (SciPy releases are regular but stable)
