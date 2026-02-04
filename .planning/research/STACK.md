# Stack Research: Interactive Annotation

**Project:** Bioimage-MCP (v0.5.0)
**Researched:** 2026-02-04
**Confidence:** HIGH

## Core Dependencies

The interactive annotation stack for v0.5.0 is centered around **napari** for visualization and the **micro-sam napari plugin** for SAM-based annotation. 

**Key architectural decision:** We are **reusing the existing micro-sam napari plugin** rather than building custom annotation UI. Our work focuses on integrating the plugin with the MCP artifact system.

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **Python** | `3.10+` | Runtime | Compatibility with existing bioimage-mcp core server. |
| **napari** | `^0.5.5` | Interactive Viewer | Industry standard for multi-dimensional microscopy; robust support for point/shape layers required for SAM prompts. |
| **micro-sam** | `^1.4.2` | SAM Wrapper | Specialized SAM implementation for microscopy; provides pre-trained specialist models (LM/EM) and a stable API for interactive loops. |
| **PyTorch** | `^2.5.1` | DL Engine | Dependency for `micro-sam`. Version 2.5+ provides significant speedups for SAM's transformer backbone on modern GPUs. |
| **segment-anything** | `^1.0` | Model Architecture | Core architecture backbone. *Note: SAM2 support is currently in the roadmap/experimental phase for micro-sam.* |
| **torch-em** | `^0.8.0` | DL Training/Utils | Required by `micro-sam` for seamless data handling and model management. |
| **trackastra** | `^0.1.x` | Tracking | (Optional) Required for "Annotator Tracking" features to enable cell lineage construction across time. |

## napari Ecosystem

We leverage the **micro-sam napari plugin** which provides a complete annotation UI out of the box.

### micro-sam Plugin Features (Reused, Not Rebuilt)
The micro-sam plugin already provides:
- **Points Layer**: For positive (object) and negative (background) clicks
- **Shapes Layer**: For bounding boxes
- **Labels Layer**: For scribbles and displaying segmentation masks
- **Model Selection**: UI for choosing SAM model variants
- **Undo/Redo**: Built-in prompt history
- **3D Propagation**: Multi-slice annotation support

### Essential Plugins
- **micro-sam**: The core annotation plugin - provides all interactive UI
- **napari-ome-zarr**: Native loader for OME-Zarr, ensuring `BioImageRef` artifacts are opened without memory-intensive data copying

## µSAM Requirements

Hardware requirements are a significant constraint for deployment.

### GPU (Required for Interactive Speed)
- **VRAM (8GB Minimum)**: Required for `vit_b` (Base) models.
- **VRAM (16GB Recommended)**: Required for `vit_l` (Large) models and to ensure overhead for large image embeddings.
- **CUDA**: `micro-sam` is optimized for NVIDIA hardware. While CPU execution is possible, it is unsuitable for "live" interactive refinement (>10s latency).

### Model Selection
1. **Light Microscopy (LM)**: Use `vit_b_lm` as default.
2. **Electron Microscopy (EM)**: Use `vit_b_em_organelles` for organelles.
3. **Generalist**: `vit_b` (Original SAM) for unconventional microscopy modalities.

## Integration Points

How the new stack connects to the existing `bioimage-mcp` infrastructure:

1. **Artifact Bridge**:
   - `BioImageRef` (OME-Zarr) -> `napari-ome-zarr` -> `napari.layers.Image`.
   - `napari.layers.Labels` -> `BioImageRef` (Export/Save) -> `ObjectRef`.
2. **Isolated Runtimes**:
   - A new tool pack `micro-sam` will be registered in `bioimage-mcp`.
   - The environment will include `napari[all]` and `micro-sam` to ensure the GUI and inference run in the same isolated process.
3. **Workflow Recording**:
   - Prompt coordinates (points/boxes) should be captured as "params" in the MCP `run` record to allow reproducibility of the segmentation.

## Recommendations

- **Version Lock**: Strictly pin `micro-sam>=1.4.0` to ensure the new model selector UI and stable API are available.
- **Embedding Cache**: Implement local file caching for image embeddings. Calculating embeddings for a 2048x2048 image takes 2-5s; caching allows instant restarts of the annotator.
- **Debounced Inference**: Trigger SAM inference 200-300ms after the last user click to prevent UI lag during rapid clicking.

## Anti-Recommendations

- **Avoid SAM-H (Huge)**: Do not recommend `vit_h` for general users. It requires extreme VRAM and slows down the interactive loop with minimal accuracy gains over `vit_l_lm`.
- **Avoid Custom Annotation UI**: Do not rebuild micro-sam plugin features. The plugin already provides point prompts, box prompts, scribbles, undo/redo, and 3D propagation. Our work is integration only.
- **Avoid Raw Pixel Pipes**: Never transfer raw image arrays over the MCP protocol. Always pass URIs to artifacts.

## Sources
- [micro-sam Documentation](https://computational-cell-analytics.github.io/micro-sam/)
- [micro-sam environment.yaml](https://raw.githubusercontent.com/computational-cell-analytics/micro-sam/master/environment.yaml)
- [napari-hub: micro-sam](https://www.napari-hub.org/plugins/micro-sam)
- [Context7: /napari/napari](/napari/napari)
