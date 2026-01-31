---
phase: 15-artifact-previews
plan: 03
subsystem: api
tags: [ObjectRef, native_type, x-native-type, serialization, introspect]

provides:
  - ObjectRef type visibility via native_type and x-native-type
  - repr() based previews for in-memory objects
  - Dedicated error handling for expired session-scoped object references

key-files:
  created: [tests/unit/registry/test_engine_native_type.py]
  modified: [src/bioimage_mcp/api/artifacts.py, src/bioimage_mcp/registry/engine.py, src/bioimage_mcp/api/discovery.py, src/bioimage_mcp/errors.py, tests/unit/api/test_artifacts.py]

key-decisions:
  - "Exempt ObjectRef parameters from artifact filtering in params_schema when x-native-type is present."
  - "Prefer fully qualified class names for native_type identification."
  - "Use 500 character limit for object repr previews to maintain token efficiency."
---

# Phase 15 Plan 03: ObjectRef Type Visibility Summary

**Implemented enhanced ObjectRef visibility including native type identification, repr-based previews, and session-scoped expiration handling.**

## Accomplishments
- Extended `ArtifactsService.artifact_info` to return `native_type` (fully qualified class name) and `object_preview` (truncated `repr()`) for `ObjectRef` artifacts.
- Added `OBJECT_REF_EXPIRED` error code and implemented session-scoped validation for memory artifacts.
- Enhanced `DiscoveryEngine` to automatically detect `ObjectRef` parameters and annotate them with `x-native-type` in the JSON schema.
- Modified filtering logic in both `DiscoveryEngine` and `DiscoveryService` to preserve `ObjectRef` parameters in `params_schema` when they are annotated with `x-native-type`, enabling LLMs to discover expected Python types.
- Updated `ArtifactStore` to correctly reconstruct `ObjectRef` and its subclasses (`GroupByRef`, `FigureRef`, etc.).

## Task Commits
1. **Task 1: Add ObjectRef native_type and object_preview to artifact_info** - `48aa04a` (feat)
2. **Task 2: Add x-native-type to params_schema** - `0f7fb25` (feat)
3. **Finalize Task 2 & 3: Tests and Schema consistency** - `b3ee8db` (feat)

## Deviations from Plan
- **Rule 3 - Blocking:** Discovered that `MemoryArtifactStore` uses `register()` instead of `put()`. Fixed tests accordingly.
- **Policy Adjustment:** Discovered that artifact ports were being filtered out of `params_schema` by default. Modified the filtering logic to exempt parameters with `x-native-type` so that ObjectRef types remain visible to LLMs as documented in the spec.
