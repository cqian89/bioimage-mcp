---
phase: quick-001-fix-introspect-schema-issues
plan: 1
subsystem: Core Introspection
tags: [python, introspection, json-schema, artifacts]
requires: []
provides: [fixed-axis-inference, regionprops-artifact-omission]
affects: [tool-contract-tests]
tech-stack:
  added: []
  patterns: [Pattern-based type inference, Artifact port omission]
key-files:
  created: []
  modified: [src/bioimage_mcp/runtimes/introspect.py, tests/unit/runtimes/test_introspect.py]
decisions:
  - Phase: quick-001
    Decision: Standardize 'axis' as integer in fallback inference.
    Rationale: Runtime arrays are numpy ndarrays which only support integer indices; string labels are for xarray which is not our runtime standard.
  - Phase: quick-001
    Decision: Omit 'label_image' and 'intensity_image' from params_schema.
    Rationale: These are standard regionprops-style artifact inputs; including them in params_schema causes multiple-value-for-argument errors when the runner also binds them as artifacts.
metrics:
  duration: 102s
  completed: 2026-01-30
---

# Phase quick-001 Plan 1: Fix Introspect Schema Issues Summary

## Objective
Fix dynamic introspection schema bugs causing contract/runtime failures: emit integer axis indices (ndarray-friendly) and omit regionprops artifact inputs from params_schema.

## One-liner
Fixed axis inference to use integers and expanded artifact port omission to include regionprops-style inputs.

## Key Changes
- Updated `PARAM_TYPE_PATTERNS['axis']` to `"integer"` in `src/bioimage_mcp/runtimes/introspect.py`.
- Added `"label_image"` and `"intensity_image"` to `ARTIFACT_PORTS` to ensure they are omitted from `params_schema`.
- Added regression tests in `tests/unit/runtimes/test_introspect.py` covering both changes.

## Verification Results
- `pytest tests/unit/runtimes/test_introspect.py` passed with 30 tests (including 2 new regression tests).

## Deviations from Plan
None - plan executed exactly as written.
