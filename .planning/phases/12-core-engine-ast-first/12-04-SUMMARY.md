---
phase: 12-core-engine-ast-first
plan: 04
subsystem: registry
tags: [sqlite, caching, introspection]

# Dependency graph
requires:
  - phase: 12-core-engine-ast-first
    provides: [DiscoveryEngine, AST-first discovery]
provides:
  - Persistent schema cache with invalidation on version/env/source changes
  - callable_fingerprint persistence in RegistryIndex
affects: [DiscoveryEngine caching logic]

# Tech tracking
tech-stack:
  added: []
  patterns: [Hash-based cache invalidation]

key-files:
  created: [tests/unit/registry/test_index_cache.py]
  modified:
    - src/bioimage_mcp/storage/sqlite.py
    - src/bioimage_mcp/registry/index.py
    - src/bioimage_mcp/config/schema.py
    - src/bioimage_mcp/config/loader.py

key-decisions:
  - "Use env_lock_hash and source_hash for strict cache invalidation in RegistryIndex."
  - "Maintain backward compatibility in get_cached_schema by allowing optional hashes for lookup."

# Metrics
duration: 35min
completed: 2026-01-27
---

# Phase 12 Plan 04: Persistent cache invalidation keys Summary

**Persistent schema caching upgraded with multi-key invalidation (tool_version, env_lock_hash, source_hash) and callable_fingerprint storage.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-01-27T14:30:00Z
- **Completed:** 2026-01-27T15:05:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Extended SQLite `schema_cache` table with `env_lock_hash`, `callable_fingerprint`, and `source_hash`.
- Updated `RegistryIndex` to enforce hash-based validation during cache lookups.
- Added config fields `enable_schema_cache` and `schema_cache_use_db` for granular control.
- Fixed regression in `test_trackpy_discovery.py` caused by previous discovery refactoring.
- Fixed `test_server_call_tool.py` to match updated `call_tool` signature.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend schema_cache table** - `40120a6` (feat)
2. **Task 2: Update RegistryIndex methods** - `9dbbaad` (feat)
3. **Task 3: Expose config fields** - `da4d8f0` (feat)
4. **Fix: Repair broken tests** - `228ab1c` (fix)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/storage/sqlite.py` - Extended DB schema and added migrations.
- `src/bioimage_mcp/registry/index.py` - Updated cache hit/miss logic with hash validation.
- `src/bioimage_mcp/config/schema.py` - Added new config fields.
- `src/bioimage_mcp/config/loader.py` - Set defaults for new config fields.
- `tests/unit/registry/test_index_cache.py` - New unit tests for cache logic.
- `tests/integration/test_trackpy_discovery.py` - Fixed broken import.
- `tests/unit/api/test_server_call_tool.py` - Fixed signature mismatch.

## Decisions Made
- Used `env_lock_hash` and `source_hash` as primary invalidation keys alongside `tool_version`.
- Allowed `get_cached_schema` to be called without hashes for backward compatibility, while recommending their use for safety.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed broken tests due to discovery engine refactoring**
- **Found during:** Overall verification
- **Issue:** `_discover_via_subprocess` was removed from `loader.py` in Plan 12-03, breaking `test_trackpy_discovery.py`. `test_server_call_tool.py` had a signature mismatch.
- **Fix:** Updated tests to use `DiscoveryEngine` and corrected the signature mismatch.
- **Files modified:** `tests/integration/test_trackpy_discovery.py`, `tests/unit/api/test_server_call_tool.py`
- **Verification:** `pytest` on these files passes.
- **Committed in:** `228ab1c`

## Issues Encountered
- Significant number of pre-existing test failures in `bootstrap/test_install.py` were identified during overall verification. These appear unrelated to the current plan and were left for future maintenance to avoid scope creep.

## Next Phase Readiness
- Persistent cache infrastructure is ready for wiring into `DiscoveryEngine`.
- Ready for Plan 12-05: Wire Unified Discovery Orchestrator into MCP Server.

---
*Phase: 12-core-engine-ast-first*
*Completed: 2026-01-27*
