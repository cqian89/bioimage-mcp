# Tasks: Native Artifact Types and Dimension Preservation

**Input**: Design documents from `/specs/014-native-artifact-types/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: REQUIRED (TDD approach requested) - Write tests first, ensure they FAIL before implementation.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies and environment verification

- [X] T001 Verify bioio-ome-zarr availability in base environment (already in envs/bioimage-mcp-base.yaml)
- [X] T001a [P] Review img.reader.data vs img.data patterns in current codebase
- [X] T002 [P] Review existing artifact model structure in src/bioimage_mcp/artifacts/models.py
- [X] T003 [P] Review existing metadata extraction in src/bioimage_mcp/artifacts/metadata.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests First (TDD)

- [X] T004 [P] Contract test for ArtifactRef with native dimension fields (shape, ndim, dims, dtype) in tests/contract/test_artifact_metadata_contract.py
- [X] T005 [P] Contract test for ScalarRef artifact type and JSON schema compliance in tests/contract/test_scalar_ref_contract.py
- [X] T006 [P] Contract test for TableRef with column metadata in tests/contract/test_table_ref_contract.py
- [X] T007 [P] Unit test for dimension metadata validation (shape/ndim/dims consistency) in tests/unit/artifacts/test_dimension_validation.py
- [X] T007a [P] Unit test for load_native() helper function in tests/unit/base/test_native_loading.py

### Implementation (After Tests Fail)

- [X] T008 Add `ndim`, `dims`, `physical_pixel_sizes` fields to ArtifactRef model in src/bioimage_mcp/artifacts/models.py
- [X] T009 Add ScalarRef class with JSON format and ScalarMetadata in src/bioimage_mcp/artifacts/models.py
- [X] T010 Add ColumnMetadata and TableMetadata classes in src/bioimage_mcp/artifacts/models.py
- [X] T011 Add model_validator for dimension metadata consistency in src/bioimage_mcp/artifacts/models.py
- [X] T012 Update ARTIFACT_TYPES registry to include ScalarRef in src/bioimage_mcp/artifacts/models.py
- [X] T012a Create load_native() helper in tools/base/bioimage_mcp_base/native_io.py

**Checkpoint**: Foundation ready - core artifact models support native dimensions. Tests should now PASS.

---

## Phase 3: User Story 1 - Dimension-Reducing Pipeline Execution (Priority: P1) 🎯 MVP

**Goal**: Dimension-reducing operations produce artifacts with correct native dimensions. Pipeline squeeze → threshold → regionprops works.

**Independent Test**: Run squeeze on 5D image, verify output artifact reports 2D dimensions.

### Tests for User Story 1 (Write FIRST - must FAIL)

- [X] T013 [P] [US1] Unit test: XarrayAdapter preserves native dimensions (no 5D expansion) in tests/unit/adapters/test_xarray_native_dims.py
- [X] T014 [P] [US1] Unit test: squeeze operation produces correct ndim/dims metadata in tests/unit/adapters/test_xarray_native_dims.py
- [X] T015 [P] [US1] Unit test: SkimageAdapter handles native dimension output in tests/unit/adapters/test_skimage_native_dims.py
- [X] T016 [P] [US1] Integration test: squeeze → threshold → regionprops pipeline in tests/integration/test_squeeze_threshold_pipeline.py
- [X] T016a [P] [US1] Unit test: squeeze on non-singleton dimension produces clear error message in tests/unit/ops/test_dimension_errors.py

### Implementation for User Story 1 (After Tests Fail)

- [X] T017 [US1] Switch XarrayAdapter from img.data to img.reader.data for native dimensions in src/bioimage_mcp/registry/dynamic/adapters/xarray.py
- [X] T018 [US1] Update XarrayAdapter._save_output to use native dimensions and populate ndim/dims metadata in src/bioimage_mcp/registry/dynamic/adapters/xarray.py
- [X] T019 [US1] Update save_native_ome_zarr to use OMEZarrWriter with axes_names/axes_types (NOT ome-zarr-py) in src/bioimage_mcp/registry/dynamic/adapters/xarray.py
- [X] T020 [US1] Switch SkimageAdapter from img.data to img.reader.data in src/bioimage_mcp/registry/dynamic/adapters/skimage.py
- [X] T021 [US1] Update metadata extraction to populate ndim/dims from array in src/bioimage_mcp/artifacts/metadata.py

**Checkpoint**: User Story 1 complete. Dimension-reducing pipelines work. Tests should now PASS.

---

## Phase 4: User Story 2 - Rich Artifact Metadata Inspection (Priority: P2)

**Goal**: Agents can inspect artifact metadata (shape, ndim, dtype, dims) without loading data.

**Independent Test**: Create artifact and call get_artifact, verify dimension metadata present in response.

### Tests for User Story 2 (Write FIRST - must FAIL)

- [X] T022 [P] [US2] Unit test: metadata extraction returns ndim, dims, shape, dtype, physical_pixel_sizes in tests/unit/artifacts/test_native_metadata.py
- [X] T023 [P] [US2] Unit test: table metadata extraction returns columns with types in tests/unit/artifacts/test_native_metadata.py
- [X] T024 [P] [US2] Contract test: get_artifact response includes dimension metadata fields in tests/contract/test_get_artifact_dims.py
- [ ] T024a [P] [US2] Performance test: metadata inspection completes in under 100ms without data loading in tests/contract/test_metadata_performance.py

### Implementation for User Story 2 (After Tests Fail)

- [X] T025 [US2] Update extract_image_metadata to return ndim, dims from BioImage in src/bioimage_mcp/artifacts/metadata.py
- [X] T026 [US2] Add extract_table_metadata function for column names/types in src/bioimage_mcp/artifacts/metadata.py
- [X] T027 [US2] Add get_ndim fallback helper for legacy artifacts (infer from shape/axes) in src/bioimage_mcp/artifacts/metadata.py
- [X] T028 [US2] Update artifact store import to populate full dimension metadata in src/bioimage_mcp/artifacts/store.py
- [ ] T028a [US2] Add dimension metadata to workflow provenance recording in src/bioimage_mcp/runs/recorder.py

**Checkpoint**: User Story 2 complete. Agents can inspect dimensions without data loading. Tests should now PASS.

---

## Phase 5: User Story 3 - Flexible Export Format Selection (Priority: P3)

**Goal**: Users can export artifacts to PNG, OME-TIFF, OME-Zarr, CSV, NPY with intelligent format inference.

**Independent Test**: Export 2D image to PNG and table to CSV, verify valid output files.

### Tests for User Story 3 (Write FIRST - must FAIL)

- [X] T029 [P] [US3] Unit test: infer_export_format returns correct format for 2D uint8 (PNG) in tests/unit/ops/test_export_format_inference.py
- [X] T030 [P] [US3] Unit test: infer_export_format returns OME-TIFF for 3D+ with metadata in tests/unit/ops/test_export_format_inference.py
- [X] T031 [P] [US3] Unit test: infer_export_format returns OME-Zarr for large files in tests/unit/ops/test_export_format_inference.py
- [X] T032 [P] [US3] Unit test: export function respects explicit format parameter in tests/unit/ops/test_export.py
- [X] T033 [P] [US3] Integration test: export 2D to PNG, 5D to OME-TIFF, table to CSV in tests/integration/test_multi_format_export.py

### Implementation for User Story 3 (After Tests Fail)

- [X] T034 [US3] Create infer_export_format function in tools/base/bioimage_mcp_base/ops/export.py
- [X] T035 [US3] Create export function with format parameter in tools/base/bioimage_mcp_base/ops/export.py
- [X] T036 [US3] Implement PNG export (2D uint8/uint16) in tools/base/bioimage_mcp_base/ops/export.py
- [X] T037 [US3] Implement OME-TIFF export (5D expand at export boundary) in tools/base/bioimage_mcp_base/ops/export.py
- [X] T038 [US3] Implement OME-Zarr export using bioio_ome_zarr.writers.OMEZarrWriter with axes_names/axes_types parameters in tools/base/bioimage_mcp_base/ops/export.py
- [X] T039 [US3] Implement CSV export for TableRef in tools/base/bioimage_mcp_base/ops/export.py
- [X] T040 [US3] Add export function to base manifest in tools/base/manifest.yaml

**Checkpoint**: User Story 3 complete. Multi-format export works. Tests should now PASS.

---

## Phase 6: User Story 4 - Cross-Environment Tool Chaining (Priority: P4)

**Goal**: Artifacts transfer between environments (base, cellpose) without losing dimensionality or metadata.

**Independent Test**: Create 3D artifact in base env, pass to cellpose env, verify same shape/dims/metadata.

### Tests for User Story 4 (Write FIRST - must FAIL)

- [ ] T041 [P] [US4] Integration test: artifact dimension preservation across base→cellpose env boundary in tests/integration/test_cross_env_dim_preservation.py
- [ ] T042 [P] [US4] Unit test: memory artifact ref carries correct dimension metadata in tests/unit/artifacts/test_memory_artifact_dims.py
- [ ] T043 [P] [US4] Contract test: dimension_requirements in manifest functions correctly parsed in tests/contract/test_dimension_requirements.py

### Implementation for User Story 4 (After Tests Fail)

- [ ] T044 [US4] Add create_memory_artifact_ref helper with dimension metadata in src/bioimage_mcp/artifacts/store.py
- [ ] T045 [US4] Implement should_expand_to_5d helper for adapter expansion decisions in src/bioimage_mcp/registry/dynamic/adapters/xarray.py
- [ ] T045a [US4] Apply expand_if_required helper to SkimageAdapter in src/bioimage_mcp/registry/dynamic/adapters/skimage.py
- [ ] T046 [US4] Add dimension_requirements to cellpose functions in tools/cellpose/manifest.yaml
- [ ] T047 [US4] Add dimension_requirements to base functions in tools/base/manifest.yaml
- [ ] T048 [US4] Update adapter input loading to respect dimension_requirements from manifest in src/bioimage_mcp/registry/dynamic/adapters/xarray.py

**Checkpoint**: User Story 4 complete. Cross-environment pipelines preserve dimensions. Tests should now PASS.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and cleanup

- [ ] T049 [P] Update docs/reference/artifacts.md with native dimension documentation
- [ ] T050 [P] Update docs/developer/image_handling.md with dimension preservation patterns
- [ ] T051 [P] Validate quickstart.md examples against implementation in specs/014-native-artifact-types/quickstart.md
- [ ] T052 [P] Add contract test validating artifact-metadata-schema.json compliance in tests/contract/test_artifact_metadata_contract.py
- [ ] T053 Run full test suite and verify all tests pass
- [ ] T054 Verify bioio-ome-zarr is sufficient (no ome-zarr-py needed)
- [ ] T054a Update AGENTS.md Standard BioImage Loading Pattern section for native loading
- [ ] T055 Review backward compatibility: legacy artifacts without ndim/dims handled correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational; can run in parallel with US1
- **User Story 3 (Phase 5)**: Depends on US1 (needs native dimension artifacts)
- **User Story 4 (Phase 6)**: Depends on US1, US2 (needs dimension metadata inspection)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

| Story | Dependencies | Can Start After |
|-------|--------------|-----------------|
| US1 (P1) | Foundational only | Phase 2 complete |
| US2 (P2) | Foundational only | Phase 2 complete (parallel with US1) |
| US3 (P3) | US1 (native dims exist) | Phase 3 complete |
| US4 (P4) | US1 + US2 | Phase 3 + Phase 4 complete |

### TDD Flow Within Each User Story

```
1. Write test → 2. Run test → 3. Verify FAIL → 4. Implement → 5. Run test → 6. Verify PASS
```

### Parallel Opportunities

**Phase 2 (Foundational):**
```bash
# All contract tests can run in parallel:
Task T004: Contract test for ArtifactRef with native dimension fields
Task T005: Contract test for ScalarRef artifact type
Task T006: Contract test for TableRef with column metadata
Task T007: Unit test for dimension metadata validation
```

**Phase 3 (US1) Tests:**
```bash
# All US1 tests can run in parallel:
Task T013: Unit test XarrayAdapter preserves native dimensions
Task T014: Unit test squeeze operation produces correct ndim/dims
Task T015: Unit test SkimageAdapter handles native dimensions
Task T016: Integration test squeeze→threshold→regionprops pipeline
```

**Cross-Story Parallelism:**
```bash
# After Foundational complete, US1 and US2 tests can start in parallel:
Team A: US1 tests (T013-T016) → US1 implementation (T017-T021)
Team B: US2 tests (T022-T024) → US2 implementation (T025-T028)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational - Tests FIRST (T004-T007), then implementation (T008-T012)
3. Complete Phase 3: User Story 1 - Tests FIRST (T013-T016), then implementation (T017-T021)
4. **STOP and VALIDATE**: Verify squeeze → threshold → regionprops pipeline works
5. Deploy/demo if ready

