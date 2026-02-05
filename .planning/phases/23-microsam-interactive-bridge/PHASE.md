# Phase 23: µSAM Interactive Bridge

## Goal
Enable launching the `micro-sam` interactive annotators (Napari-based) from the MCP server.

Function IDs MUST follow:

`micro_sam.sam_annotator.<callable>`

## Scope Boundaries
- **In-Scope:** Public callables in `micro_sam.sam_annotator` (e.g., `annotator_2d`, `annotator_3d`, `annotator_tracking`, `image_series_annotator`, and nested helpers documented upstream).
- **Challenges:** Remote execution vs Local GUI. This phase assumes the MCP client and server share a display environment (e.g., local workstation) or uses a remote desktop solution.

## Deliverables
1. **Interactive Tools:** Expose `micro_sam.sam_annotator.*` callables via MCP `run()`.
2. **Context Passing:** Provide a supported way to pass `BioImageRef` (and optional precomputed `ObjectRef` state) into the annotator.
3. **Session Capture:** Capture the user-committed labels/masks back into MCP as `LabelImageRef` (or a `NativeOutputRef` bundle if multiple layers/metadata are produced).

## Success Criteria
1. `bioimage-mcp list` includes `micro_sam.sam_annotator.annotator_2d`.
2. Running `micro_sam.sam_annotator.annotator_2d` via MCP launches a napari window with the specified image pre-loaded.
3. If embeddings/state were precomputed in Phase 22, they can be loaded into the interactive session.

## Plan
- 23-01: Extend `tools/microsam/manifest.yaml` `dynamic_sources` to include `micro_sam.sam_annotator`.
- 23-02: Implement display-environment checks and clear error reporting for headless environments.
- 23-03: Implement artifact-to-napari loading (image + optional state) and napari-to-artifact export for committed labels.
