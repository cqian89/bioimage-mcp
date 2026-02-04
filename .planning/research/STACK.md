# Stack Research: Interactive Annotation

**Project:** Bioimage-MCP (v0.5.0)
**Researched:** 2026-02-04
**Confidence:** HIGH

## Core Dependencies

The interactive annotation stack for v0.5.0 is centered around **napari** for visualization and **micro-sam** (Segment Anything for Microscopy) for inference.

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

Leveraging the native napari event system and layer types is critical for a smooth user experience.

### Layer-Based Prompting
- **Points Layer**: For positive (object) and negative (background) clicks. `micro-sam` maps click coordinates to the SAM prompt encoder.
- **Shapes Layer**: For bounding boxes. Encapsulates a region of interest to constrain segmentation.
- **Labels Layer**: Used for "Scribbles" (dense point prompts) and displaying the final segmentation mask.

### Essential Plugins
- **napari-ome-zarr**: Native loader for OME-Zarr, ensuring `BioImageRef` artifacts are opened without memory-intensive data copying.
- **magicgui**: Used for generating the control panel (model selection, commit buttons, parameter sliders) directly from Python functions.

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
- **Avoid Custom GUI**: Do not build a standalone Qt/React GUI for the viewer. napari is the industry standard; building a custom one creates massive technical debt.
- **Avoid Raw Pixel Pipes**: Never transfer raw image arrays over the MCP protocol. Always pass URIs to artifacts.

## Sources
- [micro-sam Documentation](https://computational-cell-analytics.github.io/micro-sam/)
- [micro-sam environment.yaml](https://raw.githubusercontent.com/computational-cell-analytics/micro-sam/master/environment.yaml)
- [napari-hub: micro-sam](https://www.napari-hub.org/plugins/micro-sam)
- [Context7: /napari/napari](/napari/napari)
