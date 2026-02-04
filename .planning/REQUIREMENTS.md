# Requirements: v0.5.0 Interactive Annotation

**Milestone:** v0.5.0 Interactive Annotation
**Goal:** Enable napari-based image annotation workflows for µSAM segmentation
**Created:** 2026-02-04

## v0.5.0 Requirements

### Infrastructure

- [ ] **INFRA-01**: User can launch napari viewer in an isolated subprocess without blocking the MCP server
- [ ] **INFRA-02**: User can load OME-Zarr artifacts directly into napari image layers
- [ ] **INFRA-03**: User can save napari Labels layer back to MCP artifact store as OME-Zarr
- [ ] **INFRA-04**: User receives clear error message when running interactive tools in headless environment
- [ ] **INFRA-05**: User can run µSAM inference on CUDA, MPS (macOS), or CPU with automatic detection

### µSAM Tool Pack

- [ ] **USAM-01**: User can install µSAM tool pack with isolated conda environment (napari, micro-sam, PyTorch)
- [ ] **USAM-02**: Agent can launch napari with micro-sam plugin via MCP `run()` call, loading an image artifact
- [ ] **USAM-03**: User can precompute SAM embeddings for an image via `compute_embeddings` tool
- [ ] **USAM-04**: User can run zero-shot automatic segmentation via `segment_automatic` tool (headless)
- [ ] **USAM-05**: User can select specialist SAM models (Light Microscopy, Electron Microscopy, Generalist)
- [ ] **USAM-06**: User has SAM models downloaded during tool pack installation, not first-run

### Interactive Annotation (via micro-sam plugin)

*Note: These features are provided by the existing micro-sam napari plugin. Our work is integrating the plugin with the MCP artifact system, not rebuilding UI.*

- [ ] **ANNOT-01**: User can add positive/negative point prompts via micro-sam plugin UI
- [ ] **ANNOT-02**: User can draw bounding boxes via micro-sam plugin UI
- [ ] **ANNOT-03**: User can see segmentation mask update in real-time (micro-sam plugin feature)
- [ ] **ANNOT-04**: User can commit annotations and close viewer, returning results to MCP
- [ ] **ANNOT-05**: User can use scribble/brush refinement via micro-sam plugin
- [ ] **ANNOT-06**: User can propagate masks across Z-slices via micro-sam plugin
- [ ] **ANNOT-07**: User can undo/redo prompts via micro-sam plugin

### Session Management

- [ ] **SESS-01**: User can re-enter annotation session instantly with cached embeddings
- [ ] **SESS-02**: User's napari process is cleaned up automatically if MCP server terminates
- [ ] **SESS-03**: User can resume annotation session after closing viewer without losing progress
- [ ] **SESS-04**: User sees progress indicators during model loading and embedding computation

---

## Future Requirements

Deferred to later milestones:

- [ ] **FUTURE-01**: Remote-desktop / cloud viewer support (web-based fallback)
- [ ] **FUTURE-02**: Multi-user VRAM management for concurrent sessions
- [ ] **FUTURE-03**: SAM2/SAM3 integration for faster inference and video tracking
- [ ] **FUTURE-04**: Model fine-tuning on user-specific datasets
- [ ] **FUTURE-05**: Real-time video tracking annotation

## Out of Scope

Explicitly excluded from v0.5.0:

| Feature | Reason |
|---------|--------|
| In-browser canvas | High development cost; poor performance for large bioimages |
| Custom Qt/React GUI | napari is industry standard; custom GUI creates technical debt |
| Model fine-tuning | Requires large datasets and long training times |
| Real-time video tracking | Bandwidth/latency requirements too high for initial implementation |
| SAM-H (Huge) models | Extreme VRAM requirements with minimal accuracy gains |

## Traceability

| Requirement | Phase | Plan | Status |
|-------------|-------|------|--------|
| INFRA-01 | — | — | Pending |
| INFRA-02 | — | — | Pending |
| INFRA-03 | — | — | Pending |
| INFRA-04 | — | — | Pending |
| INFRA-05 | — | — | Pending |
| USAM-01 | — | — | Pending |
| USAM-02 | — | — | Pending |
| USAM-03 | — | — | Pending |
| USAM-04 | — | — | Pending |
| USAM-05 | — | — | Pending |
| USAM-06 | — | — | Pending |
| ANNOT-01 | — | — | Pending |
| ANNOT-02 | — | — | Pending |
| ANNOT-03 | — | — | Pending |
| ANNOT-04 | — | — | Pending |
| ANNOT-05 | — | — | Pending |
| ANNOT-06 | — | — | Pending |
| ANNOT-07 | — | — | Pending |
| SESS-01 | — | — | Pending |
| SESS-02 | — | — | Pending |
| SESS-03 | — | — | Pending |
| SESS-04 | — | — | Pending |

---
*Requirements defined: 2026-02-04*
*Total: 22 requirements across 4 categories*
