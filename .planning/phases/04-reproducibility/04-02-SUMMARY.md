---
phase: 04-reproducibility
plan: 02
subsystem: api
tags: [reproducibility, session-replay, environment-detection, versioning]

# Dependency graph
requires:
  - phase: 04-reproducibility
    provides: Override validation for session replay
provides:
  - Version mismatch detection and warnings during session replay
  - Missing environment detection with structured auto-install offers
affects: [session-replay, user-experience, reproducibility]

# Tech tracking
tech-stack:
  added: []
  patterns: [Pre-replay environment verification, Two-step function resolution]

key-files:
  created: []
  modified: [src/bioimage_mcp/api/sessions.py, src/bioimage_mcp/api/errors.py, src/bioimage_mcp/api/schemas.py, tests/unit/api/test_sessions.py]

key-decisions:
  - "Detect version mismatches via lock_hash comparison but allow replay to proceed (lenient mode)"
  - "Use 'conda run -n ... --dry-run' as the source of truth for environment installation status"
  - "Provide a structured InstallOffer in the response to enable client-side auto-install logic"

patterns-established:
  - "Environment missing detection before function lookup"

# Metrics
duration: 18 min
completed: 2026-01-22
---

# Phase 04 Plan 02: Version & Environment Validation Summary

**Implemented version mismatch detection and missing environment detection with structured auto-install guidance for session replay.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-01-22T17:42:47Z
- **Completed:** 2026-01-22T18:00:53Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- **Version Mismatch Detection:** Added logic to compare recorded `lock_hash` with current environment state.
- **Environment Detection:** Implemented pre-flight checks to verify if the required Conda environment is installed before attempting to resolve functions.
- **Auto-install Offers:** Added `InstallOffer` model and integrated it into the `SessionReplayResponse` to provide actionable guidance (command: `bioimage-mcp install <env>`) when tools are missing.
- **Structured Error Reporting:** Added `VERSION_MISMATCH` and `ENVIRONMENT_MISSING` error codes with corresponding helper functions for consistent API responses.
- **Function Resolution Refinement:** Improved function lookup to distinguish between "environment missing" and "function not found in existing environment".

## Task Commits

Each task was committed atomically:

1. **Task 1: Add version mismatch detection and warnings** - `91ced44` (feat)
2. **Task 2: Add missing environment detection with auto-install offer** - `c64d45c` (feat)

**Plan metadata:** (Will be committed after STATE update)

## Files Created/Modified
- `src/bioimage_mcp/api/sessions.py` - Integrated version and environment checks into `replay_session`.
- `src/bioimage_mcp/api/errors.py` - Added new error codes and warning helpers.
- `src/bioimage_mcp/api/schemas.py` - Added `InstallOffer` and updated `SessionReplayResponse`.
- `tests/unit/api/test_sessions.py` - Added unit tests for version mismatches, missing environments, and install offers.

## Decisions Made
- Used `conda run -n <env> --dry-run` to detect installation status, which is more reliable than just checking for manifest files.
- Decided to proceed with replay despite version mismatches (lenient mode) while collecting warnings for later surfacing.
- Standardized the install command format as `bioimage-mcp install <env_name>`.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- None.

## Next Phase Readiness
- Ready for Phase 4 Plan 03: Step progress reporting and tool message surfacing.
