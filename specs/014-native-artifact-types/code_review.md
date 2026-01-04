# Code Review: 014-native-artifact-types

Date: 2026-01-04T16:33:22+01:00

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | FAIL | Core US1 pipeline still breaks when chaining `XarrayAdapterForRegistry` → `SkimageAdapter` due to artifact dict shape mismatch (`path` vs `uri`). Tasks tracking in `specs/014-native-artifact-types/tasks.md` is also out of sync with the repo (some unchecked tasks appear implemented/tests exist). |
| Tests    | FAIL | Selected unit/contract tests: PASS (26/26). Selected integration tests: 2 passed, 1 failed (`tests/integration/test_squeeze_threshold_pipeline.py`). |
| Coverage | LOW | No coverage tooling configured (`pytest-cov` not present). Good coverage around models/metadata basics; gaps remain for OME-Zarr export + ScalarRef end-to-end behavior. |
| Architecture | FAIL | Adapter/tool interfaces use inconsistent artifact reference shapes (`uri` vs `path`). Export responsibilities appear split between core server (`src/bioimage_mcp/artifacts/store.py`) and base tool (`tools/base/bioimage_mcp_base/ops/export.py`), diverging from `specs/014-native-artifact-types/spec.md` isolation expectation. |
| Constitution | FAIL | OME-Zarr materialization paths use `bioio_ome_zarr.writer.OmeZarrWriter` + `write_image()` and unconditionally expand to 5D, conflicting with Constitution III guidance on native dimensions + writer choice. |

## Findings

- **CRITICAL**: Adapter chaining breaks on artifact reference shape.
  - Evidence: `tests/integration/test_squeeze_threshold_pipeline.py` fails because `XarrayAdapterForRegistry._save_output()` returns `{"path": ...}` but `SkimageAdapter._load_image()` requires `artifact["uri"]`.
  - Trace: `src/bioimage_mcp/registry/dynamic/adapters/skimage.py:159` raises `KeyError: 'uri'`.
  - Impact: Violates US1 acceptance (“squeeze → threshold → region analysis”) at the adapter boundary; makes mixed-adapter pipelines brittle.

- **CRITICAL**: Constitution III misalignment in OME-Zarr materialization.
  - Evidence: `tools/base/bioimage_mcp_base/entrypoint.py:351` imports `bioio_ome_zarr.writer.OmeZarrWriter` and calls `write_image(...)` with `dimension_order="TCZYX"`; it also expands data via `_expand_to_5d(...)` before writing.
  - Evidence: `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py:444` follows the same pattern.
  - Impact: Constitution III states tools should preserve native dimensions and use `bioio_ome_zarr.writers.OMEZarrWriter` with explicit `axes_names`/`axes_types` for native-dim OME-Zarr writing.

- **HIGH**: Potential axis-length mismatch when exporting to OME-Zarr.
  - Evidence: `src/bioimage_mcp/artifacts/store.py:604` uses `dims = ref.metadata.get("dims") or ...` but loads `data` via `BioImage(...).data`, which normalizes to 5D in bioio. If `ref.metadata["dims"]` is native (e.g., `['Y','X']`) but `data.ndim` is 5, writer axis metadata may not match `data.shape`.
  - Similar risk: `tools/base/bioimage_mcp_base/ops/export.py:149-161` loads `img.data` then passes `dims` from artifact metadata into `export_ome_zarr(...)`.

- **MEDIUM**: Tasks tracking is inconsistent with implementation.
  - Evidence: `specs/014-native-artifact-types/tasks.md` marks `T028a` and multiple US4 items as incomplete, but code/tests exist (e.g., `src/bioimage_mcp/runs/recorder.py:6` implements `record_artifact_dimensions(..., # T028a)`, and `tests/integration/test_cross_env_dim_preservation.py` exists).
  - Impact: Reviewers/users can’t trust checklist status to reflect actual delivery.

- **MEDIUM**: Performance test does not match stated requirement.
  - Evidence: `tests/contract/test_metadata_performance.py:13` docstring says “under 100ms” but the assertion enforces `< 500ms`.

- **LOW**: Debug prints in `XarrayAdapterForRegistry`.
  - Evidence: `src/bioimage_mcp/registry/dynamic/adapters/xarray.py:71-87` prints DEBUG lines to stderr.
  - Impact: Noisy test output and logs; makes failures harder to diagnose.

- **LOW**: Repo state not clean.
  - Evidence: `git status` shows local modifications/deletions and untracked tests (`AGENTS.md`, `tests/unit/ops/test_export.py`, `tests/contract/test_phasorpy_adapter.py`, plus new untracked files). These may confuse future test runs.

## Remediation / Suggestions

- Fix adapter artifact reference compatibility: ensure both adapters accept and emit a consistent shape (`uri` preferred) OR make `SkimageAdapter._load_image()` accept `path` as a fallback. This should make `tests/integration/test_squeeze_threshold_pipeline.py` pass.
- Align OME-Zarr materialization with Constitution III: replace `bioio_ome_zarr.writer.OmeZarrWriter.write_image(...)` usage with `bioio_ome_zarr.writers.OMEZarrWriter` and preserve native dims (only expand when the manifest’s `dimension_requirements` or the output format actually requires 5D).
- Add explicit tests for OME-Zarr export correctness with native-dim artifacts (e.g., start with a 2D artifact where metadata dims are `['Y','X']`, export to OME-Zarr, and verify axes metadata matches data shape).
- Update `specs/014-native-artifact-types/tasks.md` to reflect actual completion status (mark implemented items complete, and keep only genuinely pending tasks unchecked).
- Remove or gate debug prints in `src/bioimage_mcp/registry/dynamic/adapters/xarray.py`.
- Tighten the metadata performance contract to match the stated requirement (either enforce 100ms consistently, or update the docstring/acceptance criteria).