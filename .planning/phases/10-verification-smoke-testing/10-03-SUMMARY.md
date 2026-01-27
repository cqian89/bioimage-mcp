---
phase: 10-verification-smoke-testing
plan: 03
subsystem: testing
tags: [pytest, scipy, discovery, smoke-tests]

# Dependency graph
requires:
  - phase: 09-spatial-signal-processing
    provides: [Spatial and Signal processing wrappers]
provides:
  - [Dataset presence guardrail tests]
  - [SciPy tool discovery smoke tests]
affects: [Phase 10 verification runs]

# Tech tracking
tech-stack:
  added: []
  patterns: [Live-server discovery verification]

key-files:
  created: [tests/smoke/test_smoke_scipy_discovery.py]
  modified: [tests/smoke/test_smoke_scipy_datasets.py]

key-decisions:
  - "Decided to use explicit path-based listing in discovery tests to handle non-recursive catalog structure."

patterns-established:
  - "Discovery validation pattern: list root -> list environment -> assert package presence."

# Metrics
duration: 15 min
completed: 2026-01-27
---

# Phase 10 Plan 03: Dataset + Discovery Guardrail Summary

**Added guardrail smoke tests asserting required dataset presence and SciPy tool discoverability across all major submodules.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-01-27T08:55:00Z
- **Completed:** 2026-01-27T09:10:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Implemented `test_smoke_scipy_datasets.py` to fail fast if `test.tif` or `measurements.csv` are missing.
- Implemented `test_smoke_scipy_discovery.py` to validate hierarchical discovery (`list`) and schema correctness (`describe`).
- Verified that all SciPy submodules (`ndimage`, `stats`, `spatial`, `signal`) are correctly exposed and introspected on a live server.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add dataset presence smoke test** - `69b8287` (test)
2. **Task 2: Add SciPy discovery smoke test** - `62331b0` (test)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `tests/smoke/test_smoke_scipy_datasets.py` - Verifies presence of critical datasets.
- `tests/smoke/test_smoke_scipy_discovery.py` - Verifies discovery of SciPy tools.

## Decisions Made
- Used explicit path-based listing (`list(path="base")`) in smoke tests because the MCP `list` tool returns only immediate children of the specified node, not a full recursive tree by default.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- The initial `list` test failed because it expected a `nodes` key and recursive children list, whereas the API returns an `items` key and a `children` count summary. Fixed by updating the test to use `items` and manual traversal.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for full verification runs in Phase 10.
- SciPy surface area is confirmed stable and discoverable.

---
*Phase: 10-verification-smoke-testing*
*Completed: 2026-01-27*
