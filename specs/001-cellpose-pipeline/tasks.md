# Tasks: v0.1 First Real Pipeline (Cellpose)

**Input**: Design documents from `/specs/001-cellpose-pipeline/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md, meta-describe-protocol.md

**Tests**: Included (Constitution Check requires tests for workflow execution, artifact schemas, and tool shims).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 0: meta.describe Protocol Infrastructure

**Purpose**: Implement the `meta.describe` protocol for dynamic parameter schema extraction (see meta-describe-protocol.md)

**⚠️ CRITICAL**: This phase enables scalable tool integration. Complete before Phase 1.

### Tests for Phase 0

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T000a [P] Unit test for introspect_python_api() utility in tests/unit/runtimes/test_introspect.py
- [ ] T000b [P] Unit test for introspect_argparse() utility in tests/unit/runtimes/test_introspect.py
- [ ] T000c [P] Contract test for meta.describe request/response schema in tests/contract/test_meta_describe_contract.py
- [ ] T000c2 [P] Contract test that discovery listings remain summary-only (no `params_schema` blobs) in tests/contract/test_discovery_summary_first.py
- [ ] T000c3 [P] Contract test for discovery pagination/cursor stability in tests/contract/test_discovery_pagination_contract.py

### Implementation for Phase 0

- [ ] T000d Create introspection utilities module at src/bioimage_mcp/runtimes/introspect.py with introspect_python_api() and introspect_argparse()
- [ ] T000e [P] Add introspection_source field to Function model in src/bioimage_mcp/registry/manifest_schema.py
- [ ] T000f [P] Add schema_cache table to SQLite schema in src/bioimage_mcp/storage/sqlite.py (tool_id, tool_version, fn_id, params_schema_json, introspection_source)
- [ ] T000g Implement on-demand schema enrichment in ToolRegistry.describe_function() at src/bioimage_mcp/registry/index.py (call meta.describe only when `describe_function` is invoked; cache results)
- [ ] T000g2 [P] Implement schema cache lookup/validation logic in ToolRegistry at src/bioimage_mcp/registry/index.py (check tool_version before calling meta.describe; invalidate stale cache)
- [ ] T000h Update DiscoveryService.describe_function() to include introspection_source in response at src/bioimage_mcp/api/discovery.py
- [ ] T000i Implement meta.describe handler in builtin tool pack at tools/builtin/bioimage_mcp_builtin/entrypoint.py

**Checkpoint**: meta.describe protocol ready - tool packs can expose dynamic schemas

---

## Phase 1: Setup (Cellpose Tool Pack Infrastructure)

**Purpose**: Create Cellpose tool pack structure, environment definition, and entrypoint scaffolding

### Tests for Phase 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T001a [P] Contract test that env definition pins Cellpose version in tests/contract/test_cellpose_env_contract.py
- [ ] T001b [P] Contract test that Cellpose env lockfile exists at envs/bioimage-mcp-cellpose.lock.yml in tests/contract/test_cellpose_env_lock_contract.py
- [ ] T003a [P] Contract test validating Cellpose tool manifest schema and env_id in tests/contract/test_cellpose_manifest_contract.py
- [ ] T006a [P] Contract test ensuring .gitignore ignores Cellpose caches in tests/contract/test_gitignore_cellpose_contract.py

### Implementation for Phase 1

- [ ] T001 Create Cellpose environment definition at envs/bioimage-mcp-cellpose.yaml with cellpose, numpy, torch dependencies (pin cellpose version)
- [ ] T001c Generate conda-lock file at envs/bioimage-mcp-cellpose.lock.yml for reproducible installs (use conda-lock; include lockfile hash in workflow provenance)
- [ ] T002 [P] Create Cellpose tool pack directory structure at tools/cellpose/
- [ ] T003 [P] Create Cellpose tool manifest at tools/cellpose/manifest.yaml with minimal params_schema (full schema fetched on-demand via meta.describe)
- [ ] T004 Create Cellpose entrypoint scaffold at tools/cellpose/bioimage_mcp_cellpose/entrypoint.py implementing JSON stdin/stdout protocol including meta.describe handler
- [ ] T005 [P] Create Cellpose ops module at tools/cellpose/bioimage_mcp_cellpose/ops/segment.py with placeholder segmentation logic
- [ ] T005a [P] Create Cellpose curated descriptions at tools/cellpose/bioimage_mcp_cellpose/descriptions.py for key CellposeModel.eval() parameters
- [ ] T006 [P] Add tools/cellpose cache ignore patterns to .gitignore

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Phase 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T007a [P] Unit test that Run model exposes native_output_ref_id in tests/unit/runs/test_run_model.py
- [ ] T008b [P] Unit test that ArtifactRef includes schema_version in tests/unit/artifacts/test_artifactref_schema_version.py
- [ ] T011a [P] Integration test for artifact import allowlist enforcement in tests/integration/test_artifact_import_allowlist.py
- [ ] T011b [P] Integration test for workflow read/write allowlist enforcement in tests/integration/test_workflow_allowlists.py
- [ ] T012b [P] Unit test that default tool manifest roots include tools/cellpose in tests/unit/config/test_default_manifest_roots.py

### Implementation for Phase 2

- [ ] T007 Extend Run model to include native_output_ref_id field in src/bioimage_mcp/runs/models.py
- [ ] T008 [P] Add NativeOutputRef artifact type constant and validation in src/bioimage_mcp/artifacts/models.py (note: `format` field is open/extensible; values like `workflow-record-json`, `cellpose-seg-npy` are tool-dependent)
- [ ] T008a [P] Document NativeOutputRef usage for vendor bundle outputs (format: e.g., `cellpose-seg-npy`) in src/bioimage_mcp/artifacts/models.py
- [ ] T008c [P] Add schema_version field to ArtifactRef model and validate serialization in src/bioimage_mcp/artifacts/models.py
- [ ] T009 [P] Add workflow compatibility validation helper in src/bioimage_mcp/runtimes/protocol.py for I/O port type matching (FR-006)
- [ ] T010 Add validate_workflow_compatibility() to ExecutionService that checks step I/O types before execution in src/bioimage_mcp/api/execution.py
- [ ] T011 [P] Add LabelImageRef artifact type handling in ArtifactStore.import_file() in src/bioimage_mcp/artifacts/store.py
- [ ] T011c Enforce filesystem allowlists for artifact imports and workflow/tool I/O in src/bioimage_mcp/artifacts/store.py and src/bioimage_mcp/api/execution.py
- [ ] T012 Register tools/cellpose as a manifest root in default config or document configuration in src/bioimage_mcp/config/schema.py
- [ ] T012a Ensure ToolRegistry fetches dynamic params_schema only on-demand via describe_function (no schema enrichment during list_tools) in src/bioimage_mcp/registry/index.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Run a Cell Segmentation Pipeline (Priority: P1) 🎯 MVP

**Goal**: Execute Cellpose segmentation on a single image, produce LabelImageRef + LogRef + NativeOutputRef (workflow-record-json)

**Independent Test**: Using a sample microscopy image, run segmentation workflow and verify label output reference is exported to a local file

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [P] [US1] Contract test for ToolProtocolRequest/Response schema validation in tests/contract/test_cellpose_protocol.py
- [ ] T014 [P] [US1] Contract test verifying introspected Cellpose schema contains expected key params (diameter, flow_threshold) via meta.describe in tests/contract/test_cellpose_params_contract.py
- [ ] T014a [P] [US1] Contract test for cellpose.segment meta.describe response format (ok, result, tool_version) in tests/contract/test_cellpose_meta_describe.py
- [ ] T015 [P] [US1] Integration test for run_workflow with Cellpose in tests/integration/test_cellpose_e2e.py (requires sample image)
- [ ] T015a [P] [US1] Integration test that failed run_workflow still returns LogRef in tests/integration/test_run_logs.py
- [ ] T015b [P] [US1] Integration test that OME-Zarr input fails fast with clear error in tests/integration/test_unsupported_formats.py
- [ ] T016 [P] [US1] Unit test for workflow compatibility validation in tests/unit/runtimes/test_workflow_validation.py

### Implementation for User Story 1

- [ ] T017 [US1] Implement Cellpose segmentation logic in tools/cellpose/bioimage_mcp_cellpose/ops/segment.py using cellpose.models.CellposeModel (NOT models.Cellpose which is removed in v4)
- [ ] T018 [US1] Wire segment function in entrypoint dispatcher at tools/cellpose/bioimage_mcp_cellpose/entrypoint.py
- [ ] T019 [US1] Add OME-TIFF label image output writing using tifffile in tools/cellpose/bioimage_mcp_cellpose/ops/segment.py
- [ ] T019a [US1] Add NativeOutputRef (format: cellpose-seg-npy) output writing for full-fidelity Cellpose output (_seg.npy) in tools/cellpose/bioimage_mcp_cellpose/ops/segment.py (dual-output strategy per research.md Section 9)
- [ ] T020 [US1] Add NativeOutputRef (format: workflow-record-json) generation logic to ExecutionService.run_workflow() in src/bioimage_mcp/api/execution.py
- [ ] T021 [US1] Create write_native_output() helper in ArtifactStore at src/bioimage_mcp/artifacts/store.py (accepts format parameter for workflow records, vendor bundles, etc.)
- [ ] T022 [US1] Update ExecutionService.run_workflow() to call validate_workflow_compatibility() before execution in src/bioimage_mcp/api/execution.py
- [ ] T023 [US1] Add clear error messages for unsupported format/missing file in src/bioimage_mcp/artifacts/store.py (FR-007)
- [ ] T023a [US1] Ensure ExecutionService.run_workflow() persists and returns LogRef on failure paths in src/bioimage_mcp/api/execution.py (FR-003)
- [ ] T024 [US1] Ensure ExecutionService.run_workflow() returns native_output_ref (workflow record) in outputs in src/bioimage_mcp/api/execution.py

**Checkpoint**: User Story 1 complete - single-image Cellpose segmentation works end-to-end

---

## Phase 4: User Story 2 - Replay a Recorded Workflow (Priority: P2)

**Goal**: Accept a NativeOutputRef (format: workflow-record-json), parse it, and start a new run with equivalent workflow spec

**Independent Test**: Using workflow record from US1, replay and verify new run produces outputs of same artifact types

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T025 [P] [US2] Contract test for WorkflowRecord JSON schema in tests/contract/test_workflow_record_contract.py
- [ ] T026 [P] [US2] Integration test for replay_workflow() in tests/integration/test_replay_workflow.py

### Implementation for User Story 2

- [ ] T027 [P] [US2] Define WorkflowRecord pydantic model with schema_version, steps, tool_manifests, env_fingerprint in src/bioimage_mcp/runs/models.py
- [ ] T028 [US2] Implement parse_native_output() helper to load NativeOutputRef JSON (format: workflow-record-json) in src/bioimage_mcp/artifacts/store.py
- [ ] T029 [US2] Implement replay_workflow(native_output_ref_id) method in ExecutionService at src/bioimage_mcp/api/execution.py
- [ ] T030 [US2] Add validation for missing inputs in workflow record with clear error message in src/bioimage_mcp/api/execution.py
- [ ] T031 [US2] Link replayed run to original run_id in provenance field in src/bioimage_mcp/api/execution.py

**Checkpoint**: User Story 2 complete - workflow replay from saved record works

---

## Phase 5: User Story 3 - Validate Pipeline Reliability on Sample Data (Priority: P3)

**Goal**: Automated validation script runs pipeline on sample dataset(s) and confirms label outputs produced

**Independent Test**: Run validation script on sample datasets; script exits 0 and produces label references

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T032 [P] [US3] Integration test for validation script success in tests/integration/test_validate_pipeline.py

### Implementation for User Story 3

- [ ] T033 [P] [US3] Add sample microscopy image(s) to datasets/samples/ directory (1–2 images, ≤ 25 MB each, Creative Commons; record source + license)
- [ ] T034 [US3] Create validation script at scripts/validate_pipeline.py that runs segmentation on sample datasets
- [ ] T035 [US3] Add validation script invocation to pytest as a marker in pytest.ini (e.g., @pytest.mark.pipeline_validation)
- [ ] T036 [US3] Document sample dataset sources and licenses in datasets/README.md

**Checkpoint**: User Story 3 complete - automated pipeline validation passes on sample data

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T037 [P] Update README.md with quickstart instructions for Cellpose pipeline
- [ ] T038 [P] Verify and update specs/001-cellpose-pipeline/quickstart.md with actual CLI commands (include platform-specific Cellpose install notes/constraints)
- [ ] T039 [P] Add provenance env_fingerprint capture (Python version, env_id, platform, conda-lock hash) in ExecutionService at src/bioimage_mcp/api/execution.py
- [ ] T040 [P] Add tool manifest checksum capture to workflow record in src/bioimage_mcp/api/execution.py
- [ ] T041 [P] Unit test for WorkflowRecord model serialization in tests/unit/runs/test_workflow_record.py
- [ ] T042 Run full test suite via pytest (see pytest.ini) and fix any failures
- [ ] T043 Run ruff check (see ruff.toml) and fix any linting issues
- [ ] T044 Validate quickstart.md end-to-end using scripts/validate_quickstart.sh

---

## Phase 6.1: Cross-Cutting Contract Coverage (Remediations)

**Purpose**: Close requirements/test gaps identified by `/speckit.analyze` output (payload size discipline, export allowlists).

- [ ] T045a [P] [US1] Integration test for artifact export success to local filesystem path in tests/integration/test_artifact_export.py
- [ ] T045 [P] [US1] Contract/integration test for artifact export allowlist enforcement in tests/integration/test_artifact_export.py
- [ ] T046 [P] [US1] Contract test asserting workflow/run responses contain only refs/metadata (no pixel arrays) in tests/contract/test_payload_size_discipline.py

---

## Phase 6.2: Dynamic Format Handling (Future Code Tasks)

**Purpose**: Ensure `ArtifactRef.format` is treated as an open, extensible field with dynamic runtime handling (per research.md Section 10).

- [ ] T047 [P] Update ArtifactRef model docstring in src/bioimage_mcp/artifacts/models.py to clarify that `format` values are open/extensible and tool-dependent
- [ ] T048 [P] Update _guess_mime_type() in src/bioimage_mcp/artifacts/store.py to handle unknown formats gracefully (fallback to `application/octet-stream` for NativeOutputRef)
- [ ] T049 [P] Ensure ArtifactStore does not hardcode format-specific logic; use registry/lookup pattern for any format-dependent behavior in src/bioimage_mcp/artifacts/store.py
- [ ] T050 [P] Add unit tests for NativeOutputRef with various format values (workflow-record-json, cellpose-seg-npy, generic) in tests/unit/artifacts/test_store.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **meta.describe Protocol (Phase 0)**: No dependencies - can start immediately; ENABLES scalable tool integration
- **Setup (Phase 1)**: Depends on Phase 0 completion (meta.describe handlers required in entrypoints)
- **Foundational (Phase 2)**: Depends on Phase 1 completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion
- **User Story 2 (Phase 4)**: Depends on Phase 2 completion; integrates with US1 outputs
- **User Story 3 (Phase 5)**: Depends on Phase 2 completion; requires US1 working
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Phase 2 - Uses NativeOutputRef (workflow-record-json) from US1 but is independently testable with mock records
- **User Story 3 (P3)**: Can start after Phase 2 - Requires US1 pipeline working; tests end-to-end validation

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Protocol/contract tests before implementation
- Core logic before API integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 0**: T000a, T000b, T000c (tests) can run in parallel; T000e, T000f can run in parallel
- **Phase 1**: T002, T003, T005, T005a, T006 can run in parallel
- **Phase 2**: T008, T009, T011 can run in parallel
- **Phase 3 (US1)**: T013, T014, T014a, T015, T016 (all tests) can run in parallel
- **Phase 4 (US2)**: T025, T026 (tests) and T027 can run in parallel
- **Phase 5 (US3)**: T032, T033 can run in parallel
- **Phase 6**: T037, T038, T039, T040, T041 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for ToolProtocolRequest/Response in tests/contract/test_cellpose_protocol.py"
Task: "Contract test for CellposeSegmentParams in tests/contract/test_cellpose_params_contract.py"
Task: "Integration test for run_workflow with Cellpose in tests/integration/test_cellpose_e2e.py"
Task: "Unit test for workflow compatibility validation in tests/unit/runtimes/test_workflow_validation.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (Cellpose tool pack structure)
2. Complete Phase 2: Foundational (blocking prerequisites)
3. Complete Phase 3: User Story 1 (Cellpose segmentation end-to-end)
4. **STOP and VALIDATE**: Test User Story 1 independently with sample image
5. Deploy/demo if ready - user can run segmentation!

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **MVP Delivered** (segmentation works!)
3. Add User Story 2 → Test independently → Replay capability added
4. Add User Story 3 → Test independently → Validation automation added
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (core pipeline)
   - Developer B: User Story 2 (can mock WorkflowRecordRef for testing)
   - Developer C: User Story 3 (needs US1 complete, can start with sample data prep)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Cellpose env_id MUST be `bioimage-mcp-cellpose` to satisfy manifest schema validation
- Default output format is OME-TIFF per spec (not OME-Zarr)
- All artifact I/O via file-backed references; no pixel arrays in messages
- **meta.describe protocol**: Tool packs expose `meta.describe` fn_id for dynamic schema introspection (see meta-describe-protocol.md)
- **Cellpose API**: Use `cellpose.models.CellposeModel` (NOT `models.Cellpose` which is removed in Cellpose v4)
- **Manifest params_schema**: Can be minimal; full schema fetched on-demand via meta.describe (e.g., via describe_function)
- **Pin Cellpose version** in envs/bioimage-mcp-cellpose.yaml to ensure schema stability
