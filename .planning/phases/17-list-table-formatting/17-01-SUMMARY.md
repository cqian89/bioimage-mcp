---
phase: 17-list-table-formatting
plan: 01
subsystem: tooling
tags: [cli, json, table, hierarchical]

# Dependency graph
requires:
  - phase: 16-stardist-tool-environment
    provides: [stardist tool pack]
provides:
  - Hierarchical CLI list output (table + JSON)
  - Tool/Package breakdown with function counts
affects: [17-02-PLAN.md]

# Tech tracking
tech-stack:
  added: []
  patterns: [Hierarchical CLI rendering, short-id filtering]

key-files:
  created: []
  modified:
    - src/bioimage_mcp/bootstrap/list.py
    - src/bioimage_mcp/bootstrap/list_cache.py
    - tests/unit/bootstrap/test_list_output.py

key-decisions:
  - "Use short tool IDs (drop 'tools.' prefix) in CLI list output"
  - "Provide a tree-style view for packages within tool-packs"
  - "Group functions into packages based on ID prefix"

patterns-established:
  - "Hierarchical CLI list transformation: transform flat manifests into Tool -> Package tree for rendering"

# Metrics
duration: 4 min
completed: 2026-02-01
---

# Phase 17 Plan 01: Hierarchical CLI list output Summary

**Hierarchical tool -> package view for `bioimage-mcp list` with tree-style table rendering and updated JSON schema**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-01T22:56:21Z
- **Completed:** 2026-02-01T23:00:31Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Implemented hierarchical tool/package payload transformation in `list_tools`.
- Replaced flat CLI table with tree-style rendering using `├──` and `└──` characters.
- Added package breakdown summary to the `Functions` column of tool rows.
- Updated JSON output to match the new hierarchical schema (`tools` -> `packages`).
- Enabled short-id filtering (e.g., `--tool base` matches `tools.base`).
- Bumped `CACHE_VERSION` to ensure invalidation of old CLI list caches.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build hierarchical tool/package payload for CLI list** - `26e838b` (feat)
2. **Task 2: Render hierarchical table output (tree-style) from payload** - `a9f547c` (feat)
3. **Task 3: Update unit tests for new table + JSON schema** - `4c2079a` (test)

**Plan metadata:** `e7d4d3d` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/bootstrap/list.py` - Hierarchical CLI list transformation + rendering
- `src/bioimage_mcp/bootstrap/list_cache.py` - Cache version bump (v3)
- `tests/unit/bootstrap/test_list_output.py` - Updated unit tests for new output shape

## Decisions Made
- Used `removeprefix("tools.")` for tool IDs in CLI output to reduce visual noise.
- Grouped functions into packages by splitting the ID segment after the tool ID prefix.
- Limited the package breakdown summary in the tool row to the first 3 packages to prevent excessive line length.
- Maintained `introspection_source` and `env_id` in the internal payload for cache invalidation logic, but omitted them from the final JSON output to keep it clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed AttributeError on Function object in list_tools**
- **Found during:** Verification after Task 1/2
- **Issue:** Code attempted to access `fn.id` but the `Function` model uses `fn_id`.
- **Fix:** Changed `fn.id` to `fn.fn_id`.
- **Files modified:** src/bioimage_mcp/bootstrap/list.py
- **Verification:** `python -m bioimage_mcp.cli list` runs without error.
- **Committed in:** `a9f547c` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor fix to align with actual model field names. No scope change.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CLI list output is now hierarchical and ready for library version enrichment.
- Ready for 17-02-PLAN.md (Lockfile-first library versions).

---
*Phase: 17-list-table-formatting*
*Completed: 2026-02-01*
