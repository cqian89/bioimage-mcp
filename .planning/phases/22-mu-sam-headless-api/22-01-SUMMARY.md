---
phase: 22-mu-sam-headless-api
plan: 01
subsystem: api
tags: [microsam, ndjson, persistent-worker, discovery]

# Dependency graph
requires:
  - phase: 21
    provides: "µSAM tool pack foundation and model installation"
provides:
  - "tools.micro_sam tool id with consistent naming"
  - "Persistent NDJSON entrypoint for microsam"
  - "dynamic_sources configuration for micro_sam functions"
affects:
  - phase: 22
    plan: 02
    reason: "Depends on meta.list/meta.describe and persistent entrypoint for adapter implementation"

# Tech tracking
tech-stack:
  added: []
  patterns: ["Persistent NDJSON tool entrypoint", "Dynamic function discovery via runtime meta handlers"]

key-files:
  created: []
  modified:
    - tools/microsam/manifest.yaml
    - tools/microsam/bioimage_mcp_microsam/entrypoint.py
    - src/bioimage_mcp/api/execution.py
    - tests/unit/api/test_microsam_tool_config.py

key-decisions:
  - "Renamed tool_id to tools.micro_sam for consistent library-tool alignment while keeping microsam.device config name."
  - "Implemented resilient meta.list/meta.describe in entrypoint to allow discovery even if dependencies like griffe or specific adapters are missing during registration."

patterns-established:
  - "NDJSON persistent worker handshake and command loop in tool-specific entrypoints."

# Metrics
duration: 8 min
completed: 2026-02-05
---

# Phase 22 Plan 01: µSAM Tool Pack Persistent API Summary

**Renamed tool to tools.micro_sam and implemented a persistent NDJSON entrypoint with meta.list/meta.describe support for dynamic discovery.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-05T17:40:55Z
- **Completed:** 2026-02-05T17:49:43Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Renamed `tool_id` to `tools.micro_sam` across manifest, core execution logic, and tests.
- Upgraded the microsam tool entrypoint to support the persistent NDJSON protocol (ready/execute/shutdown).
- Implemented `meta.list` and `meta.describe` handlers in the microsam environment to enable future dynamic discovery.
- Added `dynamic_sources` to `manifest.yaml` to trigger library-wide function discovery.
- Verified persistent worker protocol and handshake via manual subprocess testing.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename tool_id to tools.micro_sam and update call sites** - `cd84336` (feat)
2. **Task 2: Add dynamic_sources and upgrade microsam entrypoint to persistent NDJSON** - `3ef9f06` (feat)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `tools/microsam/manifest.yaml` - Updated tool_id and added dynamic_sources.
- `tools/microsam/bioimage_mcp_microsam/entrypoint.py` - Rewritten as a persistent NDJSON worker.
- `src/bioimage_mcp/api/execution.py` - Updated tool_id check for tool_config injection.
- `tests/unit/api/test_microsam_tool_config.py` - Updated to match new tool_id.

## Decisions Made
- **Library-Tool Alignment:** Decided to rename `tools.microsam` to `tools.micro_sam` to better match the upstream library name `micro_sam`, which simplifies mapping logic during discovery.
- **Resilient Discovery:** Implemented `meta.list` to return an empty function list with a warning if discovery dependencies (like `griffe`) or the adapter are missing, rather than crashing the worker. This ensures the catalog can still be built even in partially initialized environments.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed YAML indentation in manifest.yaml**
- **Found during:** Task 2 verification
- **Issue:** Manual edit of manifest.yaml introduced an indentation error on the `functions` block.
- **Fix:** Corrected indentation to valid YAML.
- **Files modified:** tools/microsam/manifest.yaml
- **Verification:** Verified via `meta.list` call through the entrypoint.
- **Committed in:** 3ef9f06

**2. [Rule 1 - Bug] Added resilient error handling to meta.list**
- **Found during:** Task 2 verification
- **Issue:** `meta.list` crashed if `griffe` was missing or the `microsam` adapter wasn't registered yet.
- **Fix:** Added try-except block to return `ok: true` with an empty list and a warning.
- **Files modified:** tools/microsam/bioimage_mcp_microsam/entrypoint.py
- **Verification:** Verified via manual test script.
- **Committed in:** 3ef9f06

## Issues Encountered
- `griffe` dependency missing in the microsam environment prevented full function discovery during local verification, but the protocol itself was successfully verified.

## Next Phase Readiness
- Ready for 22-02-PLAN.md (MicrosamAdapter implementation).
- The entrypoint is now ready to host the adapter once it's implemented.

---
*Phase: 22-mu-sam-headless-api*
*Completed: 2026-02-05*
