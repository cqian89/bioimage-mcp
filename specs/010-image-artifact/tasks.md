# Tasks: 010-image-artifact (Standardized Image Artifacts with bioio)

**Input**: Design documents from `specs/010-image-artifact/`
**Prerequisites**: `plan.md` ✓, `spec.md` ✓, `research.md` ✓, `data-model.md` ✓, `contracts/` ✓

**Format**: `[ ] T### [P?] [US?] Description (with file paths)`

- **[P]**: Can run in parallel
- **[US#]**: Maps to a user story in `spec.md`

---

## Phase 1: Setup (Environment & Fixtures) — Tests First

- [ ] T001 [P] Write contract test asserting required `bioio*` deps in `envs/bioimage-mcp-base.yaml` (and optional CZI reader plugin policy) in `tests/contract/test_base_env_bioio_contract.py`
- [ ] T002 [P] Write contract test asserting required `bioio*` deps in `envs/bioimage-mcp-cellpose.yaml` in `tests/contract/test_cellpose_env_bioio_contract.py`
- [ ] T003 [P] Update `envs/bioimage-mcp-base.yaml` to satisfy T001 (add missing `bioio` plugins as required)
- [ ] T004 [P] Update `envs/bioimage-mcp-cellpose.yaml` to satisfy T002 (add `bioio`, `bioio-ome-tiff`)
- [ ] T005 Regenerate lockfiles for updated envs using `conda-lock`
- [ ] T006 Verify environment health with `python -m bioimage_mcp doctor` (SC-001 gate)

---

## Phase 2: Foundational (Manifest / Schema / Contracts)

- [ ] T007 [P] Write contract test enforcing canonical `Port.format` values and manifest validation in `tests/contract/test_manifest_port_format_contract.py`
- [ ] T008 Add `InterchangeFormat` enum + canonicalization/validation for `Port.format` in `src/bioimage_mcp/registry/manifest_schema.py`
- [ ] T009 [P] Update `tools/base/manifest.yaml` to use canonical `Port.format` values (`OME-TIFF`, `OME-Zarr`) where relevant
- [ ] T010 [P] Update `tools/cellpose/manifest.yaml` to use canonical `Port.format` values (`OME-TIFF`) where relevant
- [ ] T011 Add migration notes for manifest/schema semantics in `docs/developer/image_handling.md`

---

## Phase 3: User Story 1 — Proprietary Import (P1) — Tests First

- [ ] T012 [P] [US1] Add the redistributable CZI fixture `datasets/sample_czi/Plate1-Blue-A-02-Scene-1-P2-E1-01.czi` and attribution file `datasets/sample_czi/README.md` (CC BY 4.0)
- [ ] T013 [P] [US1] Unit test: BioImage loads fixture and returns 5D TCZYX in `tests/unit/base/test_bioimage_loading.py`
- [ ] T014 [P] [US1] Unit test: StandardMetadata extraction for pixel sizes/channel names in `tests/unit/api/test_metadata_extraction.py`
- [ ] T015 [P] [US1] Integration test: CZI ingest converts to OME-TIFF artifact in `tests/integration/test_czi_import_workflow.py`
- [ ] T016 [P] [US1] Integration test (SC-004): metadata preserved through a transform + write step in `tests/integration/test_metadata_preservation_roundtrip.py`
- [ ] T017 [P] [US1] Integration test (SC-003): phasor workflow runs from CZI via conversion (extend `tests/integration/test_flim_phasor_e2e.py` or add `tests/integration/test_flim_phasor_czi_e2e.py`)
- [ ] T018 [US1] Update `tools/base/bioimage_mcp_base/io.py`: simplify `load_image_fallback` to use `BioImage` directly
- [ ] T019 [US1] Update `tools/base/bioimage_mcp_base/io.py`: update `export_ome_tiff` helper to use `BioImage` and `OmeTiffWriter`
- [ ] T020 [US1] Add helper to extract `StandardMetadata` from `BioImage` in `src/bioimage_mcp/artifacts/models.py`
- [ ] T021 [US1] Populate `ArtifactRef.metadata` (shape, pixel_sizes, channel_names, dtype) in `src/bioimage_mcp/api/artifacts.py`
- [ ] T022 [US1] Implement `ensure_interchange_format()` orchestrator that invokes base conversion functions (no in-core conversion) in `src/bioimage_mcp/api/artifacts.py`

---

## Phase 4: User Story 2 — Cross-Env Analysis (P2) — Tests First

- [ ] T023 [P] [US2] Unit test: BioImage 5D normalization helpers in `tests/unit/base/test_bioimage_normalization.py`
- [ ] T024 [P] [US2] Integration test: `cellpose.segment` accepts OME-TIFF and runs successfully in `tests/integration/test_cellpose_bioimage.py`
- [ ] T025 [P] [US2] Replace `tifffile.imread` with `BioImage` in `tools/cellpose/bioimage_mcp_cellpose/segment.py`
- [ ] T026 [US2] Ensure cellpose handles 5D normalization (squeeze/expand dims) in `tools/cellpose/bioimage_mcp_cellpose/segment.py`
- [ ] T027 [US2] Standardize base tool ops input reading to `BioImage` in `tools/base/bioimage_mcp_base/ops/`

---

## Phase 5: User Story 3 — Large Dataset Handling (P3) — Tests First

- [ ] T028 [P] [US3] Unit test: dask-backed lazy loading via `BioImage` in `tests/unit/base/test_bioimage_lazy_loading.py`
- [ ] T029 [P] [US3] Integration test: chunked OME-Zarr workflow in `tests/integration/test_zarr_chunked_workflow.py`
- [ ] T030 [US3] Extend `ensure_interchange_format()` to support OME-Zarr targets in `src/bioimage_mcp/api/artifacts.py`

---

## Phase 6: Docs & Final Checks

- [ ] T031 [P] Update `docs/tutorials/cellpose_segmentation.md` to reflect `BioImage` pattern
- [ ] T032 [P] Update `docs/tutorials/flim_phasor.md` to reflect conversion boundary + OME-TIFF requirement
- [ ] T033 [P] Update `AGENTS.md` with standard `BioImage` loading pattern for tool developers
- [ ] T034 Run `pytest tests/contract/` to verify contracts
- [ ] T035 Run `pytest tests/unit/` to verify unit tests
- [ ] T036 Run `pytest tests/integration/ -v` for end-to-end validation
