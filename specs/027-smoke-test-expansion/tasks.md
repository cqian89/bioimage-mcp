# Tasks: Smoke Test Expansion (027)

**Input**: Design documents from `/specs/027-smoke-test-expansion/`
**Prerequisites**: plan.md (required), spec.md (required)
**Tests**: Smoke tests are the primary deliverable; each task includes verification via the new test suite.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

Note: Task IDs are intentionally non-contiguous due to iterative drafting; do not renumber IDs once implementation starts.

---

## Phase 0: Prerequisites (Blocking)

**Purpose**: Fix known issues that would cause equivalence tests to fail or produce misleading results.

**⚠️ CRITICAL**: These tasks MUST be completed before any smoke test work begins.

**Reference**: See `phase0-prerequisites.md` for detailed implementation guidance.

- [x] T000a Add/adjust a failing regression test in `tests/contract/test_scipy_adapter.py` or `tests/unit/adapters/test_scipy_ndimage_objectref.py` that demonstrates current SciPy adapter image output is not BioImage-readable or violates the expected OME-TIFF conventions, then migrate `ScipyNdimageAdapter._save_image()` in `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py` to use `bioio.writers.OmeTiffWriter` following the pattern in `src/bioimage_mcp/registry/dynamic/adapters/skimage.py` (no direct tifffile write fallback). Ensure: (1) extension `.ome.tiff`, (2) explicit axes metadata, (3) deterministic dtype handling for int64/uint64 (cast with clear rules or raise actionable error). Verify with `pytest tests/contract/test_scipy_adapter.py tests/unit/adapters/test_scipy_ndimage_objectref.py -v`
- [x] T000b Write a failing repository-policy test in `tests/unit/test_dataset_lfs_policy.py` asserting: (1) `.gitattributes` tracks `datasets/**`, (2) each `datasets/*/` folder contains a provenance README, and (3) LFS pointer detection correctly identifies pointer files; then update `.gitattributes`, dataset READMEs, and (if needed) `specs/027-smoke-test-expansion/phase0-prerequisites.md` to make the test pass

**Checkpoint**: Prerequisites complete - I/O consistency ensured and datasets verified.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Write a failing structural test in `tests/smoke/test_smoke_structure.py` asserting required directories exist (`tests/smoke/reference_scripts/`, `tests/smoke/utils/`), then create them
- [x] T002 Write failing tests for LFS detection + skip messaging in `tests/smoke/test_lfs_utils.py`, then implement LFS pointer detection and skip logic in `tests/smoke/utils/lfs_utils.py`; also register new dataset markers in `pytest.ini` (`uses_minimal_data`, `requires_lfs_dataset`) for later enforcement

