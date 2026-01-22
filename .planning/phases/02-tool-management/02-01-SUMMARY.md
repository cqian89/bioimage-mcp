---
phase: 02-tool-management
plan: 01
subsystem: api
tags: [argparse, sqlite3, tool-discovery]

# Dependency graph
requires:
  - phase: 01-core-runtime
    provides: [registry indexing, environment manager]
provides:
  - CLI `list` command for tool pack visibility
affects: [02-02-install-refactor, 02-03-remove-command]

# Tech tracking
tech-stack:
  added: []
  patterns: [bootstrap-module-cli-wiring]

key-files:
  created: [src/bioimage_mcp/bootstrap/list.py, tests/unit/bootstrap/test_list_output.py]
  modified: [src/bioimage_mcp/cli.py]

key-decisions:
  - "Directly query SQLite registry for tool status and function counts in the CLI bootstrap layer for performance and simplicity."

patterns-established:
  - "CLI commands following the doctor.py pattern (bootstrap module + wiring in cli.py)."

# Metrics
duration: 7min
completed: 2026-01-22
---

# Phase 02 Plan 01: Tool List Command Summary

**Implemented `bioimage-mcp list` command providing visibility into installed tool packs, their status, and function counts.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-01-22T12:04:13Z
- **Completed:** 2026-01-22T12:11:01Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created `list.py` bootstrap module for tool status detection.
- Wired `list` command to CLI with `--json` support.
- Added comprehensive unit tests for different output formats and tool states.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create list.py bootstrap module** - `c70f37f` (feat)
2. **Task 2: Wire list command to CLI and add tests** - `4abff58` (feat)
3. **Style Fix: fix ruff line length error** - `3eadeaa` (style)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/bootstrap/list.py` - Implementation of tool listing logic.
- `src/bioimage_mcp/cli.py` - CLI wiring.
- `tests/unit/bootstrap/test_list_output.py` - Unit tests for the list command.

## Decisions Made
- Used direct SQL queries in the bootstrap layer to avoid over-complicating the `DiscoveryService` for a CLI-specific report.
- Implemented environment detection at runtime to provide real-time status (installed/partial/unavailable).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Parallel execution conflict in `cli.py`**
- **Found during:** Task 2
- **Issue:** `src/bioimage_mcp/cli.py` was modified by other agents during execution, leading to merge/overlap in wiring logic.
- **Fix:** Verified that the required `list` command wiring was correctly present in the final state of the file.
- **Verification:** `bioimage-mcp list --help` shows the command.
- **Committed in:** (part of overlapping commits)

---

**Total deviations:** 1 auto-fixed (Blocking)
**Impact on plan:** None - functionality delivered as expected despite concurrent activity.

## Issues Encountered
- Ruff linting error (line too long) was fixed in a supplemental commit.

## Next Phase Readiness
- Ready for `02-02-install-refactor` or continuation of tool management CLI.

---
*Phase: 02-tool-management*
*Completed: 2026-01-22*
