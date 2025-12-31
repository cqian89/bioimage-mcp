# Tasks: Wrapper Consolidation (Spec 011)

**Input**: Design documents from `/specs/011-wrapper-consolidation/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Included per Constitution Check requirements (workflow execution, artifact schemas, tool shims).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Verify existing infrastructure and prepare for feature development

- [ ] T001 Verify project structure matches plan.md (src/bioimage_mcp/registry/dynamic/ exists)
- [ ] T002 [P] Verify bioio and xarray dependencies in pyproject.toml
- [ ] T003 [P] Create feature branch `011-wrapper-consolidation` if not exists

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Data Models

- [ ] T004 [P] Add `input_mode` field (Literal["path", "numpy", "xarray"]) to FunctionDef in src/bioimage_mcp/registry/manifest_schema.py
- [ ] T005 [P] Add `ApplyUfuncConfig` model (input_core_dims, output_core_dims, vectorize, dask, output_dtypes) in src/bioimage_mcp/registry/dynamic/models.py
- [ ] T006 [P] Update `ArtifactRef` to support `mem://` URI scheme and memory storage type in src/bioimage_mcp/artifacts/models.py
- [ ] T007 [P] Define `XARRAY_ALLOWLIST` and `XARRAY_DENYLIST` constants in src/bioimage_mcp/registry/dynamic/allowlists.py (NEW file)

### Infrastructure - Persistent Workers & Memory Store


- [ ] T008 [P] Implement `PersistentWorkerManager` for per-session, per-env workers in src/bioimage_mcp/runtimes/persistent.py
- [ ] T009 [P] Implement `MemoryArtifactStore` for tracking `mem://` references in src/bioimage_mcp/artifacts/memory.py
- [ ] T010 Implement worker crash detection and `mem://` reference invalidation logic in src/bioimage_mcp/runtimes/persistent.py

**Checkpoint**: Foundation ready - data models validated, user story implementation can begin

---

## Phase 3: User Story 1 - Axis-Independent Image Processing (Priority: P1) 🎯 MVP

**Goal**: Enable spatial filters (like Gaussian blur) to be applied to any multi-dimensional image without users specifying dimensions. The filter is applied to every spatial plane (YX) across all other dimensions (T, C, Z), with dimension names and metadata preserved. Uses persistent workers to maintain `mem://` artifacts.

**Independent Test**: Process both a 5D OME-TIFF and a 2D TIFF using the same Gaussian blur tool call, verifying both produce valid `mem://` results with correct dimensionality preserved.

### Tests for User Story 1

- [ ] T011 [P] [US1] Contract test for `mem://` artifact reference schema in tests/contract/test_memory_artifact_schema.py
- [ ] T012 [P] [US1] Integration test: Gaussian blur on 5D image produces `mem://` artifact and preserves all dimensions in tests/integration/test_axis_independent_processing.py
- [ ] T013 [P] [US1] Integration test: Worker restart invalidates existing `mem://` references in tests/integration/test_worker_resilience.py

### Implementation for User Story 1

- [ ] T014 [US1] Implement `XarrayAdapter` in src/bioimage_mcp/registry/dynamic/xarray_adapter.py to expose `base.xarray.*` tools
- [ ] T015 [US1] Implement `mem://` resolution in `ArtifactManager`
- [ ] T016 [US1] Update `ExecutionBridge` to use persistent workers and handle `mem://` artifact resolution in src/bioimage_mcp/api/execution.py
- [ ] T017 [US1] Implement `apply_ufunc` dispatch logic for numpy libraries in src/bioimage_mcp/api/execution.py
- [ ] T018 [US1] Add logging for axis-aware processing operations and worker lifecycle events

**Checkpoint**: User Story 1 complete - spatial filters work across any dimensionality

---

## Phase 4: User Story 2 - Transparent Format Interoperability & Handoff (Priority: P1)

**Goal**: When a tool requires OME-TIFF input but receives a CZI (or other proprietary format), the system automatically converts the data. Cross-env handoff uses negotiated interchange formats (default OME-TIFF) materialized to disk.

