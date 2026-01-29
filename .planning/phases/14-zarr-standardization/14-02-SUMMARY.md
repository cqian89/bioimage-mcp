---
phase: 14-zarr-standardization
plan: 02
subsystem: tool-packs
tags: [ome-zarr, tttrlib, cellpose, flim, segmentation]

# Dependency graph
requires:
  - phase: 14-zarr-standardization
    provides: ["IOBridge OME-Zarr default", "Core materialization for directories"]
provides:
  - "tttrlib produces OME-Zarr for fluorescence decay with explicit 'bins' axis"
  - "Cellpose outputs default to OME-Zarr for labels and denoised images"
  - "Smoke tests validate OME-Zarr + custom axis names"
affects: ["Future tool integrations requiring high-dimensional data"]

# Tech tracking
tech-stack:
  added: []
  patterns: ["OME-Zarr as default interchange format", "Custom axis names ('bins') for FLIM"]

key-files:
  created: []
  modified:
    - tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py
    - tools/cellpose/bioimage_mcp_cellpose/ops/segment.py
    - tools/cellpose/bioimage_mcp_cellpose/ops/denoise.py
    - tools/tttrlib/manifest.yaml
    - tools/cellpose/manifest.yaml
    - tests/smoke/test_tttrlib_live.py
    - tests/smoke/test_cellpose_pipeline_live.py

key-decisions:
  - "Standardized on 'bins' axis name for TTTR decay data to avoid 'T' axis hijacking"
  - "Defaulted Cellpose output formats to OME-Zarr to align with project standard"
  - "Updated smoke tests to use 'full' verbosity where detailed metadata validation is required"

# Metrics
duration: 27 min
completed: 2026-01-29
---

# Phase 14 Plan 02: Update tttrlib/Cellpose for OME-Zarr Summary

**Updated tttrlib and Cellpose tool packs to use OME-Zarr as the default interchange format, featuring explicit 'bins' axes for FLIM data and standardized outputs.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-01-29T15:32:37Z
- **Completed:** 2026-01-29T15:59:55Z
- **Tasks:** 5
- **Files modified:** 8

## Accomplishments
- **tttrlib Standardization**: Switched `get_fluorescence_decay` to OME-Zarr with a semantically correct `bins` axis, removing the legacy `microtime_axis: "T"` workaround.
- **Cellpose Alignment**: Updated segmentation and denoising operations to produce OME-Zarr artifacts by default, while maintaining internal OME-TIFF conversion for library compatibility.
- **Manifest Updates**: Synchronized tool manifests to declare OME-Zarr support and default formats.
- **Smoke Test Hardening**: Validated OME-Zarr outputs and custom axes in live server environments, fixing metadata assertions affected by serialization verbosity.

## Task Commits

Each task was committed atomically:

1. **Task 1: Ensure tool environments include bioio-ome-zarr** - `da946e1` (chore)
2. **Task 2: Update tttrlib to use OME-Zarr for decay outputs** - `abb0854` (feat)
3. **Task 3: Update Cellpose outputs and conversion utilities** - `a3e14b0` (feat)
4. **Task 4: Update tttrlib and Cellpose manifests** - `53e701f` (feat)
5. **Task 5: Update smoke tests for OME-Zarr outputs** - `051fccd` (test)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `envs/bioimage-mcp-tttrlib.yaml` - Added bioio-ome-zarr and unpinned tttrlib.
- `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` - Migrated all imaging outputs to OME-Zarr and cleaned up OmeTiffWriter.
- `tools/cellpose/bioimage_mcp_cellpose/ops/segment.py` - Switched labels output to OME-Zarr.
- `tools/cellpose/bioimage_mcp_cellpose/ops/denoise.py` - Switched denoised output to OME-Zarr.
- `tools/tttrlib/manifest.yaml` - Updated output formats.
- `tools/cellpose/manifest.yaml` - Updated output formats and supported storage types.
- `tests/smoke/test_tttrlib_live.py` - Validated OME-Zarr + bins axis.
- `tests/smoke/test_cellpose_pipeline_live.py` - Validated OME-Zarr labels.

## Decisions Made
- Used `bins` instead of `B` for microtime dimensions to improve semantic clarity for AI agents.
- Enabled `full` verbosity in some smoke tests to verify internal metadata fields that are stripped in `minimal` mode.
- Preserved internal OME-TIFF conversion in Cellpose utilities to avoid breaking the core library's file-based loading.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Smoke test metadata assertions failing due to serialization verbosity**
- **Found during:** Task 5 (Update smoke tests)
- **Issue:** Tests were asserting on `metadata` fields that are stripped in the default `minimal` verbosity mode.
- **Fix:** Added `verbosity: "full"` to affected `run` calls in `test_tttrlib_live.py`.
- **Files modified:** `tests/smoke/test_tttrlib_live.py`
- **Verification:** `pytest tests/smoke/test_tttrlib_live.py --smoke-full` passes.
- **Committed in:** `051fccd`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minimal. Ensuring tests pass with the new OME-Zarr standardization required adjusting how they interact with the server's serialization layer.

## Issues Encountered
None - plan executed exactly as written.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Phase 14 (OME-Zarr Standardization) is now complete. The system now defaults to OME-Zarr for most cross-tool handoffs and correctly handles multi-dimensional data with custom axis names.

---
*Phase: 14-zarr-standardization*
*Completed: 2026-01-29*
