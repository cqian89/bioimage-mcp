---
phase: 24-annotation-sessions
plan: 01
subsystem: api
tags: [microsam, cache, optimization, session]

# Dependency graph
requires:
  - phase: 22-mu-sam-headless-api
    provides: "Headless micro_sam execution and ObjectRef support"
  - phase: 23-microsam-interactive-bridge
    provides: "Interactive napari execution bridge"
provides:
  - "Session-scoped predictor/embedding cache for micro_sam"
  - "Deterministic cache keying using image identity and model type"
  - "Cache controls (force_fresh, explicit clear) with status visibility"
affects: [SESS-01, SESS-03]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Deterministic Object Cache Keying", "Side-channel Cache Status Warnings"]

key-files:
  created:
    - tests/unit/registry/test_microsam_adapter_session_cache.py
  modified:
    - src/bioimage_mcp/registry/dynamic/adapters/microsam.py
    - tools/microsam/manifest.yaml

key-decisions:
  - "Use a composite key of `microsam_predictor:{image_uri}:{model_type}` for deterministic predictor reuse."
  - "Store cached predictors in both `OBJECT_CACHE` (for URI-based resolution) and an adapter-owned `_cache_index` (for identity-based lookup)."
  - "Emit machine-readable cache status warnings (`MICROSAM_CACHE_HIT`, `MICROSAM_CACHE_MISS`, `MICROSAM_CACHE_RESET`) to provide transparency to agents."

patterns-established:
  - "Session-scoped state reuse: leveraging persistent workers to maintain heavy model state across multiple tool calls."

# Metrics
duration: 9 min
completed: 2026-02-06
---

# Phase 24 Plan 01: µSAM Session Cache Summary

**Implemented a deterministic session-scoped cache for micro_sam predictors and embeddings, enabling instant reuse for repeated calls on the same image and model.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-06T14:57:58Z
- **Completed:** 2026-02-06T15:07:05Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Added `_get_cache_key` and `_get_cached_predictor` helpers to `MicrosamAdapter` for deterministic lookup.
- Wired cache logic into `compute_embedding`, `automatic_mask_generator`, and generic `execute` paths.
- Implemented `force_fresh=true` support to bypass reuse and force recomputation.
- Added explicit `micro_sam.cache.clear` logic to wipe both object entries and metadata index.
- Established side-channel warning protocol for cache status visibility (HIT/MISS/RESET).
- Verified behavior with comprehensive unit coverage for hit/miss/reset and corruption scenarios.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add deterministic session cache keying and invalidation rules** - `084d028` (feat)
2. **Task 2: Wire cache controls into compute and segmentation paths** - `c13e272` (feat)
3. **Task 3: Add unit coverage for hit/miss/reset and clear semantics** - `b4e4e06` (test)

**Plan metadata:** (upcoming)

## Files Created/Modified
- `src/bioimage_mcp/registry/dynamic/adapters/microsam.py` - Core cache logic and status emission.
- `tools/microsam/manifest.yaml` - Exposed cache control parameters to the API.
- `tests/unit/registry/test_microsam_adapter_session_cache.py` - Deterministic coverage for cache contract.

## Decisions Made
- **Composite Cache Key:** Decided to use `image_uri + model_type` as the authoritative identity for a predictor. This prevents reusing a predictor initialized for one model (e.g., vit_b) when another is requested (e.g., vit_l).
- **Dual-Store Strategy:** Cached predictors are stored in `OBJECT_CACHE` to remain resolvable by their standard `obj://` URIs, but also tracked in `_cache_index` to support the "warm-start" requirement without the agent needing to pass an explicit `predictor` ObjectRef.
- **Side-channel Status:** Used the `adapter.warnings` mechanism to return machine-readable status codes. This keeps the primary return (the artifact) clean while providing the necessary feedback for performance monitoring.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed LRUCache.clear usage**
- **Found during:** Task 3 (Unit testing)
- **Issue:** Tried to call `OBJECT_CACHE.clear(key)` which failed because `clear()` takes no arguments.
- **Fix:** Switched to `OBJECT_CACHE.evict(key)` for specific entry removal.
- **Files modified:** src/bioimage_mcp/registry/dynamic/adapters/microsam.py
- **Verification:** Unit tests passed.
- **Commit:** b4e4e06 (Part of Task 3)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor fix to internal API usage; no impact on requirements.

## Issues Encountered
- **Mocking Tool Modules:** Encountered `ModuleNotFoundError` during unit tests because the adapter imports `bioimage_mcp_microsam` which is only available in the tool environment. Resolved by patching `sys.modules` in the test suite.

## Next Phase Readiness
- Session-scoped caching is verified and ready for integration.
- Ready for 24-02-PLAN.md (Harden worker shutdown and subprocess cleanup).
- Predictor reuse provides the necessary performance baseline for the upcoming interactive resume work.

---
*Phase: 24-annotation-sessions*
*Completed: 2026-02-06*
