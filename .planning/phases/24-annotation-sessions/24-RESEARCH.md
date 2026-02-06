# Phase 24: µSAM Session & Optimization - Research

**Researched:** 2026-02-06
**Domain:** Deep Learning Model Lifecycle & Session Management
**Confidence:** HIGH

## Summary

Phase 24 focuses on optimizing the lifecycle of heavy SAM (Segment Anything Model) objects and large embeddings within the `bioimage-mcp` framework. The research confirms that the existing **Persistent Worker** architecture (Phase 12) provides the necessary foundation for stateful caching. Since tool workers are long-lived per session/environment, in-memory objects like `SamPredictor` and computed embeddings can be reused across multiple `run()` calls, drastically reducing latency.

**Primary recommendation:** Implement a formal "Predictor Cache" within the `MicrosamAdapter` that keys off the pair `(image_uri, model_type)`. Standardize embedding persistence using OME-Zarr (via `micro_sam.precompute_state`) to support session resume across worker restarts.

## Standard Stack

The following libraries and tools are standard for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `micro-sam` | >=0.7.0 | High-level SAM API | Best-in-class bioimage-specific SAM wrappers. |
| `segment-anything` | 1.0 | Base SAM model | Authoritative foundation model implementation. |
| `zarr` | >=2.16 | Embedding storage | Standard for large, chunked array storage; used by micro-sam. |
| `tqdm` | >=4.66 | Progress reporting | Used internally by micro-sam; can be parsed for progress metadata. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `napari` | >=0.4.18 | Interactive GUI | For managed annotator subprocesses. |
| `pydantic` | v2 | IPC Schemas | For structured communication between server and worker. |

## Architecture Patterns

### Recommended Project Structure
The `micro_sam` tool pack is already structured as a standalone tool in `tools/microsam`. Optimization will primarily live in the adapter and entrypoint.
```
src/bioimage_mcp/
├── runtimes/
│   ├── persistent.py   # Manages worker lifecycle (Existing)
│   └── worker_ipc.py   # IPC message schemas (Existing)
tools/microsam/
├── bioimage_mcp_microsam/
│   ├── entrypoint.py   # Handles persistent loop
│   └── adapter.py      # Logic for caching and optimization
```

### Pattern 1: Image-Keyed Predictor Reuse
**What:** Store `SamPredictor` instances in the `OBJECT_CACHE` keyed by a hash of the image URI and model name.
**When to use:** Every `run()` call to `micro_sam.*` functions.
**Implementation details:**
- Use the image artifact's URI and `model_type` parameter to generate a lookup key.
- If match found in `OBJECT_CACHE`, reuse the `predictor` without calling `set_image()` (saves ~0.5s-2s depending on image size).

### Pattern 2: Hidden Embedding Artifacts
**What:** Save SAM embeddings to disk as `OME-Zarr` artifacts but do not include them in the primary user-facing output list.
**When to use:** When `compute_embedding` is called or when a session is initialized.
**Storage Contract:**
- Format: OME-Zarr (compat with `micro_sam.util.precompute_state`).
- Path: `.microsam/embeddings/{image_hash}_{model}.zarr` within the session work directory.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Embedding Serialization | Custom `.npy` or pickle | `micro_sam.util.precompute_state` | Handles chunking, multi-scale (if needed), and coordinate offsets correctly. |
| Process Cleanup | Custom SIGTERM handlers | `WorkerProcess.shutdown()` | Already implemented in the server; uses `kill()` if graceful shutdown fails. |
| Progress Bars | New IPC message types | Stderr parsing of `tqdm` | Least disruptive path; `PersistentWorkerManager` already captures stderr in real-time. |

## Common Pitfalls

### Pitfall 1: Memory Bloat
**What goes wrong:** Keeping multiple large SAM embeddings in GPU/System memory leads to OOM.
**How to avoid:** 
- The `LRUCache` in `OBJECT_CACHE` should have a strict memory limit (e.g., 2GB).
- Evict the oldest `predictor` (which holds the large features tensor) when the limit is hit.

### Pitfall 2: Napari Blocking IPC
**What goes wrong:** `napari.run()` blocks the Python thread, preventing the worker from reading further IPC commands (like `shutdown`).
**How to avoid:** 
- Accept that interactive sessions are "exclusive" per worker.
- Use `WorkerProcess.kill()` from the server to force-close napari if the session must end.
- Ensure `napari` is launched with `return_viewer=True` and then `napari.run()` is called explicitly to maintain control points.

## Code Examples

### Predictor Reuse logic
```python
# In MicrosamAdapter.execute
from bioimage_mcp.registry.dynamic.object_cache import OBJECT_CACHE

# Generate key from image artifact and model
image_uri = inputs[0].uri
model_type = params.get("model_type", "vit_b")
cache_key = f"microsam_predictor:{image_uri}:{model_type}"

predictor = OBJECT_CACHE.get(cache_key)
if predictor is None:
    # Compute from scratch
    predictor = util.get_sam_model(model_type=model_type)
    predictor.set_image(image_data)
    OBJECT_CACHE.set(cache_key, predictor)
    self.warnings.append("CACHE_MISS")
else:
    self.warnings.append("CACHE_HIT")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One-shot subprocess | Persistent Worker | Phase 12 | 5x speedup (removes conda/torch import overhead). |
| Pickle embeddings | Zarr embeddings | micro-sam 0.7 | Better chunking and partial loading for large volumes. |

## Open Questions

1. **Richer Progress:** Should we add a `{"command": "progress"}` message to the IPC protocol?
   - **Recommendation:** Start by parsing `tqdm` from stderr. If the UI requires high-fidelity "stage" reporting (e.g., "Loading Model...", "Computing Features..."), upgrade the IPC protocol.

2. **Cross-Session Persistence:** Should embeddings survive server restart?
   - **Recommendation:** No, keep them session-scoped by default to avoid disk bloat, but allow explicit "Export Session" to save them.

## Sources

### Primary (HIGH confidence)
- `src/bioimage_mcp/runtimes/persistent.py` - Verified persistent worker lifecycle.
- `src/bioimage_mcp/registry/dynamic/object_cache.py` - Verified in-memory caching mechanism.
- `micro-sam` GitHub (micro_sam/precompute_state.py) - Verified Zarr storage format.

### Secondary (MEDIUM confidence)
- `segment-anything` Documentation - SAM Predictor state lifecycle.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH
- Architecture: HIGH
- Pitfalls: MEDIUM

**Research date:** 2026-02-06
**Valid until:** 2026-03-08
