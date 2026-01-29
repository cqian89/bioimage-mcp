---
phase: 13-dynamic-introspection-cache-reuse
plan: 06
subsystem: cli
tags: [argparse, filtering, bootstrap]

# Dependency graph
requires:
  - phase: 13-dynamic-introspection-cache-reuse
    provides: [Persistent CLI List Cache]
provides:
  - bioimage-mcp list --tool <tool_id> filtering
affects: [Phase 13 UAT, Cache Debugging]

# Tech tracking
tech-stack:
  added: []
  patterns: [CLI Argument Forwarding, Bootstrap Filtering]

key-files:
  created: [tests/unit/bootstrap/test_list_tool_filter.py]
  modified: [src/bioimage_mcp/cli.py, src/bioimage_mcp/bootstrap/list.py]

key-decisions:
  - "Support short name (e.g. trackpy) normalization to tools. prefix for easier UX."

# Metrics
duration: 20min
completed: 2026-01-29
---

# Phase 13 Plan 06: CLI Tool Filtering Summary

**Implemented `--tool` filtering for `bioimage-mcp list`, enabling targeted tool inspection and easier cache debugging.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-01-29T09:45:00Z
- **Completed:** 2026-01-29T10:04:52Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `--tool` argument to `bioimage-mcp list` CLI.
- Implemented filtering in `list_tools` supporting both exact IDs (e.g. `tools.trackpy`) and short names (e.g. `trackpy`).
- Added comprehensive unit tests for filtering logic.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add --tool option and wire through to list_tools()** - `08bdffb` (feat)
2. **Task 2: Add unit test for --tool filtering** - `e461315` (test)

**Plan metadata:** `[TBD]` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/cli.py` - Added `--tool` argument to parser.
- `src/bioimage_mcp/bootstrap/list.py` - Implemented `_filter_tools` helper and integrated into `list_tools`.
- `tests/unit/bootstrap/test_list_tool_filter.py` - New unit tests for filtering.

## Decisions Made
- **Short Name Normalization:** Allowed users to type `trackpy` instead of `tools.trackpy` to improve CLI ergonomics.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- **Env ID Validation:** Initial unit tests failed because mocked `env_id` did not start with `bioimage-mcp-`. Corrected mock data to satisfy Pydantic validators.
- **Manifest Cache:** Added monkeypatching for `_MANIFEST_CACHE` in unit tests to prevent interference from other tests using `load_manifests`.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for 13-07-PLAN.md (Cache key refinement).
- UAT Test 3 gap is closed.

---
*Phase: 13-dynamic-introspection-cache-reuse*
*Completed: 2026-01-29*
