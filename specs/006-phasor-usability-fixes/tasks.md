---
description: "Task list for phasor workflow usability fixes"
---

# Tasks: Phasor Workflow Usability Fixes

**Input**: Design documents from `/specs/006-phasor-usability-fixes/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml

**Tests**: All tasks follow TDD approach - tests written and verified to fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each fix.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- Core server: `src/bioimage_mcp/`
- Base toolkit: `tools/base/bioimage_mcp_base/`
- Tests: `tests/unit/`, `tests/contract/`, `tests/integration/`
- Environments: `envs/`

---

## Phase 1: Setup

**Purpose**: Project initialization and branch preparation

- [X] T001 Verify working directory is clean and on main branch
- [X] T002 Create feature branch `006-phasor-usability-fixes`
- [X] T003 [P] Verify base environment exists with `python -m bioimage_mcp doctor`
- [X] T004 [P] Run existing test suite to establish baseline: `pytest tests/`

---

## Phase 2: Foundational

**Purpose**: Shared infrastructure that multiple stories depend on

**⚠️ CRITICAL**: This feature has minimal foundational work - user stories are largely independent

- [X] T005 Review `src/bioimage_mcp/api/server.py` to understand current ServerSession usage patterns

**Checkpoint**: Foundation reviewed - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Tool Discovery Works (Priority: P1) 🎯 MVP

**Goal**: Fix ServerSession.id AttributeError blocking all discovery endpoints

**Independent Test**: Run `list_tools` and `search_functions` without AttributeError

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US1] Add unit test for `get_session_identifier()` helper in `tests/unit/api/test_server_session.py` - verify it handles stdio transport (id fallback)
- [X] T007 [P] [US1] Add unit test for SSE transport session extraction in `tests/unit/api/test_server_session.py` - verify query param parsing
- [X] T008 [US1] Add contract test for DISC-001 in `tests/contract/test_discovery_contract.py` - verify `list_tools()` returns without ServerSession error
- [X] T009 [US1] Add contract test for DISC-002 in `tests/contract/test_discovery_contract.py` - verify `search_functions(query="phasor")` returns matching results
- [X] T009b [P] [US1] Add contract test for pagination in `tests/contract/test_discovery_contract.py` - verify `list_tools()` returns paginated response with `next_cursor` field when results exceed page limit
- [X] T009a [US1] **TDD GATE**: Run `pytest tests/unit/api/test_server_session.py tests/contract/test_discovery_contract.py -v` and verify ALL tests from T006-T009 FAIL (expected: no implementation yet)

### Implementation for User Story 1

- [X] T010 [US1] Implement `get_session_identifier(ctx)` helper in `src/bioimage_mcp/api/server.py` - try SSE query params first, fallback to `id(ctx.session)`
- [X] T011 [US1] Replace all `ctx.session.id` references with `get_session_identifier(ctx)` in `src/bioimage_mcp/api/server.py`
- [X] T012 [US1] Verify unit tests pass for session identifier helper
- [X] T013 [US1] Verify contract tests pass for discovery endpoints (DISC-001, DISC-002)

**Checkpoint**: At this point, discovery endpoints should work without errors

---

## Phase 4: User Story 2 - Function Schema Introspection (Priority: P1)

**Goal**: Fix `describe_function` returning empty params_schema

**Independent Test**: Call `describe_function("base.phasor_from_flim")` and receive complete schema

### Tests for User Story 2 ⚠️

- [X] T014 [P] [US2] Add contract test for DISC-003 in `tests/contract/test_discovery_contract.py` - verify `describe_function("base.phasor_from_flim")` returns params_schema with time_axis, harmonic properties
- [X] T015 [P] [US2] Add unit test for schema extraction in `tests/unit/base/test_entrypoint.py` - verify `meta.describe` returns complete JSON Schema from Pydantic models
- [X] T016 [P] [US2] Add integration test in `tests/integration/test_schema_enrichment.py` - verify end-to-end schema enrichment for static and dynamic functions
- [X] T016a [US2] **TDD GATE**: Run `pytest tests/unit/base/test_entrypoint.py tests/contract/test_discovery_contract.py tests/integration/test_schema_enrichment.py -v` and verify ALL tests from T014-T016 FAIL (expected: schema extraction incomplete)

### Implementation for User Story 2

- [X] T017 [US2] Investigate `meta.describe` implementation in `tools/base/bioimage_mcp_base/entrypoint.py` - identify why schema extraction is incomplete
- [X] T018 [US2] Fix schema extraction logic in `tools/base/bioimage_mcp_base/entrypoint.py` - ensure it returns complete JSON Schema with all properties from Pydantic model
- [X] T019 [US2] Add introspection_source field to describe response indicating "pydantic" or "manual"
- [X] T020 [US2] Verify unit tests pass for schema extraction
- [X] T021 [US2] Verify contract test passes for DISC-003
- [X] T022 [US2] Verify integration test passes for end-to-end schema enrichment

**Checkpoint**: At this point, `describe_function` should return complete parameter schemas

---

## Phase 5: User Story 3 - Phasor Calibration Workflow (Priority: P2)

**Goal**: Add phasor calibration function wrapping phasorpy

**Independent Test**: Compute sample phasors → reference phasors → calibrate and get calibrated coordinates

### Tests for User Story 3 ⚠️

- [X] T023 [P] [US3] Add contract test for CAL-001 in `tests/contract/test_phasor_calibrate.py` (NEW) - verify calibration accepts sample_phasors, reference_phasors, lifetime, frequency
- [X] T024 [P] [US3] Add contract test for CAL-002 in `tests/contract/test_phasor_calibrate.py` - verify rejection of invalid lifetime (negative value)
- [X] T025 [P] [US3] Add contract test for CAL-003 in `tests/contract/test_phasor_calibrate.py` - verify provenance recording (reference_lifetime, reference_frequency, reference_harmonic in metadata)
- [X] T026 [P] [US3] Add unit test in `tests/unit/base/test_transforms.py` - verify `phasor_calibrate` implementation wraps phasorpy correctly
- [X] T026a [US3] **TDD GATE**: Run `pytest tests/contract/test_phasor_calibrate.py tests/unit/base/test_transforms.py -v` and verify ALL tests from T023-T026 FAIL (expected: phasor_calibrate not implemented)

### Implementation for User Story 3

- [X] T027 [P] [US3] Add `phasor_calibrate` function entry to `tools/base/manifest.yaml` with inputs (sample_phasors: BioImageRef, reference_phasors: BioImageRef), params (lifetime, frequency, harmonic), outputs (calibrated_phasors: BioImageRef)
- [X] T028 [US3] Implement `phasor_calibrate()` in `tools/base/bioimage_mcp_base/transforms.py` - load 2-channel inputs, call `phasorpy.lifetime.phasor_calibrate`, return 2-channel BioImageRef
- [X] T029 [US3] Add parameter validation for lifetime > 0, frequency > 0 in phasor_calibrate implementation
- [X] T030 [US3] Add provenance metadata recording (reference_lifetime, reference_frequency, reference_harmonic) to output artifact
- [X] T031 [US3] Verify unit tests pass for phasor_calibrate wrapper
- [X] T032 [US3] Verify contract tests pass for CAL-001, CAL-002, CAL-003

**Checkpoint**: At this point, phasor calibration workflow should be fully functional end-to-end

---

## Phase 6: User Story 4 - OME-TIFF Compatibility with bioio-bioformats (Priority: P2)

**Goal**: Add bioio-bioformats plugin with fallback chain for better OME-TIFF compatibility

**Independent Test**: Load `datasets/FLUTE_FLIM_data_tif/Embryo.tif` through fallback chain and verify metadata preservation

### Tests for User Story 4 ⚠️

- [X] T033 [P] [US4] Add integration test for IO-001 in `tests/integration/test_io_fallback.py` (NEW) - verify bioio-ome-tiff is tried first for valid OME-TIFF
- [X] T034 [P] [US4] Add integration test for IO-002 in `tests/integration/test_io_fallback.py` - verify fallback to bioio-bioformats on ome-tiff failure (mock exception)
- [X] T035 [P] [US4] Add integration test for IO-003 in `tests/integration/test_io_fallback.py` - verify final fallback to tifffile with TIFFFILE_FALLBACK warning
- [X] T036 [P] [US4] Add unit test in `tests/unit/base/test_io.py` - verify `load_image_fallback()` logic and error handling
- [X] T036a [US4] **TDD GATE**: Run `pytest tests/integration/test_io_fallback.py tests/unit/base/test_io.py -v` and verify ALL tests from T033-T036 FAIL (expected: load_image_fallback not implemented)

### Implementation for User Story 4

- [ ] T037 [P] [US4] Add openjdk (>=11), scyjava, bioio-bioformats to `envs/bioimage-mcp-base.yaml` dependencies
- [X] T038 [US4] Implement `load_image_fallback()` function in `tools/base/bioimage_mcp_base/io.py` - try bioio-ome-tiff → bioio-bioformats → tifffile with explicit exception handling
- [X] T039 [US4] Add logging/warnings for each fallback level in load_image_fallback
- [X] T040 [US4] Update `load_image()` function in io.py to use `load_image_fallback()` internally
- [X] T041 [US4] Verify unit tests pass for load_image_fallback logic
- [ ] T042 [US4] Update base environment lock file: `conda-lock -f envs/bioimage-mcp-base.yaml -p linux-64`
- [X] T043 [US4] Verify integration tests pass for IO-001, IO-002, IO-003 (requires environment rebuild)

**Checkpoint**: At this point, bioio-bioformats should be available and fallback chain working

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T044 [P] Update `docs/tutorials/flim_phasor.md` to include calibration workflow example
- [ ] T045 [P] Add calibration example to quickstart validation script: `scripts/validate_pipeline.py`
- [X] T046 [P] Verify all existing tests still pass: `pytest tests/`
- [X] T047 Run full contract test suite: `pytest tests/contract/`
- [X] T048 Run full integration test suite: `pytest tests/integration/`
- [ ] T049 [P] Update `specs/006-phasor-usability-fixes/quickstart.md` with validation steps
- [ ] T050 [P] Complete code review checklist in `specs/006-phasor-usability-fixes/checklists/code-review.md`
- [X] T051 Verify constitution compliance for all changes (stable MCP surface, artifact I/O, isolation)
- [X] T052 Run `ruff check . && ruff format --check .` to verify code style

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - minimal blocking work
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 and US2 can proceed in parallel (different files)
  - US3 and US4 can proceed in parallel after US1/US2 (discovery must work to test new functions)
  - Or execute sequentially in priority order (P1 → P1 → P2 → P2)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories (parallel to US1)
- **User Story 3 (P2)**: Needs US1 complete (discovery must work to find/test calibration function)
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Independent of US1/US2/US3

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Contract tests before implementation
- Unit tests before implementation
- Implementation after all tests are written and verified failing
- Story complete before moving to next priority

### Parallel Opportunities

- T001-T004 (Setup tasks) can all run in parallel
- T006-T009 (US1 tests) can all run in parallel
- T014-T016 (US2 tests) can all run in parallel
- T023-T026 (US3 tests) can all run in parallel
- T033-T036 (US4 tests) can all run in parallel
- T027 (manifest update) can run parallel to other US3 prep work
- T037 (environment file update) can run parallel to other US4 prep work
- T044-T045, T049-T050 (Polish documentation) can all run in parallel
- Once Foundational phase completes:
  - US1 (T006-T013) and US2 (T014-T022) can run fully in parallel
  - US4 (T033-T043) can run in parallel to US1/US2/US3

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Add unit test for get_session_identifier() helper in tests/unit/api/test_server_session.py"
Task: "Add unit test for SSE transport session extraction in tests/unit/api/test_server_session.py"
Task: "Add contract test for DISC-001 in tests/contract/test_discovery_contract.py"
Task: "Add contract test for DISC-002 in tests/contract/test_discovery_contract.py"

# After tests fail, implement:
Task: "Implement get_session_identifier(ctx) helper in src/bioimage_mcp/api/server.py"
Task: "Replace all ctx.session.id references with get_session_identifier(ctx)"
```

