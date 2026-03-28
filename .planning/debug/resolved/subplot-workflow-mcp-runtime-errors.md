---
status: resolved
trigger: "Investigate issue: subplot-workflow-mcp-runtime-errors"
created: 2026-02-27T17:01:56+01:00
updated: 2026-02-27T17:12:25+01:00
---

## Current Focus

hypothesis: Implemented fixes should remove all three reported runtime failures.
test: Run targeted integration/unit tests for imshow param resolution and float PNG export.
expecting: New regression tests pass and no pre-existing failures appear in touched test modules.
next_action: Execute targeted pytest commands for `test_matplotlib_imshow_ref.py` and `test_io_functions.py`.

## Symptoms

expected: `base.matplotlib.Axes.imshow` should render grayscale images when given either a valid `BioImageRef` or a valid path input; exporting processed/rescaled images to PNG should succeed or perform required dtype/mode conversion automatically.
actual: `imshow` fails with type-related conversion/runtime errors depending on input mode; PNG export fails on float-mode images.
errors: 1) `BioImage does not support the image: '<class 'NoneType'>'` when params include `{"X": {"ref_id": "...BioImageRef..."}, "cmap":"gray"}`. 2) `Image data of dtype object cannot be converted to float` when params include `{"X":{"path":"...ome.zarr"}, "cmap":"gray"}`. 3) `cannot write mode F as PNG` when exporting rescaled float images via `base.io.bioimage.export`.
reproduction: Build the 1x3 subplot workflow; call `base.matplotlib.Axes.imshow` first with BioImageRef input and then with path input (`ome.zarr`), and call `base.io.bioimage.export` to PNG on rescaled float outputs.
started: Started while building the 1x3 subplot workflow; prior working state not confirmed.

## Eliminated

## Evidence

- timestamp: 2026-02-27T17:02:48+01:00
  checked: Initial codebase symbol search
  found: `base.matplotlib.Axes.imshow` is implemented in `tools/base/bioimage_mcp_base/ops/matplotlib_ops.py` and `base.io.bioimage.export` in `tools/base/bioimage_mcp_base/ops/io.py`.
  implication: Investigation should focus on these two operation modules.

- timestamp: 2026-02-27T17:03:36+01:00
  checked: Full implementation of `imshow` in `matplotlib_ops.py`
  found: `imshow` only loads image when `X` has `type == "BioImageRef"`; otherwise it passes `X` through directly to `ax.imshow`. If `type==BioImageRef` but `path` is missing, it calls `BioImage(None)`.
  implication: `X` values shaped as `{ref_id: ...}` or `{path: ...}` can produce exactly the reported `NoneType` and object-dtype errors.

- timestamp: 2026-02-27T17:03:36+01:00
  checked: Full implementation of `base.io.bioimage.export` and `_export_png` in `io.py`
  found: `_export_png` forwards ndarray to `imageio.v3.imwrite` without dtype/mode conversion.
  implication: Float arrays can hit backend writer errors like `cannot write mode F as PNG`.

- timestamp: 2026-02-27T17:04:14+01:00
  checked: Search for tests/manifests touching `imshow` and export
  found: Extensive test coverage exists in `tests/integration/test_us3_subplots.py`, `tests/integration/test_matplotlib_imshow_ref.py`, `tests/unit/api/test_io_functions.py`, and contract tests.
  implication: Fixes should be validated and likely require updating/adding targeted tests for the failing scenarios.

- timestamp: 2026-02-27T17:05:22+01:00
  checked: Existing subplot and imshow integration tests plus base manifest
  found: Existing tests cover `imshow` with `X` as numeric array and as explicit `{type: BioImageRef, path: ...}` input object; no coverage for `params.X` as `{ref_id: ...}` or `{path: ...}`. Export tests cover PNG for `uint8`, not float arrays.
  implication: Reported failures align with an uncovered edge case rather than expected behavior in current tests.

- timestamp: 2026-02-27T17:08:22+01:00
  checked: Core execution path and worker dispatch (`src/bioimage_mcp/api/execution.py`, `tools/base/bioimage_mcp_base/dynamic_dispatch.py`)
  found: `inputs` are resolved/materialized by `ref_id` before worker execution, but `params` are forwarded unchanged to adapters.
  implication: `params.X = {"ref_id": ...}` reaches `imshow` unresolved and cannot be loaded unless `imshow` or core resolves param refs.

- timestamp: 2026-02-27T17:08:22+01:00
  checked: `imshow` loader implementation details
  found: For `BioImageRef`, `imshow` calls `BioImage(x_val.get("path"))` and ignores `uri`; non-typed dicts (e.g., `{path: ...}`) are passed directly to `ax.imshow`.
  implication: Direct mechanism for both reported runtime errors is confirmed.

- timestamp: 2026-02-27T17:12:25+01:00
  checked: Targeted regression tests
  found: `pytest tests/integration/test_matplotlib_imshow_ref.py -q` and `pytest tests/unit/api/test_io_functions.py -q` passed after fixes.
  implication: Confirmed `imshow` param ref/path handling and float-to-PNG export conversion now work in covered scenarios.

## Resolution

root_cause: `base.matplotlib.Axes.imshow` does not robustly resolve artifact-like `X` parameters (expects `type/path` and ignores `uri`, passes dicts through), while execution only resolves artifact refs in `inputs` not `params`; additionally, `_export_png` writes float arrays without conversion to PNG-supported integer modes.
fix:
  - Added recursive parameter ref resolution in `ExecutionService.run_workflow` so dict params containing `ref_id` are hydrated like inputs.
  - Reworked `matplotlib_ops.imshow` image loading to use a generic resolver that supports dict `path`, `uri`, `ref_id`, object-cache entries, and list data.
  - Added float/bool/integer coercion in `_export_png` to write PNG-compatible dtypes.
verification:
  - Verified by passing targeted tests: `tests/integration/test_matplotlib_imshow_ref.py` and `tests/unit/api/test_io_functions.py`.
  - New tests specifically cover `params.X` as `{ref_id: ...}`, `params.X` as `{path: ...}`, and float image export to PNG.
files_changed:
  - src/bioimage_mcp/api/execution.py
  - tools/base/bioimage_mcp_base/ops/matplotlib_ops.py
  - tools/base/bioimage_mcp_base/ops/io.py
  - tests/integration/test_matplotlib_imshow_ref.py
  - tests/unit/api/test_io_functions.py
