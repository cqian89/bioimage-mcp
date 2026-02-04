# Phase 19: Add smoke test for StarDist - Research

**Researched:** 2026-02-04
**Domain:** Deep Learning Instance Segmentation / StarDist
**Confidence:** HIGH

## Summary

This research phase investigated the implementation of a smoke test for the StarDist tool pack. The standard approach for StarDist involves using pre-trained models (like `2D_versatile_fluo`) and applying them to normalized microscopy images. The established pattern for smoke tests in this repository is to compare the MCP tool output with a native script baseline using `DataEquivalenceHelper` and `NativeExecutor`.

**Primary recommendation:** Implement a StarDist equivalence test that replicates the official 2D nuclei prediction example, using `stardist.data.test_image_nuclei_2d()` as the source data and `2D_versatile_fluo` as the model, with a 3-attempt retry policy for model and data downloads.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `stardist` | ^0.9.0 | Instance segmentation | State-of-the-art for star-convex objects (nuclei) |
| `csbdeep` | ^0.7.0 | DL utilities | Required by StarDist for normalization and model handling |
| `tensorflow`| ^2.15 | Backend | Primary execution engine for StarDist models |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `bioio` | ^1.1.0 | I/O | Standard for reading/writing OME-TIFF and OME-Zarr |
| `numpy` | ^1.24 | Data handling | Internal array representation |

**Installation (in tool-pack env):**
```bash
pip install stardist csbdeep tensorflow-cpu bioio
```

## Architecture Patterns

### Recommended Test Structure
The test should reside in `tests/smoke/test_equivalence_stardist.py` and follow the `NativeExecutor` pattern seen in Cellpose tests.

### Pattern 1: Equivalence Testing
**What:** Compare MCP tool execution result with a native script running the same library.
**When to use:** For deep learning tools where non-determinism (GPU/CPU differences) might occur, but logical agreement (IoU) should be high.
**Example:**
```python
# Source: tests/smoke/test_equivalence_cellpose.py
helper.assert_labels_equivalent(
    np.asarray(mcp_img.data), np.asarray(native_img.data), iou_threshold=0.95
)
```

### Anti-Patterns to Avoid
- **Hard-coding model paths:** Always use `from_pretrained` or configurable download paths to avoid absolute path failures in different environments.
- **Skipping normalization:** StarDist models are highly sensitive to input scale. Always use `csbdeep.utils.normalize` or equivalent.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model Download | Custom `requests` logic | `cls.from_pretrained('name')` | StarDist handles registry and caching of models |
| Data Download | Custom `urllib` calls | `stardist.data.test_image_nuclei_2d()` | Built-in sample data is verified compatible |
| Label Matching | Simple pixel matching | `DataEquivalenceHelper.assert_labels_equivalent` | Handles label ID permuting and small boundary shifts |

## Common Pitfalls

### Pitfall 1: Network Flakiness during Model Download
**What goes wrong:** `from_pretrained` fails due to transient connection issues.
**Why it happens:** StarDist models are hosted on GitHub releases or S3.
**How to avoid:** Wrap model initialization in a retry loop (3 attempts with exponential backoff).
**Warning signs:** `HTTPError` or `ConnectionError` in test logs.

### Pitfall 2: Memory/GPU Contention
**What goes wrong:** Test crashes or runs extremely slowly.
**Why it happens:** StarDist (TensorFlow) can be greedy with memory.
**How to avoid:** Use `tensorflow-cpu` for smoke tests and set `TF_CPP_MIN_LOG_LEVEL=2`.

## Code Examples

### Native StarDist Baseline (Reference Script)
```python
# Reference: StarDist 3_prediction.ipynb
from stardist.models import StarDist2D
from stardist.data import test_image_nuclei_2d
from csbdeep.utils import normalize
import numpy as np
from bioio.writers import OmeTiffWriter

def run_baseline(output_path):
    img = test_image_nuclei_2d()
    model = StarDist2D.from_pretrained('2D_versatile_fluo')
    labels, details = model.predict_instances(normalize(img))
    OmeTiffWriter.save(labels.astype(np.uint16), output_path, dim_order="YX")
    return {"labels_path": str(output_path), "label_count": len(np.unique(labels)) - 1}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom ZIP downloads | `stardist.data.*` | v0.6.0 | Easier access to standard test datasets |
| Manual normalization | `csbdeep.utils.normalize` | v0.1.0 | Standardized percentile-based scaling |

## Open Questions

1. **Deterministic behavior:** Does `StarDist2D.predict_instances` have any internal stochasticity on CPU?
   - What we know: Standard inference is usually deterministic on CPU.
   - What's unclear: Minor variations due to floating point precision across different CPU architectures.
   - Recommendation: Use a slightly relaxed IoU threshold (0.98 instead of 1.0) if needed.

## Sources

### Primary (HIGH confidence)
- `tools/stardist/bioimage_mcp_stardist/ops/predict.py` - Implementation details
- `tools/stardist/manifest.yaml` - Function IDs and schemas
- `stardist` GitHub Examples - [2D/3_prediction.ipynb](https://github.com/stardist/stardist/blob/main/examples/2D/3_prediction.ipynb)

### Secondary (MEDIUM confidence)
- StarDist Data Release - [dsb2018.zip](https://github.com/stardist/stardist/releases/download/0.1.0/dsb2018.zip)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Directly from tool pack implementation.
- Architecture: HIGH - Follows existing codebase patterns.
- Pitfalls: MEDIUM - Based on general DL deployment experience.

**Research date:** 2026-02-04
**Valid until:** 2026-03-04
