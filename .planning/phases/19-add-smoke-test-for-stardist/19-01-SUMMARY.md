---
phase: 19-add-smoke-test-for-stardist
plan: 1
subsystem: testing
tags: [pytest, stardist, smoke-test, mcp]

# Dependency graph
requires:
  - phase: 16-add-stardist-tool-pack
    provides: [bioimage-mcp-stardist conda environment, stardist tool pack]
provides:
  - StarDist smoke equivalence test (MCP vs native baseline)
  - Native StarDist baseline reference script
affects: [future-ci-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [Native Baseline Equivalence Testing]

key-files:
  created: [tests/smoke/test_equivalence_stardist.py, tests/smoke/reference_scripts/stardist_baseline.py]
  modified: [pytest.ini, tests/smoke/conftest.py]

key-decisions:
  - "Use 'datasets/smoke_tmp' for smoke test input image to comply with server read-path restrictions."
  - "Added convenience marker 'requires_stardist' to conftest.py for easier environment-gated test skipping."

patterns-established:
  - "Pattern: Redirect tool pack baseline stdout to stderr to preserve JSON-on-stdout contract for NativeExecutor."

# Metrics
duration: 6 min
completed: 2026-02-04
---

# Phase 19 Plan 1: StarDist Smoke Test Summary

**StarDist smoke equivalence test implemented, matching MCP inference against native StarDist baseline with IoU > 0.95.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-04T00:16:33Z
- **Completed:** 2026-02-04T00:22:52Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Registered `requires_stardist` pytest marker in `pytest.ini` and `conftest.py`.
- Created `tests/smoke/reference_scripts/stardist_baseline.py` using `stardist.data.test_image_nuclei_2d()` for reproducible ground truth.
- Implemented `tests/smoke/test_equivalence_stardist.py` which validates full MCP pipeline (load -> model init -> predict) against native execution.
- Verified that the test passes in `smoke-full` mode and adheres to marker enforcement rules.

## Task Commits

Each task was committed atomically:

1. **Task 1: Register and wire `requires_stardist` pytest marker** - `afa3377` (chore)
2. **Task 2: Add native StarDist baseline script** - `ac68552` (feat)
3. **Task 3: Add StarDist equivalence smoke test** - `c565893` (test)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `pytest.ini` - Added `requires_stardist` marker.
- `tests/smoke/conftest.py` - Updated `check_required_env` for environment-specific convenience markers.
- `tests/smoke/reference_scripts/stardist_baseline.py` - Native baseline script for StarDist.
- `tests/smoke/test_equivalence_stardist.py` - MCP vs Native equivalence smoke test.

## Decisions Made
- Used `datasets/smoke_tmp` for temporary test data to ensure the MCP server has read access (paths outside of the repo/datasets are restricted).
- Added `requires_stardist` as a convenience marker in `conftest.py` mapping to the `bioimage-mcp-stardist` conda environment, improving developer experience.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MCP Load failure due to restricted read paths**
- **Found during:** Task 3 (test execution)
- **Issue:** Using `tmp_path` (usually `/tmp/...`) for input images caused MCP `base.io.bioimage.load` to fail because the server is configured to only read from specific allowed directories.
- **Fix:** Changed the test to use `datasets/smoke_tmp` for the input image, which is an allowed read path.
- **Files modified:** `tests/smoke/test_equivalence_stardist.py`
- **Verification:** Test passed after path update.
- **Committed in:** `c565893` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minimal. Ensuring tests use allowed paths is standard practice in this repo.

## Issues Encountered
- Network flakiness during model download was handled by the implemented 3-attempt retry logic in both baseline and MCP test paths.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- StarDist tool pack is now fully verified with an E2E smoke test.
- The project is ready for any further tool pack integrations or CI automation improvements.

---
*Phase: 19-add-smoke-test-for-stardist*
*Completed: 2026-02-04*
