# Tasks: MCP Interface Redesign (Clean Surface)

**Input**: Design documents from `/specs/016-mcp-interface-redesign/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, quickstart.md
**Approach**: TDD (Test-Driven Development) - Write failing tests FIRST, then implement

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in all descriptions

## Path Conventions

- **Core server**: `src/bioimage_mcp/api/`
- **Tests**: `tests/contract/`, `tests/integration/`, `tests/unit/api/`

---

## Phase 1: Setup

**Purpose**: Verify project structure matches implementation plan

- [ ] T001 Verify project structure exists per plan.md in src/bioimage_mcp/api/
- [ ] T002 Verify pytest and pytest-asyncio are in pyproject.toml dependencies
- [ ] T003 [P] Create tests/contract/ directory structure if missing

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

### Core Pydantic Models

- [ ] T004 [P] Define NodeType enum in src/bioimage_mcp/api/schemas.py
- [ ] T005 [P] Define ChildCounts model in src/bioimage_mcp/api/schemas.py
- [ ] T006 [P] Define IOPort and IOSummary models in src/bioimage_mcp/api/schemas.py
- [ ] T007 [P] Define CatalogNode model in src/bioimage_mcp/api/schemas.py
- [ ] T008 [P] Define InputHints, InputPort, OutputPort models in src/bioimage_mcp/api/schemas.py
- [ ] T009 [P] Define FunctionExample and NextStep models in src/bioimage_mcp/api/schemas.py
- [ ] T010 [P] Define FunctionDescriptor model in src/bioimage_mcp/api/schemas.py
- [ ] T011 [P] Define ArtifactType enum and ArtifactChecksum model in src/bioimage_mcp/api/schemas.py
- [ ] T012 [P] Define ArtifactRef model in src/bioimage_mcp/api/schemas.py
- [ ] T013 [P] Define ErrorDetail and StructuredError models in src/bioimage_mcp/api/schemas.py

### Request/Response Models

- [ ] T014 [P] Define ListRequest and ListResponse models in src/bioimage_mcp/api/schemas.py
- [ ] T015 [P] Define DescribeRequest and DescribeResponse models in src/bioimage_mcp/api/schemas.py
- [ ] T016 [P] Define SearchRequest, SearchResult, SearchResponse models in src/bioimage_mcp/api/schemas.py
- [ ] T017 [P] Define RunRequest and RunResponse models in src/bioimage_mcp/api/schemas.py
- [ ] T018 [P] Define StatusRequest, Progress, StatusResponse models in src/bioimage_mcp/api/schemas.py
- [ ] T019 [P] Define ArtifactInfoRequest and ArtifactInfoResponse models in src/bioimage_mcp/api/schemas.py
- [ ] T020 [P] Define SessionExportRequest (optional dest_path) and SessionExportResponse models in src/bioimage_mcp/api/schemas.py
- [ ] T021 [P] Define SessionReplayRequest and SessionReplayResponse models in src/bioimage_mcp/api/schemas.py

### Workflow Models

- [ ] T022 [P] Define ExternalInput and InputSource models in src/bioimage_mcp/api/schemas.py
- [ ] T023 [P] Define StepProvenance (tool_pack_id, tool_pack_version, lock_hash, timestamps) and WorkflowStep models in src/bioimage_mcp/api/schemas.py
- [ ] T024 [P] Define WorkflowRecord model in src/bioimage_mcp/api/schemas.py

### Cleanup Deprecated Tools

- [ ] T025 Remove describe_tool handler from src/bioimage_mcp/api/server.py
- [ ] T026 [P] Remove activate_functions handler from src/bioimage_mcp/api/server.py
- [ ] T027 [P] Remove deactivate_functions handler from src/bioimage_mcp/api/server.py
- [ ] T028 [P] Remove run_workflow handler from src/bioimage_mcp/api/server.py
- [ ] T029 [P] Remove resume_session handler from src/bioimage_mcp/api/server.py
- [ ] T030 [P] Remove export_artifact handler from src/bioimage_mcp/api/artifacts.py

### Error Handling Infrastructure

- [ ] T031 Create structured error helper functions in src/bioimage_mcp/api/errors.py (validation_error, not_found_error, execution_error)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1+3 - Discover and Execute with Child Counts (Priority: P1) - MVP

**Goal**: LLM can browse catalog with child counts, get function details, execute functions, and check status

**Independent Test**: Navigate catalog -> describe function -> execute with valid inputs -> verify output artifacts

### Tests for US1+US3 (TDD: Write FIRST, must FAIL before implementation)

- [ ] T032 [P] [US1] RED: Contract test for list tool deterministic ordering + cursor pagination (`cursor`, `limit`, `next_cursor`) in tests/contract/test_list.py
- [ ] T033 [P] [US1] RED: Contract test for list tool child counts in tests/contract/test_list.py
- [ ] T034 [P] [US1] RED: Contract test for list tool I/O summaries in tests/contract/test_list.py
- [ ] T035 [P] [US1] RED: Contract test for list tool NOT_FOUND error in tests/contract/test_list.py
- [ ] T036 [P] [US1] RED: Contract test for describe function with separated inputs/outputs/params in tests/contract/test_describe.py
- [ ] T037 [P] [US1] RED: Contract test for describe non-function node in tests/contract/test_describe.py
- [ ] T038 [P] [US1] RED: Contract test for describe NOT_FOUND error in tests/contract/test_describe.py
- [ ] T039 [P] [US1] RED: Contract test for run tool success in tests/contract/test_run.py
- [ ] T040 [P] [US1] RED: Contract test for run tool VALIDATION_FAILED error in tests/contract/test_run.py
- [ ] T041 [P] [US1] RED: Contract test for run tool structured error format in tests/contract/test_run.py
- [ ] T119 [P] [US1] RED: Contract test for run tool status:"failed" with log reference when underlying function crashes in tests/contract/test_run.py
- [ ] T042 [P] [US1] RED: Contract test for status tool in tests/contract/test_status.py

### Implementation for US1+US3 (GREEN: Make tests pass)

- [ ] T043 [US1] Implement list handler in src/bioimage_mcp/api/discovery.py with pagination
- [ ] T044 [US1] Add child counts computation to list handler in src/bioimage_mcp/api/discovery.py
- [ ] T045 [US1] Add I/O summaries for function nodes in list handler in src/bioimage_mcp/api/discovery.py
- [ ] T046 [US1] Implement describe handler in src/bioimage_mcp/api/discovery.py
- [ ] T047 [US1] Add separated inputs/outputs/params_schema generation in describe handler in src/bioimage_mcp/api/discovery.py
- [ ] T048 [US1] Implement run handler in src/bioimage_mcp/api/execution.py
- [ ] T049 [US1] Add input validation with structured errors to run handler in src/bioimage_mcp/api/execution.py
- [ ] T050 [US1] Add output artifact generation to run handler in src/bioimage_mcp/api/execution.py
- [ ] T051 [US1] Implement status handler in src/bioimage_mcp/api/execution.py
- [ ] T052 [US1] Register list, describe, run, status tools in src/bioimage_mcp/api/server.py

### Refactor for US1+US3

- [ ] T053 [US1] Verify params_schema contains no artifact port keys (FR-005) in describe handler
- [ ] T054 [US1] Verify JSON Schema types are correct (numbers as numbers, booleans as booleans) in describe handler

**Checkpoint**: Core discover-describe-run flow works - MVP complete

---

## Phase 4: User Story 2 - Search for Functions (Priority: P1)

**Goal**: LLM can find functions by keyword, tag, or I/O type without manual browsing

**Independent Test**: Search for "threshold" with io_out: LabelImageRef -> receive relevant segmentation functions with I/O summaries

### Tests for US2 (TDD: Write FIRST, must FAIL before implementation)

- [ ] T055 [P] [US2] RED: Contract test for search with query parameter in tests/contract/test_search.py
- [ ] T056 [P] [US2] RED: Contract test for search with io_in/io_out filters in tests/contract/test_search.py
- [ ] T057 [P] [US2] RED: Contract test for search with tags filter in tests/contract/test_search.py
- [ ] T058 [P] [US2] RED: Contract test for search I/O summaries in results in tests/contract/test_search.py
- [ ] T059 [P] [US2] RED: Contract test for search VALIDATION_FAILED when no query or keywords in tests/contract/test_search.py
- [ ] T112 [P] [US2] RED: Contract test for search VALIDATION_FAILED when BOTH query and keywords are provided in tests/contract/test_search.py

### Implementation for US2 (GREEN: Make tests pass)

- [ ] T060 [US2] Implement search handler in src/bioimage_mcp/api/discovery.py
- [ ] T061 [US2] Add query/keywords validation (exactly one required) in search handler
- [ ] T062 [US2] Add io_in/io_out filtering in search handler
- [ ] T063 [US2] Add tags filtering in search handler
- [ ] T064 [US2] Add I/O summaries to search results in search handler
- [ ] T065 [US2] Add scoring and ranking to search results in search handler
- [ ] T066 [US2] Register search tool in src/bioimage_mcp/api/server.py

**Checkpoint**: Search functionality complete - LLMs can efficiently find functions

---

## Phase 5: User Story 5 - Dry-Run Validation (Priority: P2)

**Goal**: LLM can validate tool calls before committing to execution

**Independent Test**: Call run with dry_run: true and missing inputs -> receive validation_failed status with same error as real run

### Tests for US5 (TDD: Write FIRST, must FAIL before implementation)

- [ ] T067 [P] [US5] RED: Contract test for dry_run success in tests/contract/test_run.py
- [ ] T068 [P] [US5] RED: Contract test for dry_run validation_failed with missing input in tests/contract/test_run.py
- [ ] T069 [P] [US5] RED: Contract test for dry_run validation parity with real execution in tests/contract/test_run.py

### Implementation for US5 (GREEN: Make tests pass)

- [ ] T070 [US5] Add dry_run flag handling to run handler in src/bioimage_mcp/api/execution.py
- [ ] T071 [US5] Ensure dry_run performs identical validation to real execution in run handler
- [ ] T072 [US5] Return validation_failed status with structured error on dry_run failure in run handler

**Checkpoint**: Dry-run validation works - LLMs can pre-validate before expensive operations

---

## Phase 6: User Story 6 - Artifact Metadata and Preview (Priority: P3)

**Goal**: User can inspect artifact metadata or preview text artifacts without downloading

**Independent Test**: Call artifact_info on log artifact with text_preview_bytes: 4096 -> receive metadata plus truncated preview

### Tests for US6 (TDD: Write FIRST, must FAIL before implementation)

- [ ] T073 [P] [US6] RED: Contract test for artifact_info metadata retrieval in tests/contract/test_artifact_info.py
- [ ] T074 [P] [US6] RED: Contract test for artifact_info text preview in tests/contract/test_artifact_info.py
- [ ] T075 [P] [US6] RED: Contract test for artifact_info checksums in tests/contract/test_artifact_info.py
- [ ] T076 [P] [US6] RED: Contract test for artifact_info NOT_FOUND error in tests/contract/test_artifact_info.py
- [ ] T077 [P] [US6] RED: Contract test for artifact_info image metadata (dims, dtype, shape) in tests/contract/test_artifact_info.py

### Implementation for US6 (GREEN: Make tests pass)

- [ ] T078 [US6] Implement artifact_info handler in src/bioimage_mcp/api/artifacts.py
- [ ] T079 [US6] Add metadata retrieval (mime_type, size_bytes, checksums) in artifact_info handler
- [ ] T080 [US6] Add text_preview support for safe text artifacts in artifact_info handler
- [ ] T081 [US6] Add image metadata (dims, dtype, shape) extraction in artifact_info handler
- [ ] T082 [US6] Register artifact_info tool in src/bioimage_mcp/api/server.py

**Checkpoint**: Artifact inspection works - Users can inspect without downloading

---

## Phase 7: User Story 4 - Export and Replay Workflows (Priority: P2)

**Goal**: User can record multi-step sessions and replay on different input data

**Independent Test**: Run 3 functions in session -> export -> replay with new input images -> all steps execute successfully

### Tests for US4 (TDD: Write FIRST, must FAIL before implementation)

- [ ] T083 [P] [US4] RED: Contract test for session_export basic export in tests/contract/test_session_export.py
- [ ] T084 [P] [US4] RED: Contract test for session_export external_inputs tracking in tests/contract/test_session_export.py
- [ ] T085 [P] [US4] RED: Contract test for session_export step input sources in tests/contract/test_session_export.py
- [ ] T113 [P] [US4] RED: Contract test for session_export provenance fields (tool_pack_id, tool_pack_version, lock_hash, timestamps) in tests/contract/test_session_export.py
- [ ] T117 [P] [US4] RED: Contract test for session_export dest_path allowlist enforcement (DENIED when outside allowed roots) in tests/contract/test_session_export.py
- [ ] T086 [P] [US4] RED: Contract test for session_replay basic replay in tests/contract/test_session_replay.py
- [ ] T087 [P] [US4] RED: Contract test for session_replay with new input bindings in tests/contract/test_session_replay.py
- [ ] T088 [P] [US4] RED: Contract test for session_replay missing external input error in tests/contract/test_session_replay.py
- [ ] T114 [P] [US4] RED: Contract test for session_replay VALIDATION_FAILED when a referenced function no longer exists in tests/contract/test_session_replay.py
- [ ] T089 [P] [US4] RED: Contract test for session_replay params_overrides in tests/contract/test_session_replay.py
- [ ] T090 [P] [US4] RED: Contract test for session_replay step_overrides in tests/contract/test_session_replay.py

### Implementation for US4 (GREEN: Make tests pass)

- [ ] T091 [US4] Create sessions.py module in src/bioimage_mcp/api/sessions.py
- [ ] T092 [US4] Implement session state tracking (external_inputs vs step outputs) in sessions.py
- [ ] T093 [US4] Implement session_export handler in src/bioimage_mcp/api/sessions.py
- [ ] T094 [US4] Generate WorkflowRecord with external_inputs classification in session_export
- [ ] T095 [US4] Mark step input sources with source field (external vs step) in session_export
- [ ] T096 [US4] Implement session_replay handler in src/bioimage_mcp/api/sessions.py
- [ ] T097 [US4] Add external input binding validation in session_replay
- [ ] T098 [US4] Add params_overrides support (by function id) in session_replay
- [ ] T099 [US4] Add step_overrides support (by step index) in session_replay
- [ ] T118 [US4] Enforce allowed-roots validation for SessionExportRequest.dest_path in src/bioimage_mcp/api/sessions.py (session_export handler)
- [ ] T100 [US4] Register session_export and session_replay tools in src/bioimage_mcp/api/server.py
- [ ] T101 [US4] Integrate session tracking with run handler in src/bioimage_mcp/api/execution.py

**Checkpoint**: Workflow replay works - Full reproducibility on new data

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, documentation, and final validation

### Integration Tests

- [ ] T102 [P] Integration test for full discover->describe->run flow in tests/integration/test_end_to_end.py
- [ ] T103 [P] Integration test for search->describe->run flow in tests/integration/test_end_to_end.py
- [ ] T104 [P] Integration test for multi-step session->export->replay flow in tests/integration/test_end_to_end.py
- [ ] T120 [P] Integration test for run crash -> status failed + log artifact reference in tests/integration/test_end_to_end.py
- [ ] T121 [P] Integration test for concurrent runs in one session (append-only; may interleave) in tests/integration/test_end_to_end.py

### Documentation & Validation

- [ ] T105 [P] Update existing MCP documentation to reflect 8-tool surface
- [ ] T106 [P] Validate quickstart.md examples work with implemented tools
- [ ] T107 Verify tool count is exactly 8 in server.py (SC-008)
- [ ] T115 [P] Add migration section mapping 13-tool surface -> 8-tool surface in docs/reference/tools.md (tool name + request/response changes)
- [ ] T116 [P] Apply semver bump rationale in pyproject.toml and add breaking-change note in docs/reference/tools.md

### Schema Validation

- [ ] T108 [P] Validate all function descriptions have correct JSON Schema types (SC-003)
- [ ] T109 [P] Validate artifact ports never appear inside params_schema (SC-004)

### Final Cleanup

- [ ] T110 Remove any remaining deprecated tool references from codebase
- [ ] T111 Run full test suite and verify all tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **US1+US3 (Phase 3)**: Depends on Phase 2 - MVP, must complete first
- **US2 (Phase 4)**: Depends on Phase 2 - Can parallel with US1 if team allows
- **US5 (Phase 5)**: Depends on Phase 3 (run tool) - Enhances run tool
- **US6 (Phase 6)**: Depends on Phase 2 - Can parallel with other stories
- **US4 (Phase 7)**: Depends on Phase 3 (run tool) - Needs run to work first
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1+US3 (P1)**: Foundation only - No dependencies on other stories - **MVP**
- **US2 (P1)**: Foundation only - Independent of US1
- **US5 (P2)**: Requires US1's run tool to exist
- **US6 (P3)**: Foundation only - Independent of other stories
- **US4 (P2)**: Requires US1's run tool with session_id support

### Within Each User Story (TDD Flow)

1. **RED**: Write contract tests FIRST, verify they FAIL
2. **GREEN**: Implement minimum code to make tests pass
3. **REFACTOR**: Clean up while keeping tests green

### Parallel Opportunities

**Phase 2 (Foundational)** - Maximum parallelism:
```bash
# All schema models can be defined in parallel:
Task: T004-T024 (all Pydantic models)
Task: T025-T030 (remove deprecated tools)
Task: T031 (error helpers)
```

**Phase 3 (US1+US3)** - Tests parallel, then implementation:
```bash
# All contract tests in parallel:
Task: T032-T042 (all US1 contract tests)

