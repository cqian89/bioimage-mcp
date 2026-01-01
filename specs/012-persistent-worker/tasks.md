# Tasks: 012-persistent-worker

Transition from one-shot subprocess execution to persistent worker subprocesses with memory artifacts, delegated materialization, and NDJSON IPC protocol.

## Task Format
```
- [ ] [TaskID] [P?] [Story?] Description with file path
```
- **[P]**: Parallelizable (different files, no dependencies)
- **[Story]**: User story label (US1-US5) for story-specific tasks only

---

## Phase 1: Setup

- [X] T001 [P] Create worker IPC contract file at `specs/012-persistent-worker/contracts/worker-ipc.yaml`
- [X] T002 [P] Create worker resilience test file stub at `tests/integration/test_worker_resilience.py`
- [X] T003 [P] Create persistent worker test file stub at `tests/integration/test_persistent_worker.py`
- [X] T004 [P] Create worker IPC unit test file stub at `tests/unit/runtimes/test_worker_ipc.py`

---

## Phase 2: Foundational (BLOCKING)

### Configuration Schema
- [X] T005 Write failing test for worker config settings in `tests/unit/config/test_schema.py`
- [X] T006 Add worker settings to ConfigSchema in `src/bioimage_mcp/config/schema.py` (worker_timeout_seconds=600, max_workers=8, session_timeout_seconds=1800)
- [X] T007 Verify worker config test passes

### IPC Message Types
- [X] T008 Write failing contract test for IPC message schemas in `tests/contract/test_worker_ipc_schema.py`
- [X] T009 Create `src/bioimage_mcp/runtimes/worker_ipc.py` with Pydantic models (ExecuteRequest, ExecuteResponse, MaterializeRequest, MaterializeResponse, EvictRequest, EvictResponse, ShutdownRequest, ShutdownResponse)
- [X] T010 Add NDJSON framing helpers (encode_message, decode_message) to `src/bioimage_mcp/runtimes/worker_ipc.py`
- [X] T011 Verify IPC contract tests pass

### Worker State Enum
- [X] T012 Write failing test for WorkerState enum in `tests/unit/runtimes/test_worker_ipc.py`
- [X] T013 Add WorkerState enum to `src/bioimage_mcp/runtimes/worker_ipc.py` (spawning, ready, busy, terminated)
- [X] T014 Verify WorkerState test passes

### Tool Entrypoint Update
- [X] T015 Write failing test for NDJSON loop in base tool entrypoint in `tests/integration/test_persistent_worker.py`
- [X] T016 Update `tools/base/bioimage_mcp_base/entrypoint.py` to NDJSON loop (stdin read, dispatch, stdout write)
- [X] T017 Add execute handler in `tools/base/bioimage_mcp_base/entrypoint.py`
- [X] T018 Verify NDJSON loop test passes

---

## Phase 3: User Story 1 - Sequential Tool Calls Without Startup Overhead (P1) 🎯 MVP

**Goal**: Eliminate conda activation overhead; workers persist across calls; second call 5x faster than cold-start

### Tests First (TDD)
- [X] T019 [US1] Write failing test for PID reuse across sequential calls in `tests/integration/test_persistent_worker.py`
- [X] T020 [US1] Write failing test for warm/cold latency ratio (target 5x speedup) in `tests/integration/test_persistent_worker.py` (mark absolute <200ms threshold as non-gating/local-only)
- [X] T093 [US1] Write failing test for per-worker request queueing (FR-015) in `tests/integration/test_persistent_worker.py`
- [X] T095 [US1] Write failing test for max worker limit enforcement (FR-016) in `tests/integration/test_persistent_worker.py`
- [X] T097 [US1] Write failing test for per-operation timeout enforcement (FR-017) in `tests/integration/test_persistent_worker.py`

### Subprocess Spawning
- [X] T021 [US1] Create WorkerProcess class in `src/bioimage_mcp/runtimes/persistent.py` (subprocess.Popen with stdin=PIPE, stdout=PIPE, stderr=PIPE)
- [X] T022 [US1] Add stdin/stdout pipe handling in `src/bioimage_mcp/runtimes/persistent.py`
- [X] T023 [US1] Add stderr capture thread in `src/bioimage_mcp/runtimes/persistent.py`

