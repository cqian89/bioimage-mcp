# Tasks: FLIM Phasor Analysis Gap Fix

**Feature**: FLIM Phasor Analysis Gap Fix (003-base-tool-schema)
**Status**: Pending
**Derived From**: `specs/003-base-tool-schema/plan.md` and `spec.md`

## Phase 1: Setup
*Goal: Initialize project structure and dependencies.*

- [ ] T001 Create `tools/base/bioimage_mcp_base/transforms.py` (empty/scaffold) for phasor logic
- [ ] T002 Create `tools/base/bioimage_mcp_base/preprocess.py` (empty/scaffold) for denoising logic if it doesn't exist, or verify it exists
- [ ] T003 Update `tools/base/bioimage_mcp_base/descriptions.py` to include parameter descriptions for `phasor_from_flim` and `denoise_image`

## Phase 2: Foundational
*Goal: Define tool interfaces and prepare the environment.*

- [ ] T004 Update `tools/base/manifest.yaml` to include tool definitions for `base.phasor_from_flim` and `base.denoise_image`

## Phase 3: User Story 1 - Compute phasor maps from FLIM data (P1)
*Goal: Enable conversion of FLIM data to phasor coordinates.*
*Independent Test*: `tests/unit/base/test_phasor.py` passing and producing valid OME-TIFF outputs from test data.

- [ ] T005 [US1] Create `tests/unit/base/test_phasor.py` with test cases for FR-001 (transform), FR-006 (validation), FR-008 (timing), FR-009 (multi-channel)
- [ ] T006 [US1] Implement `phasor_from_flim` logic in `tools/base/bioimage_mcp_base/transforms.py` using `phasorpy` and `bioio`
- [ ] T007 [US1] Update `tools/base/bioimage_mcp_base/entrypoint.py` to support multi-output tools and register `base.phasor_from_flim`
- [ ] T008 [US1] Verify `base.phasor_from_flim` with unit tests

## Phase 4: User Story 2 - Reduce noise in phasor outputs (P2)
*Goal: Provide optional denoising for phasor maps.*
*Independent Test*: `tests/unit/base/test_denoise.py` passing and verifying noise reduction on test images.

- [ ] T009 [US2] Create `tests/unit/base/test_denoise.py` with test cases for FR-005 (denoising options and defaults)
- [ ] T010 [US2] Implement `denoise_image` logic in `tools/base/bioimage_mcp_base/preprocess.py` using `scikit-image`
- [ ] T011 [US2] Register `base.denoise_image` in `tools/base/bioimage_mcp_base/entrypoint.py`
- [ ] T012 [US2] Verify `base.denoise_image` with unit tests

## Phase 5: User Story 3 - Validate an end-to-end FLIM workflow (P3)
*Goal: Ensure the full workflow (Phasor -> Intensity -> Segmentation) works as expected.*
*Independent Test*: `tests/integration/test_flim_phasor_e2e.py` completes successfully.

- [ ] T013 [US3] Create `tests/integration/test_flim_phasor_e2e.py` implementing the workflow validation logic (FR-007)
- [ ] T014 [US3] Implement logic to generate or download a small reference FLIM dataset for testing if one is not available
- [ ] T015 [US3] Run the E2E test and fix any integration issues

## Phase 6: Polish
*Goal: Final verification and cleanup.*

- [ ] T016 Run full test suite (`pytest`) to ensure no regressions
- [ ] T017 Verify error messages for invalid inputs (FR-006) are clear and actionable

## Dependencies

- **US1** (Phasor Transform) is the core capability.
- **US2** (Denoising) depends on `tools/base/bioimage_mcp_base/preprocess.py` but can be developed in parallel with US1 logic if the file structure is agreed upon.
- **US3** (E2E) depends on US1 and US2 (optional but recommended for full workflow) and the availability of segmentation tools.

## Implementation Strategy

1.  **MVP (US1)**: Focus on getting `phasor_from_flim` working with correct OME-TIFF I/O and `phasorpy` integration. This delivers the primary missing value.
2.  **Enhancement (US2)**: Add the `denoise_image` tool. This is low risk as it leverages `scikit-image`.
3.  **Integration (US3)**: Wire it all together in an E2E test. This is crucial for regression prevention.
