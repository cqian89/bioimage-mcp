# Tasks: Cellpose Object-Oriented API & Stateful Execution

**Input**: Design documents from `/specs/017-cellpose-api/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: TDD approach - write tests FIRST, ensure they FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure verification

- [X] T001 Verify feature branch `017-cellpose-api` exists or create it
- [X] T002 Verify Cellpose environment readiness via `python -m bioimage_mcp doctor`
- [X] T003 [P] Review existing ObjectRef-related code patterns in `src/bioimage_mcp/artifacts/models.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational (TDD - write first, must FAIL)

- [X] T004 [P] Write ObjectRef schema contract tests in `tests/contract/test_object_ref.py` (Assert required `uri`, `python_class` and optional `device`, `sha256`, `init_params`)
- [X] T005 [P] Write ObjectRef URI validation tests (obj:// scheme) in `tests/contract/test_object_ref.py`
- [X] T006 [P] Write DynamicSource extension tests (target_class, class_methods) in `tests/unit/registry/test_class_discovery.py`
- [X] T047 [P] Write unit tests for `**kwargs` filtering in class-based discovery in `tests/unit/registry/test_class_discovery.py`
- [X] T049 [P] Write contract test for `describe` of `CellposeModel.eval` asserting `ObjectRef` input port in `tests/contract/test_cellpose_meta_describe.py` (Verify artifact ports NOT in `params_schema`)
- [X] T043 [P] Write integration tests for `session_export` (workflow-record-json) containing `ObjectRef` in `tests/integration/test_export_session.py` (Assert `init_params` and class identity are recorded) [Blocking FR-004]
- [X] T044 [P] Write integration tests for `session_replay` reconstruction of `ObjectRef` in `tests/integration/test_workflows.py` [Blocking FR-004]
- [X] T007 [P] Write ExecuteRequest class_context tests in `tests/unit/runtimes/test_worker_ipc.py`

### Implementation for Foundational

- [X] T008 Add ObjectRef to ARTIFACT_TYPES dict in `src/bioimage_mcp/artifacts/models.py` (Ensure schema matches spec: `uri` + `python_class` required)
- [X] T009 Implement ObjectRef Pydantic model with python_class, obj:// URI validator in `src/bioimage_mcp/artifacts/models.py` (Include optional fields: `device`, `sha256`, `init_params`)
- [X] T010 Add target_class and class_methods fields to DynamicSource in `src/bioimage_mcp/registry/manifest_schema.py`
- [X] T048 Implement `**kwargs` filtering logic in `src/bioimage_mcp/registry/dynamic/discovery.py` (or adapter) to ensure methods with `**kwargs` are excluded unless schema overlay exists
- [X] T045 Update `src/bioimage_mcp/runs/models.py` and `src/bioimage_mcp/api/schemas.py` to support `ObjectRef` metadata in workflow records [Blocking FR-004]
- [X] T046 Implement `ObjectRef` reconstruction logic in `src/bioimage_mcp/api/execution.py` and `src/bioimage_mcp/api/sessions.py` (Use `init_params` to re-instantiate if artifact load fails) [Blocking FR-004]
- [X] T011 Add ClassContext model with init_params to `src/bioimage_mcp/runtimes/worker_ipc.py`
- [X] T012 Add class_context field to ExecuteRequest in `src/bioimage_mcp/runtimes/worker_ipc.py`
- [X] T013 Run foundational tests and verify all pass

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Fast Iterative Segmentation (Priority: P1) 🎯 MVP

**Goal**: Load a Cellpose model once and reuse it for multiple images without reloading weights

**Independent Test**: Call model loader → receive ObjectRef → call eval twice with same ObjectRef → verify second call is faster

### Tests for User Story 1 (TDD - write first, must FAIL) ⚠️

- [X] T014 [P] [US1] Write integration test for ObjectRef creation via model instantiation in `tests/integration/test_cellpose_stateful.py`
- [X] T015 [P] [US1] Write integration test for eval with ObjectRef input in `tests/integration/test_cellpose_stateful.py`
- [X] T016 [P] [US1] Write integration test for model reuse performance comparison in `tests/integration/test_cellpose_stateful.py`
- [X] T017 [P] [US1] Write unit test for object caching/retrieval in entrypoint in `tests/unit/tools/test_cellpose_entrypoint.py`

### Implementation for User Story 1

- [X] T018 [US1] Implement _OBJECT_CACHE dict for model persistence in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
- [X] T019 [US1] Implement _store_object and _load_object helpers with obj:// URI in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
- [X] T020 [US1] Create handle_model_init function for CellposeModel instantiation in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
- [X] T021 [US1] Update handle_segment to accept ObjectRef model input in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
- [X] T022 [US1] Add cellpose.CellposeModel function entry to manifest.yaml in `tools/cellpose/manifest.yaml`
- [X] T023 [US1] Add cellpose.CellposeModel.eval function entry to manifest.yaml in `tools/cellpose/manifest.yaml`
- [X] T024 [US1] Update FUNCTION_HANDLERS dispatch table in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
- [X] T025 [US1] Run User Story 1 tests and verify all pass

**Checkpoint**: User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Model Fine-Tuning Workflow (Priority: P2)

**Goal**: Train a model, get weight reference, use weights for new model instance validation

**Independent Test**: Execute train_seg → verify returns NativeOutputRef (weights) + TableRef (losses) → pass weight reference to model instantiation

### Tests for User Story 2 (TDD - write first, must FAIL) ⚠️

- [ ] T026 [P] [US2] Write integration test for train_seg output artifacts in `tests/integration/test_cellpose_training.py`
- [ ] T027 [P] [US2] Write integration test for using trained weights in new model in `tests/integration/test_cellpose_training.py`
- [ ] T028 [P] [US2] Write unit test for training parameter schema in `tests/unit/tools/test_cellpose_training.py`

### Implementation for User Story 2

- [ ] T029 [US2] Create training ops module in `tools/cellpose/bioimage_mcp_cellpose/ops/training.py`
- [ ] T030 [US2] Implement run_train_seg function with NativeOutputRef + TableRef outputs in `tools/cellpose/bioimage_mcp_cellpose/ops/training.py`
- [ ] T031 [US2] Create handle_train_seg function in entrypoint in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
- [ ] T032 [US2] Update handle_model_init to accept pretrained_model weights path in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
- [ ] T033 [US2] Update FUNCTION_HANDLERS with train_seg entry in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
- [ ] T034 [US2] Run User Story 2 tests and verify all pass

**Checkpoint**: User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T035 [P] Write tests for ObjectRef eviction in `tests/unit/tools/test_cellpose_eviction.py`
- [ ] T036 Extend handle_evict to support ObjectRef (obj:// URIs) in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
- [ ] T051 [P] Write integration test for `cellpose.cache.clear` tool-pack function in `tests/integration/test_cellpose_cache.py`
- [ ] T052 Add `cellpose.cache.clear` function definition to `tools/cellpose/manifest.yaml`
- [ ] T053 Implement `handle_cache_clear` in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`
- [ ] T037 [P] Add error handling for evicted/invalid ObjectRef with constitution-compliant structured errors in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py` (Require `code`, `message`, `details[]` with `path` + `hint`)
- [ ] T050 [P] Write unit tests validating structured error shape for ObjectRef failures (missing artifact, incompatible device) in `tests/unit/api/test_errors.py`
- [ ] T054 [P] Write test for missing ObjectRef artifact (URI deleted) returning structured `ArtifactNotFoundError` (FR-009) in `tests/unit/api/test_errors.py`
- [ ] T055 [P] Write test for GPU->CPU replay behavior (map_location or structured error with hint) in `tests/integration/test_workflows.py`
- [ ] T038 [P] Update CellposeAdapter to handle class-based discovery in `src/bioimage_mcp/registry/dynamic/adapters/cellpose.py`
- [ ] T039 [P] Document ObjectRef usage in `specs/017-cellpose-api/quickstart.md`
- [ ] T040 Update `AGENTS.md` with ObjectRef artifact type
- [ ] T041 Run full test suite and verify all tests pass
- [ ] T042 Validate quickstart.md scenarios work end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Uses ObjectRef from US1 but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Core models before handlers
- Handlers before manifest updates
- Story complete before moving to next priority

### Parallel Opportunities

- All Foundational tests marked [P] can run in parallel (T004-T007, T047, T049, T043, T044)
- All US1 tests marked [P] can run in parallel (T014-T017)
- All US2 tests marked [P] can run in parallel (T026-T028)
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (TDD):
Task: "Write integration test for ObjectRef creation via model instantiation in tests/integration/test_cellpose_stateful.py"
Task: "Write integration test for eval with ObjectRef input in tests/integration/test_cellpose_stateful.py"
Task: "Write integration test for model reuse performance comparison in tests/integration/test_cellpose_stateful.py"
Task: "Write unit test for object caching/retrieval in entrypoint in tests/unit/tools/test_cellpose_entrypoint.py"

# After tests FAIL, implementation can proceed sequentially
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests FAIL before implementing (TDD Red-Green-Refactor)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- ObjectRef uses pickle serialization (research.md Q1)
- ObjectRef URI scheme: obj://session_id/env_id/object_id (research.md Q4)
- Extend existing evict for ObjectRef, not new tool (research.md Q5)