### Worker Management
- [X] T024 [US1] Create WorkerManager class in `src/bioimage_mcp/runtimes/persistent.py` (registry, get_or_spawn, send_command)
- [X] T025 [US1] Add worker lifecycle tracking (spawning -> ready -> busy -> ready) in `src/bioimage_mcp/runtimes/persistent.py`
- [X] T094 [US1] Implement per-worker request queue in `src/bioimage_mcp/runtimes/persistent.py` (ensure one request at a time per worker)
- [X] T096 [US1] Implement max worker limit enforcement and queueing in WorkerManager in `src/bioimage_mcp/runtimes/persistent.py`
- [X] T098 [US1] Implement per-operation timeout enforcement and worker termination on timeout in `src/bioimage_mcp/runtimes/persistent.py`

### Execute Command
- [X] T026 [US1] Add execute command dispatch in `src/bioimage_mcp/runtimes/persistent.py` (send ExecuteRequest, await ExecuteResponse)
- [X] T027 [US1] Update `src/bioimage_mcp/runtimes/executor.py` to use WorkerManager for persistent pipes

### Verification
- [X] T028 [US1] Verify PID reuse test passes
- [X] T029 [US1] Verify warm/cold latency ratio test passes

---

## Phase 4: User Story 2 - Memory Artifact Retention Between Calls (P1) 🎯 MVP

**Goal**: mem:// artifacts stay in worker process memory without disk I/O; data accessed directly from memory

### Tests First (TDD)
- [X] T030 [US2] Write failing test for memory artifact creation in `tests/integration/test_persistent_worker.py`
- [X] T031 [US2] Write failing test to verify no disk I/O in artifact store for mem:// transfers in `tests/integration/test_persistent_worker.py`
- [X] T089 [US2] Write failing test for explicit artifact eviction (FR-010) in `tests/integration/test_persistent_worker.py`

### Memory Artifact Store in Worker
- [X] T032 [US2] Add in-memory artifact storage dict to `tools/base/bioimage_mcp_base/entrypoint.py`
- [X] T033 [US2] Update execute handler to store outputs with mem:// URIs in `tools/base/bioimage_mcp_base/entrypoint.py`
- [X] T034 [US2] Add artifact retrieval from memory in `tools/base/bioimage_mcp_base/entrypoint.py`
- [X] T090 [US2] Add eviction handler in `tools/base/bioimage_mcp_base/entrypoint.py` (remove from memory dict)

### Eviction Logic
- [X] T091 [US2] Add eviction command dispatch in `src/bioimage_mcp/runtimes/persistent.py`
- [X] T092 [US2] Update ArtifactStore to trigger worker eviction on `delete_artifact` for mem:// in `src/bioimage_mcp/storage/artifact_store.py`

### mem:// URI Scheme
- [X] T035 [US2] Add mem:// URI parsing helper in `src/bioimage_mcp/artifacts/reference.py` (parse session_id, env_id, artifact_id)
- [X] T036 [US2] Update ArtifactReference model to support storage_type="memory" in `src/bioimage_mcp/artifacts/reference.py`

### Core Routing
- [X] T037 [US2] Update ArtifactStore to route mem:// access to owning worker in `src/bioimage_mcp/storage/artifact_store.py`
- [X] T038 [US2] Add worker routing logic in WorkerManager in `src/bioimage_mcp/runtimes/persistent.py`

### Verification
- [X] T039 [US2] Verify memory artifact creation test passes
- [X] T040 [US2] Verify no disk I/O in artifact store for mem:// transfers test passes

---

## Phase 5: User Story 3 - Cross-Environment Data Handoff (P2)

**Goal**: Automatic materialization when mem:// artifact crosses environments; output in OME-Zarr or OME-TIFF

### Tests First (TDD)
- [X] T041 [US3] Write failing test for cross-env handoff in `tests/integration/test_persistent_worker.py`
- [X] T042 [US3] Write failing test for automatic materialization in `tests/integration/test_persistent_worker.py`
- [X] T101 [US3] Write failing test for cleanup of partial files on worker death during materialization (U2) in `tests/integration/test_worker_resilience.py`

