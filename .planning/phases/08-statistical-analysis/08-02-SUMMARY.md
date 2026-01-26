---
phase: 08-statistical-analysis
plan: 08-02
subsystem: stats
tags: [scipy, stats, hypothesis-test, distribution, json, pandas]

# Dependency graph
requires:
  - phase: 08-01
    provides: [Composite Scipy Adapter, stats discovery infrastructure]
provides:
  - Discovered stats wrappers (describe, ttest, ANOVA, ks_2samp)
  - Discovered probability distribution methods (pdf, cdf, ppf, pmf)
  - Execution logic for table-to-json and distribution-to-json patterns
affects: [08-03, 10-verification]

# Tech tracking
tech-stack:
  added: [scipy.stats wrappers]
  patterns: [Table-to-JSON normalization, distribution freezing]

key-files:
  created: []
  modified:
    - src/bioimage_mcp/registry/dynamic/adapters/scipy_stats.py
    - src/bioimage_mcp/registry/dynamic/adapters/scipy.py
    - src/bioimage_mcp/registry/dynamic/models.py
    - src/bioimage_mcp/registry/loader.py

key-decisions:
  - "Curated Stats Wrappers: Exposing specific *_table wrappers instead of raw scipy.stats functions ensures reliable artifact I/O and easier agent consumption."
  - "TABLE_PAIR_TO_JSON pattern: Introduced a specific I/O pattern for two-sample tests to simplify port mapping for t-tests and KS-tests."
  - "Auto-column Selection: Defaulting to the first numeric column when none is provided enables high-success 'yolo' execution for simple tables."

patterns-established:
  - "Table-friendly stats wrappers: Naming convention *_table for functions that load artifacts and select columns."
  - "Distribution method routing: Dynamically parsing scipy.stats.{dist}.{method} to enable a broad set of probability functions."

# Metrics
duration: 25 min
completed: 2026-01-26
---

# Phase 08 Plan 2: Statistical Analysis Wrappers Summary

**Implemented `scipy.stats` table-friendly wrappers for summary statistics and hypothesis tests, plus curated probability distribution methods with JSON serialization.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-01-26T12:00:00Z
- **Completed:** 2026-01-26T12:25:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- **Discovery Implementation**: Replaced the stats stub with a real discovery engine that exposes `describe_table`, `ttest_ind_table`, `f_oneway_table`, etc., plus methods for 10 curated distributions.
- **Execution Engine**: Implemented robust execution for table wrappers that handles `TableRef`/`ObjectRef` inputs, performs automatic numeric column selection, and applies `nan_policy` (propagate/omit/raise).
- **Distribution Support**: Enabled `pdf`, `cdf`, `ppf` (and `pmf`) for standard distributions using frozen scipy distribution objects to ensure consistent parameter application.
- **JSON Normalization**: Standardized all stats outputs to JSON artifacts, correctly handling numpy scalars and structured result objects (e.g., `DescribeResult`).

## Task Commits

Each task was committed atomically:

1. **Task 0: Infrastructure Support** - `e274b7b` (chore)
2. **Task 1 & 2: Stats Wrappers & Execution** - `33ec173` (feat)

## Files Created/Modified
- `src/bioimage_mcp/registry/dynamic/adapters/scipy_stats.py` - Core implementation of discovery and execution for statistical tools.
- `src/bioimage_mcp/registry/dynamic/adapters/scipy.py` - Updated routing to handle distribution method namespaces.
- `src/bioimage_mcp/registry/dynamic/models.py` - Added `TABLE_PAIR_TO_JSON` pattern.
- `src/bioimage_mcp/registry/loader.py` - Added port mapping for the new pattern.

## Decisions Made
- **Named Result Serialization**: Used `_asdict()` and explicit attribute mapping (`statistic`, `pvalue`) to ensure scipy result objects are converted into clear, agent-friendly JSON payloads.
- **IOPattern Specificity**: Added `TABLE_PAIR_TO_JSON` rather than forcing `MULTI_TABLE_TO_JSON` for two-sample tests to provide clearer port names (`table_a`, `table_b`) in the MCP schema.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing TABLE_PAIR_TO_JSON IOPattern**
- **Found during:** Task 1 (Implement discovery)
- **Issue:** The plan required `TABLE_PAIR_TO_JSON` for t-tests, but this pattern was not defined in `models.py` or mapped in `loader.py`.
- **Fix:** Added the enum member and implemented the corresponding port mapping (table_a, table_b -> output).
- **Files modified:** src/bioimage_mcp/registry/dynamic/models.py, src/bioimage_mcp/registry/loader.py
- **Verification:** Discovery and execution tests pass using the new pattern.
- **Committed in:** e274b7b

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor infrastructure addition required to satisfy the plan's I/O requirements. No scope creep.

## Issues Encountered
None - implementation followed the architectural patterns established in Phase 7.

## Next Phase Readiness
- Stats wrappers are operational and verified via patched execution.
- Ready for 08-03-PLAN.md to add exhaustive behavioral tests and contract verification.

---
*Phase: 08-statistical-analysis*
*Completed: 2026-01-26*