---

## Parallel Example: User Story 3 + User Story 4

```bash
# After US1/US2 complete, both US3 and US4 can start in parallel:

# US3 tests in parallel:
Task: "Add contract test for CAL-001 in tests/contract/test_phasor_calibrate.py"
Task: "Add contract test for CAL-002 in tests/contract/test_phasor_calibrate.py"
Task: "Add contract test for CAL-003 in tests/contract/test_phasor_calibrate.py"
Task: "Add unit test in tests/unit/base/test_transforms.py"

# US4 tests in parallel (independent of US3):
Task: "Add integration test for IO-001 in tests/integration/test_io_fallback.py"
Task: "Add integration test for IO-002 in tests/integration/test_io_fallback.py"
Task: "Add integration test for IO-003 in tests/integration/test_io_fallback.py"
Task: "Add unit test in tests/unit/base/test_io.py"

# US3 + US4 implementation can also proceed in parallel (different files):
Task: "Implement phasor_calibrate() in tools/base/bioimage_mcp_base/transforms.py"
Task: "Implement load_image_fallback() in tools/base/bioimage_mcp_base/io.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only - Both P1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (minimal review)
3. Complete Phase 3: User Story 1 (Discovery infrastructure fix)
4. Complete Phase 4: User Story 2 (Schema introspection fix)
5. **STOP and VALIDATE**: Test discovery and schema introspection independently
6. Deploy/demo if ready - this unblocks all downstream workflows

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Discovery works (MVP partial!)
3. Add User Story 2 → Test independently → Schema introspection works (MVP complete!)
4. Add User Story 3 → Test independently → Calibration available (Enhanced!)
5. Add User Story 4 → Test independently → Better OME-TIFF support (Full feature!)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Discovery fix)
   - Developer B: User Story 2 (Schema fix)
3. After US1/US2 complete:
   - Developer A: User Story 3 (Calibration)
   - Developer B: User Story 4 (IO fallback)
4. Stories complete and integrate independently

### Sequential Strategy (Single Developer)

Priority order (highest value first):

1. Setup + Foundational
2. US1 (P1): Discovery - BLOCKING all workflows
3. US2 (P1): Schema introspection - BLOCKING practical usage
4. US3 (P2): Calibration - Enhances phasor workflows
5. US4 (P2): IO compatibility - Better file support
6. Polish: Documentation and validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD enforcement)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- US1 and US2 are both P1 (critical infrastructure) - should be completed first
- US3 and US4 are both P2 (enhancements) - can be deferred if needed
- All changes maintain backward compatibility (no breaking API changes)

---

## Contract Coverage

This task list ensures coverage of all contract assertions:

- **DISC-001, DISC-002**: Covered by US1 contract tests (T008, T009)
- **DISC-003**: Covered by US2 contract tests (T014)
- **DISC-004**: Covered by US2 error handling test (T014 extended)
- **CAL-001, CAL-002, CAL-003**: Covered by US3 contract tests (T023, T024, T025)
- **CAL-004**: Covered by US3 contract tests (new assertion)
- **IO-001, IO-002, IO-003**: Covered by US4 integration tests (T033, T034, T035)

---

## Test-First Enforcement

Every implementation task has corresponding test tasks that:
1. MUST be written before implementation
2. MUST be verified to FAIL before implementation
3. MUST PASS after implementation

This ensures adherence to TDD principles required by the constitution.