### Materialize Command
- [X] T043 [US3] Add materialize handler in `tools/base/bioimage_mcp_base/entrypoint.py` (export mem:// to OME-Zarr/OME-TIFF, fallback OME-TIFF)
- [X] T099 [US3] Update MaterializeRequest schema to include `format` negotiation (OME-Zarr, OME-TIFF) in `src/bioimage_mcp/runtimes/worker_ipc.py` (default OME-TIFF)
- [X] T100 [US3] Update materialize handler to use requested format and bioio writers in `tools/base/bioimage_mcp_base/entrypoint.py`
- [X] T044 [US3] Add materialize command dispatch in `src/bioimage_mcp/runtimes/persistent.py` (send MaterializeRequest, await MaterializeResponse)
- [X] T102 [US3] Implement cleanup of partial files in WorkerManager/ArtifactStore in `src/bioimage_mcp/runtimes/persistent.py`

### Cross-Env Trigger
- [X] T045 [US3] Add cross-env detection logic in `src/bioimage_mcp/api/execution.py` (detect env mismatch)
- [X] T046 [US3] Add automatic materialization trigger in `src/bioimage_mcp/api/execution.py` (call materialize before cross-env call)

### Remove bioio from Core (Constitution III compliance)
- [X] T047 [US3] Remove bioio imports from `src/bioimage_mcp/api/execution.py`
- [X] T048 [US3] Remove bioio imports from `src/bioimage_mcp/api/artifacts.py`
- [X] T049 [US3] Verify no bioio references in `src/bioimage_mcp/` (grep check)

### Verification
- [X] T050 [US3] Verify cross-env handoff test passes
- [X] T051 [US3] Verify automatic materialization test passes

---

## Phase 6: User Story 4 - Graceful Worker Crash Recovery (P2)

**Goal**: Detect crash within 5s; invalidate mem:// artifacts; auto-spawn new worker; clear error messages

### Tests First (TDD)
- [X] T052 [US4] Write failing test for crash detection in `tests/integration/test_worker_resilience.py`
- [X] T053 [US4] Write failing test for artifact invalidation in `tests/integration/test_worker_resilience.py`
- [X] T054 [US4] Write failing test for automatic respawn in `tests/integration/test_worker_resilience.py`

### Process Health Monitoring
- [X] T055 [US4] Add process health check in `src/bioimage_mcp/runtimes/persistent.py` (poll subprocess.returncode)
- [X] T056 [US4] Add periodic health monitoring thread in `src/bioimage_mcp/runtimes/persistent.py`

### Crash Detection
- [X] T057 [US4] Add crash detection within 5 seconds in `src/bioimage_mcp/runtimes/persistent.py` (mark worker as terminated)
- [X] T058 [US4] Add stderr log capture on crash in `src/bioimage_mcp/runtimes/persistent.py`

### Artifact Invalidation
- [X] T059 [US4] Add mem:// artifact invalidation on crash in `src/bioimage_mcp/storage/artifact_store.py` (mark as unavailable)
- [X] T060 [US4] Add clear error message for invalid mem:// artifacts in `src/bioimage_mcp/storage/artifact_store.py`

### Automatic Respawn
- [X] T061 [US4] Add automatic worker respawn in `src/bioimage_mcp/runtimes/persistent.py` (spawn new worker for subsequent calls)

### Verification
- [X] T062 [US4] Verify crash detection test passes
- [X] T063 [US4] Verify artifact invalidation test passes
- [X] T064 [US4] Verify automatic respawn test passes

---

## Phase 7: User Story 5 - Controlled Worker Shutdown (P3)

**Goal**: Complete in-flight ops; release memory; auto-shutdown after idle timeout

### Tests First (TDD)
- [X] T065 [US5] Write failing test for graceful shutdown in `tests/integration/test_worker_resilience.py`
- [X] T066 [US5] Write failing test for idle timeout in `tests/integration/test_worker_resilience.py`

### Shutdown Command
- [X] T067 [US5] Add shutdown handler in `tools/base/bioimage_mcp_base/entrypoint.py` (release memory, exit loop)
- [X] T068 [US5] Add shutdown command dispatch in `src/bioimage_mcp/runtimes/persistent.py` (send ShutdownRequest, await ShutdownResponse)

### Idle Timeout
- [X] T069 [US5] Add idle time tracking in `src/bioimage_mcp/runtimes/persistent.py` (last_activity_at)
- [X] T070 [US5] Add idle timeout check in WorkerManager in `src/bioimage_mcp/runtimes/persistent.py` (session_timeout_seconds)
- [X] T071 [US5] Add automatic shutdown trigger for idle workers in `src/bioimage_mcp/runtimes/persistent.py`

### Graceful Shutdown
- [X] T072 [US5] Add in-flight operation completion before shutdown in `src/bioimage_mcp/runtimes/persistent.py` (wait for busy -> ready)
- [X] T073 [US5] Add memory release verification in shutdown handler in `tools/base/bioimage_mcp_base/entrypoint.py`

### Verification
- [X] T074 [US5] Verify graceful shutdown test passes
- [X] T075 [US5] Verify idle timeout test passes

---

## Phase 8: Polish

### Documentation
- [ ] T076 [P] Update `docs/developer/architecture.md` with persistent worker architecture diagram
- [ ] T077 [P] Add memory artifact documentation to `docs/reference/artifacts.md`
- [ ] T078 [P] Update `README.md` with performance improvements from persistent workers

### Static Analysis
- [ ] T080 Run ruff linting on all modified files (ruff check .)
- [ ] T081 Run ruff formatting on all modified files (ruff format .)

### Validation
- [ ] T082 Run quickstart validation script (bash scripts/validate_quickstart.sh)
- [ ] T083 Verify all existing integration tests pass (pytest tests/integration/ -v)
- [ ] T084 Verify all existing contract tests pass (pytest tests/contract/ -v)

### Final Checks
- [ ] T085 Verify worker timeout configuration loads correctly
- [ ] T086 Verify max_workers limit is enforced
- [ ] T087 Run full test suite (pytest -v)
- [ ] T088 Update CHANGELOG.md with Phase 2 transition notes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 and US2 can proceed in parallel (both P1 priority)
  - US3 and US4 can proceed in parallel after US1/US2 (both P2 priority)
  - US5 (P3) can start after Foundational but lower priority
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational - No dependencies on other stories (parallel with US1)
- **User Story 3 (P2)**: Depends on US1 (needs workers) and US2 (needs mem:// artifacts) for meaningful testing
- **User Story 4 (P2)**: Depends on US1 (needs workers) - crash recovery requires active workers
- **User Story 5 (P3)**: Depends on US1 (needs workers) - shutdown requires active workers

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD per Constitution §6)
- Infrastructure before handlers
- Handlers before integration
- Core updates before verification
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: T001-T004 all [P] - run in parallel
**Phase 2 (Foundational)**: T005-T018 must be sequential within subsections, but subsections can be parallelized after T007
**Phase 3-7 (User Stories)**:
- US1 (T019-T029) and US2 (T030-T040) can run in parallel by different developers
- US3 and US4 can run in parallel after US1+US2 are complete
**Phase 8 (Polish)**: T076-T078 are [P] - can run in parallel

---

## Parallel Example: User Story 1 + User Story 2

```bash
# Developer A (US1): Persistent Workers
Task: T019 [US1] Write failing test for PID reuse
Task: T021 [US1] Create WorkerProcess class in persistent.py
Task: T024 [US1] Create WorkerManager class in persistent.py

# Developer B (US2): Memory Artifacts (parallel)
Task: T030 [US2] Write failing test for memory artifact creation
Task: T032 [US2] Add in-memory artifact storage dict
Task: T035 [US2] Add mem:// URI parsing helper
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only) - Recommended Path

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T018) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T019-T029) - Persistent workers with PID reuse
4. Complete Phase 4: User Story 2 (T030-T040) - Memory artifacts with no-disk-I/O
5. **STOP and VALIDATE**: Test US1 + US2 independently
6. Deploy/demo MVP - workers persist + mem:// works

**MVP Cut-off**: T040 and T089-T098 complete MVP functionality

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add US1 → Workers persist → Deploy/Demo (core capability!)
3. Add US2 → mem:// artifacts → Deploy/Demo (MVP complete!)
4. Add US3 → Cross-env handoff → Deploy/Demo
5. Add US4 → Crash recovery → Deploy/Demo
6. Add US5 → Graceful shutdown → Deploy/Demo (full feature!)
7. Polish → Documentation and validation

### Parallel Team Strategy

With 2 developers after Foundational phase:

| Developer A | Developer B |
|-------------|-------------|
| US1 (T019-T029) | US2 (T030-T040) |
| US3 (T041-T051) | US4 (T052-T064) |
| US5 (T065-T075) | Polish (T076-T088) |

---

## Summary

**Total Tasks**: 101

| Phase | Tasks | Story | Priority |
|-------|-------|-------|----------|
| Setup | T001-T004 (4) | - | - |
| Foundational | T005-T018 (14) | - | - |
| User Story 1 | T019-T029, T093-T098 (17) | US1 | P1 🎯 MVP |
| User Story 2 | T030-T040, T089-T092 (15) | US2 | P1 🎯 MVP |
| User Story 3 | T041-T051, T099-T102 (15) | US3 | P2 |
| User Story 4 | T052-T064 (13) | US4 | P2 |
| User Story 5 | T065-T075 (11) | US5 | P3 |
| Polish | T076-T088 (12) | - | - |

**MVP Scope**: T001-T040, T089-T098 (50 tasks) - Phases 1-4 only
**Full Feature**: T001-T102 (101 tasks) - All phases

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD per Constitution §6)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution III compliance verified at T047-T049 (no bioio in Core)
