---
phase: 25-add-missing-tttr-methods
plan: 01
subsystem: api
tags: [tttrlib, parity, contract-tests, error-handling]
requires:
  - phase: 24-annotation-sessions
    provides: session lifecycle hardening used by tttr runtime execution
provides:
  - Runtime-derived callable parity inventory for TTTR, CLSMImage, and Correlator
  - Stable unsupported-method routing with TTTRLIB_UNSUPPORTED_METHOD responses
  - Contract drift guard asserting runtime callables always have valid coverage status
affects: [25-02, 25-03, tttrlib-runtime-parity]
tech-stack:
  added: []
  patterns:
    - Runtime parity registry keyed by strict upstream IDs
    - Coverage-first unsupported gating before handler dispatch
key-files:
  created:
    - tools/tttrlib/schema/tttrlib_coverage.json
    - tests/contract/test_tttrlib_parity_inventory.py
    - tests/unit/test_tttrlib_entrypoint_unsupported.py
  modified:
    - tools/tttrlib/schema/tttrlib_api.json
    - tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py
key-decisions:
  - "Use a runtime-derived coverage registry as the parity source of truth rather than a handwritten list."
  - "Treat deferred and denied methods as explicitly unsupported with a stable error code before dispatch."
patterns-established:
  - "Parity inventory entries require status, owner, rationale, and revisit_trigger for every callable."
  - "Unsupported and unknown IDs remain distinct paths to preserve diagnostics and discoverability."
requirements-completed: [TTTR-01, TTTR-04]
duration: 4 min
completed: 2026-03-05
---

# Phase 25 Plan 01: Parity Foundation Summary

**Runtime parity inventory and unsupported-method routing now make tttrlib coverage explicit, testable, and deterministic.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-05T14:09:07Z
- **Completed:** 2026-03-05T14:12:54Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added `tttrlib_coverage.json` with 146 runtime-derived callable entries across TTTR, CLSMImage, and Correlator.
- Linked `tttrlib_api.json` metadata to the parity inventory source used for coverage governance.
- Added runtime drift contract test that validates callable completeness and status schema against the installed tttrlib environment.
- Added unsupported-method policy checks in tttr entrypoint so deferred/denied IDs fail fast with stable remediation.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create runtime parity inventory and contract drift guard** - `77a74af` (feat)
2. **Task 2 (RED): Add failing unsupported-routing tests** - `8cd89ed` (test)
3. **Task 2 (GREEN): Implement unsupported-callable routing** - `4ae17f1` (feat)

**Plan metadata:** pending

## Files Created/Modified
- `tools/tttrlib/schema/tttrlib_coverage.json` - Runtime parity registry with supported/supported_subset/deferred/denied classifications.
- `tools/tttrlib/schema/tttrlib_api.json` - Adds parity inventory metadata linkage while preserving upstream version.
- `tests/contract/test_tttrlib_parity_inventory.py` - Contract guard for runtime callable coverage completeness and status validity.
- `tests/unit/test_tttrlib_entrypoint_unsupported.py` - TDD coverage for unsupported vs unknown dispatch behavior.
- `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` - Centralized unsupported-method policy reader and stable error generation.

## Decisions Made
- Use strict upstream IDs (`tttrlib.Class.method`) in the coverage registry to prevent alias drift.
- Run unsupported-method checks before handler dispatch so denied/deferred IDs are deterministic and explicit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Avoided local import dependency for runtime parity checks**
- **Found during:** Task 1 (Create runtime parity inventory and contract drift guard)
- **Issue:** Contract test initially required `tttrlib` import in the pytest environment, which failed locally and blocked verification.
- **Fix:** Switched runtime callable enumeration to `conda run -n bioimage-mcp-tttrlib python -c ...` inside the contract test.
- **Files modified:** `tests/contract/test_tttrlib_parity_inventory.py`
- **Verification:** `pytest tests/contract/test_tttrlib_parity_inventory.py -q`
- **Committed in:** `77a74af` (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Deviation was necessary to keep parity drift validation tied to the actual tttr runtime and unblock automated verification.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Parity governance baseline is in place for broader callable expansion in `25-02-PLAN.md`.
- Deferred and denied IDs now return stable diagnostics, enabling safe incremental surface growth.

## Self-Check: PASSED
