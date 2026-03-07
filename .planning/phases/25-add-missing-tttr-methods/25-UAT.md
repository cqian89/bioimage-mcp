---
status: diagnosed
phase: 25-add-missing-tttr-methods
source:
  - 25-01-SUMMARY.md
  - 25-02-SUMMARY.md
  - 25-03-SUMMARY.md
  - 25-04-SUMMARY.md
  - 25-05-SUMMARY.md
  - 25-06-SUMMARY.md
  - 25-07-SUMMARY.md
  - 25-08-SUMMARY.md
started: 2026-03-07T02:49:50Z
updated: 2026-03-07T03:02:56Z
---

## Current Test

[testing complete]

## Tests

### 1. Unsupported TTTR methods fail with stable guidance
expected: Calling a deferred or removed `tttrlib.*` method through MCP is rejected immediately with a stable `TTTRLIB_UNSUPPORTED_METHOD` error that clearly marks the method unsupported, rather than a generic missing-function or runtime failure.
result: pass

### 2. TTTR getters and selections return usable artifact outputs
expected: Calling supported TTTR methods such as `get_count_rate`, `get_intensity_trace`, `get_selection_by_channel`, `get_selection_by_count_rate`, and `get_tttr_by_selection` succeeds for supported argument shapes and returns usable artifact-backed outputs (`NativeOutputRef`, `TableRef`, or file-backed `TTTRRef`) with sensible table metadata, including empty-selection cases.
result: issue
reported: "Returned artifacts were usable and selection/count-rate flows worked, but selection and intensity-trace table metadata reported column dtypes as string instead of numeric despite numeric CSV contents."
severity: minor

### 3. TTTR export surface is runtime-safe and sandboxed
expected: Unsafe output paths or wrong extensions are rejected with stable guardrail errors, removed specialized export methods fail cleanly as unsupported, and supported `tttrlib.TTTR.write` exports only succeed when a real file is created inside the run work directory.
result: issue
reported: "Unsafe path guardrail worked, but wrong-extension and supported .spc exports both failed with TTTRRef format schema validation instead of stable export guardrail behavior, and removed specialized export methods returned NOT_FOUND rather than TTTRLIB_UNSUPPORTED_METHOD."
severity: blocker

### 4. CLSM metadata artifacts are clean JSON
expected: `tttrlib.CLSMImage.get_image_info` and `tttrlib.CLSMImage.get_settings` return JSON metadata through artifact references, and the serialized payload excludes SWIG transport fields like `this` and `thisown` while preserving useful domain metadata.
result: issue
reported: "`get_image_info` returned clean JSON metadata, but `get_settings` still included SWIG transport fields `this` and `thisown`."
severity: major

### 5. Correlator getters return consistent tabular artifacts
expected: Calling Correlator methods such as `get_curve`, `get_x_axis`, and `get_corr` works for supported constructor and argument shapes, returns consistent table artifacts with usable columns and metadata, and rejects unsupported combinations with a stable subset-validation error.
result: pass

## Summary

total: 5
passed: 2
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: "Calling supported TTTR methods such as get_count_rate, get_intensity_trace, get_selection_by_channel, get_selection_by_count_rate, and get_tttr_by_selection succeeds for supported argument shapes and returns usable artifact-backed outputs with sensible numeric table metadata, including empty-selection cases."
  status: failed
  reason: "User reported: Returned artifacts were usable and selection/count-rate flows worked, but selection and intensity-trace table metadata reported column dtypes as string instead of numeric despite numeric CSV contents."
  severity: minor
  test: 2
  root_cause: "TTTR table handlers still emit schema only as top-level columns/row_count instead of nested metadata.columns/metadata.row_count, execution import drops that top-level schema, and preview fallback labels columns as string when high-fidelity metadata is missing."
  artifacts:
    - path: "tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py"
      issue: "`handle_get_intensity_trace()` and `_write_selection_table()` omit nested table metadata even though correlator table helpers include it."
    - path: "src/bioimage_mcp/api/execution.py"
      issue: "Only `out[\"metadata\"]` is preserved during file import, so top-level TTTR table schema is discarded."
    - path: "src/bioimage_mcp/artifacts/metadata.py"
      issue: "Generic CSV dtype inference is brittle for one-column/header-only TTTR tables."
    - path: "src/bioimage_mcp/artifacts/preview.py"
      issue: "Fallback preview dtypes are hardcoded to `string` when richer metadata is unavailable."
  missing:
    - "Emit `metadata.columns` and `metadata.row_count` for affected TTTR table outputs."
    - "Or merge top-level table schema into nested metadata before import in execution."
    - "Stop relying on generic CSV sniffing for TTTR selection table dtype metadata."
  debug_session: ".planning/debug/phase25-gap2-table-dtypes.md"
