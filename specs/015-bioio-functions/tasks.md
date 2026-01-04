# Tasks: Bioimage I/O Functions

**Input**: Design documents from `/specs/015-bioio-functions/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/io-functions.yaml ✓

**Tests**: Included per Constitution requirement ("TDD tests required" in plan.md).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project structure and manifest updates for all 6 new functions

- [ ] T001 Update manifest.yaml with all 6 base.io.bioimage.* function definitions in tools/base/manifest.yaml
- [ ] T002 Remove deprecated base.bioio.export function from tools/base/manifest.yaml
- [ ] T003 Create io.py module with function stubs in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T004 Update entrypoint.py routing to dispatch base.io.bioimage.* functions in tools/base/bioimage_mcp_base/entrypoint.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that all I/O functions depend on

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete

- [ ] T005 Implement path validation helper using filesystem.allowed_read/allowed_write config in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T006 Implement structured error response helpers (PATH_NOT_ALLOWED, FILE_NOT_FOUND, etc.) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T007 [P] Create contract test file for I/O function schemas in tests/contract/test_io_functions_schema.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Load and Inspect Image Metadata (Priority: P1) 🎯 MVP

**Goal**: Enable AI agents to load microscopy images and understand their structure before processing

**Independent Test**: Load any supported image file, inspect metadata, verify dimensions/channels/pixel sizes match expected values

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T008 [P] [US1] Contract test for load function schema validation in tests/contract/test_io_functions_schema.py
- [ ] T009 [P] [US1] Contract test for inspect function schema validation in tests/contract/test_io_functions_schema.py
- [ ] T010 [P] [US1] Unit test for load function with valid/invalid paths in tests/unit/api/test_io_functions.py
- [ ] T011 [P] [US1] Unit test for inspect function metadata extraction in tests/unit/api/test_io_functions.py

### Implementation for User Story 1

- [ ] T012 [US1] Implement base.io.bioimage.load function (BioImage instantiation, artifact creation) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T013 [US1] Implement base.io.bioimage.inspect function (lazy metadata extraction via BioImage properties) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T014 [US1] Add path validation checks to load and inspect functions in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T015 [US1] Add error handling for missing files, unsupported formats, access denied in tools/base/bioimage_mcp_base/ops/io.py

**Checkpoint**: User Story 1 should be fully functional - agents can load and inspect images independently

---

## Phase 4: User Story 4 - Export Results to Standard Formats (Priority: P1)

**Goal**: Enable AI agents to export processed images to user-viewable formats (OME-TIFF, PNG, OME-Zarr, CSV)

**Independent Test**: Load an image artifact, export to each format, verify output files are valid and readable

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T016 [P] [US4] Contract test for export function schema validation in tests/contract/test_io_functions_schema.py
- [ ] T017 [P] [US4] Unit test for export to OME-TIFF in tests/unit/api/test_io_functions.py
- [ ] T018 [P] [US4] Unit test for export to PNG (2D images) in tests/unit/api/test_io_functions.py
- [ ] T019 [P] [US4] Unit test for export to OME-Zarr in tests/unit/api/test_io_functions.py
- [ ] T020 [P] [US4] Unit test for export TableRef to CSV in tests/unit/api/test_io_functions.py

### Implementation for User Story 4

- [ ] T021 [US4] Implement base.io.bioimage.export function with format routing in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T022 [US4] Add OME-TIFF export using bioio.writers.OmeTiffWriter in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T023 [US4] Add PNG export using PIL for 2D uint8/uint16 images in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T024 [US4] Add OME-Zarr export using bioio_ome_zarr.writers.OMEZarrWriter in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T025 [US4] Add CSV export for TableRef using pandas/shutil in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T026 [US4] Add write path validation against filesystem.allowed_write in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T027 [US4] Remove deprecated export.py file in tools/base/bioimage_mcp_base/ops/export.py

**Checkpoint**: User Stories 1 AND 4 complete - agents can load → export workflow

---

## Phase 5: User Story 2 - Validate and Check Format Support (Priority: P2)

**Goal**: Enable pre-flight validation of input files and discovery of supported formats

**Independent Test**: Call get_supported_formats to list formats, call validate on valid and corrupted files, verify reports

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T028 [P] [US2] Contract test for get_supported_formats schema validation in tests/contract/test_io_functions_schema.py
- [ ] T029 [P] [US2] Contract test for validate function schema validation in tests/contract/test_io_functions_schema.py
- [ ] T030 [P] [US2] Unit test for get_supported_formats returns known formats in tests/unit/api/test_io_functions.py
- [ ] T031 [P] [US2] Unit test for validate with valid file in tests/unit/api/test_io_functions.py
- [ ] T032 [P] [US2] Unit test for validate with corrupted/invalid file in tests/unit/api/test_io_functions.py

### Implementation for User Story 2

- [ ] T033 [US2] Implement base.io.bioimage.get_supported_formats using bioio plugin introspection in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T034 [US2] Implement base.io.bioimage.validate with multi-level checks (existence, format, metadata, integrity) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T035 [US2] Add ValidationReport response structure with issues array in tools/base/bioimage_mcp_base/ops/io.py

**Checkpoint**: User Stories 1, 2, AND 4 complete - agents can validate → load → export workflow

---

## Phase 6: User Story 3 - Slice Multi-dimensional Images (Priority: P2)

**Goal**: Enable extraction of specific subsets from 5D images (TCZYX) with metadata preservation

**Independent Test**: Load 5D image, slice by C/T/Z dimensions, verify output has reduced dimensions and preserved pixel sizes

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T036 [P] [US3] Contract test for slice function schema validation in tests/contract/test_io_functions_schema.py
- [ ] T037 [P] [US3] Unit test for slice single channel (C index) in tests/unit/api/test_io_functions.py
- [ ] T038 [P] [US3] Unit test for slice timepoint range (T start/stop) in tests/unit/api/test_io_functions.py
- [ ] T039 [P] [US3] Unit test for slice Z-range with step in tests/unit/api/test_io_functions.py
- [ ] T040 [P] [US3] Unit test for slice preserves physical_pixel_sizes metadata in tests/unit/api/test_io_functions.py
- [ ] T041 [P] [US3] Unit test for slice out-of-bounds error in tests/unit/api/test_io_functions.py

### Implementation for User Story 3

- [ ] T042 [US3] Implement base.io.bioimage.slice using xarray .isel() for named dimension slicing in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T043 [US3] Add SliceSpec parameter parsing (integer index vs range object) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T044 [US3] Add physical metadata preservation (copy attrs to output artifact) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T045 [US3] Add bounds checking with informative error messages in tools/base/bioimage_mcp_base/ops/io.py

**Checkpoint**: All 4 user stories complete - full I/O workflow available

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, documentation, and cleanup

- [ ] T046 [P] Integration test for load→inspect→slice→export workflow with OME-TIFF in tests/integration/test_io_workflow.py
- [ ] T047 [P] Integration test for load→slice→export workflow with CZI format in tests/integration/test_io_workflow.py
- [ ] T048 [P] Integration test for load→slice→export workflow with LIF format in tests/integration/test_io_workflow.py
- [ ] T049 [P] Verify all 6 functions discoverable via list_tools and describe_function MCP calls in tests/integration/test_io_workflow.py
- [ ] T050 [P] Update ops/__init__.py to export io module functions in tools/base/bioimage_mcp_base/ops/__init__.py
- [ ] T051 Run quickstart.md workflow validation manually
- [ ] T052 Verify deprecated base.bioio.export is fully removed from codebase

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (P1) and US4 (P1) can proceed in parallel after Foundational
  - US2 (P2) and US3 (P2) can proceed in parallel after Foundational
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 4 (P1)**: Can start after Foundational - May use artifacts from US1 but independently testable
- **User Story 2 (P2)**: Can start after Foundational - Independently testable
- **User Story 3 (P2)**: Can start after Foundational - Requires BioImageRef from load (US1) for testing but function is independent

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Path validation helpers before function implementation
- Core function logic before error handling refinement
- Story complete before moving to next priority

### Parallel Opportunities

- T003, T004 can run in parallel (different files)
- T005, T006, T007 can run in parallel
- All tests within a user story marked [P] can run in parallel
- US1 and US4 (both P1) can be worked on in parallel
- US2 and US3 (both P2) can be worked on in parallel
- All integration tests (T046-T049) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for load function schema validation"
Task: "Contract test for inspect function schema validation"
Task: "Unit test for load function with valid/invalid paths"
Task: "Unit test for inspect function metadata extraction"
```

---

## Parallel Example: User Story 4

```bash
# Launch all tests for User Story 4 together:
Task: "Contract test for export function schema"
Task: "Unit test for export to OME-TIFF"
Task: "Unit test for export to PNG"
Task: "Unit test for export to OME-Zarr"
Task: "Unit test for export TableRef to CSV"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 4 Only)

1. Complete Phase 1: Setup (manifest updates, file creation)
2. Complete Phase 2: Foundational (path validation, error helpers)
3. Complete Phase 3: User Story 1 (load + inspect)
4. Complete Phase 4: User Story 4 (export)
5. **STOP and VALIDATE**: Test load→export workflow independently
6. Can deploy with basic I/O capability

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add US1 (load/inspect) → Test independently (MVP incremental!)
3. Add US4 (export) → Test load→export workflow → Full MVP
4. Add US2 (validate/formats) → Pre-flight validation available
5. Add US3 (slice) → Multi-dimensional workflow complete
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (load/inspect)
   - Developer B: User Story 4 (export)
3. Then:
   - Developer A: User Story 2 (validate/formats)
   - Developer B: User Story 3 (slice)
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All functions share io.py module but are logically independent
