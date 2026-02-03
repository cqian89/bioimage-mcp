# Phase 19: Add smoke test for stardist - Research

**Researched:** 2026-02-04
**Domain:** Deep Learning / StarDist Instance Segmentation
**Confidence:** HIGH

## Summary

Phase 19 involves adding a smoke test for the StarDist tool pack. StarDist is a popular library for object detection (primarily nuclei) using star-convex polygons. The tool pack is already implemented with support for dynamic discovery, pre-trained model loading via `ObjectRef`, and instance segmentation returning `LabelImageRef` and `NativeOutputRef` (containing polygons).

The research confirms that StarDist relies on TensorFlow and CSBDeep. It uses a registry of pre-trained models (e.g., `2D_versatile_fluo`, `3D_demo`) which are downloaded on first use. The tools in this repository handle image normalization and axis alignment internally, making the pipeline straightforward for an agent or user.

**Primary recommendation:** Follow the established `test_cellpose_pipeline_live.py` pattern, using a persistent session to load a pre-trained model into an `ObjectRef` and then performing prediction on a synthetic image.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stardist | 0.9.x | Core StarDist implementation | De facto standard for star-convex object detection in bioimaging. |
| csbdeep | 0.7.x | Deep learning toolbox for bioimaging | Base library for StarDist and CARE; handles model loading and normalization. |
| tensorflow | 2.x | DL Backend | StarDist (currently) requires TensorFlow. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| bioio | Latest | Image I/O | Used by tools to load/save multi-dimensional images. |
| bioio-ome-zarr | Latest | OME-Zarr support | Standard format for multi-dimensional label images in this project. |

**Installation:**
```bash
# Handled by conda environment: bioimage-mcp-stardist
conda create -n bioimage-mcp-stardist python=3.11 stardist
```

## Architecture Patterns

### Recommended Smoke Test Pipeline
The smoke test should verify the end-to-end lifecycle of a StarDist model within the MCP server:

1.  **Discovery:** Verify `list` returns StarDist functions.
2.  **Schema:** Verify `describe` returns correct parameters for `stardist.models.StarDist2D.from_pretrained`.
3.  **Model Loading:** Call `run` with `stardist.models.StarDist2D.from_pretrained` (e.g., `name="2D_versatile_fluo"`) to get an `ObjectRef`.
4.  **Data Loading:** Call `base.io.bioimage.load` on a synthetic image (e.g., `datasets/synthetic/test.tif`).
5.  **Prediction:** Call `run` with `stardist.models.StarDist2D.predict_instances` using the model `ObjectRef` and image `BioImageRef`.
6.  **Verification:**
    *   Assert `labels` output is a `LabelImageRef` in OME-Zarr format.
    *   Assert `details` output is a `NativeOutputRef` in `stardist-details-json` format.
    *   Verify artifact references are valid using `assert_valid_artifact_ref()`.

### Object Persistence
StarDist models are loaded as Python objects. The `tools/stardist/bioimage_mcp_stardist/entrypoint.py` implements a persistent `_OBJECT_CACHE` keyed by a URI like `obj://{session_id}/.../{uuid}`. This allows the model to stay in memory between MCP tool calls within the same session.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model Discovery | Custom model list | `cls.from_pretrained()` | StarDist/CSBDeep maintain the registry of available models. |
| Image Normalization | Custom mean/std/percentile | `csbdeep.utils.normalize` | StarDist models are trained on images normalized by this specific utility. |
| Polygon Export | Custom JSON format | `NativeOutputRef` | The tool already serializes StarDist's `details` dict to JSON correctly. |
| Axis Alignment | Manual transpose/squeeze | `BioImage` + `np.squeeze` | StarDist expects (Y, X) or (Z, Y, X); the tool already handles this. |

## Common Pitfalls

### Pitfall 1: Model Download Timeouts
**What goes wrong:** StarDist downloads pre-trained models from the web (GitHub/Zenodo) on the first call to `from_pretrained`.
**How to avoid:** Set a generous timeout for the smoke test (e.g., `@pytest.mark.timeout(300)`). If running in air-gapped CI, models must be pre-cached in `~/.stardist/models`.

### Pitfall 2: TensorFlow CPU vs GPU
**What goes wrong:** StarDist uses TensorFlow. If GPU libraries (CUDA/cuDNN) are missing but a GPU is present, or if there's a version mismatch, TF may crash.
**How to avoid:** For smoke tests, default to CPU by setting `os.environ["CUDA_VISIBLE_DEVICES"] = "-1"` or ensuring the environment uses `tensorflow-cpu`.

### Pitfall 3: Empty Results
**What goes wrong:** Synthetic images (like pure noise) may result in zero detected objects, returning an empty label image and empty `details`.
**How to avoid:** Use a synthetic image that contains star-convex-like blobs or use a slightly lower `prob_thresh` (e.g., 0.3) to ensure at least some detections occur.

## Code Examples

### Loading a Pre-trained Model
```python
# MCP call
result = await live_server.call_tool(
    "run",
    {
        "id": "stardist.models.StarDist2D.from_pretrained",
        "params": {"name": "2D_versatile_fluo"}
    }
)
model_ref = result["outputs"]["model"]
```

### Running Prediction
```python
# MCP call
result = await live_server.call_tool(
    "run",
    {
        "id": "stardist.models.StarDist2D.predict_instances",
        "inputs": {
            "model": model_ref,
            "image": img_ref
        },
        "params": {
            "prob_thresh": 0.5,
            "nms_thresh": 0.3
        }
    }
)
labels_ref = result["outputs"]["labels"]
details_ref = result["outputs"]["details"]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom model loaders | `from_pretrained()` | StarDist 0.6+ | Unified access to standard models. |
| Hard-coded axes | Dynamic axes (YX, CYX) | Always | Better support for multi-channel/3D data. |
| TIF label export | OME-Zarr export | Phase 15 | Native support for large/multiscale labels. |

## Open Questions

1.  **3D Smoke Test:** Should we test `StarDist3D`?
    *   *Recommendation:* Start with 2D as it's faster and uses less memory. Add 3D if resources permit.
2.  **Dataset Availability:** Does CI have access to `datasets/synthetic/test.tif`?
    *   *Finding:* Yes, it's used by Cellpose tests.

## Sources

### Primary (HIGH confidence)
- `/stardist/stardist` (Context7) - API documentation and usage examples.
- `tools/stardist/manifest.yaml` - Existing tool definitions.
- `tools/stardist/bioimage_mcp_stardist/entrypoint.py` - Implementation of the tool worker.

### Secondary (MEDIUM confidence)
- `tests/smoke/test_cellpose_pipeline_live.py` - Established pattern for DL smoke tests.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - StarDist is a stable, well-documented project.
- Architecture: HIGH - Implementation follows the repo's persistent worker pattern.
- Pitfalls: MEDIUM - Model download/CI environment issues are common but manageable.

**Research date:** 2026-02-04
**Valid until:** 2026-03-04
