---
status: diagnosed
phase: 25-add-missing-tttr-methods
source:
  - 25-01-SUMMARY.md
  - 25-02-SUMMARY.md
  - 25-03-SUMMARY.md
started: 2026-03-06T07:21:03Z
updated: 2026-03-06T08:48:58Z
---

## Current Test

[testing complete]

## Tests

### 1. Unsupported TTTR methods fail with stable guidance
expected: Calling a deferred or denied `tttrlib.*` method through MCP does not fall through to an ambiguous runtime failure. The call is rejected immediately with a stable unsupported-method error that clearly identifies the method as unsupported.
result: pass

### 2. Expanded TTTR getters and selections return artifact outputs
expected: Calling newly exposed TTTR methods such as count-rate, intensity-trace, or selection-based APIs succeeds for supported argument shapes and returns artifact-backed outputs (`NativeOutputRef` or `TableRef`) instead of raw arrays.
result: issue
reported: "- tttrlib.TTTR.get_count_rate succeeded and returned NativeOutputRef with {\"count_rate\": 10202.693119095684}.\n  - tttrlib.TTTR.get_intensity_trace still failed: unexpected keyword time_window.\n  - tttrlib.TTTR.get_selection_by_channel still failed: unexpected keyword channels.\n  - tttrlib.TTTR.get_selection_by_count_rate still failed: unexpected keyword minimum_window_length.\n  - tttrlib.TTTR.get_tttr_by_selection still reported success without exposing the expected TTTR artifact output."
severity: major

### 3. TTTR exports stay sandboxed and format-safe
expected: Write-family TTTR exports succeed only for valid output filenames inside the run work directory with the correct extension. Unsafe paths or wrong extensions are rejected with stable guardrail errors instead of writing files unexpectedly.
result: issue
reported: "- Wrong extension was correctly rejected with stable TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN.\n  - Escaping path ../escape.spc was correctly rejected with stable TTTRLIB_UNSAFE_OUTPUT_PATH.\n  - Valid in-sandbox export exports/m1_copy.spc failed unexpectedly with TTTR.write_spc132_events() missing 1 required positional argument: 'tttr'."
severity: blocker

### 4. CLSM metadata methods return JSON artifacts
expected: Calling CLSMImage metadata methods such as `get_image_info` or `get_settings` succeeds and returns JSON metadata via artifact references rather than inline raw payloads.
result: issue
reported: "PARTIAL / FAIL\n  - tttrlib.CLSMImage construction succeeded on this sample.\n  - tttrlib.CLSMImage.get_image_info succeeded and returned a NativeOutputRef; artifact content was JSON: {\"global_resolution_s\": 1.0}.\n  - tttrlib.CLSMImage.get_settings succeeded and returned a NativeOutputRef, but the artifact content was a stringified SWIG proxy, not JSON metadata."
severity: major

### 5. Correlator methods return tabular data with clear subset validation
expected: Calling Correlator methods such as `get_curve`, `get_x_axis`, or `get_corr` works for supported constructor and argument shapes, returns tabular artifacts, and rejects unsupported combinations with a stable subset-validation error.
result: issue
reported: "PARTIAL / FAIL\n  - tttrlib.Correlator constructor succeeded and returned a TableRef curve with tau,correlation.\n  - tttrlib.Correlator.get_x_axis succeeded and returned a TableRef with tau.\n  - tttrlib.Correlator.get_corr succeeded and returned a TableRef; the CSV content was tabular, though metadata/column naming looked inconsistent.\n  - tttrlib.Correlator.get_curve failed: cannot unpack non-iterable CorrelatorCurve object.\n  - Unsupported subset validation worked: passing normalize=true was rejected with stable TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN."
severity: major

## Summary

total: 5
passed: 1
issues: 4
pending: 0
skipped: 0

## Gaps

- truth: "Calling newly exposed TTTR methods such as count-rate, intensity-trace, or selection-based APIs succeeds for supported argument shapes and returns artifact-backed outputs (`NativeOutputRef` or `TableRef`) instead of raw arrays."
  status: failed
  reason: "User reported: - tttrlib.TTTR.get_count_rate succeeded and returned NativeOutputRef with {\"count_rate\": 10202.693119095684}. tttrlib.TTTR.get_intensity_trace still failed: unexpected keyword time_window. tttrlib.TTTR.get_selection_by_channel still failed: unexpected keyword channels. tttrlib.TTTR.get_selection_by_count_rate still failed: unexpected keyword minimum_window_length. tttrlib.TTTR.get_tttr_by_selection still reported success without exposing the expected TTTR artifact output."
  severity: major
  test: 2
  root_cause: "Phase 25 mapped several TTTR methods to the wrong live tttrlib signatures and emits an invalid memory-backed TTTRRef for get_tttr_by_selection, so supported calls reject valid params or complete without a usable output artifact."
  artifacts:
    - path: "tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py"
      issue: "Wrong handler signatures for get_intensity_trace, get_selection_by_channel, and get_selection_by_count_rate; invalid TTTR subset output contract in get_tttr_by_selection."
    - path: "tools/tttrlib/manifest.yaml"
      issue: "Published params drift from live tttrlib method signatures."
    - path: "tools/tttrlib/schema/tttrlib_api.json"
      issue: "Schema repeats drifted TTTR method params and output contract."
    - path: "src/bioimage_mcp/api/execution.py"
      issue: "Execution output registration ignores memory-backed TTTRRef results without file paths."
    - path: "tests/unit/test_tttrlib_entrypoint_tttr_methods.py"
      issue: "Mocks accept the wrong kwargs and miss get_selection_by_count_rate/get_tttr_by_selection output coverage."
  missing:
    - "Align manifest, schema, and handlers to the live tttrlib signatures for get_intensity_trace, get_selection_by_channel, and get_selection_by_count_rate."
    - "Either expose the real count-rate selection contract or reclassify the current drifted design as unsupported."
    - "Materialize get_tttr_by_selection as a valid file-backed TTTRRef or add proper memory-backed TTTRRef registration in execution."
    - "Add live-signature-accurate unit/integration coverage for all affected TTTR methods."
  debug_session: ".planning/debug/phase-25-uat-gap-2-tttrlib.md"
