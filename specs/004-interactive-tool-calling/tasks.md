---

description: "Task list for Interactive Tool Calling"
---

# Tasks: Interactive Tool Calling

**Input**: Design documents from `specs/004-interactive-tool-calling/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/openapi.yaml`, `quickstart.md`

**Tests**: Included by default (per repo constitution + spec requirements).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format

Every task MUST follow:

- [ ] T001 [P?] [Story?] Description with file path

Where:
- `[P]` appears only when the task is parallelizable.
- `[US#]` appears only for user-story phase tasks.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new module surfaces and test scaffolding required for interactive sessions.

- [x] T001 [P] Create sessions package directory and init in `src/bioimage_mcp/sessions/__init__.py`
- [x] T002 [P] Add session models module stub in `src/bioimage_mcp/sessions/models.py`
- [x] T003 [P] Add session store module stub in `src/bioimage_mcp/sessions/store.py`
- [x] T004 [P] Add session manager module stub in `src/bioimage_mcp/sessions/manager.py`
- [x] T005 [P] Add unit test scaffolding for sessions in `tests/unit/sessions/test_session_store.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core session persistence + wiring that MUST exist before any user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Storage + Models

- [x] T006 Extend SQLite schema with `sessions`, `session_steps`, `session_active_functions` in `src/bioimage_mcp/storage/sqlite.py`
- [x] T007 [P] Implement `Session` and `SessionStep` Pydantic models in `src/bioimage_mcp/sessions/models.py`
- [x] T008 Implement `SessionStore` CRUD (sessions, step attempts, active functions) in `src/bioimage_mcp/sessions/store.py`
- [x] T009 [P] Add store CRUD unit tests in `tests/unit/sessions/test_session_store.py`

### Session Lifecycle + TTL

- [x] T010 Implement `SessionManager` (implicit per-connection creation, resume, activity update) in `src/bioimage_mcp/sessions/manager.py`
- [x] T011 [P] Add `SessionManager` unit tests in `tests/unit/sessions/test_session_manager.py`
- [x] T012 Add session TTL configuration (e.g., `session_ttl_hours`) to `src/bioimage_mcp/config/schema.py`
- [x] T013 Add default `session_ttl_hours` loading to `src/bioimage_mcp/config/loader.py`
- [x] T014 [P] Add config unit test for TTL defaults in `tests/unit/config/test_session_ttl_config.py`

### Server Wiring

- [x] T015 Wire a shared `SessionStore`/`SessionManager` into server startup in `src/bioimage_mcp/bootstrap/serve.py`
- [x] T016 Add a helper to obtain current MCP connection/session context in `src/bioimage_mcp/api/server.py`

### Output Summaries

- [x] T017 Implement lightweight output summary helper (dtype/shape/approx bytes from ArtifactRef metadata) in `src/bioimage_mcp/api/interactive_summaries.py`
- [x] T018 [P] Add unit tests for output summaries in `tests/unit/api/test_interactive_summaries.py`

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Step-by-Step Image Analysis (Priority: P1) 🎯 MVP

**Goal**: Execute tools one-by-one, immediately observe artifact refs + lightweight summaries, and retain a session step history.

**Independent Test**: Execute 3+ interactive calls in a single session and verify each step is recorded and returns `session_id`.

### Tests (write first)

- [x] T019 [P] [US1] Add integration test for step-by-step `call_tool` success path in `tests/integration/test_interactive_call_tool.py`

### Implementation

- [x] T020 [US1] Implement `InteractiveExecutionService.call_tool()` (create run, persist step attempt, return summaries, support async polling via `run_id`/`taskId`) in `src/bioimage_mcp/api/interactive.py`
- [x] T021 [US1] Add MCP tool `call_tool` that routes to `InteractiveExecutionService` in `src/bioimage_mcp/api/server.py`
- [x] T022 [US1] Persist successful interactive step attempts (including `run_id`, outputs, log ref) in `src/bioimage_mcp/sessions/store.py`
- [x] T023 [US1] Ensure `call_tool` responses include `session_id` in `src/bioimage_mcp/api/server.py`

**Checkpoint**: US1 is independently functional and testable.

---

## Phase 4: User Story 2 — Error Recovery and Retry (Priority: P1)

**Goal**: Provide actionable structured errors and enable micro-retries without losing session history; only the successful retry becomes canonical for export.

**Independent Test**: Trigger (a) invalid params preflight and (b) runtime failure, then retry successfully and verify history contains both attempts.

### Tests (write first)

- [x] T024 [P] [US2] Add integration tests for invalid params vs runtime error transport in `tests/integration/test_interactive_errors.py`
- [x] T025 [P] [US2] Add integration test for retry semantics and canonical selection in `tests/integration/test_interactive_retry_canonical.py`

### Implementation

- [x] T026 [US2] Implement preflight validation errors as JSON-RPC invalid params (`-32602`) for `call_tool` in `src/bioimage_mcp/api/server.py`
- [x] T027 [US2] Implement runtime execution errors as tool result with `isError: true` and `log_ref` in `src/bioimage_mcp/api/interactive.py`
- [x] T028 [US2] Record failed attempts (with structured `error_json`) in `src/bioimage_mcp/sessions/store.py`
- [x] T029 [US2] Implement canonical attempt selection (last successful attempt per logical step) in `src/bioimage_mcp/sessions/store.py`

**Checkpoint**: US2 is independently functional and testable.

---

## Phase 5: User Story 3 — Selective Tool Activation (Priority: P2)

**Goal**: Allow activating a subset of manifest functions per session, emit tool list change notifications, and reduce visible tools for clients that support dynamic discovery.

**Independent Test**: Activate a small set of fn IDs and verify tool discovery reflects only the active set; deactivate and verify tools are hidden again.

### Tests (write first)

- [x] T030 [P] [US3] Add integration test for activation state persistence in `tests/integration/test_interactive_activation_store.py`
- [x] T031 [P] [US3] Add integration test for tool list filtering + list_changed notification in `tests/integration/test_interactive_tool_activation.py`

### Implementation

- [x] T032 [US3] Add `activate_functions` MCP tool (persist set, update last_activity, emit list_changed, include `session_id` in response) in `src/bioimage_mcp/api/server.py`
- [x] T033 [US3] Add `deactivate_functions` MCP tool (persist set, emit list_changed, include `session_id` in response) in `src/bioimage_mcp/api/server.py`
- [x] T034 [US3] Implement per-session active function persistence APIs in `src/bioimage_mcp/sessions/store.py`
- [x] T035 [US3] Filter per-session tool discovery to active functions in `src/bioimage_mcp/api/server.py`

**Checkpoint**: US3 is independently functional and testable.

---

## Phase 6: User Story 4 — Workflow Export and Replay (Priority: P2)

**Goal**: Export an interactive session to a reproducible `workflow-record-json` (canonical steps only) and replay it on a different input.

**Independent Test**: Execute a session with retries, export, then replay using `ExecutionService.replay_workflow()` and verify it runs.

### Tests (write first)

- [x] T036 [P] [US4] Add integration test for `export_session` canonical-only export in `tests/integration/test_export_session.py`
- [x] T037 [P] [US4] Add integration test for replaying exported session workflow in `tests/integration/test_replay_exported_session.py`
- [x] T051 [P] [US4] Add integration test for replay failure when session artifacts are missing in `tests/integration/test_replay_exported_session.py`

### Implementation

- [x] T038 [US4] Add MCP tool `export_session` (write `workflow-record-json` NativeOutputRef, include `session_id` in response) in `src/bioimage_mcp/api/server.py`
- [x] T039 [US4] Build exported workflow spec from canonical session steps in `src/bioimage_mcp/api/interactive.py`
- [x] T040 [US4] Persist export state/metadata (e.g., `exported_at`) in `src/bioimage_mcp/sessions/store.py`

**Checkpoint**: US4 is independently functional and testable.

---

## Phase 7: User Story 5 — Compatibility Fallback for Static Clients (Priority: P3)

**Goal**: Support interactive calling for clients without dynamic tool discovery via the `call_tool` wrapper (including `dry_run=true`).

**Independent Test**: Use only `call_tool` (no activation/dynamic tools) to validate, execute, and receive structured errors with `session_id`.

### Tests (write first)

- [x] T041 [P] [US5] Add integration test for `call_tool(dry_run=true)` validation-only behavior in `tests/integration/test_call_tool_dry_run.py`

### Implementation

- [x] T042 [US5] Implement `dry_run` parameter handling (validate only; no run created) in `src/bioimage_mcp/api/interactive.py`
- [x] T043 [US5] Ensure calling non-activated functions works via wrapper (clear messaging if direct call blocked) in `src/bioimage_mcp/api/server.py`

**Checkpoint**: US5 is independently functional and testable.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Requirements that cut across stories (persistence robustness, tasks support, docs alignment, performance discipline).

- [x] T044 [P] Add `resume_session(session_id)` MCP tool to reattach persisted sessions (include `session_id` in response) in `src/bioimage_mcp/api/server.py`
- [x] T045 Add session cleanup (TTL expiry) execution path via periodic sweep in `src/bioimage_mcp/sessions/manager.py`
- [x] T046 [P] Add integration test for resume after restart semantics in `tests/integration/test_resume_session.py`
- [ ] T047 Add MCP Tasks support (map `taskId` to `run_id` for interactive calls) in `src/bioimage_mcp/api/server.py`
- [x] T048 [P] Add contract test coverage for interactive contracts in `tests/contract/test_interactive_tool_calling_contract.py`
- [x] T049 [P] Update quickstart for interactive calling with examples in `specs/004-interactive-tool-calling/quickstart.md`
- [x] T050 Run full test suite and fix any interactive-feature regressions in `tests/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories
- **User Stories (Phase 3–7)**: All depend on Foundational
- **Polish (Phase 8)**: Depends on the user stories you intend to ship

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 only
- **US2 (P1)**: Depends on US1 (uses `call_tool` surface + session step recording)
- **US3 (P2)**: Depends on Phase 2 only (activation + discovery filtering)
- **US4 (P2)**: Depends on US1 + US2 (needs canonical step semantics)
- **US5 (P3)**: Depends on US1 (wrapper exists) and complements US3

---

## Parallel Execution Examples

### Parallel Example: US1

```bash
# Tests and implementation can be split across files.
# Parallel work items:
# - T019 tests/integration/test_interactive_call_tool.py
# - T020 src/bioimage_mcp/api/interactive.py
# - T021 src/bioimage_mcp/api/server.py
# - T017 src/bioimage_mcp/api/interactive_summaries.py (if not done already)
```

### Parallel Example: US2

```bash
# Parallel work items:
# - T024 tests/integration/test_interactive_errors.py
# - T025 tests/integration/test_interactive_retry_canonical.py
# - T028 src/bioimage_mcp/sessions/store.py
```

### Parallel Example: US3

```bash
# Parallel work items:
# - T030 tests/integration/test_interactive_activation_store.py
# - T031 tests/integration/test_interactive_tool_activation.py
# - T034 src/bioimage_mcp/sessions/store.py
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 + Phase 2
2. Complete US1 (Phase 3)
3. Stop and validate via `tests/integration/test_interactive_call_tool.py`

### Incremental Delivery

- Add US2 next (retry + error transport), then US3 (activation), then US4 (export/replay), then US5 (dry-run + static client fallback).
