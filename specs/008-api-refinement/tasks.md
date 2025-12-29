# Implementation Tasks: API Refinement & Permission System

**Feature Branch**: `008-api-refinement`
**Spec**: `specs/008-api-refinement/spec.md`

## Phase 1: Setup & Data Models
**Goal**: Initialize configuration, data models, and clean up legacy tools.

- [x] T001 Define `PermissionMode`, `OverwritePolicy`, and `PermissionDecision` models in `src/bioimage_mcp/api/schemas.py`
- [x] T002 Define `ToolHierarchyNode` and `ListToolsResponse` models in `src/bioimage_mcp/api/schemas.py`
- [x] T003 Define `ScoredFunction`, `SearchFunctionsRequest`, and `SearchFunctionsResponse` models in `src/bioimage_mcp/api/schemas.py`
- [x] T004 Update `BioimageMCPConfig` to include permissions and agent_guidance settings in `src/bioimage_mcp/config/schema.py`
- [x] T005 Remove `tools/builtin` directory and its contents (Tool Consolidation Prerequisite)

## Phase 2: Foundational (Blocking)
**Goal**: Establish the base environment and canonical naming.

- [x] T006 Update `tools/base/manifest.yaml` to include all consolidated functions with canonical names (`base.skimage.filters.gaussian` etc.)
- [x] T007 [P] Create `src/bioimage_mcp/api/permissions.py` module with empty service class
- [x] T008 [P] Create `src/bioimage_mcp/registry/search.py` module with empty ranking logic
- [x] T009 [P] Create `src/bioimage_mcp/registry/index.py` module with empty hierarchy logic

## Phase 3: User Story 1 - Seamless File Access (Permissions)
**Goal**: Implement dynamic permission inheritance and overwrite protection.
**Independent Test**: `tests/integration/test_inherit_permissions.py`

### Phase 3a: Contract Tests (TDD Red Phase - must complete before 3b)
- [x] T010 [US1] Create contract test `tests/contract/test_permissions_schema.py` for permission models

### Phase 3b: Implementation (TDD Green Phase - requires T010 complete)
- [x] T011 [US1] Implement `PermissionService.list_roots` logic using MCP client capability in `src/bioimage_mcp/api/permissions.py`
- [x] T012 [US1] Implement `PermissionService.check_permission` logic (inherit vs explicit modes) in `src/bioimage_mcp/api/permissions.py`
- [x] T013 [US1] Implement `elicit_confirmation` logic for `on_overwrite: ask` in `src/bioimage_mcp/api/permissions.py`
- [x] T014 [US1] Update `src/bioimage_mcp/config/fs_policy.py` to use `PermissionService`
- [x] T015 [US1] Integrate `PermissionService` initialization and logging into `src/bioimage_mcp/api/server.py`
- [x] T016 [US1] Create integration test `tests/integration/test_inherit_permissions.py` to verify root inheritance and allow/deny logic

## Phase 4: User Story 2 - Unified Tool Environment
**Goal**: Verify all tools function in `base` environment without `builtin`.
**Independent Test**: `tests/integration/test_base_consolidation.py`

- [x] T017 [US2] Verify `base` environment creation and function loading in `src/bioimage_mcp/bootstrap/environments.py`
- [x] T018 [US2] Create integration test `tests/integration/test_base_consolidation.py` running a workflow with previously cross-env functions
- [x] T019 [US2] Update `src/bioimage_mcp/config/loader.py` to support canonical naming validation

## Phase 5: User Story 3 - Hierarchical Tool Discovery
**Goal**: Implement navigable tool hierarchy with shortcuts.
**Independent Test**: `tests/contract/test_discovery_hierarchy.py`

### Phase 5a: Contract Tests (TDD Red Phase - must complete before 5b)
- [x] T020 [US3] Create contract test `tests/contract/test_discovery_hierarchy.py` for `list_tools` output structure