# Implementation after tests fail:
Task: T043-T054 (sequential with dependencies)
```

**Cross-Story Parallelism** (with team):
- US1+US3 and US2 can be developed in parallel after Phase 2
- US6 can be developed in parallel with US5 and US4

---

## Implementation Strategy

### MVP First (User Story 1+3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: US1+US3 (TDD: tests first, then implement)
4. **STOP and VALIDATE**: Test discover->describe->run flow
5. Deploy/demo if ready - **This is a functional MVP**

### Incremental Delivery

1. Setup + Foundational -> Foundation ready
2. Add US1+US3 (list/describe/run/status) -> Test independently -> **MVP!**
3. Add US2 (search) -> Test independently -> Improved discovery
4. Add US5 (dry_run) -> Test independently -> Better validation
5. Add US6 (artifact_info) -> Test independently -> Better debugging
6. Add US4 (session_export/replay) -> Test independently -> Full reproducibility
7. Polish phase -> Integration tests, docs

### TDD Workflow Per Story

```bash
# For each user story:
1. Write ALL contract tests (marked [P] - parallel)
2. Run tests - verify they FAIL (RED)
3. Implement handlers one at a time
4. Run tests after each implementation - watch them turn GREEN
5. Refactor if needed while keeping tests green
6. Move to next story
```

---

## Summary

| Phase | Story | Priority | Test Tasks | Impl Tasks | Total |
|-------|-------|----------|------------|------------|-------|
| 1 | Setup | - | 0 | 3 | 3 |
| 2 | Foundation | - | 0 | 28 | 28 |
| 3 | US1+US3 | P1 | 12 | 12 | 24 |
| 4 | US2 | P1 | 6 | 7 | 13 |
| 5 | US5 | P2 | 3 | 3 | 6 |
| 6 | US6 | P3 | 5 | 5 | 10 |
| 7 | US4 | P2 | 11 | 12 | 23 |
| 8 | Polish | - | 5 | 9 | 14 |
| **Total** | | | **42** | **79** | **121** |

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- TDD: Contract tests MUST fail before implementation begins
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All 8 tools verified at completion: list, describe, search, run, status, artifact_info, session_export, session_replay
