---
phase: 13-dynamic-introspection-cache-reuse
plan: 02
subsystem: tools
tags: [trackpy, cache, introspection]

# Dependency graph
requires:
  - phase: 12-core-engine-ast-first
    provides: Unified introspection engine foundations
provides:
  - Trackpy dynamic discovery cache reuse
affects: [Phase 14 OME-Zarr Standardization]

# Tech tracking
tech-stack:
  added: []
  patterns: [Adapter-based dynamic discovery]

key-files:
  created: 
    - tools/trackpy/bioimage_mcp_trackpy/dynamic_discovery.py
    - tests/unit/tools/test_trackpy_dynamic_introspection_cache.py
  modified: 
    - tools/trackpy/bioimage_mcp_trackpy/entrypoint.py
    - tools/trackpy/bioimage_mcp_trackpy/introspect.py

key-decisions:
  - "Reuse Unified IntrospectionCache for trackpy instead of bespoke JSON cache"

patterns-established:
  - "Tool-specific discovery adapters for out-of-process metadata emission"

# Metrics
duration: 7 min
completed: 2026-01-28
---

# Phase 13 Plan 02: Trackpy Dynamic Introspection Cache Reuse Summary

**Trackpy meta.list now uses IntrospectionCache keyed by env lockfile hash, avoiding repeated module scanning.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-01-28T20:13:27Z
- **Completed:** 2026-01-28T20:20:45Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Implemented `TrackpyAdapter` to bridge trackpy introspection with unified discovery.
- Wired `IntrospectionCache` into `tools.trackpy` entrypoint.
- Added comprehensive unit tests for cache hits, misses, and invalidation.
- Ensured canonical `meta.list` result shape compatibility.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement trackpy cache reuse** - `f1a4689` (feat)
2. **Task 2: Add unit test for trackpy cache reuse/invalidation** - `ea9c57d` (test)

**Plan metadata:** `b591a27` (style: cleanup and format)

## Files Created/Modified
- `tools/trackpy/bioimage_mcp_trackpy/dynamic_discovery.py` - New adapter class
- `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` - meta.list wiring
- `tests/unit/tools/test_trackpy_dynamic_introspection_cache.py` - Unit coverage
- `tools/trackpy/bioimage_mcp_trackpy/introspect.py` - Style fixes
- `tests/integration/test_uat_rerun.py` - Formatting (unrelated but included in final commit)

## Decisions Made
- Reused `IntrospectionCache` and `discover_functions` from the core engine to ensure consistent invalidation behavior (lockfile hash gating) across all tool packs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Missing `manifest_version` in mock manifest caused Pydantic validation error during testing; fixed by adding it.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Trackpy dynamic discovery is now efficient and aligned with the unified engine.
- Ready for Phase 14: OME-Zarr Standardization.

---
*Phase: 13-dynamic-introspection-cache-reuse*
*Completed: 2026-01-28*
