---
phase: 04-reproducibility
plan: 03
subsystem: api
tags: [reproducibility, session-replay, progress-reporting, observability]

# Dependency graph
requires:
  - phase: 04-reproducibility
    provides: Version and environment validation
provides:
  - Step-by-step progress reporting during session replay
  - Surfacing of tool-level and version warnings in replay responses
  - Dry-run mode for workflow validation and preview
affects: [session-replay, user-experience, workflow-observability]

# Tech tracking
tech-stack:
  added: []
  patterns: [Step-based progress tracking, Tool message surfacing]

key-files:
  created: []
  modified: [src/bioimage_mcp/api/sessions.py, src/bioimage_mcp/api/schemas.py, tests/unit/api/test_sessions.py]

key-decisions:
  - "Include full progress history in the final replay response for retrospective observability"
  - "Use 'pending' status in dry-run mode to show a preview of the execution plan without tool invocation"
  - "Add 'completed' and 'failed' to SessionReplayResponse status to distinguish from the initial 'running' state"

patterns-established:
  - "Progress entry update pattern (started_at -> status -> ended_at) during execution loops"

# Metrics
duration: 4 min
completed: 2026-01-22
---

# Phase 04 Plan 03: Progress Reporting & Warning Surfacing Summary

**Implemented step-by-step progress reporting and tool message surfacing for session replay, enhancing observability and debugging.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-22T17:51:28Z
- **Completed:** 2026-01-22T17:55:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- **Progress Models:** Added `StepProgress` and `ReplayWarning` Pydantic models to standard API schemas.
- **Observability Enhancement:** Updated `SessionReplayResponse` to include `step_progress`, `warnings`, and final `outputs`.
- **Progress Tracking:** Implemented logic in `SessionService.replay_session` to record status, timing, and descriptive messages for each step as it executes.
- **Warning Surfacing:** Tool-level warnings (e.g., from tool pack stdout/stderr) and version mismatch warnings (lock_hash differences) are now extracted and aggregated in the response.
- **Dry-run Semantics:** Refined `dry_run` mode to perform all validations and return a `pending` progress list, allowing clients to preview the workflow before execution.
- **Response Status Refinement:** Added `completed` and `failed` terminal statuses to provide clear completion signals.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add progress and warnings models to schemas** - `2f30303` (feat)
2. **Task 2 & 3: Populate progress and warnings during replay** - `2739c8a` (feat)

**Plan metadata:** `713364f` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/api/schemas.py` - Added progress/warning models and updated response shape.
- `src/bioimage_mcp/api/sessions.py` - Implemented progress tracking and warning collection in `replay_session`.
- `tests/unit/api/test_sessions.py` - Added tests for progress reporting, dry-run, and tool warnings.

## Decisions Made
- Added `outputs` to `SessionReplayResponse` specifically for collecting results from the last successful step, ensuring agents can easily access final artifacts without re-traversing the session history.
- Status values like `running`, `ready`, `completed`, and `failed` were standardized across the replay lifecycle.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## Next Phase Readiness
- Ready for Phase 4 Plan 04: Missing input handling, resume capability, and error summaries.
