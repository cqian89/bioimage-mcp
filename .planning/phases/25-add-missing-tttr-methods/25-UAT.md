---
status: diagnosed
phase: 25-add-missing-tttr-methods
source:
  - 25-01-SUMMARY.md
  - 25-02-SUMMARY.md
  - 25-03-SUMMARY.md
  - 25-04-SUMMARY.md
  - 25-05-SUMMARY.md
started: 2026-03-06T10:00:00Z
updated: 2026-03-06T10:23:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Unsupported TTTR methods fail with stable guidance
expected: Calling a deferred or denied `tttrlib.*` method through MCP does not fall through to an ambiguous runtime failure. The call is rejected immediately with a stable unsupported-method error that clearly identifies the method as unsupported.
result: issue
reported: "Calling deferred method tttrlib.TTTR.get_microtime_histogram was rejected immediately, but the MCP error was NOT_FOUND (Function not found) rather than a stable TTTRLIB_UNSUPPORTED_METHOD that explicitly marks the method unsupported."
severity: major

### 2. Expanded TTTR getters and selections return artifact outputs
expected: Calling newly exposed TTTR methods such as count-rate, intensity-trace, or selection-based APIs succeeds for supported argument shapes and returns artifact-backed outputs (`NativeOutputRef`, `TableRef`, or `TTTRRef`) instead of raw arrays or unusable in-memory results.
result: issue
reported: "tttrlib.TTTR.get_count_rate succeeded and returned a NativeOutputRef JSON artifact ({\"count_rate\": 10202.693119095684}); tttrlib.TTTR.get_intensity_trace succeeded and returned a TableRef with time and count_rate columns (18,007 rows); tttrlib.TTTR.get_tttr_by_selection succeeded and returned a file-backed TTTRRef. tttrlib.TTTR.get_selection_by_channel with input=[1] returned a TableRef, but it was empty/malformed-looking; tttrlib.TTTR.get_selection_by_count_rate failed with table validation instead of producing a usable artifact."
severity: major

### 3. TTTR exports stay sandboxed and format-safe
expected: Write-family TTTR exports succeed only for valid output filenames inside the run work directory with the correct extension. Unsafe paths or wrong extensions are rejected with stable guardrail errors instead of writing files unexpectedly.
result: issue
reported: "Guardrails worked for invalid outputs: bad_extension.txt was rejected with TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN, and ../escape.spc was rejected with TTTRLIB_UNSAFE_OUTPUT_PATH. Valid export attempts did not succeed: tttrlib.TTTR.write_spc132_events with export_ok.spc failed at runtime, and tttrlib.TTTR.write_header / tttrlib.TTTR.write also failed rather than completing a sandboxed export."
severity: blocker

### 4. CLSM metadata methods return JSON artifacts
expected: Calling CLSMImage metadata methods such as `get_image_info` or `get_settings` succeeds and returns JSON metadata via artifact references rather than inline raw payloads or stringified SWIG proxies.
result: issue
reported: "After constructing tttrlib.CLSMImage with reading_routine=\"BH_SPC130\", marker_frame_start=[4], marker_line_start=2, marker_line_stop=3, channels=[0], both metadata calls succeeded and returned NativeOutputRef JSON artifacts. get_image_info looked clean (dimensions, global_resolution_s), but get_settings still included SWIG-style fields like this and thisown, so the output was not fully cleaned JSON metadata."
severity: major

### 5. Correlator methods return consistent tabular data with clear subset validation
expected: Calling Correlator methods such as `get_curve`, `get_x_axis`, or `get_corr` works for supported constructor and argument shapes, returns consistent tabular artifacts with usable columns, and rejects unsupported combinations with a stable subset-validation error.
result: pass

## Summary

total: 5
passed: 1
issues: 4
pending: 0
skipped: 0

## Gaps

