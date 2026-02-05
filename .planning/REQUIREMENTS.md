# Requirements: v0.5.0 micro_sam API + Interactive Annotation

**Milestone:** v0.5.0 Interactive Annotation
**Goal:** Expose the upstream `micro_sam` Python API via MCP `run()` (headless first) and enable napari-based annotation via `micro_sam.sam_annotator`.
**Created:** 2026-02-04 (updated 2026-02-05)

## v0.5.0 Requirements

### Registry & Schemas (API-first)

- [x] **API-01**: `bioimage-mcp list` exposes `micro_sam.<submodule>.<callable>` IDs for the `micro_sam` library API
- [x] **API-02**: `bioimage-mcp describe micro_sam.<...>` returns parameter schemas generated via AST + docstring parsing (Introspector)
- [x] **API-03**: Phase 22 exposure includes all `micro_sam.*` callables EXCEPT `micro_sam.sam_annotator.*`
- [ ] **API-04**: Phase 23 exposure includes `micro_sam.sam_annotator.*` callables
- [x] **API-05**: Any callables that are not MCP-safe (non-serializable params/returns) are handled via wrappers or are explicitly denylisted with rationale

### Headless Execution (Phase 22)

- [x] **HEAD-01**: User can run prompt-based segmentation headlessly via `micro_sam.prompt_based_segmentation.*` (e.g., points/boxes/masks)
- [x] **HEAD-02**: User can run automatic/instance segmentation headlessly via `micro_sam.instance_segmentation.*` (e.g., mask generators)
- [x] **HEAD-03**: Image inputs/outputs preserve artifact boundary: `BioImageRef`/`LabelImageRef` are used for image-like values (no raw arrays in the MCP protocol)
- [x] **HEAD-04**: Stateful or heavy objects (predictors, decoders, embedding state) are passed via `ObjectRef` and can be reused across `run()` calls
- [x] **HEAD-05**: Headless tools preserve native axes/dims metadata end-to-end (avoid TCZYX padding)
- [x] **HEAD-06**: User can precompute and reuse embeddings/state via `micro_sam.precompute_state.*` and/or `micro_sam.util.*` (artifactized where feasible)

### Interactive Annotation (Phase 23)

*Note: The annotation UI is provided by upstream `micro_sam` napari widgets. Our work is exposing entrypoints and bridging artifacts to/from napari.*

- [ ] **GUI-01**: Agent can launch `micro_sam.sam_annotator.annotator_2d` via MCP `run()` with an image artifact pre-loaded
- [ ] **GUI-02**: Agent can launch `micro_sam.sam_annotator.annotator_3d` via MCP `run()` with a volumetric image artifact pre-loaded
- [ ] **GUI-03**: Agent can launch `micro_sam.sam_annotator.annotator_tracking` via MCP `run()` with a time series artifact pre-loaded
- [ ] **GUI-04**: User can export committed label results back to MCP artifact store as `LabelImageRef` (or `NativeOutputRef` bundle when multiple layers/metadata are produced)

### Infrastructure & Robustness (shared)

- [ ] **INFRA-01**: Interactive napari runs in an isolated subprocess and does not block the MCP server event loop
- [ ] **INFRA-02**: Clear, stable error is returned when interactive tools are invoked in a headless environment (no display)
- [ ] **INFRA-03**: Tool pack supports inference on CUDA, MPS (macOS), or CPU with automatic detection (device selection is tool-scoped config)

### Session & Optimization (Phase 24)

- [ ] **SESS-01**: Cached predictors/embeddings reduce latency for repeated calls on the same image (cache hit/miss visible in logs)
- [ ] **SESS-02**: Napari subprocess cleanup occurs automatically if the MCP server terminates
- [ ] **SESS-03**: User can resume a session after closing the viewer without losing progress (within the constraints of artifact + state storage)
- [ ] **SESS-04**: User sees progress indicators during model loading and embedding computation (at minimum via logs; optional richer progress artifacts)

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

| Requirement | Phase | Status |
|-------------|-------|--------|
| API-01 | Phase 22 | Complete |
| API-02 | Phase 22 | Complete |
| API-03 | Phase 22 | Complete |
| API-04 | Phase 23 | Pending |
| API-05 | Phase 22 | Complete |
| HEAD-01 | Phase 22 | Complete |
| HEAD-02 | Phase 22 | Complete |
| HEAD-03 | Phase 22 | Complete |
| HEAD-04 | Phase 22 | Complete |
| HEAD-05 | Phase 22 | Complete |
| HEAD-06 | Phase 22 | Complete |
| GUI-01 | Phase 23 | Pending |
| GUI-02 | Phase 23 | Pending |
| GUI-03 | Phase 23 | Pending |
| GUI-04 | Phase 23 | Pending |
| INFRA-01 | Phase 23 | Pending |
| INFRA-02 | Phase 23 | Pending |
| INFRA-03 | Phase 21 | Pending |
| SESS-01 | Phase 24 | Pending |
| SESS-02 | Phase 24 | Pending |
| SESS-03 | Phase 24 | Pending |
| SESS-04 | Phase 24 | Pending |

---
*Requirements defined: 2026-02-04; updated: 2026-02-05*
*Total: 22 requirements across 5 categories*
