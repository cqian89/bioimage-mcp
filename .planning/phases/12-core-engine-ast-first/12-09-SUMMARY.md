---
phase: 12-core-engine-ast-first
plan: 09
subsystem: api
tags: [pydantic, json-schema, introspection]

# Dependency graph
requires:
  - phase: 12-core-engine-ast-first
    provides: [Unified DiscoveryEngine with AST-first + runtime fallback]
provides:
  - Hardened runtime params_schema emission with explicit required field validation.
  - Unit tests for required/docstring/TypeAdapter interactions.
affects: [api, registry]

# Tech tracking
tech-stack:
  added: []
  patterns: [Deterministic schema post-processing]

key-files:
  created: []
  modified: [src/bioimage_mcp/runtimes/introspect.py, tests/unit/runtimes/test_introspect.py]

key-decisions:
  - "Enforce required/properties consistency at the object level by stripping required fields that don't match emitted properties (e.g. omitted artifacts)."
  - "Omit the 'required' key entirely when empty for cleaner, more deterministic schema output."
  - "Allow TypeAdapter descriptions to be overridden by curated/docstring descriptions, but use them as high-fidelity fallbacks when no others are present."

patterns-established:
  - "Post-processing cleanup of generated schemas to ensure internal consistency (properties vs required)."

# Metrics
duration: 3min
completed: 2026-01-27
---

# Phase 12 Plan 09: Introspection Hardening Summary

**Hardened runtime parameter schema emission with explicit required-field consistency and stabilized description merging.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-27T15:41:14Z
- **Completed:** 2026-01-27T15:44:06Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Updated `introspect_python_api()` to ensure the `required` list only contains keys present in `properties`.
- Implemented removal of empty `required` keys in `introspect_python_api()`, `introspect_argparse()`, and `schema_from_descriptions()`.
- Stabilized description merging precedence (curated > docstring > TypeAdapter > fallback).
- Added comprehensive unit tests in `tests/unit/runtimes/test_introspect.py` covering artifact omission, required/docstring interaction, and TypeAdapter isolation.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add explicit required/properties validation and stabilize description merging in introspect_python_api** - `f4a8b1c` (feat)
2. **Task 2: Add unit tests for required/docstring/TypeAdapter interactions** - `a2b3c4d` (test)

**Plan metadata:** `344343d` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/runtimes/introspect.py` - Hardened schema emission logic.
- `tests/unit/runtimes/test_introspect.py` - Added 6 new unit tests for schema fidelity.

## Decisions Made
- Chose to apply required-field cleanup as a final post-processing step in both signature and argparse introspection paths for maximum reliability.
- Decided to treat `TypeAdapter` descriptions as a secondary source: better than a generic fallback but inferior to explicit docstrings or curated metadata.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Runtime introspection engine is now hardened and verified for schema fidelity.
- Ready for v0.4.0 release once remaining discovery gaps are closed.

---
*Phase: 12-core-engine-ast-first*
*Completed: 2026-01-27*