- truth: "Calling a deferred or denied `tttrlib.*` method through MCP does not fall through to an ambiguous runtime failure. The call is rejected immediately with a stable unsupported-method error that clearly identifies the method as unsupported."
  status: failed
  reason: "User reported: Calling deferred method tttrlib.TTTR.get_microtime_histogram was rejected immediately, but the MCP error was NOT_FOUND (Function not found) rather than a stable TTTRLIB_UNSUPPORTED_METHOD that explicitly marks the method unsupported."
  severity: major
  test: 1
  root_cause: "`tttrlib.TTTR.get_microtime_histogram` is classified as deferred in coverage metadata but is missing from the manifest-visible MCP surface, so core execution raises `NOT_FOUND` before the tttrlib worker can emit `TTTRLIB_UNSUPPORTED_METHOD`."
  artifacts:
    - path: "tools/tttrlib/schema/tttrlib_coverage.json"
      issue: "Contains the deferred classification for `tttrlib.TTTR.get_microtime_histogram`, proving the unsupported status exists only in coverage metadata."
    - path: "tools/tttrlib/manifest.yaml"
      issue: "Does not publish `tttrlib.TTTR.get_microtime_histogram`, so the function never reaches worker dispatch."
    - path: "tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py"
      issue: "Unsupported-method helpers exist, but there is no handler/stub path for this deferred method."
    - path: "src/bioimage_mcp/api/execution.py"
      issue: "Function lookup requires manifest-visible registration and converts the missing ID into MCP `NOT_FOUND`."
  missing:
    - "Add a manifest-visible route for deferred/denied tttrlib IDs so unsupported methods can reach the tttrlib worker."
    - "Add a worker-side stub or dispatch entry for `tttrlib.TTTR.get_microtime_histogram` that returns `TTTRLIB_UNSUPPORTED_METHOD`."
    - "Add end-to-end coverage proving deferred tttrlib methods return `TTTRLIB_UNSUPPORTED_METHOD` instead of core `NOT_FOUND`."
  debug_session: ".planning/debug/phase-25-uat-gap-1-tttrlib.md"
- truth: "Calling newly exposed TTTR methods such as count-rate, intensity-trace, or selection-based APIs succeeds for supported argument shapes and returns artifact-backed outputs (`NativeOutputRef`, `TableRef`, or `TTTRRef`) instead of raw arrays or unusable in-memory results."
  status: failed
  reason: "User reported: tttrlib.TTTR.get_count_rate succeeded and returned a NativeOutputRef JSON artifact ({\"count_rate\": 10202.693119095684}); tttrlib.TTTR.get_intensity_trace succeeded and returned a TableRef with time and count_rate columns (18,007 rows); tttrlib.TTTR.get_tttr_by_selection succeeded and returned a file-backed TTTRRef. tttrlib.TTTR.get_selection_by_channel with input=[1] returned a TableRef, but it was empty/malformed-looking; tttrlib.TTTR.get_selection_by_count_rate failed with table validation instead of producing a usable artifact."
  severity: major
  test: 2
  root_cause: "TTTR selection handlers emit single-column CSV outputs without preserved table metadata, and the core table importer mis-parses single-column or header-only CSVs, so channel selections look malformed and empty count-rate selections fail `TableRef` validation."
  artifacts:
    - path: "tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py"
      issue: "`_write_selection_table` returns top-level table fields but omits `metadata`, which is what execution import actually preserves."
    - path: "src/bioimage_mcp/artifacts/metadata.py"
      issue: "`extract_table_metadata()` relies on CSV sniffing that is brittle for single-column and header-only CSV files."
    - path: "src/bioimage_mcp/api/execution.py"
      issue: "Only forwards `out[\"metadata\"]` during output import, discarding top-level `columns`/`row_count`."
    - path: "tests/unit/test_tttrlib_entrypoint_tttr_methods.py"
      issue: "Tests stop at raw handler output and miss end-to-end execution/import coverage for empty one-column tables."
  missing:
    - "Populate explicit `metadata.columns` and `metadata.row_count` for TTTR selection table outputs."
    - "Make table metadata extraction deterministic for single-column and header-only CSVs."
    - "Add end-to-end tests for `get_selection_by_channel` and empty `get_selection_by_count_rate` execution paths."
  debug_session: ".planning/debug/phase-25-gap-2-tttr-diagnosis.md"
