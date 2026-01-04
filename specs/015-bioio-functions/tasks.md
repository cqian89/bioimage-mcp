# Tasks: Bioimage I/O Functions

**Input**: Design documents from `/specs/015-bioio-functions/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/io-functions.yaml ✓

**Tests**: Included per Constitution requirement (TDD: tests written and failing before implementation).

**Organization**: Tasks grouped by user story where possible, with shared infrastructure first. Ordering is intentionally **tests → implementation** to satisfy Constitution TDD requirements.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Contracts, Discovery, and Versioning Gates (Red)

**Purpose**: Establish failing tests for discovery, schemas, docs, and versioning before touching implementation.

- [ ] T007 [P] Create contract test scaffolding + shared expected fn_id list in tests/contract/test_io_functions_schema.py
- [ ] T049 [P] Add integration test verifying all 6 functions discoverable via list_tools and describe_function (and base.bioio.export absent) in tests/integration/test_io_workflow.py
- [ ] T053 [P] Add contract test asserting tools/base/manifest.yaml tool_version is bumped (not 0.1.0) when io functions are added in tests/contract/test_io_functions_schema.py
- [ ] T054 [P] Add contract test asserting schema docs completeness (descriptions + examples where relevant) for all 6 functions in tests/contract/test_io_functions_schema.py

---

## Phase 2: Setup (Green)

**Purpose**: Project structure + manifest/routing updates for all 6 new functions.

- [ ] T001 Update manifest.yaml with all 6 base.io.bioimage.* function definitions in tools/base/manifest.yaml
- [ ] T055 Bump Base tool version to reflect MCP surface change (e.g., tools/base/manifest.yaml tool_version: 0.1.0 -> 0.2.0) and ensure plan justification is satisfied
- [ ] T002 Remove deprecated base.bioio.export function from tools/base/manifest.yaml
- [ ] T003 Create io.py module with function stubs in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T004 Update entrypoint.py routing to dispatch base.io.bioimage.* functions in tools/base/bioimage_mcp_base/entrypoint.py
- [ ] T050 [P] Update ops/__init__.py to export io module functions in tools/base/bioimage_mcp_base/ops/__init__.py

---

## Phase 3: Foundational Helpers (Red → Green)

**Purpose**: Shared utilities that all I/O functions depend on (allowlists, structured errors).

- [ ] T056 [P] Unit test for path validation helper behavior (allowed_read/allowed_write allowlists) in tests/unit/api/test_io_functions.py
- [ ] T057 [P] Unit test for structured error response shapes/codes (PATH_NOT_ALLOWED, FILE_NOT_FOUND, UNSUPPORTED_FORMAT, etc.) in tests/unit/api/test_io_functions.py
- [ ] T005 Implement path validation helper using filesystem.allowed_read/allowed_write config in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T006 Implement structured error response helpers (PATH_NOT_ALLOWED, FILE_NOT_FOUND, etc.) in tools/base/bioimage_mcp_base/ops/io.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 4: User Story 1 - Load and Inspect Image Metadata (Priority: P1) 🎯 MVP

**Goal**: Enable AI agents to load microscopy images and understand their structure before processing.

**Independent Test**: Load any supported image file, inspect metadata, verify dimensions/channels/pixel sizes match expected values.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T008 [P] [US1] Contract test for load function schema validation in tests/contract/test_io_functions_schema.py
- [ ] T009 [P] [US1] Contract test for inspect function schema validation in tests/contract/test_io_functions_schema.py
- [ ] T010 [P] [US1] Unit test for load function with valid/invalid paths in tests/unit/api/test_io_functions.py
- [ ] T011 [P] [US1] Unit test for inspect function metadata extraction (axes, dtype, physical_pixel_sizes) in tests/unit/api/test_io_functions.py
- [ ] T058 [P] [US1] Unit test: inspect accepts BioImageRef input as well as file path in tests/unit/api/test_io_functions.py
- [ ] T059 [P] [US1] Unit test: inspect preserves native axes (does not force TCZYX unless required) in tests/unit/api/test_io_functions.py
- [ ] T060 [P] [US1] Performance proxy test: inspect does not trigger full pixel load/decode (SC-004) in tests/unit/api/test_io_functions.py
- [ ] T061 [P] [US1] Unit test: inspect returns channel_names when available (optional field) in tests/unit/api/test_io_functions.py

### Implementation for User Story 1

- [ ] T012 [US1] Implement base.io.bioimage.load function (BioImage instantiation, artifact creation) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T013 [US1] Implement base.io.bioimage.inspect function (lazy metadata extraction via BioImage properties; preserve native axes) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T014 [US1] Add path validation checks to load and inspect functions in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T015 [US1] Add error handling for missing files, unsupported formats, access denied in tools/base/bioimage_mcp_base/ops/io.py

**Checkpoint**: User Story 1 should be fully functional - agents can load and inspect images independently.

---

## Phase 5: User Story 4 - Export Results to Standard Formats (Priority: P1)

**Goal**: Enable AI agents to export processed images to user-viewable formats (OME-TIFF, PNG, OME-Zarr, CSV).

**Independent Test**: Load an image artifact, export to each format, verify output files are valid and readable.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T016 [P] [US4] Contract test for export function schema validation in tests/contract/test_io_functions_schema.py
- [ ] T017 [P] [US4] Unit test for export to OME-TIFF in tests/unit/api/test_io_functions.py
- [ ] T018 [P] [US4] Unit test for export to PNG (2D images) using imageio/bioio-imageio in tests/unit/api/test_io_functions.py
- [ ] T019 [P] [US4] Unit test for export to OME-Zarr in tests/unit/api/test_io_functions.py
- [ ] T020 [P] [US4] Unit test for export TableRef to CSV (use stdlib csv; no pandas) in tests/unit/api/test_io_functions.py
- [ ] T062 [P] [US4] Unit test: export infers output format when format is omitted (spec US4 acceptance) in tests/unit/api/test_io_functions.py
- [ ] T063 [P] [US4] Unit test: OME-Zarr export does not require full pixel load (proxy for chunked/lazy behavior) in tests/unit/api/test_io_functions.py

### Implementation for User Story 4

- [ ] T021 [US4] Implement base.io.bioimage.export function with format routing + format inference when unspecified in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T022 [US4] Add OME-TIFF export using bioio.writers.OmeTiffWriter in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T023 [US4] Add PNG export using imageio (via bioio-imageio plugin) for 2D uint8/uint16 images in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T024 [US4] Add OME-Zarr export using bioio_ome_zarr.writers.OMEZarrWriter (explicit axes_names/axes_types) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T025 [US4] Add CSV export for TableRef using Python stdlib (csv/shutil) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T026 [US4] Add write path validation against filesystem.allowed_write in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T027 [US4] Remove deprecated export.py file in tools/base/bioimage_mcp_base/ops/export.py

**Checkpoint**: User Stories 1 AND 4 complete - agents can load → export workflow.

---

## Phase 6: User Story 2 - Validate and Check Format Support (Priority: P2)

**Goal**: Enable pre-flight validation of input files and discovery of supported formats.

**Independent Test**: Call get_supported_formats to list formats, call validate on valid and corrupted files, verify reports.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T028 [P] [US2] Contract test for get_supported_formats schema validation in tests/contract/test_io_functions_schema.py
- [ ] T029 [P] [US2] Contract test for validate function schema validation in tests/contract/test_io_functions_schema.py
- [ ] T030 [P] [US2] Unit test for get_supported_formats returns known formats in tests/unit/api/test_io_functions.py
- [ ] T031 [P] [US2] Unit test for validate with valid file (metadata-only by default) in tests/unit/api/test_io_functions.py
- [ ] T032 [P] [US2] Unit test for validate with corrupted/invalid file in tests/unit/api/test_io_functions.py
- [ ] T064 [P] [US2] Unit test: validate default does not trigger full pixel load; optional deep mode performs additional checks (if implemented) in tests/unit/api/test_io_functions.py

### Implementation for User Story 2

- [ ] T033 [US2] Implement base.io.bioimage.get_supported_formats using bioio plugin introspection in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T034 [US2] Implement base.io.bioimage.validate with explicit validation tiers (default metadata-only; optional deep checks behind parameter) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T035 [US2] Add ValidationReport response structure with issues array in tools/base/bioimage_mcp_base/ops/io.py

**Checkpoint**: User Stories 1, 2, AND 4 complete - agents can validate → load → export workflow.

---

## Phase 7: User Story 3 - Slice Multi-dimensional Images (Priority: P2)

**Goal**: Enable extraction of specific subsets from multi-dimensional images with metadata preservation.

**Independent Test**: Load 5D image, slice by C/T/Z dimensions, verify output has reduced dimensions and preserved pixel sizes.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T036 [P] [US3] Contract test for slice function schema validation in tests/contract/test_io_functions_schema.py
- [ ] T037 [P] [US3] Unit test for slice single channel (C index) in tests/unit/api/test_io_functions.py
- [ ] T038 [P] [US3] Unit test for slice timepoint range (T start/stop) in tests/unit/api/test_io_functions.py
- [ ] T039 [P] [US3] Unit test for slice Z-range with step in tests/unit/api/test_io_functions.py
- [ ] T040 [P] [US3] Unit test for slice preserves physical_pixel_sizes metadata in tests/unit/api/test_io_functions.py
- [ ] T041 [P] [US3] Unit test for slice out-of-bounds error in tests/unit/api/test_io_functions.py
- [ ] T065 [P] [US3] Unit test: slice preserves native axes names/order and does not pad to 5D unless required in tests/unit/api/test_io_functions.py

### Implementation for User Story 3

- [ ] T042 [US3] Implement base.io.bioimage.slice using xarray .isel() for named dimension slicing in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T043 [US3] Add SliceSpec parameter parsing (integer index vs range object) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T044 [US3] Add physical metadata preservation (copy attrs to output artifact) in tools/base/bioimage_mcp_base/ops/io.py
- [ ] T045 [US3] Add bounds checking with informative error messages in tools/base/bioimage_mcp_base/ops/io.py

**Checkpoint**: All 4 user stories complete - full I/O workflow available.

---

## Phase 8: Cross-Cutting Concerns (Integration, Provenance, Regression)

**Purpose**: Validate end-to-end workflows, reproducibility/provenance, and regression checks.

- [ ] T046 [P] Integration test for load→inspect→slice→export workflow with OME-TIFF in tests/integration/test_io_workflow.py
- [ ] T047 [P] Integration test for SC-002 workflow using CZI: load → inspect → slice one Z-plane → export PNG in tests/integration/test_io_workflow.py
- [ ] T048 [P] Integration test for load→slice→export workflow with LIF format in tests/integration/test_io_workflow.py
- [ ] T066 [P] Integration test verifying provenance recording includes input reference/path, parameters, and output reference for I/O calls in tests/integration/test_io_workflow.py
- [ ] T051 [P] Doc smoke test: quickstart.md examples reference current fn_ids/parameters and remain consistent with schemas (SC-005 support) in tests/contract/test_io_functions_schema.py
- [ ] T052 [P] Regression test ensuring deprecated base.bioio.export is absent from manifest + discovery results in tests/contract/test_io_functions_schema.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Contracts/Discovery)**: No dependencies - start immediately
- **Phase 2 (Setup)**: Implement only after Phase 1 tests exist/fail
- **Phase 3 (Foundational)**: Depends on Setup completion
- **User Stories (Phases 4-7)**: Depend on Foundational completion
- **Phase 8 (Cross-cutting)**: Depends on all user stories being complete

### Parallel Opportunities

- Phase 1 tasks marked [P] can run in parallel
- Within each user story, tests marked [P] can run in parallel
- Integration tests (Phase 8) can run in parallel

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing (TDD)
