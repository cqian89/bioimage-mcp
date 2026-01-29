---
phase: 13-dynamic-introspection-cache-reuse
plan: 08
subsystem: bootstrap
tags: [caching, introspection, cli]

# Dependency graph
requires:
  - phase: 13-dynamic-introspection-cache-reuse
    provides: [persistent CLI list cache, dynamic introspection cache reuse]
provides:
  - CLI cache-hit path now validates underlying per-tool dynamic cache presence
  - bioimage-mcp list now acts as a reliable cache repair/warmer step
affects: [v0.4.0 release]

# Tech tracking
tech-stack:
  added: []
  patterns: [cache-hit invariant validation]

key-files:
  created: []
  modified: [src/bioimage_mcp/bootstrap/list.py, src/bioimage_mcp/runtimes/meta_protocol.py, tests/unit/bootstrap/test_list_cache.py]

key-decisions:
  - "Validate dynamic cache presence on CLI cache-hit: Ensures that deleting a per-tool cache file triggers its regeneration even when the higher-level CLI cache is still valid."
  - "Propagate top-level introspection_source in meta.list: Critical for detecting tools that use dynamic discovery (like trackpy) from the cached function metadata."

patterns-established:
  - "Cache-hit invariant validation: Checking the existence of downstream dependencies during a fast-path cache hit to ensure system integrity."

# Metrics
duration: 20 min
completed: 2026-01-29
---

# Phase 13 Plan 08: Dynamic Introspection Cache Reuse Gap Closure Summary

**Ensured `bioimage-mcp list` regenerates missing per-tool dynamic caches even on CLI cache hits by adding invariant validation to the fast path.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-01-29T11:00:00Z
- **Completed:** 2026-01-29T11:20:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Modified `list_tools` to check for `introspection_cache.json` existence for tools using `dynamic_discovery`.
- Fixed `parse_meta_list_result` to propagate `introspection_source` from tool `meta.list` results to function entries, enabling detection of dynamic discovery tools from the CLI cache.
- Added a comprehensive regression test covering cold path, missing dynamic cache miss, and warm hit scenarios.

## Task Commits

Each task was committed atomically:

1. **Task 1: Invalidate CLI list_tools cache hit when per-tool dynamic cache is missing** - `7617f89` (fix)
2. **Task 2: Add regression test for cache-hit + missing dynamic cache fallback** - `a0b2cd7` (test)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/bootstrap/list.py` - Added dynamic cache existence check to fast path.
- `src/bioimage_mcp/runtimes/meta_protocol.py` - Propagated top-level introspection_source to function entries.
- `tests/unit/bootstrap/test_list_cache.py` - Added regression test for dynamic cache fallback.

## Decisions Made
- **Propagate introspection_source in meta_protocol**: This was necessary because the CLI-level cache only stores function summaries, and without knowing which functions came from dynamic discovery, we couldn't know which tools needed a `introspection_cache.json` check.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Propagated introspection_source in meta_protocol**
- **Found during:** Task 1
- **Issue:** `tools.trackpy` functions were missing the `dynamic_discovery` source in the CLI cache because `parse_meta_list_result` dropped the top-level source field.
- **Fix:** Updated `parse_meta_list_result` to copy the top-level `introspection_source` to each function entry if not already present.
- **Files modified:** src/bioimage_mcp/runtimes/meta_protocol.py
- **Verification:** `bioimage-mcp list --json` now correctly shows `runtime:dynamic_discovery` for trackpy.
- **Committed in:** 7617f89

---

**Total deviations:** 1 auto-fixed ([Rule 2])
**Impact on plan:** Essential for making the fix work for tools like trackpy that use out-of-process dynamic discovery.

## Issues Encountered
None

## User Setup Required
None

## Next Phase Readiness
Phase 13 is now fully complete with all identified UAT gaps closed. Ready for Phase 14: OME-Zarr Standardization.

---
*Phase: 13-dynamic-introspection-cache-reuse*
*Completed: 2026-01-29*
