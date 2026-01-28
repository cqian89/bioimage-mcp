---
phase: 13-dynamic-introspection-cache-reuse
plan: 01
subsystem: tools
tags: [caching, introspection, discovery, tools.base]

# Dependency graph
requires:
  - phase: 12-core-engine-ast-first
    provides: IntrospectionCache, discover_functions
provides:
  - "Lockfile-gated dynamic introspection caching for tools.base meta.list"
  - "Unit tests for cache reuse and invalidation"
affects:
  - 13-02-PLAN.md (trackpy cache reuse)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lockfile-hash based cache invalidation for dynamic discovery"
    - "Hierarchical project root detection in tool entrypoints"

key-files:
  created:
    - tests/unit/tools/test_base_dynamic_introspection_cache.py
  modified:
    - tools/base/bioimage_mcp_base/entrypoint.py

key-decisions:
  - "Store dynamic cache under ~/.bioimage-mcp/cache/dynamic/<tool_id> to ensure it is stable across runs and safe for tool environments."
  - "Use env/<env_id>.lock.yml hash as the primary invalidation key for dynamic introspection."

# Metrics
duration: 5 min
completed: 2026-01-28
---

# Phase 13 Plan 01: tools.base Cache Wiring Summary

**Wired lockfile-gated dynamic introspection caching into the base tool pack's meta.list, enabling sub-second repeated listing by reusing cached discovery results.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-28T20:13:03Z
- **Completed:** 2026-01-28T20:17:55Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- **Task 1: Wire IntrospectionCache + project_root into tools.base meta.list** - `4ed3358` (feat)
- **Task 2: Add unit tests for cache wiring and reuse/invalidation** - `a580e1a` (test)

## Files Created/Modified
- `tools/base/bioimage_mcp_base/entrypoint.py` - Updated `handle_meta_list` to use `IntrospectionCache` and `project_root`.
- `tests/unit/tools/test_base_dynamic_introspection_cache.py` - New test module verifying cache wiring, hit/miss behavior, and invalidation.

## Decisions Made
- Used the same heuristic for project root detection as the core server to ensure consistency.
- Standardized the dynamic cache path to be user-home-based, avoiding writes into the repository which might be read-only or managed by git.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- **ToolManifest validation:** Mock manifest in tests initially failed validation due to missing `manifest_version` and `modules` fields. Resolved by aligning mock data with Pydantic models.
- **index.lock:** Encountered a temporary git lock issue during Task 2 commit, resolved by manually removing the lock file.

## Next Phase Readiness
- `tools.base` now supports efficient discovery reuse.
- Ready for `13-02-PLAN.md` to bring the same benefits to the trackpy tool pack.

---
*Phase: 13-dynamic-introspection-cache-reuse*
*Completed: 2026-01-28*
