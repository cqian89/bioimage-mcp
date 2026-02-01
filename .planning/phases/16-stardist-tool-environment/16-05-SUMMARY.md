---
phase: 16-stardist-tool-environment
plan: 05
subsystem: testing
tags: [stardist, integration-test, persistent-worker, ndjson-ipc]

# Dependency graph
requires:
  - phase: 16-04
    provides: "StarDist tool pack and initial tests"
provides:
  - "Core-env StarDist integration test validating real subprocess execution"
affects: [v0.4.0 release]

# Tech tracking
tech-stack:
  added: []
  patterns: [subprocess-stdout-redirection]

key-files:
  created: []
  modified:
    - tests/integration/test_stardist_adapter_e2e.py
    - tools/stardist/bioimage_mcp_stardist/entrypoint.py

key-decisions:
  - "Redirect tool stdout to stderr in entrypoint to avoid breaking NDJSON IPC when tools print noise."

metrics:
  duration: 15min
  completed: 2026-02-01
---

# Phase 16 Plan 05: StarDist E2E Test Core-Env Migration Summary

**Rewrote StarDist E2E integration test to run from the core server environment (Py3.13) via persistent worker subprocess, resolving the UAT gap.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-01T19:53:00Z
- **Completed:** 2026-02-01T20:08:02Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Migrated StarDist E2E test to core environment using `PersistentWorkerManager` and `execute_step`.
- Removed direct imports of StarDist/tool entrypoint from integration tests.
- Added assertions for worker PID reuse to verify persistent behavior.
- Fixed NDJSON IPC protocol violation by redirecting tool `stdout` to `stderr` in the StarDist entrypoint.

## Task Commits

Each task was committed atomically:

1. **Task 1 & 2: Rewrite StarDist E2E test and add PID assertions** - `44939e4` (test)

## Files Created/Modified
- `tests/integration/test_stardist_adapter_e2e.py` - Rewritten E2E test.
- `tools/stardist/bioimage_mcp_stardist/entrypoint.py` - Added stdout redirection to fix IPC.

## Decisions Made
- **Redirect tool stdout to stderr:** StarDist (and TensorFlow) sometimes print to `stdout`. Since our IPC relies on `stdout` for NDJSON responses, any extra print breaks the protocol. Redirecting all tool-level `stdout` to `stderr` ensures robust communication while preserving logs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed NDJSON protocol violation in StarDist entrypoint**
- **Found during:** Task 1 verification.
- **Issue:** `StarDist2D.from_pretrained` prints "Found model..." to `stdout`, causing `json.loads` to fail in the worker manager.
- **Fix:** Wrapped tool calls in `contextlib.redirect_stdout(sys.stderr)` within the entrypoint.
- **Files modified:** `tools/stardist/bioimage_mcp_stardist/entrypoint.py`
- **Verification:** `pytest tests/integration/test_stardist_adapter_e2e.py` passes.
- **Committed in:** `44939e4`

## Issues Encountered
- None - fix was straightforward once the cause was identified.

## Next Phase Readiness
- StarDist Tool Environment is now fully validated and integrated into the core server runtime.
- Ready for v0.4.0 release.

---
*Phase: 16-stardist-tool-environment*
*Completed: 2026-02-01*
