---
phase: 02-tool-management
plan: 02
subsystem: api
tags: [cli, conda, micromamba, install]

# Dependency graph
requires:
  - phase: 02-tool-management
    provides: [doctor command]
provides:
  - Extensible install command with tool discovery
  - Support for profiles and individual tool selection
affects: [future tool packs installation]

# Tech tracking
tech-stack:
  added: []
  patterns: [dynamic tool discovery from envs directory]

key-files:
  created: []
  modified:
    - src/bioimage_mcp/bootstrap/install.py
    - src/bioimage_mcp/cli.py
    - tests/integration/test_cli_doctor_install.py

key-decisions:
  - "Default to 'cpu' profile if neither tools nor profile specified"
  - "Mutually exclusive tools and --profile to avoid ambiguity"
  - "Base environment is always prepended to the install list"

patterns-established:
  - "Dynamic environment specification discovery using bioimage-mcp-*.yaml naming convention"

# Metrics
duration: 3 min
completed: 2026-01-22
---

# Phase 02: Tool Management Plan 02 Summary

**Refactored `install` command to support dynamic tool discovery and individual tool selection, fulfilling TOOL-01.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-22T12:04:46Z
- **Completed:** 2026-01-22T12:08:44Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Refactored `install.py` to dynamically discover available tools in the `envs/` directory.
- Added support for installation profiles (`cpu`, `gpu`, `minimal`) and individual tool selection.
- Updated CLI to accept positional tool names and a `--force` flag for reinstallation.
- Enhanced installation logic to skip already-installed environments unless forced.
- Added comprehensive integration tests for new installation features.

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor install.py for extensibility** - `5b00acd` (feat)
2. **Task 2: Update CLI with new install options** - `36284d6` (feat)
3. **Task 3: Update integration tests** - `e2ea97a` (test)

## Files Created/Modified
- `src/bioimage_mcp/bootstrap/install.py` - Refactored install logic with discovery and profiles.
- `src/bioimage_mcp/cli.py` - Updated CLI parser for install command.
- `tests/integration/test_cli_doctor_install.py` - Added tests for discovery, skip logic, and CLI wiring.

## Decisions Made
- Chose to always include the `base` environment as it is a foundation for other tools.
- Implemented `micromamba/conda env list --json` parsing for reliable environment existence checks.
- Enforced mutual exclusivity between positional tool arguments and the `--profile` flag to simplify the user interface.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Minor linting error regarding line length in `install.py` which was fixed immediately.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `install` command is now fully flexible and ready for additional tool packs.
- Ready to implement `list` and `remove` commands to complete Phase 2.

---
*Phase: 02-tool-management*
*Completed: 2026-01-22*