- truth: "Unsafe output paths or wrong extensions are rejected with stable guardrail errors, removed specialized export methods fail cleanly as unsupported, and supported tttrlib.TTTR.write exports only succeed when a real file is created inside the run work directory."
  status: failed
  reason: "User reported: Unsafe path guardrail worked, but wrong-extension and supported .spc exports both failed with TTTRRef format schema validation instead of stable export guardrail behavior, and removed specialized export methods returned NOT_FOUND rather than TTTRLIB_UNSUPPORTED_METHOD."
  severity: blocker
  test: 3
  root_cause: "The current working tree regressed the Phase 25 export-safety changes: TTTR write handlers now derive invalid `TTTRRef.format` values from raw suffixes like `TXT`/`SPC`, generic `tttrlib.TTTR.write` no longer verifies file creation, and execution fallback for removed/deferred tttrlib IDs was removed so specialized export methods now fail at core lookup with `NOT_FOUND`."
  artifacts:
    - path: "tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py"
      issue: "Builds `TTTRRef` formats from raw suffixes and returns write success without verifying a file exists."
    - path: "src/bioimage_mcp/api/execution.py"
      issue: "Coverage-based tttrlib fallback for removed/deferred IDs is missing, so removed exports resolve to `NOT_FOUND`."
    - path: "src/bioimage_mcp/artifacts/models.py"
      issue: "`TTTRRef` accepts canonical formats only, which is why `TXT` and `SPC` fail schema validation."
    - path: "tools/tttrlib/manifest.yaml"
      issue: "Re-exposes specialized export IDs that were supposed to stay out of discovery."
    - path: "tools/tttrlib/schema/tttrlib_api.json"
      issue: "Republishes the removed specialized export surface."
    - path: "tools/tttrlib/schema/tttrlib_coverage.json"
      issue: "Coverage statuses regressed away from deferred runtime rejection for removed export methods."
  missing:
    - "Restore canonical TTTR format mapping and post-write file-existence checks in the tttrlib entrypoint."
    - "Reinstate execution-layer fallback so removed/deferred tttrlib export IDs return `TTTRLIB_UNSUPPORTED_METHOD` instead of `NOT_FOUND`."
    - "Re-align manifest/schema/coverage with the reduced runtime-safe export surface."
  debug_session: ".planning/debug/tttr-export-guardrail-diagnose.md"
- truth: "tttrlib.CLSMImage.get_image_info and get_settings return JSON metadata through artifact references, and the serialized payload excludes SWIG transport fields like this and thisown while preserving useful domain metadata."
  status: failed
  reason: "User reported: get_image_info returned clean JSON metadata, but get_settings still included SWIG transport fields this and thisown."
  severity: major
  test: 4
  root_cause: "The current working tree regressed the Phase 25 CLSM cleanup: `_normalize_json_safe_value()` again serializes every public `CLSMSettings` attribute, so live SWIG proxy fields `this` and `thisown` leak into the output, and the matching unit/smoke assertions that were meant to catch this regression were removed."
  artifacts:
    - path: "tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py"
      issue: "Serializer no longer filters SWIG transport attrs before JSON export."
    - path: "tests/unit/test_tttrlib_entrypoint_clsm_methods.py"
      issue: "Regression test no longer models `this`/`thisown` or asserts their absence."
    - path: "tests/smoke/test_tttrlib_live.py"
      issue: "Live smoke test checks for non-empty payloads but no longer rejects SWIG transport keys."
    - path: ".planning/phases/25-add-missing-tttr-methods/25-08-SUMMARY.md"
      issue: "Documents cleanup that no longer matches the current working tree."
  missing:
    - "Restore SWIG transport-field filtering in the CLSM settings serializer."
    - "Reinstate unit coverage that injects `this` and `thisown` and asserts they are removed."
    - "Reinstate smoke coverage that rejects `this` and `thisown` while keeping domain-field checks."
  debug_session: ".planning/debug/phase25-gap4-settings-swig.md"
