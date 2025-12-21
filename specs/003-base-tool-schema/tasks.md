# Tasks: FLIM Phasor Analysis Gap Fix

**Feature**: FLIM Phasor Analysis Gap Fix (003-base-tool-schema)
**Status**: Pending
**Derived From**: `specs/003-base-tool-schema/plan.md` and `spec.md`

**Local Test Dataset (no network fetch)**: Use a file from `datasets/FLUTE_FLIM_data_tif/` (preferred default: `datasets/FLUTE_FLIM_data_tif/Fluorescein_Embryo.tif`). If the dataset is unavailable in the current environment, tests MUST skip with an explicit, actionable reason.

## Phase 0: Decisions / Verification
*Goal: Remove ambiguity before writing implementation code.*

- [X] T001 Verify `phasorpy` can compute G/S phasor maps for OME-TIFF FLIM inputs with explicit control over the time/bin axis (and supports the required bin-to-phase mapping behavior). If not viable, select an alternative (and update plan/spec accordingly).
- [X] T002 Define and document the stable tool response shapes for multi-output tools (artifact refs + warnings) for `base.phasor_from_flim` and `base.denoise_image` so tests can target a deterministic contract.

## Phase 1: Tests First (Red)
*Goal: Write failing tests that capture the desired behavior BEFORE implementation work.*

- [X] T003 [US1] Create failing `tests/unit/base/test_phasor.py` covering:
  - FR-001/FR-003: `base.phasor_from_flim` returns artifact references only
  - FR-004: returns **three outputs** (G, S, and derived integrated intensity) as artifacts
  - FR-002: time/bin axis inference when unambiguous AND `time_axis` override when specified
  - FR-008: timing metadata preferred, otherwise uniform (0..2π) mapping, and mode is surfaced/recorded
  - FR-006: invalid/unsupported inputs fail fast with actionable errors; oversized inputs (>4GB) surface a warning but proceed
  - FR-009: multi-channel inputs preserve channel dimension in outputs
- [X] T004 [US1] Create failing `tests/unit/base/test_phasor_provenance.py` asserting the workflow/run record for `base.phasor_from_flim` captures (at minimum) inputs, resolved params (including `time_axis` + mapping mode), output artifact refs, and tool-pack version info.
- [X] T005 [US1] Create failing `tests/unit/base/test_phasor_logging.py` (or extend provenance test) asserting runs persist structured logs as artifacts (e.g., `LogRef`) and link them from the run record.
- [X] T006 [US2] Create failing `tests/unit/base/test_denoise.py` covering FR-005:
  - default filter type (Median)
  - supported filters (Mean, Gaussian, Median, Bilateral)
  - structured param schema validation (e.g., `sigma` only for Gaussian, `radius` only for Mean/Median, `sigma_color`/`sigma_spatial` only for Bilateral)
  - multi-channel behavior: per-channel 2D filtering (no cross-channel filtering)
- [X] T007 [US3] Create failing `tests/integration/test_flim_phasor_e2e.py` that:
  - loads a FLIM dataset from `datasets/FLUTE_FLIM_data_tif/`
  - runs `base.phasor_from_flim` and verifies G/S/intensity artifacts are readable
  - runs the existing segmentation capability in its isolated env using artifact references only
  - verifies the segmentation mask artifact is produced and readable
  - skips with explicit reasons if prerequisites (dataset or segmentation env) are unavailable
  - if the chosen dataset is multi-channel, restrict segmentation input to a single channel (e.g., channel 0) while still validating that the derived intensity artifact preserves the channel dimension.

## Phase 2: Tool Surface (Green)
*Goal: Implement the stable public interface so tests can execute through real tool registration.*

- [X] T008 Update `tools/base/manifest.yaml` to define:
  - `base.phasor_from_flim` with params including `time_axis` (override) and documented outputs (G/S/intensity)
  - `base.denoise_image` with the structured filter schema
- [X] T009 Update `tools/base/bioimage_mcp_base/descriptions.py` to match the manifest schemas and clearly document parameter meanings, defaults, validation rules, and error behaviors.
- [X] T010 Update `tools/base/bioimage_mcp_base/entrypoint.py` to register `base.phasor_from_flim` and `base.denoise_image`, and to support deterministic multi-output responses per T002.

## Phase 3: User Story 1 - Compute phasor maps from FLIM data (P1)
*Goal: Enable conversion of FLIM data to phasor coordinates.*

- [X] T011 [US1] Implement `base.phasor_from_flim` in `tools/base/bioimage_mcp_base/transforms.py`:
  - read OME-TIFF artifact input
  - infer or apply `time_axis`
  - compute G/S phasor maps
  - compute integrated intensity (sum over time/bins) preserving channel dimension
  - fail fast on unsupported formats (e.g., OME-Zarr) with actionable guidance
  - surface warnings for oversized inputs (>4GB) without failing
  - record provenance (inputs, resolved params, mapping mode, versions, outputs)
  - persist structured logs as artifacts
- [X] T012 [US1] Make `tests/unit/base/test_phasor.py` pass.
- [X] T013 [US1] Make `tests/unit/base/test_phasor_provenance.py` and `tests/unit/base/test_phasor_logging.py` pass.

## Phase 4: User Story 2 - Reduce noise in phasor outputs (P2)
*Goal: Provide optional denoising for phasor maps.*

- [X] T014 [US2] Implement `base.denoise_image` in `tools/base/bioimage_mcp_base/preprocess.py` using `scikit-image`, including schema validation and per-channel 2D filtering.
- [X] T015 [US2] Make `tests/unit/base/test_denoise.py` pass.

## Phase 5: User Story 3 - Validate an end-to-end FLIM workflow (P3)
*Goal: Ensure the full workflow (Phasor -> Intensity -> Segmentation) works as expected.*

- [X] T016 [US3] Make `tests/integration/test_flim_phasor_e2e.py` pass (or skip with explicit, actionable reasons when prerequisites are unavailable).

## Phase 6: Quality Gates
*Goal: Final verification and cleanup.*

- [X] T017 Verify that error messages and warnings required by FR-006 are clear and actionable (preferably asserted in tests).
- [X] T018 Run full test suite (`pytest`) to ensure no regressions.