### Incremental Delivery

| Increment | Stories Included | Value Delivered |
|-----------|-----------------|-----------------|
| MVP | US1 | Dimension-reducing pipelines work |
| +1 | US1 + US2 | Agents can inspect dimensions |
| +2 | US1 + US2 + US3 | Multi-format export |
| Full | All stories | Cross-environment preservation |

### Parallel Team Strategy

```
Developer A: Foundational → US1 → US3
Developer B: Foundational → US2 → US4
Both: Polish phase together
```

---

## Key Files Modified

| File | Phase | Changes |
|------|-------|---------|
| src/bioimage_mcp/artifacts/models.py | Phase 2 | Add ndim, dims, ScalarRef, TableMetadata |
| src/bioimage_mcp/artifacts/metadata.py | Phase 3-4 | Native dimension extraction |
| src/bioimage_mcp/artifacts/store.py | Phase 4, 6 | OME-Zarr import, memory artifact metadata |
| src/bioimage_mcp/registry/dynamic/adapters/xarray.py | Phase 3, 6 | Remove 5D forcing, native dims |
| src/bioimage_mcp/registry/dynamic/adapters/skimage.py | Phase 3 | Native dimension handling |
| tools/base/bioimage_mcp_base/native_io.py | Phase 2 | NEW: load_native() and expand_if_required() helpers |
| tools/base/bioimage_mcp_base/ops/export.py | Phase 5 | NEW: Multi-format export |
| tools/base/manifest.yaml | Phase 5-6 | Add export function, dimension_requirements |
| tools/cellpose/manifest.yaml | Phase 6 | Add dimension_requirements |

---

## Notes

- **[P]** tasks = different files, no dependencies - can parallelize
- **[Story]** label maps task to specific user story
- **TDD**: Tests MUST be written and FAIL before implementation begins
- Commit after each test group or implementation block
- Stop at any checkpoint to validate story independently
- **Native-First Loading**: All image loading should use `img.reader.data` (native dimensions) unless the tool manifest explicitly requires 5D via `dimension_requirements.min_ndim: 5`
- **Constitution Compliance**: Use `bioio_ome_zarr.writers.OMEZarrWriter` for OME-Zarr output, NOT `ome_zarr.writer.write_image`
