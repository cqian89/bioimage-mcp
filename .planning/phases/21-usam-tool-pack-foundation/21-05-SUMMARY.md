---
phase: 21-usam-tool-pack-foundation
plan: 05
subsystem: infra
tags: [microsam, torch, device-selection, cuda, mps]

# Dependency graph
requires:
  - phase: 21-usam-tool-pack-foundation
    provides: [microsam tool pack structure, core config schema]
provides:
  - microsam device selection wiring
  - runtime device selection logic (CUDA > MPS > CPU)
  - structured DEVICE_UNAVAILABLE errors
affects: [Phase 21 interactive annotation, Phase 22 performance tuning]

# Tech tracking
tech-stack:
  added: []
  patterns: [tool-specific config injection, lazy torch imports, structured device error]

key-files:
  created: 
    - tools/microsam/bioimage_mcp_microsam/device.py
    - tests/unit/api/test_microsam_tool_config.py
    - tests/unit/tools/test_microsam_device_selection.py
  modified:
    - src/bioimage_mcp/api/execution.py
    - tools/microsam/bioimage_mcp_microsam/entrypoint.py

key-decisions:
  - "Use a dedicated tool_config payload in execute_step to pass tool-specific preferences without bloating the generic request schema."
  - "Implement lazy torch imports in microsam tool pack to avoid heavy dependency loading during discovery/meta.describe."
  - "Enforce strict device availability only for non-meta requests to ensure tools remain discoverable on all machines."

patterns-established:
  - "Structured tool errors with remediation hints (DEVICE_UNAVAILABLE)."
  - "Mock-based testing for tool-specific logic without installing heavy dependencies in the base environment."

# Metrics
duration: 8 min
completed: 2026-02-05
---

# Phase 21 Plan 05: Microsam Device Selection Summary

**Implemented core-to-tool wiring for `microsam.device` and runtime selection logic with CUDA > MPS > CPU preference.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-05T10:09:05Z
- **Completed:** 2026-02-05T10:16:40Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Wired `microsam.device` from core `Config` into the microsam tool execution request via a new `tool_config` payload.
- Implemented `select_device` logic in the microsam tool pack with priority: CUDA > MPS > CPU.
- Added structured error handling for `DEVICE_UNAVAILABLE` with remediation hints when an unavailable accelerator is forced.
- Ensured `meta.describe` remains functional even if a requested accelerator is missing, facilitating discovery.
- Added comprehensive unit tests for both core wiring and tool-side device selection.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pass microsam.device into the microsam tool execution request** - `51ee7a0` (feat)
2. **Task 2: Implement microsam runtime device selection** - `f3fbe2b` (feat)
3. **Task 3: Add unit tests for request wiring and device-selection behavior** - `3539f57` (test)

## Files Created/Modified
- `src/bioimage_mcp/api/execution.py` - Injects `tool_config` for microsam tools.
- `tools/microsam/bioimage_mcp_microsam/device.py` - Device selection logic.
- `tools/microsam/bioimage_mcp_microsam/entrypoint.py` - Resolved runtime device from request.
- `tests/unit/api/test_microsam_tool_config.py` - Core wiring tests.
- `tests/unit/tools/test_microsam_device_selection.py` - Device resolution tests.

## Decisions Made
- **Tool-scoped Config:** Only `microsam.device` is passed to the microsam tool pack, keeping the execution protocol lean and avoiding serializing the entire core configuration.
- **Lazy Imports:** `torch` is only imported inside `select_device` to keep entrypoint startup fast and avoid errors during discovery on non-torch environments.
- **Strict Mode Bypass:** `meta.describe` uses `strict=False` to ensure that a tool can still be described even if the user has configured an accelerator that is not available on the current machine.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- **Manifest Validation in Tests:** The initial test manifest was missing required Pydantic fields (`manifest_version`, `name`, etc.), causing `KeyError` during `execute_step`. Resolved by updating the test manifest to be fully compliant.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The Phase 21 device-selection gap is closed.
- Ready for interactive annotation work in Phase 22.
- The `microsam` tool pack can now correctly leverage accelerators when available.

---
*Phase: 21-usam-tool-pack-foundation*
*Completed: 2026-02-05*
