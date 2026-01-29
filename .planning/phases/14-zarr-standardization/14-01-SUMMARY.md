---
phase: 14-zarr-standardization
plan: 01
subsystem: artifacts
tags: [zarr, ome-zarr, bioio, materialization, handoff]

# Dependency graph
requires:
  - phase: 13-dynamic-introspection-cache-reuse
    provides: lockfile-gated dynamic discovery caching
provides:
  - OME-Zarr as primary interchange format
  - Directory-backed artifact materialization in core
  - Multi-character axis name support in metadata schema
affects:
  - 14-02-PLAN.md (tttrlib/Cellpose OME-Zarr update)

# Tech tracking
tech-stack:
  added: [bioio-ome-zarr]
  patterns: [directory-backed materialization, native axes preservation]

key-files:
  created: []
  modified:
    - src/bioimage_mcp/registry/dynamic/io_bridge.py
    - src/bioimage_mcp/api/execution.py
    - tools/base/bioimage_mcp_base/entrypoint.py
    - src/bioimage_mcp/registry/dynamic/adapters/xarray.py
    - tools/base/bioimage_mcp_base/ops/io.py
    - specs/014-native-artifact-types/contracts/artifact-metadata-schema.json

key-decisions:
  - "Standardized on OME-Zarr (.ome.zarr) as the default interchange format for all cross-env handoffs."
  - "Enabled core server to import directory-backed artifacts directly using ArtifactStore.import_directory."
  - "Relaxed metadata schema constraints to support multi-character axis names (e.g. 'bins') and >5D datasets."

# Metrics
duration: 11 min
completed: 2026-01-29
---

# Phase 14 Plan 01: OME-Zarr Standardization Summary

**Standardized OME-Zarr as primary interchange format, enabled directory materialization, and relaxed metadata constraints for native axes.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-01-29T12:32:20Z
- **Completed:** 2026-01-29T12:44:03Z
- **Tasks:** 8
- **Files modified:** 14

## Accomplishments
- Updated `IOBridge` to default to `OME-Zarr` for cross-environment handoffs.
- Fixed `ExecutionService` to support materializing directory-backed artifacts (OME-Zarr) by using `import_directory`.
- Upgraded worker materialization logic to use `OMEZarrWriter` and preserve native axes.
- Standardized `XarrayAdapter`, `SkimageAdapter`, `ScipyNdimageAdapter`, and `PhasorPyAdapter` to produce `OME-Zarr` outputs by default.
- Updated Base toolkit manifest to explicitly support `zarr-temp` storage for key functions.
- Relaxed the Artifact Metadata Schema to allow multi-character dimension names and datasets with up to 10 dimensions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update IOBridge to default to OME-Zarr** - `8837288` (feat)
2. **Task 2: Fix Core materialization for directory-backed artifacts** - `c1414d1` (fix)
3. **Task 3: Update Worker Materialization to handle OME-Zarr** - `23f8992` (feat)
4. **Task 4: Standardize Xarray Adapter and Base Export to OME-Zarr** - `b5ef6d0` (feat)
5. **Task 5: Standardize Dynamic Adapters to OME-Zarr outputs** - `909922c` (feat)
6. **Task 6: Update Base Manifest supported storage types** - `60330f6` (feat)
7. **Task 7: Update Artifact Metadata Schema for native axes** - `ca6a28b` (feat)
8. **Task 8: Update Tests for OME-Zarr defaults and handoff** - `82a1b1d` (test)

**Plan metadata:** `docs(14-01): complete OME-Zarr standardization plan` (see final commit)

## Files Created/Modified
- `src/bioimage_mcp/registry/dynamic/io_bridge.py` - Updated defaults
- `src/bioimage_mcp/api/execution.py` - Fixed directory materialization
- `tools/base/bioimage_mcp_base/entrypoint.py` - Upgraded worker materialization
- `src/bioimage_mcp/registry/dynamic/adapters/xarray.py` - Preferred OME-Zarr outputs
- `tools/base/bioimage_mcp_base/ops/io.py` - Preferred OME-Zarr in export
- `src/bioimage_mcp/registry/dynamic/adapters/skimage.py` - Defaulted to OME-Zarr
- `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py` - Defaulted to OME-Zarr
- `src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py` - Defaulted to OME-Zarr
- `tools/base/manifest.yaml` - Updated storage types
- `specs/014-native-artifact-types/contracts/artifact-metadata-schema.json` - Relaxed constraints
- `tests/contract/test_artifact_metadata_schema_allows_custom_dims.py` - Updated contract tests
- `tests/unit/api/test_execution_storage_materialization.py` - Updated tests
- `tests/integration/test_cross_env_handoff.py` - Updated tests
- `tests/smoke/test_equivalence_xarray.py` - Updated smoke tests

## Decisions Made
- **Standardized on .ome.zarr extension**: To ensure OME-Zarr directories are easily identifiable and distinguishable from plain Zarr.
- **Preferred OME-Zarr over OME-TIFF**: To support higher dimensionality and custom axis names natively, while keeping OME-TIFF as a fallback for compatibility.
- **Enabled import_directory in core**: Crucial for supporting OME-Zarr as a first-class citizen in the artifact store.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Undefined artifact_type in execution.py**
- **Found during:** Verification (ruff check)
- **Issue:** `artifact_type` was used before definition in `_materialize_zarr_to_file`.
- **Fix:** Moved definition up.
- **Files modified:** `src/bioimage_mcp/api/execution.py`
- **Verification:** `ruff check` passed.
- **Committed in:** `c1414d1` (Task 2 fix commit)

**2. [Rule 3 - Blocking] Syntax errors in entrypoint.py and ops/io.py**
- **Found during:** Verification (ruff check)
- **Issue:** Duplicated code and bad indentation caused invalid syntax.
- **Fix:** Cleaned up duplicated blocks and corrected indentation.
- **Files modified:** `tools/base/bioimage_mcp_base/entrypoint.py`, `tools/base/bioimage_mcp_base/ops/io.py`
- **Verification:** `ruff check` passed.
- **Committed in:** `23f8992` and `b5ef6d0` (Task 3 and 4 commits)

**3. [Rule 2 - Missing Critical] Missing logging import in skimage.py**
- **Found during:** Verification (ruff check)
- **Issue:** `logger` was used but not imported/defined.
- **Fix:** Added `import logging` and `logger` definition.
- **Files modified:** `src/bioimage_mcp/registry/dynamic/adapters/skimage.py`
- **Verification:** `ruff check` passed.
- **Committed in:** `909922c` (Task 5 commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 1 blocking, 1 missing critical)
**Impact on plan:** All auto-fixes necessary for correctness and ability to run the server. No scope creep.

## Issues Encountered
- `bioimage-mcp doctor` failed due to list in `hints.inputs.image.type` in `manifest.yaml`. Fixed by changing to a single literal `BioImageRef` while keeping the list in the `inputs` section.

## Next Phase Readiness
- Core and Base tools are now OME-Zarr native.
- Ready for Task 14-02: Updating tttrlib and Cellpose to fully leverage OME-Zarr and custom axes.

---
*Phase: 14-zarr-standardization*
*Completed: 2026-01-29*
