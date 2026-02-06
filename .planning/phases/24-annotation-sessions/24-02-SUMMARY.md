---
phase: 24-annotation-sessions
plan: 02
subsystem: infra
tags: [persistent-worker, lifecycle, shutdown, napari]

# Dependency graph
requires:
  - phase: 23-microsam-interactive-bridge
    provides: [microsam interactive bridge]
provides:
  - Robust worker shutdown behavior for BUSY napari sessions
  - Deterministic subprocess cleanup on server termination
affects: [Phase 24: final release]

# Tech tracking
tech-stack:
  added: []
  patterns: [Robust shutdown with forced-kill fallback and ACK timeouts]

key-files:
  created: [tests/unit/runtimes/test_persistent_shutdown.py]
  modified:
    - src/bioimage_mcp/runtimes/persistent.py
    - tests/unit/runtimes/test_persistent_failure.py

key-decisions:
  - "Treated BUSY timeout as a terminal condition for force-kill to avoid hanging server shutdown on interactive sessions."
  - "Added a 2.0s timeout for shutdown ACK to prevent deadlocks when IPC pipes are blocked by GUI behavior."

patterns-established:
  - "Pattern: Process shutdown must always converge to a terminal state using progressive escalation (graceful -> timeout -> force-kill)."

# Metrics
duration: 15 min
completed: 2026-02-06
---

# Phase 24 Plan 02: Hardened Worker Shutdown Summary

**Robust worker shutdown behavior for BUSY napari sessions ensuring deterministic subprocess cleanup when the MCP server terminates, backed by regression tests for all forced termination paths.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-06T14:57:59Z
- **Completed:** 2026-02-06T15:13:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Hardened `WorkerProcess.shutdown()` to handle workers blocked by GUI runtimes.
- Implemented BUSY timeout escalation to force-kill for all persistent workers.
- Added NDJSON IPC ACK timeouts to prevent deadlocks on blocked stdout/stderr pipes.
- Verified deterministic cleanup via unit tests for manager-level `shutdown_all()`.
- Enhanced shutdown diagnostics with explicit logging of the termination method used.

## Task Commits

Each task was committed atomically:

1. **Task 1: Harden worker shutdown path for blocked interactive sessions** - `64ce1de` (feat)
2. **Task 2: Add runtime regression tests for termination and manager cleanup** - `833efba` (test)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/runtimes/persistent.py` - Implemented robust shutdown logic
- `tests/unit/runtimes/test_persistent_failure.py` - Added BUSY timeout test case
- `tests/unit/runtimes/test_persistent_shutdown.py` - Added manager-level shutdown coverage

## Decisions Made
- Used a hardcoded 2.0s timeout for the shutdown ACK. This is sufficient for a responsive worker that is NOT BUSY, while being short enough to not delay server shutdown significantly.
- Ensured `self.state = WorkerState.TERMINATED` is always set, even if the process was already dead, to maintain state consistency in the manager.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **Mocking Indentation:** Encountered a minor IndentationError during test creation which was fixed immediately.
- **Subprocess Mocking Complexity:** Discovered that `detect_env_manager` calls `Popen` during initialization, requiring additional mocking in tests to avoid `StopIteration`.

## Next Phase Readiness
- Server termination is now safe even with open napari sessions.
- Ready for 24-03-PLAN.md: Interactive resume and progress visibility.

---
*Phase: 24-annotation-sessions*
*Completed: 2026-02-06*
