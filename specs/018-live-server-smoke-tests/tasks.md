---
description: "Task list for Live Server Smoke Tests implementation"
---

# Tasks: Live Server Smoke Tests

**Input**: Design documents from `/specs/018-live-server-smoke-tests/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Tests**: The smoke tests are the primary validation suite, but all implementation work MUST follow TDD (Constitution VI). Utilities/fixtures MUST be driven by failing tests first (either targeted tests under `tests/smoke/utils/test_*.py` or smoke scenario tests that exercise them).

**Organization**: Tasks are grouped by phase, with user stories enabling independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create tests/smoke/ directory structure
- [X] T002 [P] Create __init__.py files in tests/smoke/ and tests/smoke/utils/
- [X] T003 Update pytest.ini with smoke test markers (smoke_minimal, smoke_full, requires_env)
- [X] T004 Verify pytest-asyncio>=0.23 in pyproject.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T028 [P] Write failing tests for Interaction/InteractionLog schema + truncation behavior in tests/smoke/utils/test_interaction_logger.py
- [X] T029 [P] Write failing tests for TestMCPClient lifecycle, timeout behavior, diagnostics on startup failure/unresponsive server, and cleanup guarantees in tests/smoke/utils/test_mcp_client.py
- [X] T005 [P] Implement Interaction and InteractionLog Pydantic models in tests/smoke/utils/interaction_logger.py
- [X] T006 Implement InteractionLogger class with log_request, log_response, _truncate, and save methods in tests/smoke/utils/interaction_logger.py
- [X] T007 [P] Implement SmokeTestError exception class in tests/smoke/utils/mcp_client.py
- [X] T008 Implement TestMCPClient class with lifecycle management and start_with_timeout in tests/smoke/utils/mcp_client.py (server command: `bioimage-mcp serve --stdio`; default startup timeout 30s, overrideable for tests)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - CI Blocks Live-Interaction Regressions (Priority: P1) 🎯 MVP

**Goal**: Catch regressions in true end-to-end communication before merge via minimal automated suite.

**Independent Test**: Run `pytest tests/smoke/test_smoke_basic.py -m smoke_minimal -v` and verify it starts a server, performs discovery, executes a base workflow, and writes a log.

- [X] T014 [US1] Create test_smoke_discovery test in tests/smoke/test_smoke_basic.py (TDD/Red): validate `list()` summaries AND required child counts (`total`, `by_type`) for non-leaf nodes; validate `describe("base.io.bioimage.load")` response shape (separate `inputs`, `outputs`, `params_schema`) to catch protocol/schema drift (SC-005)
- [X] T015 [US1] Create test_smoke_basic_run test in tests/smoke/test_smoke_basic.py (TDD/Red): call `run(base.io.bioimage.load)` on `datasets/synthetic/test.tif`, then `run(base.xarray.squeeze)`; assert outputs are artifact references with non-empty `ref_id` and usable `uri`; enforce bounded runtime (startup <= 30s; minimal suite budget <= 120s)
- [X] T009 [P] [US1] Implement SmokeConfig dataclass in tests/smoke/conftest.py (startup_timeout_s=30, minimal_suite_budget_s=120, scenario_timeout_s=300, log_dir, minimal/full mode)
- [X] T010 [P] [US1] Implement _env_available helper function in tests/smoke/conftest.py
- [X] T011 [US1] Implement check_required_env autouse fixture in tests/smoke/conftest.py (skip with explicit reason including missing env id)
- [X] T012 [US1] Implement live_server session-scoped fixture in tests/smoke/conftest.py (starts `bioimage-mcp serve --stdio`; uses MCP Python SDK stdio client; enforces suite time budget via per-session timing; guarantees cleanup on pass/fail/timeout)
- [X] T013 [P] [US1] Implement sample_image fixture in tests/smoke/conftest.py (minimal default: `datasets/synthetic/test.tif`; full-mode default: `datasets/FLUTE_FLIM_data_tif/hMSC control.tif`; skip with explicit reason if requested dataset missing)

**Checkpoint**: User Story 1 (MVP) is fully functional and testable independently.

---

## Phase 4: User Story 2 - Developer Runs a Real Dataset Workflow (Priority: P2)

**Goal**: Validate artifact handling and end-to-end execution using real datasets.

**Independent Test**: Run `pytest tests/smoke/test_flim_phasor_live.py -m smoke_full -v` and verify it completes the full FLIM workflow with artifact refs.

- [X] T016 [US2] Implement FLIM phasor scenario in tests/smoke/test_flim_phasor_live.py (mark `smoke_full`): capability discovery (`list()`), schema fetch (`describe("base.phasorpy.phasor.phasor_from_signal")`), then `run(base.io.bioimage.load)` on `datasets/FLUTE_FLIM_data_tif/hMSC control.tif` -> `run(base.xarray.rename)` -> `run(base.phasorpy.phasor.phasor_from_signal)`; validate outputs are artifact references with non-empty `ref_id`/usable `uri`; enforce scenario timeout <= 300s; skip with explicit reason if dataset missing
- [X] T017 [US2] Implement Cellpose pipeline scenario in tests/smoke/test_cellpose_pipeline_live.py (mark `smoke_full` + `requires_env("bioimage-mcp-cellpose")`): capability discovery (`list()`), schema fetch (`describe("cellpose.models.CellposeModel.eval")`), then `run(base.io.bioimage.load)` (prefer `datasets/synthetic/test.tif`) -> `run(base.xarray.sum)` -> `run(base.io.bioimage.export)` -> `run(cellpose.models.CellposeModel.eval)`; validate outputs are artifact references with non-empty `ref_id`/usable `uri`; enforce scenario timeout <= 300s; skip with explicit reason if env/dataset missing

**Checkpoint**: Representative workflows using real datasets are validated.

---

## Phase 5: User Story 3 - Debugging Produces Actionable Logs (Priority: P3)

**Goal**: Capture full sequence of requests/responses and server diagnostics in "recording" mode.

**Independent Test**: Run a test with `--smoke-record` and confirm a structured JSON log is produced in `.bioimage-mcp/smoke_logs/` (pass or fail).

- [X] T030 [US3] Create a failing recording-mode test in tests/smoke/test_smoke_recording.py (TDD/Red): run a minimal smoke interaction with `--smoke-record` and assert a log file is written containing requests, responses, timestamps, durations, and diagnostics fields
- [X] T018 [US3] Add --smoke-record pytest option in tests/smoke/conftest.py
- [X] T019 [US3] Implement log directory creation (.bioimage-mcp/smoke_logs/) in tests/smoke/conftest.py
- [X] T020 [US3] Implement automatic log saving after each test in tests/smoke/conftest.py (always save on pass/fail/skip; one log per test invocation)
- [X] T021 [US3] Implement server stderr capture in TestMCPClient in tests/smoke/utils/mcp_client.py (store for inclusion in InteractionLog)
- [X] T022 [US3] Implement size-bounded log truncation (<= 10MB per run; see SC-004) in tests/smoke/utils/interaction_logger.py
- [X] T023 [US3] Add error_summary population on failure in tests/smoke/conftest.py (actionable hint + failing step)

**Checkpoint**: Debugging logs with full context are automatically generated.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, CI integration, and final validation.

- [X] T024 [P] Update AGENTS.md with smoke test documentation
- [X] T025 [P] Add CI workflow example to quickstart.md (Linux runner; enforce time budgets for smoke_minimal; upload `.bioimage-mcp/smoke_logs/` as artifact)
- [X] T026 Run quickstart.md validation
- [X] T027 Final code review and cleanup

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phases 3, 4, 5)**: All depend on Foundational completion.
  - US1 is the priority (P1/MVP).
  - US2 and US3 can proceed in parallel after US1 foundation or sequentially.
- **Polish (Phase 6)**: Depends on all user stories being complete.

### Parallel Opportunities

- Phase 2: Logger track (`test_interaction_logger.py`/`interaction_logger.py`: T028, T005, T006) and client track (`test_mcp_client.py`/`mcp_client.py`: T029, T007, T008) can be developed in parallel.
- Phase 3: Tests (T014, T015) can be authored before fixtures; once tests exist, config/helpers (T009, T010, T013) can be implemented in parallel.
- Phase 4: FLIM (T016) and Cellpose (T017) scenarios can be developed in parallel.
- Phase 5: Recording-mode test (T030) is authored first; then client-side capture (T021) and logger-side truncation (T022) can be done in parallel.

---

## Parallel Example: Foundational Utilities

```text
# Developer A: Logger track (TDD)
Task: "Write failing tests for Interaction/InteractionLog schema + truncation in tests/smoke/utils/test_interaction_logger.py"
Task: "Implement Interaction and InteractionLog Pydantic models in tests/smoke/utils/interaction_logger.py"
Task: "Implement InteractionLogger class... in tests/smoke/utils/interaction_logger.py"

# Developer B: Client track (TDD)
Task: "Write failing tests for TestMCPClient lifecycle, timeout behavior, and cleanup guarantees in tests/smoke/utils/test_mcp_client.py"
Task: "Implement SmokeTestError exception class in tests/smoke/utils/mcp_client.py"
Task: "Implement TestMCPClient class... in tests/smoke/utils/mcp_client.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `pytest tests/smoke/test_smoke_basic.py`

### Incremental Delivery

1. Foundation ready (Phases 1-2).
2. US1: CI-ready smoke tests (Phase 3).
3. US2: Real dataset validation (Phase 4).
4. US3: Diagnostic recording (Phase 5).
