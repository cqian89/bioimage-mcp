# Phase 15: Enhance artifact_info - Research

**Researched:** 2026-01-31
**Domain:** Bioimaging metadata, multimodal previews, object introspection
**Confidence:** HIGH

## Summary

This phase enhances the `artifact_info` API to provide rich previews suitable for LLM consumption (multimodal) and user introspection. The research confirms that the standard stack of `bioio`, `numpy`, and `Pillow` is sufficient for high-quality image previews, while `pandas` and simple string manipulation handle tabular and object previews effectively.

**Primary recommendation:** Use `bioio` for lazy, slice-aware image loading to minimize memory overhead during preview generation, and normalize all imaging data to 8-bit PNG for universal LLM/browser compatibility.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `bioio` | ^1.0 | Image loading & metadata | Standard for OME-TIFF/OME-Zarr with native axis support. |
| `numpy` | ^1.26 | Array manipulation | Efficient projections (MIP) and normalization. |
| `Pillow` | ^10.0 | Image encoding | Fast PNG generation and base64 encoding. |
| `pandas` | ^2.0 | Table handling | Efficient row-slicing and data type introspection. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `scipy` | ^1.11 | Image statistics | For `center_of_mass` calculation in LabelImageRef. |
| `tabulate`| ^0.9 | Markdown tables | If complex table formatting is required (optional). |

**Installation:**
```bash
# Core server already has bioio, pydantic. 
# Optional dependencies for previews:
pip install pillow pandas scipy
```

## Architecture Patterns

### Preview Generation Workflow
1. **Identify Artifact Type:** Determine if `BioImageRef`, `TableRef`, or `ObjectRef`.
2. **Lazy Loading:** Use `bioio` or `pandas.read_csv(nrows=...)` to load only what's needed.
3. **Dimensionality Reduction:** Map named axes (Z, T) to indices using `bioio` metadata and apply projection (Max, Mean, etc.).
4. **Encoding:** Convert to 8-bit, apply colormap (if labels), and encode to Base64 PNG.
5. **Fail Safely:** If generation fails (e.g., OOM, corrupt file), omit the preview field rather than failing the request.

### Pattern: Multimodal PNG Preview
**What:** Convert N-D bioimaging data to a 2D 8-bit PNG string.
**When to use:** For any image artifact when `include_image_preview=true`.
**Example:**
```python
# Source: bioio docs + community patterns
import base64
from io import BytesIO
from PIL import Image
import numpy as np

def generate_png_preview(array_2d: np.ndarray) -> str:
    # Normalize to 0-255
    v_min, v_max = array_2d.min(), array_2d.max()
    if v_max > v_min:
        array_2d = 255 * (array_2d - v_min) / (v_max - v_min)
    img_8bit = array_2d.astype(np.uint8)
    
    buf = BytesIO()
    Image.fromarray(img_8bit).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image Slicing | Custom binary parsers | `bioio` | Handles OME-TIFF/Zarr complexity and chunking. |
| Table Markdown | Custom cell padding logic | `df.to_markdown()` | Handles alignment and edge cases. |
| MIP Projections | Custom loops | `np.max(axis=...)` | Highly optimized in C. |
| Class Naming | Custom module parsers | `obj.__class__.__module__` | Standard Python introspection. |

## Common Pitfalls

### Pitfall 1: Memory Exhaustion
**What goes wrong:** Loading a 10GB OME-Zarr into memory just to generate a 256x256 preview.
**How to avoid:** Always use `bioio`'s slicing (`get_image_data`) to load only the specific Z/T slice or the entire stack for projection *after* checking size limits.

### Pitfall 2: Label Image Visibility
**What goes wrong:** Displaying labels (1, 2, 3...) as raw intensities makes them invisible (dark gray on black).
**How to avoid:** Apply a categorical colormap like `tab20`.

### Pitfall 3: Pickle Security
**What goes wrong:** Loading `ObjectRef` via `pickle.load()` on untrusted data.
**How to avoid:** Only load objects from the internal `_simulated_path` within the same session/environment context.

## Code Examples

### Label Image Centroids (Optimized)
```python
# Source: scipy.ndimage documentation
from scipy.ndimage import center_of_mass, label

def get_label_metadata(label_array):
    unique_labels = np.unique(label_array)
    count = len(unique_labels) - (1 if 0 in unique_labels else 0)
    # This is much faster than manual loops
    centroids = center_of_mass(label_array, label_array, unique_labels[unique_labels > 0])
    return count, centroids
```

### Tab20 Colormap Mapping
```python
TAB20_RGB = [
    (31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),
    (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),
    (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),
    (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),
    (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)
]

def apply_tab20(label_array):
    h, w = label_array.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    for label_val in np.unique(label_array):
        if label_val == 0: continue
        color = TAB20_RGB[(label_val - 1) % 20]
        rgba[label_array == label_val] = list(color) + [255]
    return rgba
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `tifffile` for all | `bioio` wrappers | 2023 | Better support for multi-scene/multi-scale images. |
| Text-only previews | Multimodal PNG | 2024 | Enables vision-capable LLMs to "see" results. |
| Raw path exposure | Artifact URI (`mem://`) | Phase 14 | Improves security and abstraction. |

## Sources

### Primary (HIGH confidence)
- `bioio` GitHub - API for `BioImage` and `get_image_data`.
- Matplotlib Docs - `tab20` colormap specification.
- Python Docs - `inspect` and `__qualname__` for introspection.

### Secondary (MEDIUM confidence)
- WebSearch - Community patterns for Base64 PNG generation from NumPy.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Core imaging libs are stable.
- Architecture: HIGH - Preview generation is a well-understood pattern.
- Pitfalls: MEDIUM - Specific OOM edge cases depend on file format.

**Research date:** 2026-01-31
**Valid until:** 2026-03-31
