# Tasks: Smoke Test Expansion (027)

**Input**: Design documents from `/specs/027-smoke-test-expansion/`
**Prerequisites**: plan.md (required), spec.md (required)
**Tests**: Smoke tests are the primary deliverable; each task includes verification via the new test suite.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 0: Prerequisites (Blocking)

**Purpose**: Fix known issues that would cause equivalence tests to fail or produce misleading results.

**⚠️ CRITICAL**: These tasks MUST be completed before any smoke test work begins.

**Reference**: See `phase0-prerequisites.md` for detailed implementation guidance.

- [ ] T000a Migrate `ScipyNdimageAdapter._save_image()` in `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py` to use `bioio.writers.OmeTiffWriter` following the pattern in `skimage.py`. Changes: (1) extension to `.ome.tiff`, (2) dtype handling for int64/uint64, (3) OmeTiffWriter with tifffile fallback, (4) add `axes` to metadata. Verify with `pytest tests/contract/test_scipy_adapter.py tests/unit/adapters/test_scipy_ndimage_objectref.py -v`
- [ ] T000b Verify dataset LFS configuration: (1) confirm `.gitattributes` tracks `datasets/**`, (2) verify each dataset folder has README with provenance, (3) test LFS pointer detection pattern works, (4) update `phase0-prerequisites.md` dataset inventory if new datasets are added

**Checkpoint**: Prerequisites complete - I/O consistency ensured and datasets verified.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create reference script and utility directories at `tests/smoke/reference_scripts/` and `tests/smoke/utils/` (use tests that import from these paths to implicitly validate structure)
- [ ] T002 Write failing tests for LFS detection + skip messaging in `tests/smoke/test_lfs_utils.py`, then implement LFS pointer detection and skip logic in `tests/smoke/utils/lfs_utils.py`

