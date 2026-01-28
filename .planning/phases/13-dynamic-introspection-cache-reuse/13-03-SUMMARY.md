---
phase: 13-dynamic-introspection-cache-reuse
plan: 03
subsystem: registry
tags: [caching, introspection, discovery, performance]

# Dependency graph
requires:
  - phase: 13-dynamic-introspection-cache-reuse
    provides: [IntrospectionCache for tool packs]
provides:
  - Persistent, lockfile-gated meta.list cache for DiscoveryEngine
affects: [Phase 14 (OME-Zarr Standardization)]

# Tech tracking
tech-stack:
  added: []
  patterns: [Core-side persistent discovery caching]

key-files:
  created: 
    - src/bioimage_mcp/registry/dynamic/meta_list_cache.py
    - tests/unit/registry/test_engine_runtime_list_cache.py
  modified:
    - src/bioimage_mcp/registry/engine.py
    - tools/base/bioimage_mcp_base/dynamic_dispatch.py

key-decisions:
  - "Core-side memoization: DiscoveryEngine now caches parsed meta.list results to avoid subprocess overhead on repeated listings."
  - "Multi-key invalidation: Cache is keyed by both environment lockfile hash and manifest checksum."

patterns-established:
  - "Lazy adapter population: Entrypoints and tests must explicitly call populate_default_adapters() if using ADAPTER_REGISTRY directly."

# Metrics
duration: 24 min
completed: 2026-01-28
---

# Phase 13 Plan 03: Core-side Introspection Cache Summary

**Persistent, lockfile-gated DiscoveryEngine cache that eliminates repeated tool subprocess overhead in catalog listing.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-01-28T23:06:16Z
- **Completed:** 2026-01-28T23:30:16Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Implemented `MetaListCache` for persistent storage of parsed discovery results.
- Wired `DiscoveryEngine._runtime_list` to skip `execute_tool` on cache hits.
- Verified that cache invalidates correctly when either the environment lockfile or the tool manifest changes.
- Fixed regressions in existing tests and tool dispatch where cold `ADAPTER_REGISTRY` was causing failures.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add a persistent MetaListCache** - `570389d` (feat)
2. **Task 2: Wire MetaListCache into DiscoveryEngine** - `2639fd3` (feat)
3. **Task 3: Add unit tests for runtime list cache** - `6f6977e` (test)

**Regression Fixes:** `6007d1b` (fix)

## Files Created/Modified
- `src/bioimage_mcp/registry/dynamic/meta_list_cache.py` - Persistent cache implementation.
- `src/bioimage_mcp/registry/engine.py` - Core discovery engine updated with caching logic.
- `tests/unit/registry/test_engine_runtime_list_cache.py` - Focused behavioral tests for caching.
- `tools/base/bioimage_mcp_base/dynamic_dispatch.py` - Fixed lazy adapter loading in tool worker.
- `tests/unit/registry/test_xarray_adapter.py` - Updated to call `populate_default_adapters()`.
- `tests/contract/test_cellpose_adapter.py` - Fixed ImportError and added registry population.
- `tests/contract/test_matplotlib_adapter_discovery.py` - Added registry population.

## Decisions Made
- Used a flat `lockfile_hash:manifest_checksum` key in `MetaListCache` for simplicity while meeting all safety requirements.
- Decided to auto-fix regressions in existing tests caused by previous plans' move to lazy adapter population, as they were blocking verification of the current plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Regressions in adapter loading**
- **Found during:** Verification phase (running `pytest -q`)
- **Issue:** Several tests and the base tool worker failed because `ADAPTER_REGISTRY` was empty by default after a previous plan's change.
- **Fix:** Added `populate_default_adapters()` calls to failing tests and `dynamic_dispatch.py`.
- **Files modified:** `tests/unit/registry/test_xarray_adapter.py`, `tests/contract/test_cellpose_adapter.py`, `tests/contract/test_matplotlib_adapter_discovery.py`, `tools/base/bioimage_mcp_base/dynamic_dispatch.py`
- **Verification:** All failing tests now pass.
- **Committed in:** `6007d1b`

## Issues Encountered
- None during planned tasks.

## Next Phase Readiness
- Core-side caching is now fully operational and verified.
- `bioimage-mcp list` should now be sub-second on subsequent runs.
- Ready for Phase 14 (OME-Zarr Standardization).

---
*Phase: 13-dynamic-introspection-cache-reuse*
*Completed: 2026-01-28*
