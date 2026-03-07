---
status: complete
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
updated: 2026-03-07T02:49:50Z
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
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Unsafe output paths or wrong extensions are rejected with stable guardrail errors, removed specialized export methods fail cleanly as unsupported, and supported tttrlib.TTTR.write exports only succeed when a real file is created inside the run work directory."
  status: failed
  reason: "User reported: Unsafe path guardrail worked, but wrong-extension and supported .spc exports both failed with TTTRRef format schema validation instead of stable export guardrail behavior, and removed specialized export methods returned NOT_FOUND rather than TTTRLIB_UNSUPPORTED_METHOD."
  severity: blocker
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "tttrlib.CLSMImage.get_image_info and get_settings return JSON metadata through artifact references, and the serialized payload excludes SWIG transport fields like this and thisown while preserving useful domain metadata."
  status: failed
  reason: "User reported: get_image_info returned clean JSON metadata, but get_settings still included SWIG transport fields this and thisown."
  severity: major
  test: 4
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
