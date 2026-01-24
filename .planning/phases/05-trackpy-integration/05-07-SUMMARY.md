---
phase: 05-trackpy-integration
plan: 07
subsystem: testing
tags: [python, pytest, cli]

# Dependency graph
requires:
  - phase: 05-trackpy-integration
    provides: [Dynamic introspection for trackpy]
provides:
  - [Optional readiness checks in doctor]
  - [Warnings section in doctor output for non-critical failures]
affects: [future tool integrations that might have optional dependencies]

# Tech tracking
tech-stack:
  added: []
  patterns: [Optional check results in bootstrap readiness]

key-files:
  created: []
  modified:
    - src/bioimage_mcp/bootstrap/checks.py
    - src/bioimage_mcp/bootstrap/doctor.py
    - tests/unit/bootstrap/test_doctor_output.py

key-decisions:
  - "Introduced 'required' field to CheckResult to distinguish between blocking and non-blocking checks."
  - "Marked conda-lock as optional to prevent readiness failures for users who don't need dev tools."

patterns-established:
  - "Pattern: Use WARNINGS section in doctor output for failures that don't affect core system readiness."

# Metrics
duration: 10 min
completed: 2026-01-24
---

# Phase 05 Plan 07: Optional Readiness Checks Summary

**Enabled 'bioimage-mcp doctor' to report READY even when optional checks like conda-lock fail, surfacing them as warnings instead of blockers.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-01-24T14:40:00Z
- **Completed:** 2026-01-24T14:50:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Extended `CheckResult` with a `required` flag.
- Configured `conda_lock` check as optional.
- Updated `doctor` logic to compute readiness based only on required checks.
- Added a `WARNINGS` section to the human-readable output for optional failures.
- Ensured JSON output reflects the new optional check semantics.

## Task Commits

Each task was committed atomically:

1. **Task 1: Adjust readiness to ignore optional checks** - `3aedfef` (feat)
2. **Task 2: Add unit coverage for READY-with-warnings behavior** - `6dd070e` (test)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/bootstrap/checks.py` - Added `required` field to `CheckResult`, marked `conda_lock` as optional.
- `src/bioimage_mcp/bootstrap/doctor.py` - Updated readiness logic and added `WARNINGS` output.
- `tests/unit/bootstrap/test_doctor_output.py` - Added regression tests for READY-with-warnings behavior.

## Decisions Made
- Used a boolean `required` field on `CheckResult` as it's the simplest way to introduce optionality without breaking existing check structures.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## Next Phase Readiness
- `bioimage-mcp doctor` now correctly reports readiness for end users who might be missing `conda-lock`.
- Ready for plan 05-08 (Fix Trackpy meta.describe schema enrichment).

---
*Phase: 05-trackpy-integration*
*Completed: 2026-01-24*
