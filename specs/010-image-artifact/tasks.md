# Tasks: 010-image-artifact (Standardized Image Artifacts with bioio)

**Input**: Design documents from `/specs/010-image-artifact/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Included per constitution requirements (workflow execution, artifact schemas, tool shims).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Core server**: `src/bioimage_mcp/`
- **Tool packs**: `tools/base/`, `tools/cellpose/`
- **Environments**: `envs/`
- **Tests**: `tests/unit/`, `tests/contract/`, `tests/integration/`

---

## Phase 1: Setup (Environment Updates)

**Purpose**: Update all tool environments to include bioio with required plugins

- [ ] T001 [P] Update base environment to include bioio dependencies in envs/bioimage-mcp-base.yaml
- [ ] T002 [P] Update cellpose environment to include bioio dependencies in envs/bioimage-mcp-cellpose.yaml
- [ ] T003 Regenerate lockfiles for all updated environments using conda-lock
- [ ] T004 Verify environment health with python -m bioimage_mcp doctor

---

## Phase 2: Foundational (Schema & Infrastructure)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Schema Updates

- [ ] T005 Create InterchangeFormat enum (OME_TIFF, OME_ZARR) in src/bioimage_mcp/registry/manifest_schema.py
- [ ] T006 Add interchange_format field to FunctionDefinition model in src/bioimage_mcp/registry/manifest_schema.py
- [ ] T007 Add bioio_plugins list field to ToolPackInterchangeConfig in src/bioimage_mcp/registry/manifest_schema.py
- [ ] T008 Update manifest validation logic to handle interchange_format defaults in src/bioimage_mcp/registry/manifest_schema.py

### Contract Tests

- [ ] T009 [P] Write contract test for InterchangeFormat schema in tests/contract/test_interchange_format_schema.py
- [ ] T010 [P] Write contract test for manifest validation with interchange_format in tests/contract/test_manifest_interchange.py

### Manifest Updates

- [ ] T011 [P] Update base manifest with interchange config in tools/base/manifest.yaml
- [ ] T012 [P] Update cellpose manifest with interchange config in tools/cellpose/manifest.yaml

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Proprietary Import (Priority: P1) 🎯 MVP

**Goal**: An agent loads a Zeiss CZI file. The base environment uses BioImage(czi_path) to read it and immediately saves it as a standard OME-TIFF artifact.

**Independent Test**: Load a CZI file via base environment → verify OME-TIFF artifact is created with correct metadata

### Tests for User Story 1

- [ ] T013 [P] [US1] Unit test for BioImage loading in tests/unit/base/test_bioimage_loading.py
- [ ] T014 [P] [US1] Unit test for metadata extraction in tests/unit/api/test_metadata_extraction.py
- [ ] T015 [P] [US1] Integration test for CZI import workflow in tests/integration/test_czi_import_workflow.py

### Implementation for User Story 1

- [ ] T016 [US1] Simplify load_image_fallback to use BioImage directly in tools/base/bioimage_mcp_base/io.py
- [ ] T017 [US1] Update export_ome_tiff helper to use BioImage and OmeTiffWriter in tools/base/bioimage_mcp_base/io.py
- [ ] T018 [US1] Create helper function to extract StandardMetadata from BioImage in src/bioimage_mcp/artifacts/models.py
- [ ] T019 [US1] Update ArtifactRef creation logic to populate metadata (shape, pixel_sizes, channel_names, dtype) in src/bioimage_mcp/api/artifacts.py
- [ ] T020 [US1] Implement ensure_interchange_format() conversion helper in src/bioimage_mcp/api/artifacts.py

**Checkpoint**: User Story 1 complete - CZI import workflow should produce valid OME-TIFF artifacts with metadata

---

## Phase 4: User Story 2 - Cross-Env Analysis (Priority: P2)

**Goal**: The Cellpose environment receives an OME-TIFF artifact reference. It loads the data via BioImage(path).data, receiving a consistent 5D TCZYX array without needing to know about OME-TIFF specifics.

**Independent Test**: Pass OME-TIFF artifact to cellpose.segment → verify consistent 5D array access and successful segmentation

### Tests for User Story 2

- [ ] T021 [P] [US2] Unit test for BioImage 5D normalization in tests/unit/base/test_bioimage_normalization.py
- [ ] T022 [P] [US2] Integration test for cellpose with OME-TIFF input in tests/integration/test_cellpose_bioimage.py

### Implementation for User Story 2

- [ ] T023 [P] [US2] Replace tifffile.imread with BioImage in cellpose tool in tools/cellpose/bioimage_mcp_cellpose/segment.py
- [ ] T024 [US2] Ensure cellpose handles 5D normalization (squeeze/expand dimensions) in tools/cellpose/bioimage_mcp_cellpose/segment.py
- [ ] T025 [US2] Standardize base tools to use BioImage for all input reading in tools/base/bioimage_mcp_base/ops/

**Checkpoint**: User Story 2 complete - Cellpose and base tools consistently use BioImage for 5D TCZYX access

---

## Phase 5: User Story 3 - Large Dataset Handling (Priority: P3)

**Goal**: An environment configured for OME-Zarr handles a multi-terabyte dataset. Because bioio uses dask, the tool can perform chunked processing natively without loading the entire image into RAM.

**Independent Test**: Load large OME-Zarr dataset → verify lazy loading via dask without memory exhaustion

### Tests for User Story 3

- [ ] T026 [P] [US3] Unit test for dask-backed lazy loading in tests/unit/base/test_bioimage_lazy_loading.py
- [ ] T027 [P] [US3] Integration test for chunked processing workflow in tests/integration/test_zarr_chunked_workflow.py

### Implementation for User Story 3

- [ ] T028 [US3] Add OME-Zarr interchange format support to conversion helper in src/bioimage_mcp/api/artifacts.py
- [ ] T029 [US3] Document chunked processing pattern for large datasets in tools/base/bioimage_mcp_base/io.py
- [ ] T030 [US3] Add bioio-zarr plugin to base environment if not present in envs/bioimage-mcp-base.yaml

**Checkpoint**: User Story 3 complete - Large dataset handling via OME-Zarr with lazy loading works

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates and final validation

- [ ] T031 [P] Update cellpose_segmentation.md tutorial in docs/tutorials/cellpose_segmentation.md
- [ ] T032 [P] Update flim_phasor.md tutorial in docs/tutorials/flim_phasor.md
- [ ] T033 [P] Update AGENTS.md with standard BioImage loading pattern in AGENTS.md
- [ ] T034 Create migration guide for tool developers in docs/developer/image_handling.md
- [ ] T035 Verify SC-001: All envs have bioio + bioio-ome-tiff via doctor check
- [ ] T036 Verify SC-002: BioImage(path).data returns consistent 5D TCZYX
- [ ] T037 Verify SC-003: Phasor workflow processes CZI via auto-conversion
- [ ] T038 Verify SC-004: StandardMetadata extraction and preservation
- [ ] T039 Run quickstart.md validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Builds on infrastructure from US1/US2 but is independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- I/O helpers before API updates
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks T001-T002 marked [P] can run in parallel
- Foundational tasks T009-T012 marked [P] can run in parallel
- Once Foundational phase completes, all user stories can start in parallel
- All tests for a user story marked [P] can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch all contract tests together:
Task: "Contract test for InterchangeFormat schema in tests/contract/test_interchange_format_schema.py"
Task: "Contract test for manifest validation in tests/contract/test_manifest_interchange.py"

# Launch all manifest updates together:
Task: "Update base manifest with interchange config in tools/base/manifest.yaml"
Task: "Update cellpose manifest with interchange config in tools/cellpose/manifest.yaml"
```

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for BioImage loading in tests/unit/base/test_bioimage_loading.py"
Task: "Unit test for metadata extraction in tests/unit/api/test_metadata_extraction.py"
Task: "Integration test for CZI import workflow in tests/integration/test_czi_import_workflow.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (environment updates)
2. Complete Phase 2: Foundational (schema updates, manifests)
3. Complete Phase 3: User Story 1 (proprietary import)
4. **STOP and VALIDATE**: Test CZI → OME-TIFF conversion independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test CZI import → Deploy/Demo (MVP!)
3. Add User Story 2 → Test cross-env analysis → Deploy/Demo
4. Add User Story 3 → Test large dataset handling → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Proprietary Import)
   - Developer B: User Story 2 (Cross-Env Analysis)
   - Developer C: User Story 3 (Large Dataset Handling)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Key dependencies: `bioio >= 1.0`, `bioio-ome-tiff`, `bioio-bioformats`
