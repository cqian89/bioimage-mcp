---
phase: 05-trackpy-integration
plan: 05
subsystem: tools
tags: [trackpy, cellpose, ndjson, logging]

# Dependency graph
requires:
  - phase: 05-trackpy-integration
    provides: trackpy tool pack
provides:
  - cellpose discovery via meta.list
  - trackpy execution isolation from stdout
affects: [reliability of ndjson ipc]

# Tech tracking
tech-stack:
  added: []
  patterns: [logging capture redirection, out-of-process discovery]

key-files:
  created: [tests/integration/test_trackpy_stdout.py]
  modified: [tools/cellpose/bioimage_mcp_cellpose/entrypoint.py, tools/trackpy/bioimage_mcp_trackpy/entrypoint.py]

key-decisions:
  - "Explicitly handle meta.list in Cellpose entrypoint to satisfy bioimage-mcp doctor."
  - "Disable trackpy logger propagation and remove existing handlers during execution to prevent NDJSON IPC corruption."

# Metrics
duration: 12 min
completed: 2026-01-23
---

# Phase 5 Plan 5: Tool Entrypoint Gap Closure Summary

**Fixed tool entrypoint issues for Cellpose and Trackpy, ensuring MCP discovery compliance and NDJSON IPC purity.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-01-23T22:24:44Z
- **Completed:** 2026-01-23T22:36:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Implemented `meta.list` handler in Cellpose entrypoint, enabling discovery via `bioimage-mcp doctor`.
- Implemented robust stdout/stderr and logging capture in Trackpy entrypoint.
- Added integration test to verify NDJSON stream purity during library execution.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add meta.list to Cellpose** - `7142664` (feat)
2. **Task 2: Capture stdout in Trackpy** - `bef3937` (feat)
3. **Task 2 (Refinement): Correct meta.list handling in Cellpose** - `b825fcd` (fix)
4. **Task 2 (Refinement): Improve Trackpy log capture robustness** - `69dee54` (fix)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py` - Added meta.list handler
- `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` - Added logging redirection
- `tests/integration/test_trackpy_stdout.py` - New purity verification test

## Decisions Made
- **Out-of-process discovery**: Ensured all tools support `meta.list` even if they can't be imported into the core server process.
- **Strict IPC Purity**: Decided to actively manage library loggers (disabling propagation) to prevent any non-JSON output from leaking into the stdout pipe used for NDJSON.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cellpose meta.list missing result in outputs**
- **Found during:** Overall verification (`bioimage-mcp doctor`)
- **Issue:** The initial implementation returned results directly instead of wrapping in `outputs['result']`, causing `ValueError: meta.list did not return outputs`.
- **Fix:** Moved `meta.list` to explicit handling block in `process_execute_request` to match `meta.describe` pattern.
- **Files modified:** `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
- **Verification:** `bioimage-mcp doctor` no longer reports error for cellpose.
- **Committed in:** `b825fcd`

**2. [Rule 1 - Bug] Trackpy logger leaking to stdout despite redirection**
- **Found during:** Integration test execution
- **Issue:** `trackpy.batch` output leaked to stdout because existing handlers were already holding references to the original `sys.stdout`.
- **Fix:** Temporarily disabled logger propagation and removed existing handlers during the function call.
- **Files modified:** `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py`
- **Verification:** `tests/integration/test_trackpy_stdout.py` passes for both `locate` and `batch`.
- **Committed in:** `69dee54`

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Essential for correctness and IPC stability. No scope creep.

## Issues Encountered
- `bioimage-mcp doctor` reports `NOT READY` due to missing `conda-lock` in the environment, but tool pack status is now healthy.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Milestone 5 complete.
- Ready for milestone audit and archive.

---
*Phase: 05-trackpy-integration*
*Completed: 2026-01-23*
