---
phase: 21-usam-tool-pack-foundation
plan: 04
subsystem: infra
tags: [microsam, config, doctor]

# Dependency graph
requires:
  - phase: 21-03
    provides: [microsam_models.json installer record]
provides:
  - microsam.device configuration
  - microsam model readiness doctor check
affects: [Phase 22, Phase 23]

# Tech tracking
tech-stack:
  added: []
  patterns: [Config-based device override, record-based doctor checks]

key-files:
  created: []
  modified:
    - src/bioimage_mcp/config/schema.py
    - src/bioimage_mcp/bootstrap/configure.py
    - src/bioimage_mcp/bootstrap/checks.py
    - tests/unit/bootstrap/test_checks.py

key-decisions:
  - "Use StrEnum for MicrosamDevice to ensure str(enum) returns the value string, satisfying validation and user-facing requirements."
  - "Check for microsam models only if the bioimage-mcp-microsam environment is installed to avoid noise in base-only installations."

patterns-established:
  - "Tool-specific config sections in central schema (microsam.*)"
  - "State-record verification in doctor checks (reading installer-produced JSON)"

# Metrics
duration: 15min
completed: 2026-02-05
---

# Phase 21 Plan 04: Microsam config and doctor verification Summary

**Implemented `microsam.device` configuration and doctor readiness checks for required SAM models.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-04T23:26:36Z
- **Completed:** 2026-02-05T23:42:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `microsam.device` (auto|cuda|mps|cpu) to the central configuration schema.
- Updated the starter configuration template to include the `microsam` section.
- Implemented a new doctor check `check_microsam_models` that verifies Generalist, LM, and EM `vit_b` models are present using the installer's metadata record.
- Added comprehensive unit tests for the new readiness check.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add microsam.device to config schema and starter config** - `aa421a8` (feat)
2. **Task 2: Add doctor check for required microsam models** - `fa36ae8` (feat)

**Plan metadata:** `c193032` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/config/schema.py` - Added MicrosamSettings and MicrosamDevice StrEnum.
- `src/bioimage_mcp/bootstrap/configure.py` - Updated starter config template.
- `src/bioimage_mcp/bootstrap/checks.py` - Added check_microsam_models.
- `tests/unit/bootstrap/test_checks.py` - Added tests for microsam model checks.

## Decisions Made
- Used `StrEnum` for `MicrosamDevice` because the plan's verification script explicitly uses `str(c.microsam.device)` and expects the string value (e.g. 'auto'). `StrEnum` ensures this behavior natively in Python 3.11+.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- The plan's verification script for Task 1 failed initially because standard `(str, Enum)` enums in Python 3.13 still return `ClassName.MemberName` for `str()`. Switched to `StrEnum` which is accepted in the codebase and fixes the issue.
- Unrelated failures in `test_list_tool_filter.py` were observed but ignored as they were not affected by the changes in this plan.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Foundation for µSAM is complete (env installation + model caching + device control + verification).
- Ready for Phase 22: Headless Tool Implementation.

---
*Phase: 21-usam-tool-pack-foundation*
*Completed: 2026-02-05*
