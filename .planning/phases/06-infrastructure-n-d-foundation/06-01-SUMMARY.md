---
phase: 06-infrastructure-n-d-foundation
plan: 1
subsystem: infra
tags: [scipy, dynamic-discovery, subprocess, metadata]

# Dependency graph
requires:
  - phase: 05.1-discovery
    provides: [standardized meta protocol]
provides:
  - rich dynamic function discovery via tool subprocesses
  - high-fidelity parameter schemas for scipy.ndimage
affects: [06-02-PLAN.md]

# Tech tracking
tech-stack:
  added: [docstring-parser]
  patterns: [Rich Subprocess Discovery]

key-files:
  created: [tests/unit/registry/test_loader_subprocess_rich_metadata.py]
  modified: [tools/base/bioimage_mcp_base/entrypoint.py, src/bioimage_mcp/registry/loader.py, src/bioimage_mcp/registry/dynamic/introspection.py]

key-decisions:
  - "Unified docstring parsing: Switched to docstring-parser as primary parser in Introspector for better cross-format support (Numpydoc, Google, Sphinx)."
  - "Transparent provenance: Prefixed subprocess-based discovery source with 'subprocess:' to distinguish it from in-process discovery."

# Metrics
duration: 20 min
completed: 2026-01-25
---

# Phase 6 Plan 1: Rich Subprocess Discovery Summary

**Enabled high-fidelity dynamic function discovery via tool subprocesses, ensuring rich parameter schemas for libraries like scipy.ndimage that cannot be imported in the server process.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-01-25T19:16:00Z
- **Completed:** 2026-01-25T19:36:32Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Implemented `meta.list` in the base tool entrypoint to return rich `FunctionMetadata`.
- Enhanced `Introspector` to use `docstring-parser` for superior schema extraction from scientific docstrings.
- Updated the registry loader to parse rich metadata (descriptions, parameters, returns) from subprocess discovery results.
- Added a hermetic unit test verifying the end-to-end rich discovery pipeline.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tool-Side meta.list: return rich FunctionMetadata for dynamic_sources** - `38d3fd8` (feat)
2. **Task 2: Loader: parse rich subprocess discovery metadata into params_schema** - `c0b721f` (feat)
3. **Task 3: Unit test: rich subprocess discovery populates params_schema** - `8566da7` (test)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/registry/dynamic/introspection.py` - Switched to docstring-parser.
- `tools/base/bioimage_mcp_base/entrypoint.py` - Added meta.list handler.
- `src/bioimage_mcp/registry/loader.py` - Updated subprocess discovery parsing.
- `tests/unit/registry/test_loader_subprocess_rich_metadata.py` - Regression test for rich discovery.

## Decisions Made
- **Unified docstring parsing:** Decided to update the core `Introspector` to use `docstring-parser` instead of just adding it to the tool entrypoint. This ensures all dynamic discovery benefits from better parsing and simplifies the `meta.list` implementation.
- **Provenance tracking:** Standardized the `introspection_source` for subprocess discovery to use the `subprocess:{adapter}` format, providing clear visibility into where tool metadata originated.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Updated Introspector to use docstring-parser**
- **Found during:** Task 1
- **Issue:** Task 1 required using `docstring-parser` for rich discovery, but the core `Introspector` (which `meta.list` uses via `discover_functions`) was still using `numpydoc`.
- **Fix:** Refactored `Introspector._parse_docstring_params` to use `docstring-parser` with a fallback to `numpydoc`.
- **Files modified:** `src/bioimage_mcp/registry/dynamic/introspection.py`
- **Verification:** Unit test passes and produces rich schemas.
- **Committed in:** `38d3fd8`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** refactoring Introspector made Task 1 implementation cleaner and benefits all tools using dynamic discovery.

## Issues Encountered
- `docstring-parser` was missing from `bioimage-mcp-base` environment lockfile despite the plan stating it was installed. Added it to the core codebase dependencies and used it in the Introspector.

## Next Phase Readiness
- Infrastructure for rich Scipy discovery is ready.
- Ready for 06-02-PLAN.md: Enable core image processing filters.

---
*Phase: 06-infrastructure-n-d-foundation*
*Completed: 2026-01-25*