**Checkpoint**: Setup complete - directories and LFS utilities ready.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Write failing tests for `NativeExecutor` behavior in `tests/smoke/test_native_executor.py` (env missing -> skip, JSON parsing, timeout handling), then implement `NativeExecutor` with `conda run` support in `tests/smoke/utils/native_executor.py`
- [x] T004 [P] Write failing tests for `DataEquivalenceHelper` in `tests/smoke/test_data_equivalence.py` (shape normalization via `np.squeeze`, float tolerance, int exact equality, label IoU threshold, table checks, and *basic* plot invariants: file exists + readable), then implement `DataEquivalenceHelper` for array, label, basic plot semantic, and table comparisons in `tests/smoke/utils/data_equivalence.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - MCP Tool Accuracy (Priority: P1) 🎯 MVP

**Goal**: Verify that MCP tool outputs match native library outputs for 7 core libraries.

**Independent Test**: Run each `test_equivalence_*.py` and verify it passes against its corresponding baseline script.

- [x] T006 [P] [US1] Write failing PhasorPy equivalence test at `tests/smoke/test_equivalence_phasorpy.py` (must include `@pytest.mark.smoke_full` + `@pytest.mark.uses_minimal_data` + `@pytest.mark.requires_env("bioimage-mcp-base")`), then implement baseline script at `tests/smoke/reference_scripts/phasorpy_baseline.py` (must emit JSON per ReferenceScript contract)
- [x] T008 [P] [US1] Write failing Scikit-image equivalence test at `tests/smoke/test_equivalence_skimage.py` (must include `@pytest.mark.smoke_full` + `@pytest.mark.uses_minimal_data` + `@pytest.mark.requires_env("bioimage-mcp-base")`; exact-vs-tolerance policy enforced by helper), then implement baseline script at `tests/smoke/reference_scripts/skimage_baseline.py` (must emit JSON per ReferenceScript contract)
- [x] T010 [P] [US1] Write failing SciPy equivalence test at `tests/smoke/test_equivalence_scipy.py` (must include `@pytest.mark.smoke_full` + `@pytest.mark.uses_minimal_data` + `@pytest.mark.requires_env("bioimage-mcp-base")`), then implement baseline script at `tests/smoke/reference_scripts/scipy_baseline.py` (must emit JSON per ReferenceScript contract)
- [x] T012 [P] [US1] Write failing Cellpose equivalence test at `tests/smoke/test_equivalence_cellpose.py` (must include `@pytest.mark.smoke_full` + `@pytest.mark.uses_minimal_data` + `@pytest.mark.requires_env("bioimage-mcp-cellpose")`; iou_threshold=0.95; apply determinism controls where possible), then implement baseline script at `tests/smoke/reference_scripts/cellpose_baseline.py` (must emit JSON per ReferenceScript contract)
- [x] T014 [P] [US1] Write failing Xarray equivalence test at `tests/smoke/test_equivalence_xarray.py` (must include `@pytest.mark.smoke_full` + `@pytest.mark.uses_minimal_data` + `@pytest.mark.requires_env("bioimage-mcp-base")`), then implement baseline script at `tests/smoke/reference_scripts/xarray_baseline.py` (must emit JSON per ReferenceScript contract)
- [x] T016 [P] [US1] Write failing Pandas equivalence test at `tests/smoke/test_equivalence_pandas.py` (must include `@pytest.mark.smoke_full` + `@pytest.mark.uses_minimal_data` + `@pytest.mark.requires_env("bioimage-mcp-base")`), then implement baseline script at `tests/smoke/reference_scripts/pandas_baseline.py` (must emit JSON per ReferenceScript contract)
- [x] T018 [P] [US1] Write failing Matplotlib equivalence test at `tests/smoke/test_equivalence_matplotlib.py` (must include `@pytest.mark.smoke_full` + `@pytest.mark.uses_minimal_data` + `@pytest.mark.requires_env("bioimage-mcp-base")`), then implement baseline script at `tests/smoke/reference_scripts/matplotlib_baseline.py` (must emit JSON per ReferenceScript contract)

**Checkpoint**: MVP Complete - all 7 library equivalence tests passing.

---

## Phase 4: User Story 2 - Schema Drift Detection (Priority: P2)

**Goal**: Ensure MCP tool schemas (describe) match their actual runtime behavior.

**Independent Test**: Run `tests/smoke/test_schema_alignment.py`.

- [x] T019 [US2] Write failing tests for schema alignment canonicalization + diff reporting in `tests/smoke/test_schema_alignment.py`, then implement schema alignment tests (describe vs runtime) against an explicit schema test vector stored in `tests/smoke/schema_vectors.py`, and add runtime schema dump script(s) at `tests/smoke/reference_scripts/schema_dump.py` (or per-env equivalents) to fetch `meta.describe` via `conda run` and emit canonicalized JSON

**Checkpoint**: Schema drift detection active.

---

## Phase 5: User Story 3 - Matplotlib Semantics (Priority: P3)

**Goal**: Improve plot validation beyond simple file existence.

**Independent Test**: Run `tests/smoke/test_equivalence_matplotlib.py` with semantic checks enabled.

- [x] T020 [US3] Add failing tests for *advanced* semantic plot validation in `tests/smoke/test_data_equivalence.py` (non-blank, dimensions within tolerance, basic intensity statistics), then implement advanced plot validation in `tests/smoke/utils/data_equivalence.py`
- [x] T021 [US3] Add semantic plot assertions to `tests/smoke/test_equivalence_matplotlib.py`

**Checkpoint**: Advanced plot validation complete.

---

## Phase 6: User Story 4 - Xarray/Pandas Metadata (Priority: P3)

**Goal**: Verify preservation of coordinates and attributes in complex data structures.

**Independent Test**: Run Xarray/Pandas equivalence tests and verify metadata assertions pass.

- [x] T022 [US4] Add failing tests for metadata preservation comparison in `tests/smoke/test_data_equivalence.py`, then implement metadata preservation assertions (coords, attrs) in `tests/smoke/utils/data_equivalence.py`
- [x] T023 [US4] Add metadata preservation checks to `tests/smoke/test_equivalence_xarray.py` and `tests/smoke/test_equivalence_pandas.py`

**Checkpoint**: Metadata preservation verified across table/array types.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final integration and verification.

- [x] T024 Update `tests/smoke/conftest.py` with fixtures for `NativeExecutor` and `DataEquivalenceHelper` (do this only after earlier tests fail due to missing fixtures)
- [x] T024a Write failing smoke_minimal sanity tests that use minimal fixtures in `tests/smoke/test_smoke_minimal_sanity.py`, then add minimal-data fixtures per library (shape/dtype/dims) in `tests/smoke/conftest.py` to satisfy FR-007
- [x] T024b Add a marker enforcement test in `tests/smoke/test_smoke_markers.py` to assert all `test_equivalence_*.py` tests are marked `smoke_full` (FR-009), include `requires_env("bioimage-mcp-...")`, include exactly one dataset marker (`uses_minimal_data` or `requires_lfs_dataset`), and do not run under `-m smoke_minimal`
- [x] T025 Run full smoke test suite with `--smoke-record` (optional debug mode; see `tests/smoke/test_smoke_recording.py`) and verify interaction logs are produced; also run `pytest tests/smoke/ -m smoke_minimal` to confirm equivalence tests are gated

**Checkpoint**: Full smoke test suite verified and ready for CI integration.

---

## Dependencies & Execution Order

### TDD Gate (Constitution VI)

- For each task line containing "Write failing tests ... then implement ...", the tests MUST be written first and MUST fail before the implementation portion begins.
- Implementation work MUST not proceed until its tests-first portion is in place.

### Phase Dependencies

- **Prerequisites (Phase 0)**: No dependencies - MUST complete first. Blocks ALL other phases.
- **Setup (Phase 1)**: Depends on Phase 0 completion.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - User stories can then proceed in parallel (if staffed).
  - Or sequentially in priority order (P1 → P2 → P3).
- **Polish (Final Phase)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1.
- **User Story 3 (P3)**: Depends on US1 Matplotlib equivalence (T018) being drafted.
- **User Story 4 (P3)**: Depends on US1 Xarray/Pandas equivalence (T014, T016) being drafted.

### Within Each User Story

- Each equivalence test is written first and fails until the baseline script + MCP wiring exists (TDD).
- Core utilities (in `utils/`) before their usage in test files.
- Each baseline script MUST follow the ReferenceScript output contract (JSON to stdout) to avoid per-script drift.
- Story complete before moving to next priority.

### Parallel Opportunities

- T003 and T004 in Foundational phase (different files).
- Equivalence tests per library (T006, T008, T010, T012, T014, T016, T018) can run in parallel once Foundation is complete.
- User stories US1 and US2 can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories).
3. Complete Phase 3: User Story 1 (core library equivalence).
4. **STOP and VALIDATE**: Test all 7 library equivalences independently.
5. Merge to main as the smoke test baseline.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready.
2. Add US1 → Test independently → Deliver MVP.
3. Add US2 → Test independently → Enhance coverage.
4. Add US3/US4 → Refine validation logic.

### Parallel Team Strategy

1. Team completes Setup + Foundational together.
2. Once Foundational is done:
   - Developer A: PhasorPy and Scikit-image tests (US1).
   - Developer B: Cellpose and SciPy tests (US1).
   - Developer C: Schema alignment (US2).
integration and polish together.

---

## Notes

- [P] tasks = different files, no dependencies (though logical dependencies like script before test may still apply for full passing).
- [Story] label maps task to specific user story for traceability.
- Each user story should be independently completable and testable.
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
- **LFS Note**: Always check for LFS pointers before attempting to read sample data in tests.
