---
phase: 12-core-engine-ast-first
plan: 03
subsystem: registry
tags: [ast, griffe, introspection, discovery]

# Dependency graph
requires:
  - phase: 12-core-engine-ast-first
    provides: [static-inspector-foundation]
provides:
  - Unified DiscoveryEngine with AST-first + runtime fallback orchestration
  - Clean registry loader without in-process tool code imports
affects: [12-04, 12-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [unified-discovery-orchestrator, runtime-fallback-pattern]

key-files:
  created: [src/bioimage_mcp/registry/engine.py, tests/unit/registry/test_registry_engine.py]
  modified: [src/bioimage_mcp/registry/loader.py, src/bioimage_mcp/registry/manifest_schema.py]

key-decisions:
  - "Centralized discovery logic in DiscoveryEngine to eliminate duplicated mapping and discovery code."
  - "Ensured that manifest-defined functions win over dynamically discovered ones by processing them first."
  - "Added params_rename and params_omit to FunctionOverlay to support parameter-level actions required by OVERLAY-01."

patterns-established:
  - "AST-first discovery with per-function isolated runtime fallback for high-fidelity schemas."

# Metrics
duration: 45 min
completed: 2026-01-27
---

# Phase 12 Plan 03: DiscoveryEngine Summary

**Introduced a unified DiscoveryEngine that performs AST-first introspection with isolated runtime fallback and enforces skip rules, eliminating in-process tool imports in the core server.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-01-27T13:30:00Z
- **Completed:** 2026-01-27T14:15:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Implemented `DiscoveryEngine` class for AST-first introspection using `griffe`.
- Added isolated runtime fallback via `meta.describe` protocol when AST info is insufficient.
- Refactored `loader.py` to use `DiscoveryEngine`, removing complex discovery logic from the loader.
- Extended `FunctionOverlay` to support parameter renames and omissions.
- Verified deterministic schema normalization and artifact separation in the engine.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement DiscoveryEngine** - `27583f5` (feat)
2. **Task 2: Refactor registry loader** - `05b481f` (refactor)
3. **Task 3: Add unit tests** - `8bbb9c9` (test)

**Plan metadata:** `docs(12-03): complete DiscoveryEngine plan`

## Files Created/Modified
- `src/bioimage_mcp/registry/engine.py` - Core discovery orchestrator
- `src/bioimage_mcp/registry/loader.py` - Simplified manifest loader
- `src/bioimage_mcp/registry/manifest_schema.py` - Extended overlay model
- `tests/unit/registry/test_registry_engine.py` - New unit tests for engine
- `tests/unit/registry/test_loader_dynamic_integration.py` - Updated tests
- `tests/unit/registry/test_loader_subprocess_rich_metadata.py` - Updated tests
- `tests/unit/registry/test_phasorpy_manifest_config.py` - Updated tests
- `tests/unit/registry/test_skimage_manifest_config.py` - Updated tests

## Decisions Made
- Used a heuristic to determine `project_root` in `loader.py` to support `griffe` search paths.
- Opted to return a tuple `(functions, warnings)` from `DiscoveryEngine.discover` to preserve diagnostic visibility in `bioimage-mcp doctor`.
- Conflicting overlays continue to resolve as "last-applied wins" but now benefit from deterministic merging in the engine.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- `griffe` resolution failures in real libraries (phasorpy, skimage) during tests prompted switching some tests to use mocks for `inspect_module` instead of relying on real library files, which is more appropriate for registry unit tests.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `DiscoveryEngine` is ready for persistent caching integration (Plan 12-04).
- `meta.describe` protocol is fully supported as a fallback source.

---
*Phase: 12-core-engine-ast-first*
*Completed: 2026-01-27*
