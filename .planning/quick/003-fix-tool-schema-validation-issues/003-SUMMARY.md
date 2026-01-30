# Phase quick-003 Plan 003: Fix tool schema validation issues Summary

Unified introspection engine alignment across three tool-pack regressions: phasorpy output naming, skimage artifact omission, and export parameter standardization.

## Summary
Fixed three schema-validation regressions by aligning tool describe schemas with runtime behavior.

## Key Changes

### Task 1: PhasorPy apparent lifetime outputs
- Added `PHASOR_TO_LIFETIMES` IOPattern to `IOPattern` enum.
- Mapped `PHASOR_TO_LIFETIMES` to `phase_lifetime` and `modulation_lifetime` ports in `DiscoveryEngine`.
- Updated `PhasorPyAdapter` to use the new pattern for `phasor_to_apparent_lifetime` and name outputs accordingly at runtime.
- Added integration regression test in `test_flim_calibration.py`.

### Task 2: skimage regionprops artifact params
- Updated `DiscoveryEngine` to globally filter common artifact parameter names (`label_image`, `intensity_image`, etc.) from `params_schema`.
- Improved `LABELS_TO_TABLE` and `IMAGE_TO_LABELS` port definitions in `DiscoveryEngine` to include `label_image`.
- Added contract test in `test_skimage_adapter.py` to verify omission.

### Task 3: base.io.bioimage.export standardization
- Standardized `base.io.bioimage.export` parameter from `path` to `dest_path` in `tools/base/manifest.yaml`.
- Updated `bioimage_mcp_base/io.py` to honor `dest_path` (with backward compatibility for `path`).
- Updated unit tests in `test_io_functions.py` to use `dest_path` and verify custom destinations work.

## Deviations from Plan
- None - plan executed exactly as written.

## Verification Results
- `ruff check .` passed (remaining errors are pre-existing).
- `pytest` for targeted tests passed:
  - `tests/contract/test_skimage_adapter.py`
  - `tests/unit/api/test_io_functions.py`
  - `tests/integration/test_flim_calibration.py`

## Commits
- 83c9f59: feat(quick-003): fix phasor_to_apparent_lifetime output naming
- e170b81: fix(quick-003): omit regionprops artifact params from schema
- 75d1ab8: feat(quick-003): standardize export to dest_path
- [Final metadata commit will be added next]
