---
phase: 20-strategize-and-execute-test-consolidation
plan: 03
subsystem: testing
tags: [pytest, smoke-tests, test-tiering]

# Dependency graph
requires:
  - phase: 20-strategize-and-execute-test-consolidation
    provides: [test consolidation strategy]
provides:
  - PR-gating smoke tier (smoke_pr)
  - Extended smoke tier (smoke_extended)
  - Tolerance-based numeric equivalence for Scipy
affects: [future PR gating, nightly coverage]

# Tech tracking
tech-stack:
  added: []
  patterns: [smoke tier markers, representative test selection]

key-files:
  created: []
  modified:
    - tests/smoke/test_equivalence_skimage.py
    - tests/smoke/test_equivalence_cellpose.py
    - tests/smoke/test_equivalence_trackpy.py
    - tests/smoke/test_equivalence_scipy.py
    - tests/smoke/test_equivalence_scipy_stats.py

key-decisions:
  - "Designated skimage (gaussian), cellpose, and trackpy as the PR-gating (smoke_pr) representative set."
  - "Demoted all other equivalence tests to smoke_extended to reduce PR latency."
  - "Standardized on tolerance-based numeric equivalence for Scipy to prevent platform/version flakiness."

# Metrics
duration: 20 min
completed: 2026-02-04
---

# Phase 20 Plan 03: Smoke Test Tiering and Tolerance Summary

**Retagged smoke tests into PR-gating vs extended tiers and implemented tolerance-based numeric equivalence for Scipy.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-02-04T12:40:48Z
- **Completed:** 2026-02-04T13:00:00Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- Established `smoke_pr` as the core PR-gating tier containing representative base and optional tool tests.
- Moved non-representative tests to `smoke_extended` for full/nightly coverage.
- Fixed overly strict bit-for-bit float comparisons in Scipy tests with robust tolerances.
- Standardized dataset markers (`uses_minimal_data`, `requires_lfs_dataset`) across equivalence suite.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace smoke_full with smoke_pr/smoke_extended and ensure dataset markers** - `d213760` (feat)
2. **Task 2: Replace bit-for-bit float comparisons with tolerance-based equivalence** - `22fd14d` (fix)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `tests/smoke/test_equivalence_cellpose.py` - Promoted to smoke_pr
- `tests/smoke/test_equivalence_trackpy.py` - Promoted to smoke_pr, updated dataset marker
- `tests/smoke/test_equivalence_skimage.py` - Split into smoke_pr (gaussian) and smoke_extended (sobel)
- `tests/smoke/test_equivalence_scipy.py` - Switched to tolerances, demoted to smoke_extended
- `tests/smoke/test_equivalence_scipy_stats.py` - Switched to tolerances, demoted to smoke_extended
- (Various other smoke tests) - Demoted smoke_full to smoke_extended

## Decisions Made
- Chose `skimage.filters.gaussian` as the representative base image filter for PR gating because it's widely used and stable.
- Kept `uses_minimal_data` for StarDist as it uses bundled package data, but ensured LFS marker for Trackpy which uses larger vendored datasets.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## Next Phase Readiness
- Smoke suite is now tiered and robust.
- Ready for final phase completion and project closure.

---
*Phase: 20-strategize-and-execute-test-consolidation*
*Completed: 2026-02-04*
