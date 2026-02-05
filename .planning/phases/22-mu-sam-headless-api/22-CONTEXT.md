# Phase 22: µSAM Headless API - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose the `micro_sam` Python library through MCP `run()` for headless segmentation (prompt-based segmentation + auto-mask), covering all `micro_sam.*` submodules except `micro_sam.sam_annotator`.

Interactive napari annotators are Phase 23. Predictor/embedding caching and other lifecycle optimizations are Phase 24.

</domain>

<decisions>
## Implementation Decisions

### Exposed API surface
- Expose a broad 1:1 surface of `micro_sam.*` functions (excluding `micro_sam.sam_annotator`), rather than a curated wrapper-only API.
- Use the upstream namespace in the MCP catalog: `micro_sam.*`.
- Stability contract: mirror upstream `micro_sam` surface/behavior (no separate stability layer).
- Include an explicit `compute_embedding` callable that returns an embedding artifact so callers can reuse embeddings across calls.
- Prefer generating `params_schema` via the unified dynamic introspection engine (`Introspector`) rather than hand-written schemas.

### Prompt schema & coordinates
- Support the full prompt surface that upstream `micro_sam` supports (e.g., points/boxes/mask prompts as applicable).
- Support multi-object prompts per call; return should accommodate multiple objects in a single result.
- If mask prompting/refinement is supported, the prompt mask is provided as an image artifact.
- Coordinate convention is left to match upstream `micro_sam` (exact ordering/normalization is Claude's discretion during planning).

### Supported image types
- Support both 2D images and 3D stacks (e.g., `YX`/`CYX` and `ZYX`/`CZYX`).
- Default behavior for Z-stacks is Claude's discretion during planning (choose what best matches upstream `micro_sam` capabilities).
- Default multi-channel handling is Claude's discretion during planning (choose what best matches upstream `micro_sam` expectations and common bioimage conventions).
- If an image is too large for the model/runtime, fail with an actionable error (do not auto-downsample or auto-tile by default).

### Return artifacts & metadata
- Primary segmentation output is a label image.
- Labeling convention: background=0, objects=1..N.
- Return minimal metadata by default.
- Do not return logits/probability maps by default (may be supported behind an explicit opt-in).

### Claude's Discretion
- Exact prompt coordinate convention (XY vs YX, pixel vs normalized, 0/1-based) based on upstream `micro_sam` expectations.
- Default Z-stack segmentation mode (slice-wise vs reject vs stack-aware) based on upstream `micro_sam` support.
- Default interpretation of non-RGB multi-channel images.
- Optional/advanced outputs (e.g., logits) and how they are requested.

</decisions>

<specifics>
## Specific Ideas

- Keep the MCP surface aligned with upstream `micro_sam` (naming + behavior) to reduce wrapper drift.
- Use dynamic introspection (Introspector) so the exposed surface stays in sync with upstream signatures/docstrings.

</specifics>

<deferred>
## Deferred Ideas

- Phase 23: launching napari-based annotators (interactive bridge).
- Phase 24: predictor caching + standardized embedding storage/optimization.

</deferred>

---

*Phase: 22-mu-sam-headless-api*
*Context gathered: 2026-02-05*
