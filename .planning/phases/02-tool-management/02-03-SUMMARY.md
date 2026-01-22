---
phase: 02-tool-management
plan: 03
subsystem: api
tags: cli, conda, micromamba

# Dependency graph
requires:
  - phase: 02-tool-management
    provides: env manager detection and doctor command
provides:
  - bioimage-mcp remove CLI command
  - Active worker safety check before environment deletion
affects:
  - Future tool lifecycle management phases

# Tech tracking
tech-stack:
  added: []
  patterns: [CLI subcommand wiring, subprocess-based env management]

key-files:
  created: [src/bioimage_mcp/bootstrap/remove.py, tests/unit/bootstrap/test_remove.py]
  modified: [src/bioimage_mcp/cli.py]

key-decisions:
  - "Used pgrep -f for a simple, cross-platform-ish check for active tool workers by environment ID."
  - "Explicitly blocked removal of the 'base' environment to prevent breaking the core installation."

patterns-established:
  - "Subcommand handler pattern: _handle_{command} in cli.py delegating to bootstrap module."

# Metrics
duration: 4 min
completed: 2026-01-22
---

# Phase 2 Plan 3: Remove Tool Command Summary

**Implemented the `bioimage-mcp remove` CLI command with safety checks and confirmation flow.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-22T12:05:18Z
- **Completed:** 2026-01-22T12:09:12Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `remove.py` bootstrap module with `remove_tool` logic.
- Implemented `is_tool_active` using `pgrep -f` to detect running workers.
- Wired `remove` command to the main CLI with `--yes` support for automation.
- Added comprehensive unit tests covering success, failure, and safety edge cases.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create remove.py bootstrap module** - `b6cf8f4` (feat)
2. **Task 2: Wire remove command to CLI and add tests** - `b51ab64` (feat)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/bootstrap/remove.py` - Core logic for tool environment removal.
- `src/bioimage_mcp/cli.py` - CLI wiring for the new command.
- `tests/unit/bootstrap/test_remove.py` - Unit tests for removal functionality.

## Decisions Made
- Used `pgrep -f` for a simple check for active workers. This is effective because environments are named uniquely (`bioimage-mcp-<tool>`).
- Blocked removal of `base` as it contains the core server and toolkit dependencies.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `remove` command is fully operational.
- CLI is nearing completion for tool management.
- Ready for MPS/GPU enhancement or reproducibility stabilization.

---
*Phase: 02-tool-management*
*Completed: 2026-01-22*
