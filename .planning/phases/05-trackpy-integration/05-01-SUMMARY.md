---
phase: 05-trackpy-integration
plan: 01
subsystem: trackpy
tags: [trackpy, conda, ndjson, ipc, discovery]

# Dependency graph
requires:
  - phase: 01-core-runtime
    provides: [PersistentWorkerManager, NDJSON IPC]
provides:
  - Trackpy tool pack skeleton
  - Dual-mode NDJSON entrypoint with meta.list
  - Installable bioimage-mcp-trackpy environment
affects: [05-02-dynamic-introspection, 05-03-api-coverage]

# Tech tracking
tech-stack:
  added: [trackpy=0.7.0, numpydoc, pims]
  patterns: [Dual-mode entrypoint (legacy/persistent), Out-of-process discovery via meta.list]

key-files:
  created:
    - envs/bioimage-mcp-trackpy.yaml
    - tools/trackpy/manifest.yaml
    - tools/trackpy/bioimage_mcp_trackpy/entrypoint.py
    - tests/unit/registry/test_trackpy_manifest.py
  modified:
    - pytest.ini

key-decisions:
  - "Used Python 3.12 for trackpy 0.7 compatibility while core server remains on 3.13"
  - "Implemented dual-mode entrypoint to support both legacy single-request and persistent worker modes"
  - "Leveraged meta.list in entrypoint for out-of-process function discovery"

# Metrics
duration: 8min
completed: 2026-01-23
---

# Phase 5 Plan 1: Trackpy Skeleton Summary

**Created trackpy tool pack skeleton with Python 3.12 environment, dual-mode NDJSON entrypoint, and out-of-process discovery support.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-23T17:15:28Z
- **Completed:** 2026-01-23T17:23:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Defined `bioimage-mcp-trackpy` conda environment with trackpy 0.7.0 and essential deps.
- Configured `manifest.yaml` with `dynamic_sources` for trackpy modules.
- Implemented `entrypoint.py` supporting both legacy JSON and persistent NDJSON IPC.
- Added `meta.list` handler to entrypoint for remote function enumeration.
- Successfully verified installation via `bioimage-mcp install trackpy`.
- Added unit test for manifest validation and discovery.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create trackpy conda environment definition** - `cb6a2c0` (feat)
2. **Task 2: Create trackpy manifest, pytest path, and entrypoint with meta.list** - `ab02f60` (feat)
3. **Task 3: Add unit test for tool pack discovery** - `821c486` (test)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `envs/bioimage-mcp-trackpy.yaml` - Conda environment definition.
- `tools/trackpy/manifest.yaml` - Tool pack metadata.
- `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` - Dual-mode worker entrypoint.
- `tools/trackpy/bioimage_mcp_trackpy/__init__.py` - Package marker.
- `pytest.ini` - Added trackpy to pythonpath.
- `tests/unit/registry/test_trackpy_manifest.py` - Manifest discovery test.

## Decisions Made
- **Out-of-process discovery:** Decided to use a specialized `meta.list` command in the worker entrypoint to discover functions, as trackpy cannot be safely imported in the server's Python 3.13 process.
- **Environment Isolation:** Strictly excluded core server editable install from trackpy environment to maintain dependency isolation and avoid version conflicts.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- **Discovery Warning in Tests:** The unit test initially failed because the `trackpy` adapter is not yet implemented in the core server (scheduled for 05-02). Fixed the test to treat discovery failures as non-fatal warnings for this phase.

## User Setup Required
None - environment is automatically managed via `bioimage-mcp install`.

## Next Phase Readiness
- Trackpy environment is installable and worker is spawnable.
- Ready for 05-02-PLAN.md: Implement TrackpyAdapter for dynamic introspection.
- Out-of-process discovery protocol is established in entrypoint.

---
*Phase: 05-trackpy-integration*
*Completed: 2026-01-23*
