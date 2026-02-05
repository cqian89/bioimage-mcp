# Phase 22: µSAM Headless API

## Goal
Expose the `micro_sam` Python library API (all submodules except `micro_sam.sam_annotator`) as MCP-callable functions.

Function IDs MUST follow the repository convention:

`micro_sam.<submodule>.<callable>`

## Scope Boundaries
- **In-Scope:** All public callables in `micro_sam.*` EXCEPT `micro_sam.sam_annotator`.
- **Out-of-Scope:** `micro_sam.sam_annotator` only (Phase 23).

Notes:
- Some `micro_sam` modules are path-centric (e.g., training/evaluation helpers). They are still in-scope for exposure, but may initially accept path-like `string` params and/or return `NativeOutputRef` until artifact-first equivalents are introduced.

## Deliverables
1. **MicrosamAdapter:** A new dynamic adapter in `src/bioimage_mcp/registry/dynamic/adapters/microsam.py` that:
   - Discovers `micro-sam` API functions.
   - Maps them to `micro_sam.<submodule>.<callable>` IDs.
   - Handles `ObjectRef` for predictors and embeddings.
2. **Tool Pack Manifest:** Update `tools/microsam/manifest.yaml` with `dynamic_sources`.
3. **Execution Logic:** Implement execution-time coercion to preserve artifact boundary where feasible:
   - `BioImageRef` / `LabelImageRef` -> `numpy.ndarray`
   - `ObjectRef` -> resolved python objects
   - image-like outputs -> `BioImageRef` / `LabelImageRef`
   - complex outputs -> `NativeOutputRef`
4. **Smoke Tests:** Minimal verification that at least one prompt-based segmentation and one automatic segmentation callable run end-to-end via MCP `run()`.

## Success Criteria
1. `bioimage-mcp list` includes `micro_sam.prompt_based_segmentation.segment_from_points` (and other `micro_sam.*` callables), excluding `micro_sam.sam_annotator.*`.
2. `bioimage-mcp describe micro_sam.prompt_based_segmentation.segment_from_points` returns a valid JSON schema derived from AST + docstrings.
3. `bioimage-mcp run micro_sam.prompt_based_segmentation.segment_from_points` produces a valid mask artifact from an input image + point prompts.

## Plan
- 22-01: Add `dynamic_sources` to `tools/microsam/manifest.yaml` for `micro_sam.*` (exclude `micro_sam.sam_annotator`).
- 22-02: Implement `MicrosamAdapter.discover()` using `Introspector` + module scanning + include/exclude patterns.
- 22-03: Implement `MicrosamAdapter.execute()` with artifact boundary coercion and `ObjectRef` lifecycle support.
- 22-04: Add smoke tests for (a) prompt-based segmentation, (b) automatic/instance segmentation.
