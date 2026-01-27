---
phase: 12-core-engine-ast-first
plan: 05
subsystem: api
tags: [discovery, schema, metadata, sqlite]

# Dependency graph
requires:
  - phase: 12-core-engine-ast-first
    provides: [Unified Discovery Orchestrator, multi-key cache invalidation]
provides:
  - describe payload aligned to Phase 12 contract
  - API wired to persistent registry schema_cache
affects: [Phase 12 complete]

# Tech tracking
tech-stack:
  added: []
  patterns: [adjacent metadata block, DB-backed schema caching]

key-files:
  created: []
  modified:
    - src/bioimage_mcp/api/discovery.py
    - src/bioimage_mcp/registry/index.py
    - src/bioimage_mcp/api/schemas.py
    - src/bioimage_mcp/runtimes/meta_protocol.py

key-decisions:
  - "Moved tool_version and introspection_source to an adjacent meta block in describe responses to keep params_schema pure."
  - "Replaced file-backed schema_cache.json with persistent SQLite registry schema_cache table for better robustness and unified management."

patterns-established:
  - "Pattern: adjacent metadata block for function details"

# Metrics
duration: 30min
completed: 2026-01-27
---

# Phase 12 Plan 05: Wire Unified Discovery Orchestrator Summary

**Aligned describe payload to Phase 12 metadata contract and wired the API layer to the persistent registry-backed schema cache.**

## Performance

- **Duration:** 30 min
- **Started:** 2026-01-27T13:53:50Z
- **Completed:** 2026-01-27T14:23:50Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- **Aligned describe payload**: The `describe` tool now returns `params_schema` as a pure JSON Schema, with `tool_version`, `introspection_source`, `callable_fingerprint`, and `module` moved to an adjacent `meta` block.
- **Unified Persistent Cache**: Removed the separate `schema_cache.json` file path. The API now uses `RegistryIndex.get_cached_schema()` and `upsert_schema_cache()` which leverage the shared SQLite database.
- **Improved Protocol Parsing**: Updated `meta.describe` worker protocol parsing to include optional `callable_fingerprint`.
- **Contract Validation**: Updated contract tests for Cellpose and general discovery to validate the new payload shape and ensure metadata fields do not leak into `params_schema`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Align meta.describe protocol and server payload contract** - `640007b` (feat)
2. **Task 2: Replace file-backed SchemaCache with persistent registry cache** - `0f89524` (feat)
3. **Task 3: Update contract tests for new metadata block** - `c6d4d8e` (test)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/api/discovery.py` - Updated `describe_function` enrichment and response shape.
- `src/bioimage_mcp/registry/index.py` - Updated `get_function` to return more metadata.
- `src/bioimage_mcp/api/schemas.py` - Added `FunctionMeta` and updated `FunctionDescriptor`.
- `src/bioimage_mcp/runtimes/meta_protocol.py` - Updated `MetaDescribeResult` model.
- `tests/contract/test_cellpose_introspection_types.py` - Added assertions for metadata absence in schema.
- `tests/contract/test_cellpose_meta_describe.py` - Aligned with new response shape.
- `tests/contract/test_describe.py` - Added meta block verification.
- `tests/contract/test_discovery_contract.py` - Updated allowed_keys.

## Decisions Made
- Used `node.module` from `ToolIndex` for the `module` field in the `meta` block to ensure consistency with the hierarchical listing.
- Retained filtering of artifact ports in the API layer even if already filtered by the engine, as a "defense in depth" measure for the API contract.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None - existing test failures in the broad suite were verified to be baseline issues unrelated to these changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Core engine integration is complete.
- Ready for final cleanup and diagnostics consolidation in Plan 12-06.

---
*Phase: 12-core-engine-ast-first*
*Completed: 2026-01-27*