- truth: "Write-family TTTR exports succeed only for valid output filenames inside the run work directory with the correct extension. Unsafe paths or wrong extensions are rejected with stable guardrail errors instead of writing files unexpectedly."
  status: failed
  reason: "User reported: - Wrong extension was correctly rejected with stable TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN. Escaping path ../escape.spc was correctly rejected with stable TTTRLIB_UNSAFE_OUTPUT_PATH. Valid in-sandbox export exports/m1_copy.spc failed unexpectedly with TTTR.write_spc132_events() missing 1 required positional argument: 'tttr'."
  severity: blocker
  test: 3
  root_cause: "Specialized TTTR export handlers call write_spc132_events and write_hht3v2_events with the wrong argument shape, so valid guarded exports fail after validation instead of writing in-sandbox outputs."
  artifacts:
    - path: "tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py"
      issue: "Specialized export handlers omit the required tttr argument when calling write_spc132_events and write_hht3v2_events."
    - path: "tests/unit/test_tttrlib_entrypoint_tttr_methods.py"
      issue: "Fake writer signatures model the wrong one-argument API and never verify the success path for SPC export."
    - path: "tests/smoke/test_tttrlib_live.py"
      issue: "No live positive specialized-export scenario exercises the real runtime signatures."
  missing:
    - "Update specialized export handlers to forward the required TTTR object using the live upstream-safe call shape."
    - "Fix fake TTTR writer signatures and add a passing SPC export unit test."
    - "Add live smoke coverage for at least one successful specialized export path."
  debug_session: ".planning/debug/phase-25-gap-3-spc-export.md"
- truth: "Calling CLSMImage metadata methods such as `get_image_info` or `get_settings` succeeds and returns JSON metadata via artifact references rather than inline raw payloads."
  status: failed
  reason: "User reported: PARTIAL / FAIL - tttrlib.CLSMImage construction succeeded on this sample. tttrlib.CLSMImage.get_image_info succeeded and returned a NativeOutputRef; artifact content was JSON: {\"global_resolution_s\": 1.0}. tttrlib.CLSMImage.get_settings succeeded and returned a NativeOutputRef, but the artifact content was a stringified SWIG proxy, not JSON metadata."
  severity: major
  test: 4
  root_cause: "The CLSM get_settings handler dumps the raw SWIG CLSMSettings proxy through a generic JSON writer with default=str, so the artifact contains a stringified proxy instead of normalized JSON metadata."
  artifacts:
    - path: "tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py"
      issue: "get_settings passes raw CLSMSettings objects into a generic serializer that stringifies SWIG proxies."
    - path: "tests/unit/test_tttrlib_entrypoint_clsm_methods.py"
      issue: "Tests validate get_image_info payloads but not get_settings artifact content."
    - path: "tests/smoke/test_tttrlib_live.py"
      issue: "Smoke coverage checks only the NativeOutputRef shape, not whether settings content is JSON."
  missing:
    - "Add an explicit CLSMSettings serializer that converts nested SWIG values to JSON-safe Python data."
    - "Route handle_clsm_get_settings through that serializer before writing the artifact."
    - "Strengthen unit and live smoke tests to open the artifact and verify JSON object content."
  debug_session: ".planning/debug/phase25-gap4-tttrlib-settings.md"
- truth: "Calling Correlator methods such as `get_curve`, `get_x_axis`, or `get_corr` works for supported constructor and argument shapes, returns tabular artifacts, and rejects unsupported combinations with a stable subset-validation error."
  status: failed
  reason: "User reported: PARTIAL / FAIL - tttrlib.Correlator constructor succeeded and returned a TableRef curve with tau,correlation. tttrlib.Correlator.get_x_axis succeeded and returned a TableRef with tau. tttrlib.Correlator.get_corr succeeded and returned a TableRef; the CSV content was tabular, though metadata/column naming looked inconsistent. tttrlib.Correlator.get_curve failed: cannot unpack non-iterable CorrelatorCurve object. Unsupported subset validation worked: passing normalize=true was rejected with stable TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN."
  severity: major
  test: 5
  root_cause: "The get_curve handler assumes tttrlib returns an iterable tuple, but the live runtime returns a CorrelatorCurve object with x/y fields; the correlator getter family also emits inconsistent table metadata across constructor and getter paths."
  artifacts:
    - path: "tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py"
      issue: "get_curve tuple-unpacks a non-iterable CorrelatorCurve object and correlator getters build inconsistent table metadata."
    - path: "tests/unit/test_tttrlib_entrypoint_clsm_methods.py"
      issue: "Test doubles return tuples, masking the real CorrelatorCurve object shape and missing get_x_axis/get_corr metadata assertions."
    - path: "tests/smoke/test_tttrlib_live.py"
      issue: "Live smoke covers get_curve/get_x_axis but not get_corr metadata consistency."
  missing:
    - "Update get_curve to read CorrelatorCurve.x and CorrelatorCurve.y instead of tuple-unpacking."
    - "Normalize constructor and correlator getter outputs through one shared table builder."
    - "Add unit tests for non-iterable CorrelatorCurve-like objects plus explicit get_x_axis/get_corr metadata assertions and live smoke for get_corr."
  debug_session: ".planning/debug/phase-25-uat-gap-5.md"
