---
phase: 12-core-engine-ast-first
plan: 01
subsystem: registry
tags: [griffe, ast, fingerprint, schema-normalization]

# Dependency graph
requires:
  - phase: 11-discovery-gap-closure
    provides: [Audit gap cleanup]
provides:
  - Static inspector foundation using griffe
  - Stable callable fingerprinting
  - Deterministic JSON Schema normalization
affects: [12-02, 12-03, 12-04, 12-05]

# Tech tracking
tech-stack:
  added: [griffe, docstring-parser]
  patterns: [AST-first static analysis]

key-files:
  created:
    - src/bioimage_mcp/registry/static/inspector.py
    - src/bioimage_mcp/registry/static/fingerprint.py
    - src/bioimage_mcp/registry/static/schema_normalize.py
  modified:
    - pyproject.toml

key-decisions:
  - "Used griffe for zero-import static inspection of tool packs"
  - "Implemented stable fingerprinting based on function source text"
  - "Adopted deterministic key ordering for JSON Schema emission"

patterns-established:
  - "Static-first discovery: Use AST to extract metadata before attempting runtime import"

# Metrics
duration: 4 min
completed: 2026-01-27
---

# Phase 12 Plan 01: Static Inspector Foundation Summary

**Implemented the AST-first static inspection foundation using griffe to enable safe discovery of tool-pack signatures without importing heavy dependencies.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-27T13:03:47Z
- **Completed:** 2026-01-27T13:07:38Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Integrated `griffe` and `docstring-parser` for lightweight static analysis.
- Created a standalone static inspector that extracts function signatures, docstrings, and source without importing modules.
- Implemented SHA256-based fingerprinting for stable tracking of code changes.
- Built a recursive JSON Schema normalizer to ensure deterministic output ordering.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add static-introspection dependencies** - `146464b` (chore)
2. **Task 2: Implement griffe-based static inspector + fingerprint + schema normalization** - `120dad0` (feat)
3. **Task 3: Add unit coverage for static inspection determinism** - `9e9a73c` (test)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/registry/static/inspector.py` - Griffe-based static inspector.
- `src/bioimage_mcp/registry/static/fingerprint.py` - Source text fingerprinting.
- `src/bioimage_mcp/registry/static/schema_normalize.py` - Deterministic schema normalization.
- `src/bioimage_mcp/registry/static/__init__.py` - Module exports.
- `pyproject.toml` - Added dependencies.
- `tests/unit/registry/test_static_inspector.py` - Unit coverage.

## Decisions Made
- Chose `griffe` for its robustness in handling modern Python type hints and its ability to resolve aliases without importing.
- Standardized on `int | None` and modern typing in new registry modules.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Ruff identified existing lint issues in the codebase; verified that new code follows conventions (modern types).

## Next Phase Readiness
- Foundation is ready for Plan 12-02 (Runtime schema emission upgrade).

---
*Phase: 12-core-engine-ast-first*
*Completed: 2026-01-27*
