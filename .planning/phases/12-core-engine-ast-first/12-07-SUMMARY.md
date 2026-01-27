---
phase: 12-core-engine-ast-first
plan: 07
subsystem: testing
tags: [ast, discovery, runtime, fallback]

# Dependency graph
requires:
  - phase: 12-core-engine-ast-first
    provides: [Unified Discovery Orchestrator]
provides:
  - Conditional runtime fallback for DiscoveryEngine
  - AST-complete isolation from tool import code
affects: [future discovery and introspection performance]

# Tech tracking
tech-stack:
  added: []
  patterns: [AST-first with selective runtime fallback]

key-files:
  created: []
  modified: [src/bioimage_mcp/registry/engine.py, tests/unit/registry/test_registry_engine.py]

key-decisions:
  - "Gated runtime fallback based on AST completeness (properties presence after filtering)."
  - "Aligned runtime describe request params with the target_fn schema used in API."

patterns-established:
  - "AST-first isolation: Prefer static inspection and only execute tool code when metadata is insufficient."

# Metrics
duration: 4 min
completed: 2026-01-27
---

# Phase 12 Plan 07: DiscoveryEngine AST-First Gating Summary

**Implemented conditional runtime fallback in DiscoveryEngine to ensure AST-complete callables do not trigger tool entrypoint execution.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-27T15:40:36Z
- **Completed:** 2026-01-27T15:44:17Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- **Conditional Fallback**: `DiscoveryEngine` now only calls `_runtime_describe` if the AST-derived schema is incomplete (missing or empty properties after artifact filtering).
- **Protocol Alignment**: Updated `_runtime_describe` to send `target_fn` in the request parameters, matching the schema expected by tool entrypoints and used in the API.
- **Unit Gating Assertions**: Added assertions to unit tests to prove that `execute_tool` is NOT called when AST data is sufficient.

## Task Commits

Each task was committed atomically:

1. **Task 1: Make runtime fallback conditional in DiscoveryEngine** - `6b643cc` (feat)
2. **Task 2: Add unit assertions that runtime fallback is not executed for AST-complete callables** - `922d645` (test)

**Plan metadata:** `e759247` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/registry/engine.py` - Updated `_process_callable` with gating logic and `_runtime_describe` with param alignment.
- `tests/unit/registry/test_registry_engine.py` - Added assertions for `execute_tool` call counts.

## Decisions Made
- **AST Completeness Definition**: Defined as having at least one non-artifact property in the schema. This ensures functions with valid signatures skip runtime fallback while those without type hints or with only artifact ports still get enriched via runtime.
- **Param Alignment**: Used `target_fn` to match the `meta.describe` protocol implementation in tool packs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `DiscoveryEngine` now correctly prioritizes AST data and maintains isolation for well-documented functions.
- Ready for Phase 12 Plan 08.

---
*Phase: 12-core-engine-ast-first*
*Completed: 2026-01-27*
