---
phase: 20-strategize-and-execute-test-consolidation
plan: 04
subsystem: testing
tags: [pytest, documentation, smoke-tests]

# Dependency graph
requires:
  - phase: 20-strategize-and-execute-test-consolidation
    provides: [consolidated smoke tiers, requires_env marker]
provides:
  - [updated contributor-facing testing guidance]
  - [copy-pastable PR gate commands]
affects: [future-contributors, ci-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [smoke_minimal/smoke_pr/smoke_extended tiers, requires_env gating]

key-files:
  created: []
  modified: [AGENTS.md, .planning/codebase/TESTING.md, tests/smoke/conftest.py]

key-decisions:
  - "Preferred requires_env marker for environment-gated tests."
  - "Standardized local PR gate command set."

# Metrics
duration: 11min
completed: 2026-02-04
---

# Phase 20 Plan 04: Test Documentation Refresh Summary

**Updated developer-facing and internal documentation to reflect the consolidated test tiers and environment gating, providing clear copy-pastable commands for local PR verification.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-02-04T12:55:25Z
- **Completed:** 2026-02-04T13:06:25Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Refreshed `AGENTS.md` with the new smoke tiers (`smoke_minimal`, `smoke_pr`, `smoke_extended`) and environment gating guidance.
- Updated `.planning/codebase/TESTING.md` (internal runbook) with directory-to-marker mappings and a "CI-like PR gate" section.
- Fixed an `AttributeError` in `tests/smoke/conftest.py` that was blocking smoke test execution.

## Task Commits

Each task was committed atomically:

1. **Task 1: Refresh marker documentation and examples for the new smoke tiers** - `7558463` (docs)
2. **Task 2: Update internal test runbook to reflect directory + marker alignment** - `70df0d5` (docs)

**Bug Fix (Rule 1):** `18b7d45` (fix) - Fix AttributeError in smoke test conftest.

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `AGENTS.md` - Contributor guidelines updated with test tiers.
- `.planning/codebase/TESTING.md` - Internal test runbook updated.
- `tests/smoke/conftest.py` - Fixed bug in `sample_image` fixture.

## Decisions Made
- Preferred `@pytest.mark.requires_env("bioimage-mcp-...")` as the standard for environment gating.
- Defined the local PR gate as a specific sequence of pytest commands for consistency.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed AttributeError in smoke test conftest**
- **Found during:** Plan verification
- **Issue:** `SmokeConfig` object was missing `minimal_mode` attribute, causing fixture failures.
- **Fix:** Changed to `smoke_config.mode == SmokeMode.MINIMAL`.
- **Files modified:** `tests/smoke/conftest.py`
- **Verification:** `pytest tests/smoke -m smoke_minimal -q` now runs successfully.
- **Committed in:** `18b7d45`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for verification of the documented commands.

## Issues Encountered
None - documentation updates were straightforward.

## User Setup Required
None.

## Next Phase Readiness
- Test consolidation phase is complete.
- Documentation accurately reflects the current state of the codebase.

---
*Phase: 20-strategize-and-execute-test-consolidation*
*Completed: 2026-02-04*