### Phase 5b: Implementation (TDD Green Phase - requires T020 complete)
- [x] T021 [US3] Implement `ToolIndex.build_hierarchy` with auto-expansion logic in `src/bioimage_mcp/registry/index.py`
- [x] T022 [US3] Implement `ToolIndex.flatten_tools` logic in `src/bioimage_mcp/registry/index.py`
- [x] T023 [US3] Update `list_tools` handler in `src/bioimage_mcp/api/discovery.py` to support `path`, `paths`, and `flatten` arguments
- [x] T024 [US3] Verify pagination support for hierarchical listings in `src/bioimage_mcp/api/discovery.py`

## Phase 6: User Story 4 - Multi-Keyword Search
**Goal**: Implement weighted ranking search.
**Independent Test**: `tests/unit/registry/test_search_ranking.py`

### Phase 6a: Contract Tests (TDD Red Phase - must complete before 6b)
- [x] T025 [US4] Create unit test `tests/unit/registry/test_search_ranking.py` for ranking algorithm

### Phase 6b: Implementation (TDD Green Phase - requires T025 complete)
- [x] T026 [US4] Implement `SearchIndex.tokenize` (n-grams) in `src/bioimage_mcp/registry/search.py`
- [x] T027 [US4] Implement `SearchIndex.rank` (BM25 + weights) in `src/bioimage_mcp/registry/search.py`
- [x] T028 [US4] Update `search_functions` handler in `src/bioimage_mcp/api/discovery.py` to use `SearchIndex`

## Phase 7: User Story 5 - Batch Function Descriptions
**Goal**: Enable bulk schema retrieval.
**Independent Test**: `tests/contract/test_batch_describe.py`

### Phase 7a: Contract Tests (TDD Red Phase - must complete before 7b)
- [x] T029 [US5] Create contract test `tests/contract/test_batch_describe.py`

### Phase 7b: Implementation (TDD Green Phase - requires T029 complete)
- [x] T030 [US5] Update `describe_function` in `src/bioimage_mcp/api/discovery.py` to handle `fn_ids` list
- [x] T031 [US5] Ensure backward compatibility for single `fn_id` in `src/bioimage_mcp/api/discovery.py`

## Phase 8: User Story 6 - Execution & Guidance
**Goal**: Consolidate execution API and add workflow hints.
**Independent Test**: `tests/contract/test_run_function.py`

### Phase 8a: Contract Tests (TDD Red Phase - must complete before 8b)
- [x] T032 [US6] Create contract test `tests/contract/test_run_function.py` checking for `workflow_hint`

### Phase 8b: Implementation (TDD Green Phase - requires T032 complete)
- [x] T033 [US6] Implement `run_function` handler in `src/bioimage_mcp/api/execution.py`
- [x] T034 [US6] Add logic to check activation status and inject `workflow_hint` in `src/bioimage_mcp/api/execution.py`
- [x] T035 [US6] Remove `call_tool` handler and routing from `src/bioimage_mcp/api/server.py`
- [x] T036 [US6] Register `run_function` as MCP tool in `src/bioimage_mcp/api/server.py`

## Phase 9: Polish & Cross-Cutting
**Goal**: Final verification and documentation.

- [x] T037 Update `README.md` with new configuration options and migration guide
- [x] T038 Run full validation workflow `scripts/validate_pipeline.py` (update script if needed for new API)
- [x] T039 Verify `server.log` contains proper permission audit logs

## Dependencies
- Phase 1 & 2 must be completed before any User Story phases.
- Within each User Story phase, sub-phase "a" (contract tests) MUST complete before sub-phase "b" (implementation) per TDD.
- US1 (Permissions) blocks US2 (Environment) testing if I/O is involved.
- US3, US4, US5 can be executed in parallel at the phase level (different developers can work on different User Stories simultaneously), but each maintains internal TDD sequencing.
- US6 depends on `server.py` stability.

## Implementation Strategy
- **MVP**: Complete Phase 1, 2, 3, and 8 (Run Function) to restore basic functionality with new permissions.
- **Enhancement**: Follow with Phase 5 (Discovery) and Phase 6 (Search).
- **Refinement**: Finish with Phase 7 (Batch) and Phase 9 (Polish).
