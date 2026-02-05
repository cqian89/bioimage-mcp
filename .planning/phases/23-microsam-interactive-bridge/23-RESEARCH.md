# Phase 23: µSAM Interactive Bridge - Research

**Researched:** 2026-02-05
**Domain:** `micro_sam` Interactive Annotation (napari bridge)
**Confidence:** HIGH

## Summary

Phase 23 focuses on bridging the `micro_sam` napari-based annotation tools to the MCP environment. Instead of building a custom UI, we reuse the mature `micro_sam.sam_annotator` module, which provides 2D, 3D, and tracking annotators out of the box. The integration involves launching these annotators in an isolated worker process, pre-loading them with image and embedding artifacts, and capturing the resulting segmentation labels upon session completion.

**Primary recommendation:** Use the `return_viewer=True` flag in `micro_sam` annotator functions to obtain a viewer handle, then call `napari.run()` and export the `committed_objects` layer data as a `LabelImageRef` once the event loop returns.

## Standard Stack

The established libraries for this domain are already part of the `bioimage-mcp-microsam` environment.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `micro_sam` | `^1.7.0` | SAM-based annotation logic | Upstream library providing the widgets. |
| `napari` | `^0.5.5` | Interactive nD image viewer | Standard viewer for bioimage analysis in Python. |
| `torch` | `^2.x` | Deep learning backend | Required for SAM inference. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `bioio` | `^1.x` | Artifact I/O | Loading and saving OME-Zarr artifacts. |
| `qtpy` | `^2.4` | Qt abstraction | Required for display/headless detection. |

**Installation:**
```bash
# Handled via envs/bioimage-mcp-microsam.yaml
conda env create -f envs/bioimage-mcp-microsam.yaml
```

## Architecture Patterns

### Recommended Project Structure
Interactive logic belongs in the `MicrosamAdapter` and the tool pack entrypoint.
```
src/bioimage_mcp/registry/dynamic/adapters/microsam.py  # Execution logic
tools/microsam/bioimage_mcp_microsam/entrypoint.py      # Worker loop
tools/microsam/bioimage_mcp_microsam/device.py          # Device selection
```

### Pattern 1: Interactive Worker Execution
The tool pack process is already isolated from the MCP server. Calling a blocking GUI function within the adapter's `execute` method naturally blocks the specific tool call without affecting the main server.

**Example:**
```python
# Based on micro_sam/sam_annotator/annotator_2d.py
from micro_sam.sam_annotator import annotator_2d
import napari

def run_interactive_2d(image, embeddings=None):
    # 1. Start annotator with viewer handle
    viewer = annotator_2d(
        image=image,
        embedding_path=embeddings,
        return_viewer=True
    )
    
    # 2. Block until window is closed
    napari.run()
    
    # 3. Export results
    if "committed_objects" in viewer.layers:
        return viewer.layers["committed_objects"].data
    return None
```

### Anti-Patterns to Avoid
- **In-process GUI:** Never launch napari in the same process as the MCP server; it WILL block the event loop or crash due to Qt threading constraints.
- **Manual Layer Sync:** Avoid trying to sync layers via IPC during the session. Let the user work in napari and export the final state on close.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Annotation UI | Custom React/Qt widgets | `micro_sam.sam_annotator` | Upstream already solved propagation, AMG, and tracking. |
| Event Loop Management | Custom `QApplication` logic | `napari.run()` | Napari handles platform-specific event loop nuances. |
| Device Detection | Manual `torch.cuda` checks | `select_device()` | Project already has a shared utility for this. |

## Common Pitfalls

### Pitfall 1: Headless Environments
**What goes wrong:** Launching napari on a server with no X11/Wayland display causes an immediate crash or hang.
**How to avoid:** Check for `DISPLAY` environment variable or use `qtpy` to verify if a GUI can be created before launching.
**Warning signs:** `RuntimeError: Collectable QApplication already exists` or `Could not connect to any X display`.

### Pitfall 2: VRAM Exhaustion
**What goes wrong:** Concurrent interactive sessions on the same GPU can lead to Out-Of-Memory (OOM).
**How to avoid:** Document that interactive tools are intended for single-user/single-session local use or implement a VRAM-aware scheduler (out of scope for Phase 23).

## Code Examples

### Launching with Embeddings
Verified from `micro_sam` source: `embedding_path` can point to a directory containing precomputed `.zarr` embeddings.

```python
# Source: https://github.com/computational-cell-analytics/micro-sam/blob/master/micro_sam/sam_annotator/annotator_2d.py
from micro_sam.sam_annotator import annotator_2d
import napari

# embedding_path can be a local path to an artifact directory
viewer = annotator_2d(
    image=image_ndarray,
    embedding_path="/path/to/embeddings/", 
    return_viewer=True
)
napari.run()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom UI widgets | `micro_sam.sam_annotator` | v1.0+ | Massive reduction in maintenance; full feature parity with upstream. |
| Headless-only | Interactive Bridge | Phase 23 | Enables human-in-the-loop refinement of AI results. |

## Open Questions

1. **Wait for Signal vs. Save-on-Close:** Should we add a custom "Commit to MCP" button in napari, or is closing the window sufficient?
   - *Recommendation:* Start with Save-on-Close. If users find it confusing, add a custom widget with a "Finalize" button in a future sub-phase.
2. **Multi-layer Export:** What if the user creates multiple labels layers?
   - *Recommendation:* Prioritize `committed_objects` as per `micro_sam` conventions.

## Sources

### Primary (HIGH confidence)
- `computational-cell-analytics/micro-sam` GitHub source - `annotator_2d.py`, `annotator_3d.py`, `annotator_tracking.py` signatures and behavior.
- `/napari/napari` Context7 - `napari.run()` and layer data access.

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` - Subprocess isolation strategy.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Env already exists and verified.
- Architecture: HIGH - Follows established worker/adapter pattern.
- Pitfalls: MEDIUM - GUI detection needs platform-specific verification.

**Research date:** 2026-02-05
**Valid until:** 2026-03-05