**Independent Test**: Load a `.czi` file and pass it directly to a tool in a different environment, verifying automatic materialization and successful execution.

### Tests for User Story 2

- [ ] T019 [P] [US2] Integration test: Cross-env handoff negotiates OME-TIFF materialization in tests/integration/test_cross_env_handoff.py
- [ ] T020 [P] [US2] Integration test: `base.bioio.export` successfully materializes `mem://` to file-backed artifact in tests/integration/test_artifact_export.py

### Implementation for User Story 2

- [ ] T021 [US2] Implement cross-env format negotiation in `IOBridge`
- [ ] T022 [US2] Implement coordination for source-side materialization in `IOBridge` (invokes `bioio` in worker)
- [ ] T023 [US2] Implement `base.bioio.export` (agent tool) in `tools/base/manifest.yaml` and dynamic implementation
- [ ] T024 [US2] Integrate `IOBridge` handoff with `ExecutionBridge`

**Checkpoint**: User Story 2 complete - proprietary formats work transparently with any tool

---

## Phase 5: User Story 3 - Efficient Axis Manipulation (Priority: P2)

**Goal**: Users can rename, squeeze, transpose, and select along dimensions using a unified interface. Operations preserve data integrity while updating metadata.

**Independent Test**: Rename 'Z' to 'T' and remove singleton dimensions, verify resulting file has updated header metadata while data remains bit-identical.

### Tests for User Story 3

- [ ] T033 [US3] Integration test: rename('Z' → 'T') updates metadata correctly in tests/integration/test_axis_manipulation.py
- [ ] T034 [US3] Integration test: squeeze() removes singleton dimensions in tests/integration/test_axis_manipulation.py
- [ ] T035 [US3] Integration test: transpose() reorders dimensions correctly in tests/integration/test_axis_manipulation.py
- [ ] T036 [US3] Integration test: isel() selects along dimensions without data corruption in tests/integration/test_axis_manipulation.py

### Implementation for User Story 3

- [ ] T025 [US3] Register `base.xarray.rename`, `base.xarray.squeeze`, etc. as individual tools in `tools/base/manifest.yaml`
- [ ] T026 [US3] Add `rename` method implementation to `XarrayAdapter` in src/bioimage_mcp/registry/dynamic/xarray_adapter.py
- [ ] T027 [US3] Add `squeeze` method implementation to `XarrayAdapter`
- [ ] T028 [US3] Add `expand_dims` method implementation to `XarrayAdapter`
- [ ] T029 [US3] Add `transpose` method implementation to `XarrayAdapter`
- [ ] T030 [US3] Add `isel` method implementation to `XarrayAdapter`
- [ ] T031 [US3] Add `pad` method implementation to `XarrayAdapter`
- [ ] T032 [US3] Add `sum/max/mean` reduction methods to `XarrayAdapter`

**Checkpoint**: User Story 3 complete - all axis manipulations available through unified interface

---

## Phase 6: Migration - Wrapper Deletion

**Purpose**: Remove the 16 legacy wrapper tools now replaced by `base.xarray.*` and `base.bioio.*`

### Manifest Cleanup

- [ ] T037 [P] Remove all legacy `base.wrapper.*` tools from `tools/base/manifest.yaml`
- [ ] T038 [P] Delete `tools/base/bioimage_mcp_base/wrapper/` directory and all its contents
- [ ] T039 [P] Clean up any wrapper-specific dependencies in `tools/base/pyproject.toml`

**Checkpoint**: All 16 wrapper tools deleted, migration complete

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, documentation, and performance validation

### Documentation

- [ ] T040 [P] Update `docs/reference/tools.md` with new `base.xarray.*` documentation
- [ ] T041 [P] Update `docs/developer/architecture.md` with persistent workers and `mem://` sections

### Provenance & Artifact Validation

- [ ] T042 Integration test: CZI → Squeeze → Denoise chain records all transformations in `tests/integration/test_provenance_chain.py`
- [ ] T043 [P] Verify `mem://` artifacts record minimal provenance, and materialized files record full history

