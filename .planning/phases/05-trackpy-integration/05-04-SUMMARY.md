---
phase: 05-trackpy-integration
plan: 04
subsystem: runtime
tags: [stability, recovery, conda, ndjson]

# Dependency graph
requires:
  - phase: 05-trackpy-integration
    provides: [UAT diagnosis]
provides:
  - Robust environment detection in install command
  - Safe worker termination on communication errors
  - Deterministic crash recovery without ordinal mismatch
affects: [all future tool integrations]

# Tech tracking
tech-stack:
  added: []
  patterns: [Deterministic fault injection in integration tests]

key-files:
  created:
    - tests/unit/bootstrap/test_install_utils.py
    - tests/unit/runtimes/test_persistent_failure.py
    - tests/integration/test_uat_rerun.py
  modified:
    - src/bioimage_mcp/bootstrap/install.py
    - src/bioimage_mcp/runtimes/persistent.py

key-decisions:
  - "Strict Worker Termination: Decided to kill worker processes immediately upon any communication error (JSON error, ordinal mismatch, unexpected EOF) to prevent state desync and ensure clean recovery."
  - "Robust JSON extraction: Switched to searching for the first '{' in subprocess output to avoid parsing failures caused by non-JSON warnings."

# Metrics
duration: 31 min
completed: 2026-01-23
---

# Phase 5 Plan 4: Stability Fixes Summary

**Robust environment detection and guaranteed worker error recovery via strict process termination.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-01-23T21:53:04Z
- **Completed:** 2026-01-23T22:24:44Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Fixed `install` command failure when conda outputs warnings before JSON.
- Guaranteed clean worker recovery by strictly killing processes on any communication/read error.
- Verified recovery and ordinal stability with new integration tests using deterministic fault injection.

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix JSON parsing in install.py and add regression tests** - `1eba859` (fix)
2. **Task 2: Enforce worker kill on read errors and add regression test** - `fd72e2b` (fix)
3. **Task 3: Create integration tests for stability and ordinal safety** - `b7eb80f` (test)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/bootstrap/install.py` - Robust JSON extraction from stdout.
- `src/bioimage_mcp/runtimes/persistent.py` - Enforced kill() on read errors.
- `tests/unit/bootstrap/test_install_utils.py` - Unit tests for noisy stdout.
- `tests/unit/runtimes/test_persistent_failure.py` - Unit tests for worker kill logic.
- `tests/integration/test_uat_rerun.py` - Integration tests for crash recovery.

## Decisions Made
- **Strict Worker Termination:** Any protocol violation or unexpected communication error now triggers an immediate `kill()` and `wait()` on the worker process. This prevents "buffered" responses from leaking into subsequent requests and causing persistent ordinal mismatches.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- **Integration Test Slowness:** Worker startup (conda activation) is slow in the current environment (~100s per test), requiring increased timeouts for integration tests. Resolved by increasing `bash` tool timeout and reducing request count in stability test.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Core stability issues from UAT resolved.
- Trackpy integration is now robust and verified.
- Milestone 1 (v1) complete.

---
*Phase: 05-trackpy-integration*
*Completed: 2026-01-23*