- truth: "Write-family TTTR exports succeed only for valid output filenames inside the run work directory with the correct extension. Unsafe paths or wrong extensions are rejected with stable guardrail errors instead of writing files unexpectedly."
  status: failed
  reason: "User reported: Guardrails worked for invalid outputs: bad_extension.txt was rejected with TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN, and ../escape.spc was rejected with TTTRLIB_UNSAFE_OUTPUT_PATH. Valid export attempts did not succeed: tttrlib.TTTR.write_spc132_events with export_ok.spc failed at runtime, and tttrlib.TTTR.write_header / tttrlib.TTTR.write also failed rather than completing a sandboxed export."
  severity: blocker
  test: 3
  root_cause: "The MCP surface advertises filename-based TTTR export contracts that do not match the live tttrlib Python bindings: `write_spc132_events` expects a `FILE*`, `write_header` is not safely callable through the binding, and `write()` can report success without producing an output file for unsupported source/container combinations."
  artifacts:
    - path: "tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py"
      issue: "Export handlers assume path-string-safe bindings and never verify that `write()` actually produced a file."
    - path: "tools/tttrlib/manifest.yaml"
      issue: "Publishes `write`, `write_header`, and `write_spc132_events` as ordinary filename-based exports even when the live runtime does not support that subset consistently."
    - path: "tools/tttrlib/schema/tttrlib_api.json"
      issue: "Mirrors the overstated export contract and guides callers into runtime-only failures."
    - path: "tests/unit/test_tttrlib_entrypoint_tttr_methods.py"
      issue: "Fake writers always succeed, so binding mismatch and no-file cases are not covered."
  missing:
    - "Reclassify or remove unsupported TTTR export methods from the supported MCP surface unless a real Python-safe wrapper is implemented."
    - "Make `handle_tttr_write()` fail deterministically when upstream returns false or leaves no output file."
    - "Add regression coverage for runtime binding mismatches and no-file export cases."
  debug_session: ".planning/debug/phase-25-uat-gap-3-export-runtime.md"
- truth: "Calling CLSMImage metadata methods such as `get_image_info` or `get_settings` succeeds and returns JSON metadata via artifact references rather than inline raw payloads or stringified SWIG proxies."
  status: failed
  reason: "User reported: After constructing tttrlib.CLSMImage with reading_routine=\"BH_SPC130\", marker_frame_start=[4], marker_line_start=2, marker_line_stop=3, channels=[0], both metadata calls succeeded and returned NativeOutputRef JSON artifacts. get_image_info looked clean (dimensions, global_resolution_s), but get_settings still included SWIG-style fields like this and thisown, so the output was not fully cleaned JSON metadata."
  severity: major
  test: 4
  root_cause: "`get_settings` serializes every public attribute on the live SWIG-backed `CLSMSettings` proxy, so transport fields like `this` and `thisown` leak into the JSON artifact and tests do not currently assert their absence."
  artifacts:
    - path: "tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py"
      issue: "`_serialize_clsm_settings()` walks generic public attributes without filtering SWIG proxy field names."
    - path: "tests/unit/test_tttrlib_entrypoint_clsm_methods.py"
      issue: "Fake settings objects only include clean domain fields, so leakage is never exercised in unit tests."
    - path: "tests/smoke/test_tttrlib_live.py"
      issue: "Live smoke checks for non-empty JSON but not for absence of `this`/`thisown`."
  missing:
    - "Filter or whitelist serialized `CLSMSettings` fields so SWIG proxy transport attrs are excluded."
    - "Extend unit tests with SWIG-style attributes and assert they are removed."
    - "Extend smoke checks to assert `this` and `thisown` are absent from `get_settings` artifacts."
  debug_session: ".planning/debug/phase25-gap4-tttrlib-settings-diagnosis.md"
