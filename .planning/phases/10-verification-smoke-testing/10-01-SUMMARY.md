---
phase: 10-verification-smoke-testing
plan: 01
subsystem: testing
tags: [scipy, smoke-test, ndimage, stats, spatial, signal, live-server]

# Dependency graph
requires:
  - phase: 09-spatial-signal
    provides: [Spatial metrics, KDTree persistence, Signal processing]
provides:
  - Parametrized smoke matrix for the four SciPy submodules
  - Live-server verification harness for SciPy integration
affects: [10-02-PLAN.md, 10-03-PLAN.md]

# Tech tracking
tech-stack:
  added: []
  patterns: [Parametrized smoke matrix, Live server tool calls]

key-files:
  created: [tests/smoke/test_smoke_scipy_submodules.py]
  modified: [tools/base/bioimage_mcp_base/ops/io.py, src/bioimage_mcp/registry/dynamic/adapters/scipy_stats.py]

key-decisions:
  - "Use a temporary directory within 'datasets/smoke_tmp' for dynamically created CSVs to ensure live server read access."
  - "Map 'mean_table' to 'scipy.stats.tmean' in the adapter to provide a standard mean statistic."
  - "Expect 'NativeOutputRef' for SciPy stats functions returning structured JSON payloads."

patterns-established:
  - "Smoke matrix coverage: at least one representative tool per submodule in minimal mode, 6-10 in full mode."

# Metrics
duration: 25min
completed: 2026-01-27
---

# Phase 10 Plan 01: SciPy Smoke Test Matrix Summary

**Live-server smoke test matrix implemented for ndimage, stats, spatial, and signal submodules, passing 4 minimal and 19 full end-to-end execution tests.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-01-27T08:58:25Z
- **Completed:** 2026-01-27T09:23:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created SciPy submodule smoke test harness with input helpers and assertions.
- Implemented minimal and full smoke matrices covering ndimage, stats, spatial, and signal.
- Verified 4 minimal smoke tests and 19 full smoke tests passing via a live MCP server.
- Fixed KDTree build/query lifecycle roundtrip in smoke tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SciPy submodule smoke test harness (inputs + asserts)** - `6066ce7` (feat)
2. **Task 2: Implement minimal + full smoke matrices for 4 SciPy submodules** - `fea1624` (feat)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `tests/smoke/test_smoke_scipy_submodules.py` - Parametrized smoke test matrix
- `tools/base/bioimage_mcp_base/ops/io.py` - Fixed TableRef model alignment
- `src/bioimage_mcp/registry/dynamic/adapters/scipy_stats.py` - Fixed mean mapping to tmean

## Decisions Made
- Used a temporary directory within `datasets/smoke_tmp` for dynamically created CSVs because the live server's `allowed_read` configuration includes the `datasets` folder but might not include arbitrary `/tmp` paths.
- Mapped `mean_table` to `scipy.stats.tmean` because `scipy.stats` lacks a bare `mean` function (it provides `tmean`, `gmean`, `hmean`).
- Standardized on `NativeOutputRef` for stats wrappers returning dictionaries to allow flexible structured JSON output.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing metadata.columns in TableRef**
- **Found during:** Task 1 (Harness sanity)
- **Issue:** `base.io.table.load` was returning `columns` and `row_count` at the top level, but the core server's `TableRef` model requires them inside a `metadata` field of type `TableMetadata`.
- **Fix:** Updated `tools/base/bioimage_mcp_base/ops/io.py` to correctly populate the `metadata` field with `columns` (including `name` and `dtype`) and `row_count`.
- **Files modified:** `tools/base/bioimage_mcp_base/ops/io.py`
- **Verification:** `test_scipy_harness_sanity` passes.
- **Committed in:** `6066ce7`

**2. [Rule 1 - Bug] module 'scipy.stats' has no attribute 'mean'**
- **Found during:** Task 2 (Full matrix implementation)
- **Issue:** The `ScipyStatsAdapter` was attempting to call `scipy.stats.mean` for `mean_table`, but that attribute does not exist.
- **Fix:** Changed the function name to `tmean_table` and updated the adapter to use `tmean`.
- **Files modified:** `src/bioimage_mcp/registry/dynamic/adapters/scipy_stats.py`, `tests/smoke/test_smoke_scipy_submodules.py`
- **Verification:** `test_scipy_full_matrix` passes for `tmean_table`.
- **Committed in:** `fea1624`

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both auto-fixes were necessary for end-to-end execution. No scope creep.

## Issues Encountered
- Live server read permissions: Initial attempts to load CSVs from `/tmp` failed because the server's filesystem policy didn't include it. Resolved by using a directory under `datasets/`.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for `10-02-PLAN.md` (Strict equivalence tests).
- Smoke tests provide a solid baseline for catching regressions during further hardening.

---
*Phase: 10-verification-smoke-testing*
*Completed: 2026-01-27*