### Performance

- [ ] T044 Benchmark memory-backed artifact performance vs legacy file-backed wrappers
- [ ] T045 [P] Verify worker reuse across tool calls in a single session

### Final Validation

- [ ] T046 Run `quickstart.md` validation scenarios
- [ ] T047 Verify registry tool count reduced by at least 15 tools
- [ ] T048 Run full test suite: `pytest tests/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - xarray adapter core
- **User Story 2 (Phase 4)**: Depends on Foundational - can run parallel with US1
- **User Story 3 (Phase 5)**: Depends on US1 (uses xarray adapter)
- **Migration (Phase 6)**: Depends on US1, US2, US3 completion
- **Polish (Phase 7)**: Depends on Migration completion

### User Story Dependencies

```
Foundational (Phase 2)
       │
       ├──────────────┬──────────────┐
       ▼              ▼              │
   [US1: P1]     [US2: P1]           │
   xarray        I/O Bridge          │
   adapter       (parallel)          │
       │              │              │
       └──────┬───────┘              │
              ▼                      │
          [US3: P2]  ◄───────────────┘
          Axis Ops
          (uses US1)
              │
              ▼
         Migration
         (Phase 6)
```

### Within Each User Story

1. Tests written and FAILING before implementation
2. Models before adapters
3. Adapters before execution bridge integration
4. Core implementation before error handling
5. Error handling before logging

### Parallel Opportunities

**Phase 2 (Foundational)**:
```bash
# All model additions can run in parallel:
Task: T005 "Add ApplyUfuncConfig model"
Task: T006 "Add IORequirements model"

# All contract tests can run in parallel:
Task: T008 "Contract test for input_mode"
Task: T009 "Contract test for ApplyUfuncConfig"
Task: T010 "Contract test for IORequirements"
```

**Phase 3 (US1) + Phase 4 (US2) - Can run in parallel**:
```bash
# US1 and US2 are both P1 and independent:
Developer A: Phase 3 (xarray adapter)
Developer B: Phase 4 (I/O bridge)
```

**Phase 5 (US3) - All xarray methods can run in parallel**:
```bash
# All method implementations are independent:
Task: T026 "Add rename method"
Task: T027 "Add squeeze method"
Task: T028 "Add expand_dims method"
Task: T029 "Add transpose method"
Task: T030 "Add isel method"
Task: T031 "Add pad method"
Task: T032 "Add sum/max/mean methods"
```

**Phase 6 (Migration) - All deletions can run in parallel**:
```bash
# All manifest removals are independent:
Task: T037 "Remove legacy base.wrapper.*"
Task: T038 "Delete wrapper directory"
Task: T039 "Clean up dependencies"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (Axis-Independent Processing)
4. **STOP and VALIDATE**: Test that Gaussian blur works on 5D and 2D images
5. Deploy/demo if ready - basic xarray adapter working

### Incremental Delivery

1. Setup + Foundational → Data models validated
2. Add User Story 1 → xarray adapter MVP → Test independently
3. Add User Story 2 → I/O bridge → Test CZI workflows
4. Add User Story 3 → All axis operations → Test independently
5. Migration → Delete wrappers → Verify tool count reduced
6. Polish → Documentation, performance, full validation

### Success Criteria Verification

| Criterion | Task(s) | Verification |
|-----------|---------|--------------|
| Registry reduced by 15+ tools | T037 | T047 |
| Unified interface for axis ops | T025-T032 | T033-T036 |
| Feature parity (all wrappers replaced) | T025-T032, T037-T039 | T033-T036, T042 |
| Automated format interop | T021-T024 | T019-T020 |
| Improved efficiency | T008, T009 | T044, T045 |
| Safety (allowlist enforcement) | T007, T014 | T046 |
| Traceability (provenance) | T018, T021 | T042, T043 |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All xarray operations use the allowlist from T007
- I/O bridge conversions MUST record provenance (Constitution requirement)
- Thread pool required for I/O to avoid blocking MCP event loop
- Avoid: modifying wrapper files (delete only), same file conflicts
