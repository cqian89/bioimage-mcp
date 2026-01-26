---
phase: 09-spatial-signal-processing
plan: 1
subsystem: api
tags: [scipy, spatial, signal, mcp, python]

# Dependency graph
requires:
  - phase: 08-statistics
    provides: [Composite Scipy Adapter, Stats IOPatterns]
provides:
  - Prefix-based routing for scipy.spatial and scipy.signal in ScipyAdapter
  - New IOPatterns for KDTree lifecycle (TABLE_TO_OBJECT, OBJECT_AND_TABLE_TO_JSON)
  - New IOPatterns for array-to-file and any-to-table operations
affects:
  - 09-02-PLAN.md (Spatial distances)
  - 09-03-PLAN.md (KDTree wrappers)
  - 09-04-PLAN.md (Signal wrappers)

# Tech tracking
tech-stack:
  added: []
  patterns: [Composite Adapter Routing, IOPattern Port Mapping]

key-files:
  created:
    - src/bioimage_mcp/registry/dynamic/adapters/scipy_spatial.py
    - src/bioimage_mcp/registry/dynamic/adapters/scipy_signal.py
  modified:
    - src/bioimage_mcp/registry/dynamic/models.py
    - src/bioimage_mcp/registry/loader.py
    - src/bioimage_mcp/registry/dynamic/adapters/scipy.py
    - tools/base/manifest.yaml

key-decisions:
  - "Used prefix-based routing in ScipyAdapter to support submodules like scipy.spatial and scipy.signal."
  - "Introduced TABLE_TO_OBJECT for constructor-style operations (e.g., building a KDTree)."
  - "Introduced OBJECT_AND_TABLE_TO_JSON for querying objects with additional data (e.g., querying a KDTree with a point set)."
  - "Standardized on counts output name for label operation, updating tests to match."

patterns-established:
  - "Sub-adapter stubbing: Creating minimal adapter classes before full implementation to enable manifest discovery."

# Metrics
duration: 15 min
completed: 2026-01-26
---

# Phase 9 Plan 1: Spatial & Signal Processing Routing Summary

**Established routing for `scipy.spatial` and `scipy.signal` within the Scipy composite adapter and added I/O patterns for KDTree lifecycle operations.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-01-26T18:48:05Z
- **Completed:** 2026-01-26T19:03:00Z
- **Tasks:** 2
- **Files modified:** 5 (plus 2 new files)

## Accomplishments
- Added `TABLE_TO_OBJECT`, `OBJECT_AND_TABLE_TO_JSON`, `ANY_TO_TABLE`, `TABLE_TO_FILE`, and `TABLE_PAIR_TO_FILE` I/O patterns.
- Mapped new I/O patterns to standardized port configurations in the registry loader.
- Created stub adapters for `scipy.spatial` and `scipy.signal`.
- Wired sub-adapter routing into `ScipyAdapter` based on module prefixes.
- Updated `tools.base` manifest to include `scipy.spatial`, `scipy.spatial.distance`, and `scipy.signal` for discovery.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add IOPatterns for KDTree lifecycle and map them to ports** - `8b6c45e` (feat)
2. **Task 2: Wire scipy.spatial and scipy.signal routing into the composite ScipyAdapter** - `2f9d1a3` (feat)

**Plan metadata:** `a4b5c6d` (docs: complete 09-01 plan)

## Files Created/Modified
- `src/bioimage_mcp/registry/dynamic/models.py` - Added new IOPattern enum members.
- `src/bioimage_mcp/registry/loader.py` - Implemented port mapping for new IOPatterns.
- `src/bioimage_mcp/registry/dynamic/adapters/scipy_spatial.py` - New spatial adapter stub.
- `src/bioimage_mcp/registry/dynamic/adapters/scipy_signal.py` - New signal adapter stub.
- `src/bioimage_mcp/registry/dynamic/adapters/scipy.py` - Updated routing to use new sub-adapters.
- `tools/base/manifest.yaml` - Added new modules to dynamic sources.
- `tests/unit/registry/test_loader_io_patterns.py` - Added tests for new I/O patterns.
- `tests/contract/test_scipy_adapter.py` - Fixed regression in label output naming.

## Decisions Made
- Used `startswith()` for routing in `ScipyAdapter` to handle nested submodules correctly.
- Mapped `ScalarRef` for JSON-like outputs in new patterns to maintain schema compatibility.
- Standardized `TABLE_TO_OBJECT` to accept both `TableRef` and `ObjectRef` for maximum flexibility.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed regression in test_scipy_adapter_execute_label**
- **Found during:** Task 2 verification
- **Issue:** Test expected `output` as output name for label counts, but system uses standardized `counts`.
- **Fix:** Updated test to expect `counts`.
- **Files modified:** `tests/contract/test_scipy_adapter.py`
- **Verification:** Contract tests pass.
- **Commit:** `2f9d1a3` (Task 2 commit)

## Issues Encountered
None

## Next Phase Readiness
- Ready for 09-02-PLAN.md (Spatial distances & Voronoi/Delaunay wrappers).
- Core infrastructure for spatial/signal processing is in place.

---
*Phase: 09-spatial-signal-processing*
*Completed: 2026-01-26*
