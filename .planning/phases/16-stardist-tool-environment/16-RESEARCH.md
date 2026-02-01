# Phase 16: StarDist Tool Environment - Research

**Researched:** 2026-02-01
**Domain:** Deep Learning Instance Segmentation (StarDist)
**Confidence:** HIGH

## Summary

This research establishes the plan for integrating StarDist into the `bioimage-mcp` ecosystem. StarDist is a specialized tool for object detection (mostly nuclei) using star-convex shapes. It provides both 2D and 3D segmentation capabilities and follows a class-based API pattern.

Key findings:
- StarDist requires **TensorFlow** (2.x) and **CSBDeep**.
- The API is class-based (`StarDist2D`, `StarDist3D`), requiring a model instantiation step (ObjectRef) before inference.
- Inference (`predict_instances`) returns a tuple `(labels, details)`, where `labels` is the segmented image and `details` contains object coordinates and probabilities.
- Training is supported via a `model.train()` method.
- The integration will follow the Cellpose pattern but with a dedicated `StarDistAdapter` to handle class exposure and tuple returns.

**Primary recommendation:** Use StarDist 0.9.2 with TensorFlow 2.15+ in a Python 3.11 environment, exposing `StarDist2D` and `StarDist3D` classes directly through the unified introspection engine.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `stardist` | 0.9.2 | Core segmentation logic | Industry standard for star-convex object detection. |
| `csbdeep` | 0.8.2 | Deep learning utilities | StarDist depends on this for TF integration and normalization. |
| `tensorflow` | 2.15+ | DL Backend | StarDist is built on TensorFlow. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `bioio` | Latest | Image I/O | All artifacts must be read/written via bioio. |
| `scikit-image`| Latest | Label processing | Standard for image analysis post-processing. |
| `numba` | Latest | Acceleration | StarDist uses numba for fast overlap calculations. |

**Installation:**
```bash
conda install -c conda-forge stardist tensorflow-cpu bioio bioio-ome-tiff bioio-ome-zarr
```

## Architecture Patterns

### Class Exposure Pattern
Following the `16-CONTEXT.md` decisions, StarDist will be exposed via its core classes rather than wrappers.

```python
# Model Initialization (returns ObjectRef)
model = StarDist2D.from_pretrained('2D_versatile_fluo')

# Inference (takes ObjectRef, returns multiple artifacts)
labels, details = model.predict_instances(image)
```

### Pattern 1: Multi-Artifact Return
StarDist's `predict_instances` returns a tuple. The tool pack adapter will map this to two output ports:
1. `labels`: `LabelImageRef` (OME-Zarr)
2. `details`: `NativeOutputRef` (format: `stardist-details`, contains `coord`, `prob`, etc.)

### Anti-Patterns to Avoid
- **Functional Wrappers:** Do not create `stardist_predict()` functions. Use the `StarDist2D`/`StarDist3D` classes directly to allow for model persistence and parameter transparency.
- **Manual Normalization:** Use `csbdeep.utils.normalize` instead of hand-rolling intensity scaling.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model Management | Custom downloader | `from_pretrained()` | StarDist handles model caching and versioning internally. |
| Tiling | Custom tile loop | `n_tiles` param | `predict_instances` has built-in tiling with overlap handling. |
| Normalization | `(x - min) / max` | `csbdeep.utils.normalize` | Handles percentiles and multi-channel data correctly. |

## Common Pitfalls

### Pitfall 1: TensorFlow Memory Exhaustion
**What goes wrong:** TensorFlow allocates all available GPU memory by default, causing other tools (like Cellpose/PyTorch) to fail.
**How to avoid:** Use `tensorflow-cpu` by default, or configure `per_process_gpu_memory_fraction` if GPU is required.
**Warning signs:** `OOM` errors or "Failed to get convolution algorithm" in logs.

### Pitfall 2: Tuple Return Handling
**What goes wrong:** Discovery engine assumes single return value, losing the `details` dictionary.
**How to avoid:** Use a dedicated `StarDistAdapter` that explicitly defines two output ports for `predict_instances`.

## Code Examples

### Prediction with Pre-trained Model
```python
from stardist.models import StarDist2D
from csbdeep.utils import normalize

# 1. Initialize
model = StarDist2D.from_pretrained('2D_versatile_fluo')

# 2. Predict
# Input: x (BioImageRef)
# Output: labels (LabelImageRef), details (dict)
img = normalize(x)
labels, details = model.predict_instances(img, prob_thresh=0.5, nms_thresh=0.3)
```

### Training
```python
# model.train(X, Y, validation_data=(X_val, Y_val), epochs=400)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom wrappers | Class Exposure | Phase 16 | Direct access to all native parameters. |
| Local .h5 files | `from_pretrained` | StarDist 0.6+ | Effortless model sharing/loading. |

## Open Questions

1. **How to visualize `details` in the MCP UI?**
   - Recommendation: For now, `details` is a secondary artifact. Primary value is in the `labels` image.

2. **TensorFlow GPU vs CPU on Windows/macOS?**
   - Recommendation: Default to `tensorflow-cpu` in the standard manifest to ensure cross-platform stability. Provide a `gpu` profile for users with dedicated hardware.

## Sources

### Primary (HIGH confidence)
- `/stardist/stardist` (Context7) - API signatures and examples.
- `https://github.com/stardist/stardist` - Dependencies and build logic.
- `.planning/16-CONTEXT.md` - Project-specific decisions on class exposure.

### Secondary (MEDIUM confidence)
- `tools/cellpose` implementation - Baseline for deep learning tool pack integration.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified via conda-forge and setup.py.
- Architecture: HIGH - Matches CONTEXT.md and existing Cellpose pattern.
- Pitfalls: MEDIUM - Based on general TensorFlow experience in bioimaging.

**Research date:** 2026-02-01
**Valid until:** 2026-03-01
