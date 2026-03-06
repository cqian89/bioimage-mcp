---
status: diagnosed
trigger: "Diagnose Phase 25 UAT gap #2 in /mnt/c/Users/meqia/bioimage-mcp.\n\nIssue summary:\n- `tttrlib.TTTR.get_count_rate` works and returns NativeOutputRef.\n- `tttrlib.TTTR.get_intensity_trace` fails with `unexpected keyword time_window`.\n- `tttrlib.TTTR.get_selection_by_channel` fails with `unexpected keyword channels`.\n- `tttrlib.TTTR.get_selection_by_count_rate` fails with `unexpected keyword minimum_window_length`.\n- `tttrlib.TTTR.get_tttr_by_selection` reports success but does not expose the expected TTTR artifact output.\n\nGoal: identify the concrete root cause(s), impacted files, and missing changes needed. Read the relevant code, tests, schemas, and summaries. Do not modify files. Return a concise diagnosis with:\n1. root_cause\n2. artifacts: list of file paths plus issue\n3. missing: list of specific fixes\n4. suggested debug_session path name\n5. confidence"
created: 2026-03-06T16:01:36+08:00
updated: 2026-03-06T16:13:36+08:00
---

## Current Focus

hypothesis: Phase 25 TTTR method mappings were added against incorrect curated signatures, and the subset-output path for TTTRRef artifacts was never wired through execution.
test: compare manifest/schema/handler contracts against live tttrlib signatures and inspect execution output registration for TTTRRef results without file paths.
expecting: live signatures will contradict the curated kwargs, and execution will omit memory-backed TTTRRef outputs.
next_action: return root-cause diagnosis with impacted files and missing fixes.

## Symptoms

expected: tttrlib TTTR methods accept their advertised parameters and expose expected artifact outputs.
actual: several TTTR methods reject advertised keywords, and get_tttr_by_selection succeeds without exposing a TTTR artifact output.
errors: unexpected keyword time_window; unexpected keyword channels; unexpected keyword minimum_window_length; missing TTTR artifact output after reported success.
reproduction: invoke tttrlib.TTTR.get_intensity_trace, get_selection_by_channel, get_selection_by_count_rate, and get_tttr_by_selection via MCP/UAT flow.
started: observed in Phase 25 UAT gap #2.

## Eliminated

## Evidence

- timestamp: 2026-03-06T16:08:00+08:00
  checked: tools/tttrlib manifest, schema, entrypoint, and Phase 25 summary files
  found: Phase 25 declared `get_intensity_trace(time_window)`, `get_selection_by_channel(channels)`, `get_selection_by_count_rate(minimum_window_length, minimum_number_of_photons_in_time_window, ...)`, and `get_tttr_by_selection(selection)` as supported/supported_subset and wired handlers accordingly.
  implication: the curated MCP contract for these methods depends entirely on the new Phase 25 wrapper code and metadata being correct.

- timestamp: 2026-03-06T16:10:00+08:00
  checked: live tttrlib signatures via `conda run -n bioimage-mcp-tttrlib python -c ... inspect.signature(...)`
  found: upstream signatures are `get_intensity_trace(self, time_window_length=0.001)`, `get_selection_by_channel(self, input)`, `get_selection_by_count_rate(self, time_window, n_ph_max, invert=False, make_mask=False)`, and `get_tttr_by_selection(self, selection)`.
  implication: the wrapper metadata and handler call shapes do not match upstream tttrlib for three of the four failing methods; kwargs like `time_window`, `channels`, and `minimum_window_length` are invalid upstream.

- timestamp: 2026-03-06T16:11:00+08:00
  checked: `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` handler implementations
  found: handlers call `tttr.get_intensity_trace(**params)`, `tttr.get_selection_by_channel(channels=channels)`, and `tttr.get_selection_by_count_rate(**params)`; `get_tttr_by_selection` returns a `TTTRRef` with `storage_type: memory`, no `path`, and a reused file URI.
  implication: three methods fail at runtime with exact unexpected-keyword errors, and the TTTR subset output is emitted in a shape that execution does not materialize or register.

- timestamp: 2026-03-06T16:12:00+08:00
  checked: `src/bioimage_mcp/api/execution.py` output registration and `src/bioimage_mcp/artifacts/models.py` validation
  found: execution only persists file-backed outputs in the `elif path:` branch and only registers memory artifacts for image/object types; no branch handles memory-backed `TTTRRef` outputs without `path`. Artifact models also require `storage_type=memory` artifacts to use `mem://` or `obj://` URIs.
  implication: `get_tttr_by_selection` can report tool success yet expose no output because the returned TTTRRef is both structurally invalid and ignored by execution output registration.

- timestamp: 2026-03-06T16:13:00+08:00
  checked: `tests/unit/test_tttrlib_entrypoint_tttr_methods.py`, contract tests, and legacy integration tests
  found: unit tests use fake methods whose Python signatures accept the incorrect kwargs, contract tests only check presence/parity, and there are no direct tests for `get_selection_by_count_rate` or `get_tttr_by_selection`. Legacy integration still expects `time_window_length`, which no longer appears in tool metadata.
  implication: test coverage masked the signature drift and never exercised the missing TTTRRef output path.

## Resolution

root_cause:
  Phase 25 introduced incorrect curated contracts for three TTTR methods and an incomplete execution path for TTTR subset outputs. `get_intensity_trace` was renamed from the spec's `time_window_length` to `time_window`; `get_selection_by_channel` and `get_selection_by_count_rate` were modeled as keyword-based supported subsets even though live tttrlib exposes positional signatures (`input`, `time_window`, `n_ph_max`, ...). Separately, `get_tttr_by_selection` returns a memory-backed `TTTRRef` without a file path, but `ExecutionService` has no branch to register non-object memory outputs of type `TTTRRef`, and the emitted URI/storage_type combination is invalid for memory artifacts.
fix:
  Not applied (diagnosis only).
verification:
  Verified by file inspection plus live signature introspection in the `bioimage-mcp-tttrlib` conda environment.
files_changed: []
