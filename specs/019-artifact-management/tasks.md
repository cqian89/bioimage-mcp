# Tasks: Artifact Store Retention & Quota Management

**Input**: Design documents from `/specs/019-artifact-management/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: TDD required per Constitution Check VI (plan.md). All tests written first, verified to fail, before implementation.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Validate project structure and dependencies exist

- [X] T001 Verify project structure matches plan.md layout in src/bioimage_mcp/
- [X] T002 [P] Verify test directory structure exists in tests/unit/storage/, tests/contract/, tests/integration/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### 2.1 Schema Migration

- [X] T003 [P] Write contract test for sessions table migration in tests/contract/test_storage_schema.py
- [X] T004 [P] Write contract test for artifacts table migration (add session_id FK + index; assert size_bytes already exists) in tests/contract/test_storage_schema.py
- [X] T005 Implement sessions table migration (completed_at, is_pinned columns) in src/bioimage_mcp/storage/sqlite.py
- [X] T006 Implement artifacts table migration (add session_id FK + index) in src/bioimage_mcp/storage/sqlite.py
- [X] T007 Implement migration backfill logic for existing data in src/bioimage_mcp/storage/sqlite.py

### 2.2 Configuration Model

- [X] T008 [P] Write unit test for StorageSettings validation in tests/unit/storage/test_config.py
- [X] T009 Implement StorageSettings Pydantic model in src/bioimage_mcp/config/schema.py

### 2.3 Runtime Models

- [X] T010 [P] Write unit tests for StorageStatus model in tests/unit/storage/test_models.py
- [X] T011 [P] Write unit tests for SessionSummary model in tests/unit/storage/test_models.py
- [X] T012 [P] Write unit tests for PruneResult model in tests/unit/storage/test_models.py
- [X] T013 [P] Write unit tests for QuotaCheckResult model in tests/unit/storage/test_models.py
- [X] T014 [P] Write unit tests for OrphanFile model in tests/unit/storage/test_models.py
- [X] T015 Implement StorageStatus, SessionSummary, PruneResult, QuotaCheckResult, OrphanFile models in src/bioimage_mcp/storage/models.py

### 2.4 Service Skeleton

- [X] T016 Create StorageService class skeleton with __init__ in src/bioimage_mcp/storage/service.py

### 2.5 CLI Subparser Structure

- [X] T017 Add `storage` subparser with status/prune/pin/list stubs to src/bioimage_mcp/cli.py

**Checkpoint**: Foundation ready - schema migrated, models defined, service skeleton created

---

## Phase 3: User Story 1 - Developer Reclaims Disk Space (Priority: P1) 🎯 MVP

**Goal**: Enable developers to see storage usage and reclaim space by pruning expired sessions

**Independent Test**: 
1. Run `bioimage-mcp storage status` to see usage breakdown
2. Run `bioimage-mcp storage prune --dry-run` to preview deletions
3. Run `bioimage-mcp storage prune` to delete expired sessions and verify space reclaimed

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T018 [P] [US1] Write unit test for StorageService.get_status() in tests/unit/storage/test_service.py
- [ ] T019 [P] [US1] Write unit test for StorageService.get_session_size() in tests/unit/storage/test_service.py
- [ ] T020 [P] [US1] Write unit test for StorageService.prune() dry_run mode in tests/unit/storage/test_service.py
- [ ] T021 [P] [US1] Write unit test for StorageService.prune() actual deletion in tests/unit/storage/test_service.py
- [ ] T022 [P] [US1] Write unit test for StorageService.find_orphans() in tests/unit/storage/test_service.py
- [ ] T023 [P] [US1] Write unit test for StorageService.delete_orphans() in tests/unit/storage/test_service.py
- [ ] T024 [P] [US1] Write integration test for `storage status` CLI in tests/integration/test_storage_cli.py
- [ ] T025 [P] [US1] Write integration test for `storage prune` CLI in tests/integration/test_storage_cli.py

### Implementation for User Story 1

- [ ] T026 [US1] Implement StorageService.get_status() in src/bioimage_mcp/storage/service.py
- [ ] T027 [US1] Implement StorageService.get_session_size() in src/bioimage_mcp/storage/service.py
- [ ] T028 [US1] Implement StorageService.find_orphans() in src/bioimage_mcp/storage/service.py
- [ ] T029 [US1] Implement StorageService.delete_orphans() in src/bioimage_mcp/storage/service.py
- [ ] T030 [US1] Implement StorageService.prune() with dry_run support in src/bioimage_mcp/storage/service.py
- [ ] T031 [US1] Implement `storage status` CLI command handler in src/bioimage_mcp/cli.py
- [ ] T032 [US1] Implement `storage prune` CLI command handler in src/bioimage_mcp/cli.py
- [ ] T033 [US1] Add --json, --verbose flags to status command in src/bioimage_mcp/cli.py
- [ ] T034 [US1] Add --dry-run, --force, --older-than, --include-orphans flags to prune command in src/bioimage_mcp/cli.py
- [ ] T035 [US1] Implement human-readable output formatting for status command in src/bioimage_mcp/cli.py
- [ ] T036 [US1] Implement human-readable output formatting for prune command in src/bioimage_mcp/cli.py

**Checkpoint**: User Story 1 complete - developers can check status and prune expired sessions

---

## Phase 4: User Story 2 - CI Environment Protection (Priority: P1)

**Goal**: Enforce storage quotas to prevent CI runners from running out of disk space

**Independent Test**:
1. Configure strict quota (e.g., 1GB) and verify run blocked with clear error when exceeded
2. Set short retention (1 day) and verify cleanup removes old artifacts

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T037 [P] [US2] Write unit test for StorageService.check_quota() below warning in tests/unit/storage/test_quota.py
- [ ] T038 [P] [US2] Write unit test for StorageService.check_quota() at warning threshold in tests/unit/storage/test_quota.py
- [ ] T039 [P] [US2] Write unit test for StorageService.check_quota() at critical threshold in tests/unit/storage/test_quota.py
- [ ] T040 [P] [US2] Write unit test for quota enforcement blocking run in tests/unit/storage/test_quota.py
- [ ] T041 [P] [US2] Write integration test for quota enforcement in tests/integration/test_storage_quota.py
- [ ] T091 [P] [US2] Write integration test for structured error payload when quota exceeded in tests/integration/test_storage_quota.py

### Implementation for User Story 2

- [ ] T042 [US2] Implement StorageService.check_quota() in src/bioimage_mcp/storage/service.py
- [ ] T043 [US2] Integrate quota check into ExecutionService pre-run in src/bioimage_mcp/api/execution.py
- [ ] T044 [US2] Add warning log when storage exceeds warning threshold in src/bioimage_mcp/storage/service.py
- [ ] T045 [US2] Add blocking error when storage exceeds critical threshold in src/bioimage_mcp/storage/service.py
- [ ] T046 [US2] Implement clear error message directing users to cleanup in src/bioimage_mcp/storage/service.py

**Checkpoint**: User Story 2 complete - CI environments protected by quota enforcement

---

## Phase 5: User Story 3 - Protecting Important Results (Priority: P2)

**Goal**: Allow users to pin sessions to prevent them from being pruned

**Independent Test**:
1. Pin a session with `bioimage-mcp storage pin <session_id>`
2. Let session age exceed retention period
3. Run prune and verify pinned session preserved while others deleted

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T047 [P] [US3] Write unit test for StorageService.pin_session() in tests/unit/storage/test_service.py
- [ ] T048 [P] [US3] Write unit test for StorageService.unpin_session() in tests/unit/storage/test_service.py
- [ ] T049 [P] [US3] Write unit test for prune skipping pinned sessions in tests/unit/storage/test_service.py
- [ ] T050 [P] [US3] Write integration test for `storage pin` CLI in tests/integration/test_storage_cli.py

### Implementation for User Story 3

- [ ] T051 [US3] Implement StorageService.pin_session() in src/bioimage_mcp/storage/service.py
- [ ] T052 [US3] Implement StorageService.unpin_session() in src/bioimage_mcp/storage/service.py
- [ ] T053 [US3] Update StorageService.prune() to skip pinned sessions in src/bioimage_mcp/storage/service.py
- [ ] T054 [US3] Implement `storage pin` CLI command handler in src/bioimage_mcp/cli.py
- [ ] T055 [US3] Add --unpin flag to pin command in src/bioimage_mcp/cli.py
- [ ] T056 [US3] Implement human-readable output for pin command in src/bioimage_mcp/cli.py

**Checkpoint**: User Story 3 complete - users can protect important sessions from cleanup

---

## Phase 6: User Story 4 - Understanding Storage Usage (Priority: P2)

**Goal**: Provide detailed session listing with status, age, and size information

**Independent Test**:
1. Run `bioimage-mcp storage list` and verify output shows session status, age, size, artifact count
2. Filter by state with `--state expired` and verify only expired sessions shown

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T057 [P] [US4] Write unit test for StorageService.list_sessions() default behavior in tests/unit/storage/test_service.py
- [ ] T058 [P] [US4] Write unit test for StorageService.list_sessions() with state filter in tests/unit/storage/test_service.py
- [ ] T059 [P] [US4] Write unit test for StorageService.list_sessions() with sort options in tests/unit/storage/test_service.py
- [ ] T060 [P] [US4] Write integration test for `storage list` CLI in tests/integration/test_storage_cli.py

### Implementation for User Story 4

- [ ] T061 [US4] Implement StorageService.list_sessions() in src/bioimage_mcp/storage/service.py
- [ ] T062 [US4] Implement `storage list` CLI command handler in src/bioimage_mcp/cli.py
- [ ] T063 [US4] Add --state, --limit, --sort, --json flags to list command in src/bioimage_mcp/cli.py
- [ ] T064 [US4] Implement human-readable table output for list command in src/bioimage_mcp/cli.py
- [ ] T065 [US4] Add pinned indicator (📌) to list output in src/bioimage_mcp/cli.py

**Checkpoint**: User Story 4 complete - users can browse and understand storage usage

---

## Phase 7: Session Lifecycle Integration

**Purpose**: Complete session lifecycle management to support retention policies

- [ ] T066 Write unit test for StorageService.complete_session() in tests/unit/storage/test_service.py
- [ ] T067 Implement StorageService.complete_session() in src/bioimage_mcp/storage/service.py
- [ ] T068 Integrate session completion stamping into session lifecycle management in src/bioimage_mcp/sessions/manager.py
- [ ] T069 Add session status tracking (active → completed → expired) logic in src/bioimage_mcp/storage/service.py
- [ ] T070 Write unit test for session completion classification using idle timeout in tests/unit/storage/test_service.py
- [ ] T071 Implement session completion classification using idle timeout in src/bioimage_mcp/storage/service.py

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories

### Edge Cases & Error Handling

- [ ] T072 [P] Write test for prune during active session (must not delete) in tests/unit/storage/test_service.py
- [ ] T073 [P] Write test for idempotent cleanup (file already deleted) in tests/unit/storage/test_service.py
- [ ] T074 [P] Write test for directory-based artifacts (OME-Zarr) in tests/unit/storage/test_service.py
- [ ] T075 [P] Write test for missing file with index entry in tests/unit/storage/test_service.py
- [ ] T076 [P] Write test for quota check on empty store in tests/unit/storage/test_quota.py
- [ ] T088 [P] Write unit test for concurrent prune safety (locking prevents overlap) in tests/unit/storage/test_service.py
- [ ] T089 [P] Write unit test for interrupted prune convergence (rerun completes without corruption) in tests/unit/storage/test_service.py
- [ ] T077 Implement concurrent operation safety (locking) in src/bioimage_mcp/storage/service.py
- [ ] T090 Implement interrupted cleanup strategy (reconciliation / transactional boundaries) in src/bioimage_mcp/storage/service.py
- [ ] T078 Implement idempotent file deletion handling in src/bioimage_mcp/storage/service.py
- [ ] T079 Implement recursive directory deletion for Zarr artifacts in src/bioimage_mcp/storage/service.py
- [ ] T080 Implement stale index entry cleanup in src/bioimage_mcp/storage/service.py

### Documentation & Validation

- [ ] T081 [P] Verify quickstart.md examples work end-to-end
- [ ] T082 [P] Update AGENTS.md with storage CLI documentation
- [ ] T083 [P] Add storage management section to project README

### Performance & Exit Codes

- [ ] T084 Verify status command responds in <1s for typical stores
- [ ] T085 Verify prune of 100 sessions completes in <30s
- [ ] T092 Verify quota check overhead meets SC-2 (document environment + result)
- [ ] T093 Verify `bytes_reclaimed` matches `storage status` total delta (SC-5)
- [ ] T086 Implement correct exit codes per CLI contract in src/bioimage_mcp/cli.py
- [ ] T087 Add structured logging for all deletion events in src/bioimage_mcp/storage/service.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational and Session Lifecycle (Phase 7) - Can proceed first (P1 + MVP)
- **User Story 2 (Phase 4)**: Depends on Foundational - Can run parallel with US1 (P1)
- **User Story 3 (Phase 5)**: Depends on Foundational - Can start after US1 or in parallel (P2)
- **User Story 4 (Phase 6)**: Depends on Foundational - Can start after US1 or in parallel (P2)
- **Session Lifecycle (Phase 7)**: Depends on Foundational - Defines completion/expiry primitives used by prune
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories; depends on Phase 7 session lifecycle primitives - Core value proposition
- **User Story 2 (P1)**: No dependencies on other stories - Uses check_quota() only
- **User Story 3 (P2)**: Uses pin logic that integrates with prune (US1)
- **User Story 4 (P2)**: Shares models with US1 but independently implementable

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Service methods before CLI handlers
3. Core logic before formatting/output
4. Verify tests pass after implementation

### Parallel Opportunities

**Phase 2 Foundational**:
```bash
# All contract/unit tests for models can run in parallel:
T003, T004  # Schema tests
T008        # Config test
T010, T011, T012, T013, T014  # Model tests
```

**Phase 3 User Story 1**:
```bash
# All tests can run in parallel:
T018, T019, T020, T021, T022, T023, T024, T025
```

**Phase 4 User Story 2**:
```bash
# All tests can run in parallel:
T037, T038, T039, T040, T041
```

**Phase 5 User Story 3**:
```bash
# All tests can run in parallel:
T047, T048, T049, T050
```

**Phase 6 User Story 4**:
```bash
# All tests can run in parallel:
T057, T058, T059, T060
```

**Phase 8 Polish**:
```bash
# All edge case tests can run in parallel:
T072, T073, T074, T075, T076
# All documentation tasks can run in parallel:
T081, T082, T083
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 7: Session Lifecycle Integration (completion/expiry primitives)
4. Complete Phase 3: User Story 1 (status + prune)
5. **STOP and VALIDATE**: Test `storage status` and `storage prune` commands
6. Deploy/demo if ready - core value delivered

### Recommended Order (Priority-Based)

1. **Phase 1 + 2**: Setup + Foundational → Foundation ready
2. **Phase 7**: Session Lifecycle → Completion/expiry primitives ready
3. **Phase 3 (US1)**: Status + Prune → Test independently → **MVP Complete!**
4. **Phase 4 (US2)**: Quota Enforcement → Test independently → CI protection enabled
5. **Phase 5 (US3)**: Pin/Unpin → Test independently → Session protection enabled
6. **Phase 6 (US4)**: List Sessions → Test independently → Full visibility enabled
7. **Phase 8**: Polish → Edge cases, documentation, performance validation

### Incremental Delivery Value

| Increment | User Stories | Value Delivered |
|-----------|-------------|-----------------|
| MVP | US1 | Developers can see usage and reclaim space |
| +CI | US1 + US2 | CI environments protected from exhaustion |
| +Safety | US1-3 | Important results protected from cleanup |
| Full | US1-4 | Complete storage management visibility |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- TDD required: verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- File paths use src/bioimage_mcp/ per plan.md structure
