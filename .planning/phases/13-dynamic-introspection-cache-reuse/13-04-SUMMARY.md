---
phase: 13-dynamic-introspection-cache-reuse
plan: 04
subsystem: tools
tags: [trackpy, cache, introspection, project_root]

# Dependency graph
requires:
  - phase: 13-dynamic-introspection-cache-reuse
    provides: Trackpy dynamic discovery cache reuse foundations
provides:
  - Robust project_root detection for trackpy
  - Verified trackpy introspection cache creation
affects: [Phase 14 OME-Zarr Standardization]

# Tech tracking
tech-stack:
  added: []
  patterns: [Environment-aware project root detection]

key-files:
  created: []
  modified:
    - tools/trackpy/bioimage_mcp_trackpy/entrypoint.py
    - tests/unit/tools/test_trackpy_dynamic_introspection_cache.py
    - tests/unit/tools/test_trackpy_meta_protocol.py

key-decisions:
  - "Support BIOIMAGE_MCP_PROJECT_ROOT env var for explicit project root override"
  - "Use CWD-based heuristic for project root detection in installed environments"

patterns-established:
  - "Robust project root discovery for lockfile-based caching outside repo layout"

# Metrics
duration: 8 min
completed: 2026-01-28
---

# Phase 13 Plan 04: Robust Trackpy Introspection Cache Summary

**Trackpy now reliably writes and reuses introspection caches in installed environments by using robust project_root detection (env var + CWD heuristic).**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-28T23:06:45Z
- **Completed:** 2026-01-28T23:14:42Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Implemented robust `project_root` detection in `tools.trackpy` entrypoint.
- Added `BIOIMAGE_MCP_PROJECT_ROOT` environment variable override.
- Added CWD-based `_find_project_root` heuristic to support warm cache in installed tool envs.
- Extended unit tests to verify cache file creation and hit/miss behavior with real heuristics.
- Fixed pre-existing test regressions by restoring module-level introspection imports.

## Task Commits

Each task was committed atomically:

1. **Task 1: Make trackpy project_root detection robust** - `7b821a9` (feat)
2. **Task 2: Add unit tests for heuristics and cache creation** - `bcbae2d` (test)

**Regression fix:** `ebc4c02` (fix: restore trackpy testability and fix source metadata)

## Files Created/Modified
- `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` - Robust detection logic + module-level imports
- `tests/unit/tools/test_trackpy_dynamic_introspection_cache.py` - Coverage for CWD/Env var heuristics
- `tests/unit/tools/test_trackpy_meta_protocol.py` - Fixed source metadata and test patching

## Decisions Made
- **Explicit Project Root:** Added `BIOIMAGE_MCP_PROJECT_ROOT` to allow core server or users to specify the root when heuristics fail.
- **CWD Heuristic:** Enabled searching for `envs/` from the current working directory, which is reliable when the MCP server runs from the project root.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing trackpy test regressions**
- **Found during:** Overall verification (post-task 2)
- **Issue:** Previous plans moved imports inside functions, breaking unit tests that patched `entrypoint.py` at the module level.
- **Fix:** Restored `introspect_module`, `introspect_function`, and `get_trackpy_version` to module-level imports in `entrypoint.py`.
- **Files modified:** `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py`
- **Verification:** `pytest tests/unit/tools/test_trackpy_meta_protocol.py` passes.
- **Committed in:** `ebc4c02`

## Issues Encountered
- `introspection_source` in `test_handle_meta_list_shape` was outdated (`module_scan` vs `dynamic_discovery`); fixed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Trackpy cache writing is now verified and robust.
- Ready for Phase 14: OME-Zarr Standardization.

---
*Phase: 13-dynamic-introspection-cache-reuse*
*Completed: 2026-01-28*
