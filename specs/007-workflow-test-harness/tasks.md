---
description: "Task list for Axis Manipulation Tools, LLM Guidance Hints & Workflow Test Harness"
---

# Tasks: 007-workflow-test-harness

**Input**: Design documents from `specs/007-workflow-test-harness/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md
**Tests**: TDD approach mandated by Constitution VI (tests written first; red → green → refactor)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency wiring.

- [X] T001 Create directory `tests/integration/workflow_cases/`
- [X] T002 Add `pytest-asyncio` to `pyproject.toml` under `[project.optional-dependencies].dev` (PyYAML is already a core dependency as `PyYAML`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and schema updates required by all stories.

**⚠️ CRITICAL**: No user story implementation work can begin until this phase is complete.

### Tests for Foundational ⚠️ (Red)

- [X] T035 [P] [RED] Add failing contract tests for ArtifactRef metadata requirements in `tests/contract/test_artifact_metadata_contract.py` (FR-020..FR-023)
- [X] T036 [P] [RED] Add failing contract/unit tests for `LLMHints` + related response models in `tests/contract/test_hints_schema.py` (US6/7/8)
- [X] T037 [P] [RED] Add failing unit tests for axis tool param validation models in `tests/unit/base/test_axis_ops.py` (US1/2/3)

### Implementation for Foundational (Green)

- [X] T003 [P] Update `ArtifactRef` metadata schema in `src/bioimage_mcp/artifacts/models.py` (US9, FR-020..FR-023)
- [X] T038 [P] Extend image metadata extraction in `src/bioimage_mcp/artifacts/metadata.py` to populate `axes_inferred`, `physical_pixel_sizes`, and `file_metadata` (FR-020..FR-023)
- [X] T039 [P] Ensure artifact metadata is attached to both success and error tool responses in the API layer (FR-023)

- [X] T004 [P] Create `src/bioimage_mcp/api/schemas.py` with `LLMHints` and related pydantic models (US6/7/8)
- [X] T005 [P] Create `AxisMapping` and `AxisToolParams` models in `tools/base/bioimage_mcp_base/axis_ops.py` (US1/2/3)

**Checkpoint**: Foundational models + contracts exist; tests are in place.

---

## Phase 3: User Story 4 - Automated Workflow Test Harness (P0)

**Goal**: Enable automated testing of MCP workflows to support TDD for subsequent stories.

**Independent Test**: Run `pytest tests/integration/test_workflows.py`

### Tests for User Story 4 ⚠️ (Red)

- [X] T010 [P] [US4] Write failing workflow harness tests in `tests/integration/test_workflows.py` including FR-014 golden path sequence: `search_functions("phasor FLIM")` → `activate_functions([...])` → `describe_function("base.relabel_axes")` → `call_tool("base.relabel_axes")` → `call_tool("base.phasor_from_flim")`
- [X] T040 [P] [US4] Add failing contract tests validating YAML workflow testcase schema in `tests/contract/test_workflow_testcase_schema.py` (schema source: `specs/007-workflow-test-harness/contracts/workflow-testcase.yaml`)

### Implementation for User Story 4 (Green)

- [X] T006 [P] [US4] Create `MCPTestClient` class in `tests/integration/mcp_test_client.py` implementing all 5 FR-009 operations: `list_tools()`, `search_functions()`, `activate_functions()`, `describe_function()`, `call_tool()`
- [X] T007 [P] [US4] Implement `MockExecutor` logic in `tests/integration/mcp_test_client.py`
- [X] T008 [P] [US4] Implement YAML test case loader in `tests/integration/conftest.py` (validate cases against the workflow testcase schema)
- [X] T009 [US4] Register `mcp_test_client` and `mock_executor` fixtures in `tests/integration/conftest.py`

**Checkpoint**: Test harness operational; mock mode + schema validation works.

---

## Phase 4: User Story 1 - Axis Relabeling (P0) 🎯 MVP

**Goal**: Enable relabeling of axes (e.g., Z to T) for FLIM workflows.

**Independent Test**: `test_relabel_axes` in `tests/unit/base/test_axis_ops.py`

### Tests for User Story 1 ⚠️ (Red)

- [X] T011 [P] [US1] Create contract tests for `relabel_axes` in `tests/contract/test_axis_tools_schema.py`
- [X] T012 [P] [US1] Create unit tests for `relabel_axes` in `tests/unit/base/test_axis_ops.py` (atomic rename, error messages per NFR-004, OME metadata updates per FR-007, and `physical_pixel_sizes` remapping where applicable per FR-006)

### Implementation for User Story 1 (Green)

- [X] T013 [US1] Implement `relabel_axes` function in `tools/base/bioimage_mcp_base/axis_ops.py`
- [X] T014 [US1] Register `base.relabel_axes` in `tools/base/manifest.yaml`
- [X] T015 [US1] Create YAML test case `tests/integration/workflow_cases/axis_manipulation.yaml` with relabel scenarios

**Checkpoint**: Relabeling tool works and is tested.

---

## Phase 5: User Story 2 - Dimension Manipulation (P0)

**Goal**: Squeeze and expand dimensions for pipeline compatibility.

**Independent Test**: `test_squeeze` and `test_expand_dims` in `tests/unit/base/test_axis_ops.py`

### Tests for User Story 2 ⚠️ (Red)

- [X] T016 [P] [US2] Create contract tests for `squeeze` and `expand_dims` in `tests/contract/test_axis_tools_schema.py`
- [X] T017 [P] [US2] Create unit tests for `squeeze` and `expand_dims` in `tests/unit/base/test_axis_ops.py` (metadata updates per FR-006/FR-007 and error messages per NFR-004)

### Implementation for User Story 2 (Green)

- [X] T018 [US2] Implement `squeeze` and `expand_dims` in `tools/base/bioimage_mcp_base/axis_ops.py`
- [X] T019 [US2] Register `base.squeeze` and `base.expand_dims` in `tools/base/manifest.yaml`
- [X] T020 [US2] Update `tests/integration/workflow_cases/axis_manipulation.yaml` with dimension tests

---

## Phase 6: User Story 3 - Axis Reordering (P2)

**Goal**: Move and swap axes for algorithm requirements.

**Independent Test**: `test_moveaxis` and `test_swap_axes` in `tests/unit/base/test_axis_ops.py`

### Tests for User Story 3 ⚠️ (Red)

- [X] T021 [P] [US3] Create contract tests for `moveaxis` and `swap_axes` in `tests/contract/test_axis_tools_schema.py`
- [X] T022 [P] [US3] Create unit tests for `moveaxis` and `swap_axes` in `tests/unit/base/test_axis_ops.py` (data reorder invariants, `physical_pixel_sizes` reordering per FR-006, OME metadata updates per FR-007, and error messages per NFR-004)

### Implementation for User Story 3 (Green)

- [X] T023 [US3] Implement `moveaxis` and `swap_axes` in `tools/base/bioimage_mcp_base/axis_ops.py`
- [X] T024 [US3] Register `base.moveaxis` and `base.swap_axes` in `tools/base/manifest.yaml`
- [X] T025 [US3] Update `tests/integration/workflow_cases/axis_manipulation.yaml` with reordering tests

---

## Phase 7: User Stories 6, 7, 8 - LLM Hints Integration (P1/P2)

**Goal**: Provide structured guidance (inputs, next steps, errors) to LLMs.

**Independent Test**: `tests/contract/test_hints_schema.py`

### Tests for LLM Hints ⚠️ (Red)

- [X] T026 [P] [US6/7/8] Expand schema validation tests for hints in `tests/contract/test_hints_schema.py` (describe_function + call_tool success + call_tool error)

### Implementation for LLM Hints (Green)

- [X] T027 [US6] Update `DiscoveryService.describe_function` in `src/bioimage_mcp/api/discovery.py` to inject hints and include FR-016 outputs schema (type, description for each output)
- [X] T028 [US7] Update `ToolService.call_tool` in `src/bioimage_mcp/api/tools.py` to return success hints
- [X] T029 [US8] Update `ToolService.call_tool` in `src/bioimage_mcp/api/tools.py` to handle error hints including SC-010 requirement: axis errors return `suggested_fix` with `fn_id=base.relabel_axes`
- [X] T030 [US6] Add hints to tool definitions in `tools/base/manifest.yaml` including `supported_storage_types` per FR-015/FR-019

---

## Phase 8: User Story 5 - Systematic Tool Validation (P2)

**Goal**: Ensure all registered tools have valid schemas.

- [X] T031 [US5] Add parametrized schema validation test for all registered functions (generic registry-wide test, not axis-only)

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T032 [P] Update documentation in `docs/reference/tools.md` with new axis tools
- [X] T041 [P] Add/verify `replay_workflow` workflow harness coverage (integration test proving record→replay succeeds) (Constitution IV)
- [X] T042 [P] Verify NFR-002 time budgets for workflow tests in both mock and real modes using `pytest --durations=20`; add pytest markers `@pytest.mark.timeout(10)` for mock, `@pytest.mark.timeout(60)` for real
- [X] T043 [P] Verify NFR-003 orchestration coverage target (>=80% in mock mode) using `pytest --cov=src/bioimage_mcp/api --cov-report=term-missing` and assert coverage >= 80%
- [X] T044 [P] Implement `storage_type` handling in orchestrator: detect per-tool supported storage types from manifest, auto-materialize zarr-temp to OME-TIFF when tool requires `file` storage (per spec.md "Cross-Environment Artifact Handling" MVP scope)
- [X] T033 Run full validation suite (all tests, linting)
- [X] T034 [P] Verify performance criteria (<1s for axis tools) (NFR-001) - unit tests complete in 0.40s

---

## Dependencies & Execution Order

1. **Phase 1 (Setup)** is prerequisite wiring.
2. **Phase 2 (Foundational)** blocks all story implementation.
3. **US4 (Test Harness)** runs early so subsequent work can be integration-tested.
4. **US1/US2/US3 (Axis Tools)** can proceed after Phase 2; keep per-story test tasks immediately before implementation.
5. **US6-8 (Hints)** can run in parallel with Axis Tools once foundational schemas exist.

## Implementation Strategy

1. **Red first**: write failing tests for each phase/story before writing implementation.
2. **MVP**: implement `base.relabel_axes` (US1) + golden path workflow using `base.phasor_from_flim`.
3. **Expand**: add remaining axis tools (US2, US3).
4. **Refine**: add LLM hints (US6-8) and rich metadata (US9).
