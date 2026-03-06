---
status: diagnosed
trigger: "Diagnose Phase 25 UAT gap #4 in /mnt/c/Users/meqia/bioimage-mcp.\n\nIssue summary:\n- `tttrlib.CLSMImage` construction succeeds.\n- `tttrlib.CLSMImage.get_image_info` succeeds and returns JSON via NativeOutputRef.\n- `tttrlib.CLSMImage.get_settings` succeeds and returns NativeOutputRef, but artifact content is a stringified SWIG proxy instead of JSON metadata.\n\nGoal: identify the concrete root cause(s), impacted files, and missing changes needed. Read the relevant code, tests, schemas, and summaries. Do not modify files. Return a concise diagnosis with:\n1. root_cause\n2. artifacts: list of file paths plus issue\n3. missing: list of specific fixes\n4. suggested debug_session path name\n5. confidence"
created: 2026-03-06T00:00:00Z
updated: 2026-03-06T08:23:00Z
---

## Current Focus

hypothesis: `handle_clsm_get_settings` incorrectly passes a SWIG `CLSMSettings` object straight into `_write_native_output`, whose `json.dump(..., default=str)` silently stringifies it; tests/schema only check ref shape so the bad payload escaped.
test: confirm runtime type/value of `clsm.get_settings()`, compare with `get_image_info()`, and inspect unit/smoke/contract coverage around payload content.
expecting: runtime inspection will show `get_settings()` returns a SWIG proxy rather than a dict, and tests will not assert JSON content for settings artifacts.
next_action: finalize diagnosis and record impacted files plus missing changes.

## Symptoms

expected: `tttrlib.CLSMImage.get_settings` should emit JSON metadata via `NativeOutputRef`, consistent with `tttrlib.CLSMImage.get_image_info`.
actual: `tttrlib.CLSMImage.get_settings` succeeds but artifact content is a stringified SWIG proxy instead of JSON metadata.
errors: none reported; incorrect artifact payload.
reproduction: construct `tttrlib.CLSMImage`, call `get_settings`, inspect returned `NativeOutputRef` artifact content.
started: observed during Phase 25 UAT gap #4.

## Eliminated

## Evidence

- timestamp: 2026-03-06T08:12:00Z
  checked: tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py
  found: `_write_native_output()` writes arbitrary payloads with `json.dump(payload, default=str)`; `handle_clsm_get_image_info()` and `handle_clsm_get_settings()` both pass raw return values directly into this helper.
  implication: any non-JSON-serializable metadata object will be silently converted to a string instead of raising or being normalized.

- timestamp: 2026-03-06T08:14:00Z
  checked: live tttrlib runtime against `datasets/tttr-data/imaging/leica/sp5/LSM_1.ptu`
  found: `clsm.get_image_info()` returns a Python `dict`, while `clsm.get_settings()` returns `CLSMSettings` shown as `<tttrlib.tttrlib.CLSMSettings; proxy of <Swig Object ...>>`.
  implication: the two handlers are not equivalent at runtime; only `get_image_info()` is already JSON-safe.

- timestamp: 2026-03-06T08:15:00Z
  checked: live tttrlib runtime attribute access on `CLSMSettings`
  found: settings fields are exposed as attributes like `n_lines`, `n_pixel_per_line`, `marker_line_start`, plus nested SWIG containers such as `marker_frame_start` (`VectorInt32`) that require explicit conversion (for example `list(v)` -> `[4, 6]`).
  implication: a correct fix needs a dedicated serializer/normalizer for `CLSMSettings`, not just the existing `default=str` fallback.

- timestamp: 2026-03-06T08:17:00Z
  checked: tests/unit/test_tttrlib_entrypoint_clsm_methods.py and tests/smoke/test_tttrlib_live.py
  found: unit coverage asserts JSON content only for `get_image_info`; there is no unit test for `get_settings`, and the live smoke test only validates that both methods return `NativeOutputRef` refs without opening the settings artifact.
  implication: regression coverage misses the exact payload-level contract that UAT exercised.

- timestamp: 2026-03-06T08:18:00Z
  checked: tools/tttrlib/manifest.yaml, tools/tttrlib/schema/tttrlib_api.json, tools/tttrlib/schema/tttrlib_coverage.json, and Phase 25 summary/verification docs
  found: all declare/claim `tttrlib.CLSMImage.get_settings` returns NativeOutputRef JSON metadata and mark the work verified.
  implication: metadata/contracts and summaries overstate actual behavior; diagnosis must include docs/schema/test updates alongside code fix.

## Resolution

root_cause: `tttrlib.CLSMImage.get_settings()` returns a SWIG `CLSMSettings` object, but `handle_clsm_get_settings()` treats it like already-JSON-safe data and sends it through `_write_native_output()`, whose `json.dump(..., default=str)` stringifies the proxy instead of serializing metadata fields. The bug escaped because payload-level assertions exist for `get_image_info` only, while `get_settings` tests and smoke coverage check only the artifact reference shape.
fix: Diagnose-only session; no code changes applied.
verification: Root cause confirmed by code inspection plus live tttrlib runtime inspection showing `get_image_info()` -> `dict` and `get_settings()` -> `CLSMSettings` SWIG proxy.
files_changed: []
