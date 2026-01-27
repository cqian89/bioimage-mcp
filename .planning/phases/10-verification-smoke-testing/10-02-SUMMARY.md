---
phase: 10-verification-smoke-testing
plan: 02
subsystem: testing
tags: [scipy, smoke-test, equivalence, parity]

# Dependency graph
requires:
  - phase: 09-spatial-signal-processing
    provides: [Spatial and signal processing wrappers]
provides:
  - Bit-for-bit gaussian_filter equivalence test
  - Bit-for-bit ttest_ind_table equivalence test
  - Native reference scripts for SciPy operations
affects: [future-smoke-tests]

# Tech tracking
tech-stack:
  added: []
  patterns: [Strict bit-for-bit equivalence tests, Native reference scripts]

key-files:
  created: 
    - tests/smoke/test_equivalence_scipy_stats.py
    - tests/smoke/reference_scripts/scipy_stats_baseline.py
  modified:
    - tests/smoke/test_equivalence_scipy.py
    - tests/smoke/reference_scripts/scipy_baseline.py
    - src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py
    - src/bioimage_mcp/registry/dynamic/adapters/scipy_stats.py

key-decisions:
  - "Enforce float32 casting for filters/transforms in ScipyNdimageAdapter to ensure bit-for-bit parity with native SciPy (which often promotes uint16 to float64/float32)."
  - "Include parameters and sample sizes in ScipyStatsAdapter JSON output to facilitate detailed equivalence verification."

patterns-established:
  - "Pattern: Native Reference Script. Using a standalone script in the tool's conda environment to produce a 'ground truth' result for bit-for-bit comparison."

# Metrics
duration: 35 min
completed: 2026-01-27
---

# Phase 10 Plan 02: Strict Equivalence Summary

**Strict bit-for-bit equivalence tests for Gaussian blur and T-test against native SciPy baselines, with adapter enhancements for precision and diagnostic clarity.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-01-27T08:59:11Z
- **Completed:** 2026-01-27T09:34:11Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Tightened `gaussian_filter` equivalence to bit-for-bit parity by forcing float32 precision on both MCP and native baseline.
- Added a new strict equivalence test for `ttest_ind_table` comparing structured JSON outputs exactly.
- Enhanced `ScipyNdimageAdapter` with automatic float32 promotion for filters and transforms, preventing rounding errors on uint16 inputs.
- Improved adapter JSON serialization to handle numpy dtypes and non-serializable objects (modules, functions) by casting to strings.
- Standardized the Native Reference Script pattern for reliable regression testing.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tighten gaussian_filter equivalence to bit-for-bit** - `9fd9dc1` (feat)
2. **Task 2: Add bit-for-bit t-test equivalence (ttest_ind_table)** - `0e02766` (feat)

**Post-task fix:** `1155523` (fix) - Updated smoke tests to expect NativeOutputRef for stats.

**Plan metadata:** `docs(10-02): complete strict equivalence plan` (pending)

## Files Created/Modified
- `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py` - Added float32 casting and improved JSON serialization.
- `src/bioimage_mcp/registry/dynamic/adapters/scipy_stats.py` - Included params/sample sizes in output.
- `tests/smoke/test_equivalence_scipy.py` - Enforced bit-for-bit check.
- `tests/smoke/reference_scripts/scipy_baseline.py` - Forced float32 output.
- `tests/smoke/test_equivalence_scipy_stats.py` - New equivalence test.
- `tests/smoke/reference_scripts/scipy_stats_baseline.py` - New native baseline script.

## Decisions Made
- **Automatic Float32 Promotion:** Decided to automatically cast uint16 images to float32 for operations known to produce float results (filters, transforms). This ensures precision parity with native SciPy which defaults to float64 or input-type-preserving float promotion.
- **Stable JSON Contract:** Established a stable JSON contract for statistical tests including not just results (statistic, p-value) but also execution context (params, sample sizes) to enable strict comparison.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] NameError in ScipyNdimageAdapter.execute**
- **Found during:** Task 1
- **Issue:** `func_name` was used before being defined in the new float32 casting logic.
- **Fix:** Moved function name resolution to the top of the `execute` method.
- **Files modified:** `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py`
- **Verification:** Gaussian filter test passed.
- **Committed in:** `9fd9dc1`

**2. [Rule 1 - Bug] JSON serialization failure for numpy dtypes**
- **Found during:** Task 2
- **Issue:** `json.dump` failed when the Scipy result contained numpy `DType` objects (e.g. `Float64DType`).
- **Fix:** Updated `_to_native` helper to cast dtypes and other non-serializable objects to strings.
- **Files modified:** `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py`
- **Verification:** T-test equivalence test passed.
- **Committed in:** `9fd9dc1`

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes were necessary for correct tool execution and serialization. No scope creep.

## Issues Encountered
- **Path Permissions:** Encounted `PATH_NOT_ALLOWED` error when writing test CSVs to `/tmp`. Resolved by using `datasets/tmp` which is in the server's allowlist.

## Next Phase Readiness
- Ready for 10-03-PLAN.md (Dataset + discovery guardrail smoke tests).
- All core SciPy submodules now have at least minimal smoke coverage or strict equivalence verification.

---
*Phase: 10-verification-smoke-testing*
*Completed: 2026-01-27*
