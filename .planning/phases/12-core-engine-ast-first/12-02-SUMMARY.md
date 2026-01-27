---
phase: 12-core-engine-ast-first
plan: 02
subsystem: api
tags: [pydantic, json-schema, docstring-parser, introspection]

# Dependency graph
requires:
  - phase: 12-core-engine-ast-first
    provides: 12-01 (Static AST inspection)
provides:
  - High-fidelity runtime JSON Schema generation via Pydantic v2
  - Automated docstring parsing for parameter descriptions
  - Artifact port exclusion from params_schema
affects: [12-03, 12-04, 12-05, 12-06]

# Tech tracking
tech-stack:
  added: [docstring-parser]
  patterns: [TypeAdapter-based schema emission, artifact port omission]

key-files:
  created: []
  modified: [src/bioimage_mcp/runtimes/introspect.py, tests/unit/runtimes/test_introspect.py, envs/bioimage-mcp-base.yaml, envs/bioimage-mcp-base.lock.yml]

key-decisions:
  - "Use Pydantic v2 TypeAdapter for schema generation to leverage native Python type hint support."
  - "Omit artifact ports from params_schema by name and type to maintain separation between parameters and I/O artifacts."
  - "Prefer docstring-parser for descriptions when curated descriptions are absent."

# Metrics
duration: 15min
completed: 2026-01-27
---

# Phase 12 Plan 02: Runtime Schema Modernization Summary

**Modernized runtime introspection schema generation using Pydantic v2 TypeAdapter and integrated docstring parsing for high-fidelity, deterministic metadata.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-01-27T13:07:38Z
- **Completed:** 2026-01-27T13:22:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- **High-Fidelity Schemas:** Replaced manual type mapping with Pydantic v2 `TypeAdapter`, enabling support for `Union`, `Optional`, and other complex type hints in the `params_schema`.
- **Automated Descriptions:** Integrated `docstring-parser` to extract parameter descriptions from function docstrings, reducing the need for manual overrides.
- **Artifact Isolation:** Implemented automated omission of artifact-like parameters (e.g., `image`, `labels`, `ArtifactRef`) from the parameters schema, ensuring MCP clients only see configurable scalars/options.
- **Deterministic Output:** Guaranteed stable schema emission by sorting property keys and required parameter lists, facilitating reliable caching and contract comparisons.
- **Environment Readiness:** Updated the base tool environment spec and lockfile to include `docstring-parser`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update base tool env spec for docstring-parser** - `d39e3a8` (chore)
2. **Task 2: Replace introspect_python_api with TypeAdapter + docstring parsing** - `a2690ca` (feat)
3. **Task 3: Update unit tests to match new schema semantics** - `4c39ecf` (test)

**Plan metadata:** `docs(12-02): complete runtime schema modernization plan`

## Files Created/Modified
- `src/bioimage_mcp/runtimes/introspect.py` - Core schema generation logic.
- `tests/unit/runtimes/test_introspect.py` - Unit coverage for introspection.
- `envs/bioimage-mcp-base.yaml` - Added `docstring-parser`.
- `envs/bioimage-mcp-base.lock.yml` - Updated lockfile.

## Decisions Made
- **TypeAdapter usage:** Chose to use individual `TypeAdapter(type_hint).json_schema()` calls for each parameter to maintain fine-grained control over property merging and artifact omission.
- **Conservative artifact omission:** Defined a list of common artifact port names (`image`, `labels`, etc.) and types to prevent them from leaking into the user-facing parameters schema.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## Next Phase Readiness
- Runtime introspection now produces stable, high-fidelity schemas suitable for the unified discovery engine.
- Ready for 12-03 (Consolidate Overlays + Patch Logic).

---
*Phase: 12-core-engine-ast-first*
*Completed: 2026-01-27*
