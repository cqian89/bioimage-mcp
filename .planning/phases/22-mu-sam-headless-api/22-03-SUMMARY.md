---
phase: 22-mu-sam-headless-api
plan: 03
subsystem: api
tags: micro_sam, sam, segmentation, headless, mcp

# Dependency graph
requires:
  - phase: 22-mu-sam-headless-api
    provides: "MicrosamAdapter skeleton and discovery"
provides:
  - "Headless micro_sam execution via MCP run()"
  - "micro_sam.compute_embedding static function for state reuse"
  - "ObjectRef support for SAM predictors and embeddings"
affects:
  - "Phase 23: Interactive Annotation"
  - "Phase 24: Cache optimization"

# Tech tracking
tech-stack:
  added: ["micro_sam"]
  patterns: ["Artifact-first headless segmentation", "ObjectRef state reuse"]

key-files:
  created: ["src/bioimage_mcp/registry/dynamic/adapters/microsam.py"]
  modified: ["tools/microsam/manifest.yaml", "tools/microsam/bioimage_mcp_microsam/entrypoint.py", "src/bioimage_mcp/registry/dynamic/adapters/__init__.py"]

key-decisions:
  - "Directly route micro_sam.* functions to MicrosamAdapter.execute for 1:1 API mapping."
  - "Implement micro_sam.compute_embedding as a static function that returns a predictor ObjectRef."
  - "Use OME-Zarr as the primary interchange format for label outputs."

patterns-established:
  - "Heavy object caching: Returning non-serializable objects as ObjectRefs for session-scoped reuse."
  - "Prompt coercion: Automatically converting JSON list prompts to numpy arrays for upstream tools."

# Metrics
duration: 15 min
completed: 2026-02-05
---

# Phase 22 Plan 03: µSAM Headless API Summary

**Headless micro_sam segmentation API with artifact-based I/O and predictor state reuse via ObjectRef**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-05T17:59:09Z
- **Completed:** 2026-02-05T18:06:45Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Implemented `MicrosamAdapter.execute` supporting both prompt-based and automatic segmentation.
- Added `micro_sam.compute_embedding` static function to enable precomputing and reusing SAM embeddings.
- Bridged `BioImageRef` inputs to `micro_sam` using `bioio` for native dimension preservation.
- Established `ObjectRef` pattern for heavy SAM predictor objects, enabling state reuse across calls.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add micro_sam.compute_embedding as a static MCP function** - `9e6d662` (feat)
2. **Task 2: Implement MicrosamAdapter.execute for headless segmentation** - `32a673d` (feat)
3. **Task 3: Wire microsam entrypoint execute dispatch** - `abdc0d8` (feat)

**Additional cleanup:** `b1b5f65` (chore: register microsam adapter)

## Files Created/Modified
- `src/bioimage_mcp/registry/dynamic/adapters/microsam.py` - Core execution logic for micro_sam functions.
- `tools/microsam/manifest.yaml` - Added compute_embedding and cache.clear static functions.
- `tools/microsam/bioimage_mcp_microsam/entrypoint.py` - Routed requests to the adapter.
- `src/bioimage_mcp/registry/dynamic/adapters/__init__.py` - Registered the microsam adapter.

## Decisions Made
- Directly routed `micro_sam.*` functions to `MicrosamAdapter.execute` to maintain a 1:1 mapping with the upstream library.
- Used the `OBJECT_CACHE` to store `SamPredictor` objects, allowing subsequent segmentation calls to use precomputed embeddings.
- Ensured label outputs are cast to `int32` for compatibility with OME-Zarr and downstream labeling tools.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **Linter Errors:** Encountered Ruff errors regarding exception handling and module imports; fixed by using `raise ... from` and `# noqa: E402`.
- **Untracked Files:** Discovered `MicrosamAdapter` and its tests were untracked; staged and committed them as part of Task 2.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for Phase 23: Interactive Annotation.
- Headless API is verified via discovery tests; full integration tests will follow in subsequent phases.

---
*Phase: 22-mu-sam-headless-api*
*Completed: 2026-02-05*