**Checkpoint**: Setup complete - directories and LFS utilities ready.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Write failing tests for `NativeExecutor` behavior in `tests/smoke/test_native_executor.py` (env missing -> skip, JSON parsing, timeout handling), then implement `NativeExecutor` with `conda run` support in `tests/smoke/utils/native_executor.py`
- [ ] T004 [P] Write failing tests for `DataEquivalenceHelper` in `tests/smoke/test_data_equivalence.py` (float tolerance, int exact equality, label IoU threshold, table checks), then implement `DataEquivalenceHelper` for array, label, plot semantic, and table comparisons in `tests/smoke/utils/data_equivalence.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - MCP Tool Accuracy (Priority: P1) 🎯 MVP

**Goal**: Verify that MCP tool outputs match native library outputs for 7 core libraries.

**Independent Test**: Run each `test_equivalence_*.py` and verify it passes against its corresponding baseline script.

- [ ] T006 [P] [US1] Write failing PhasorPy equivalence test at `tests/smoke/test_equivalence_phasorpy.py` (must be `@pytest.mark.smoke_full`), then implement baseline script at `tests/smoke/reference_scripts/phasorpy_baseline.py` (must emit JSON per ReferenceScript contract)
- [ ] T008 [P] [US1] Write failing Scikit-image equivalence test at `tests/smoke/test_equivalence_skimage.py` (must be `@pytest.mark.smoke_full`; exact-vs-tolerance policy enforced by helper), then implement baseline script at `tests/smoke/reference_scripts/skimage_baseline.py` (must emit JSON per ReferenceScript contract)
- [ ] T010 [P] [US1] Write failing SciPy equivalence test at `tests/smoke/test_equivalence_scipy.py` (must be `@pytest.mark.smoke_full`), then implement baseline script at `tests/smoke/reference_scripts/scipy_baseline.py` (must emit JSON per ReferenceScript contract)
- [ ] T012 [P] [US1] Write failing Cellpose equivalence test at `tests/smoke/test_equivalence_cellpose.py` (must be `@pytest.mark.smoke_full`; iou_threshold=0.95; apply determinism controls where possible), then implement baseline script at `tests/smoke/reference_scripts/cellpose_baseline.py` (must emit JSON per ReferenceScript contract)
- [ ] T014 [P] [US1] Write failing Xarray equivalence test at `tests/smoke/test_equivalence_xarray.py` (must be `@pytest.mark.smoke_full`), then implement baseline script at `tests/smoke/reference_scripts/xarray_baseline.py` (must emit JSON per ReferenceScript contract)
- [ ] T016 [P] [US1] Write failing Pandas equivalence test at `tests/smoke/test_equivalence_pandas.py` (must be `@pytest.mark.smoke_full`), then implement baseline script at `tests/smoke/reference_scripts/pandas_baseline.py` (must emit JSON per ReferenceScript contract)
- [ ] T018 [P] [US1] Write failing Matplotlib equivalence test at `tests/smoke/test_equivalence_matplotlib.py` (must be `@pytest.mark.smoke_full`), then implement baseline script at `tests/smoke/reference_scripts/matplotlib_baseline.py` (must emit JSON per ReferenceScript contract)

**Checkpoint**: MVP Complete - all 7 library equivalence tests passing.

---

## Phase 4: User Story 2 - Schema Drift Detection (Priority: P2)

**Goal**: Ensure MCP tool schemas (describe) match their actual runtime behavior.

**Independent Test**: Run `tests/smoke/test_schema_alignment.py`.

- [ ] T019 [US2] Write failing tests for schema alignment canonicalization + diff reporting in `tests/smoke/test_schema_alignment.py`, then implement schema alignment tests (describe vs runtime), and add runtime schema dump script(s) at `tests/smoke/reference_scripts/schema_dump.py` (or per-env equivalents) to fetch `meta.describe` via `conda run` and emit canonicalized JSON

**Checkpoint**: Schema drift detection active.

---

## Phase 5: User Story 3 - Matplotlib Semantics (Priority: P3)

**Goal**: Improve plot validation beyond simple file existence.

**Independent Test**: Run `tests/smoke/test_equivalence_matplotlib.py` with semantic checks enabled.

- [ ] T020 [US3] Add failing tests for semantic plot validation in `tests/smoke/test_data_equivalence.py`, then implement semantic plot validation (non-blank, dimensions) in `tests/smoke/utils/data_equivalence.py`
- [ ] T021 [US3] Add semantic plot assertions to `tests/smoke/test_equivalence_matplotlib.py`

**Checkpoint**: Advanced plot validation complete.

---

## Phase 6: User Story 4 - Xarray/Pandas Metadata (Priority: P3)

**Goal**: Verify preservation of coordinates and attributes in complex data structures.

**Independent Test**: Run Xarray/Pandas equivalence tests and verify metadata assertions pass.

- [ ] T022 [US4] Add failing tests for metadata preservation comparison in `tests/smoke/test_data_equivalence.py`, then implement metadata preservation assertions (coords, attrs) in `tests/smoke/utils/data_equivalence.py`
- [ ] T023 [US4] Add metadata preservation checks to `tests/smoke/test_equivalence_xarray.py` and `tests/smoke/test_equivalence_pandas.py`

**Checkpoint**: Metadata preservation verified across table/array types.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final integration and verification.

- [ ] T024 Update `tests/smoke/conftest.py` with fixtures for `NativeExecutor` and `DataEquivalenceHelper` (do this only after earlier tests fail due to missing fixtures)
- [ ] T024a Write failing smoke_minimal sanity tests that use minimal fixtures in `tests/smoke/test_smoke_minimal_sanity.py`, then add minimal-data fixtures per library (shape/dtype/dims) in `tests/smoke/conftest.py` to satisfy FR-007
- [ ] T024b Add a marker enforcement test in `tests/smoke/test_smoke_markers.py` to assert all `test_equivalence_*.py` tests are marked `smoke_full` (FR-009) and do not run under `-m smoke_minimal`
- [ ] T025 Run full smoke test suite with `--smoke-record` and verify interaction logs (also run `pytest tests/smoke/ -m smoke_minimal` to confirm equivalence tests are gated)

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
3. Integrate and polish together.

---

## Notes

- [P] tasks = different files, no dependencies (though logical dependencies like script before test may still apply for full passing).
- [Story] label maps task to specific user story for traceability.
- Each user story should be independently completable and testable.
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
- **LFS Note**: Always check for LFS pointers before attempting to read sample data in tests.
