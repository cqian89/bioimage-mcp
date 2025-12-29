---

description: "Task list for Wrapper Elimination & Enhanced Dynamic Discovery"
---

# Tasks: Wrapper Elimination & Enhanced Dynamic Discovery

**Input**: Design documents from `/specs/009-wrapper-elimination/`
**Prerequisites**: `specs/009-wrapper-elimination/plan.md`, `specs/009-wrapper-elimination/spec.md`, `specs/009-wrapper-elimination/data-model.md`

**CRITICAL: TDD - Write tests first and ensure they fail before implementation.**

# Phase 1: Setup & Foundational Tests (Blocking)

- [ ] T001 Verify thin wrapper list and target functions in `tools/base/bioimage_mcp_base/preprocess.py` and `tools/base/bioimage_mcp_base/transforms.py`
- [ ] T002 Confirm legacy redirect targets and wrapper namespace layout in `tools/base/bioimage_mcp_base/entrypoint.py`
- [ ] T003 **TDD**: Write failing unit tests for `FunctionOverlay` model and internal validation in `tests/unit/registry/test_overlay_merge.py`
- [ ] T004 **TDD**: Write failing contract tests for manifest overlay schema in `tests/contract/test_overlay_schema.py`
- [ ] T005 **TDD**: Write failing integration tests for OME metadata propagation (FR-007) in `tests/integration/test_metadata_propagation.py`
- [ ] T006 **TDD**: Write failing tests for overlay `fn_id` validation and logging (FR-008) in `tests/unit/registry/test_overlay_validation.py`
- [ ] T007 **TDD**: Write failing tests for hierarchical `list_tools(path="base.skimage")` (FR-006) in `tests/integration/test_hierarchical_listing.py`

# Phase 2: Foundational Implementation (Blocking)

- [ ] T008 Implement `FunctionOverlay` model and `ToolManifest.function_overlays` field in `src/bioimage_mcp/registry/manifest_schema.py`
- [ ] T009 Implement overlay merge logic for dynamic functions in `src/bioimage_mcp/registry/loader.py`
- [ ] T010 Implement overlay `fn_id` validation and warning logging during manifest load in `src/bioimage_mcp/registry/loader.py` (FR-008)
- [ ] T011 Create wrapper package namespace in `tools/base/bioimage_mcp_base/wrapper/__init__.py`
- [ ] T012 Verify hierarchical tool listing logic in `src/bioimage_mcp/api/discovery.py` (FR-006)

**Checkpoint**: Foundation ready - all foundational tests should now pass.

# Phase 3: User Story 1 - LLM Agent Uses Library Functions Directly (Priority: P1)

- [ ] T013 [US1] **TDD**: Update dynamic execution assertions in `tests/integration/test_dynamic_execution.py` to assert failure when calling removed wrappers
- [ ] T014 [US1] Remove 15 thin wrapper functions from `tools/base/bioimage_mcp_base/preprocess.py` and `transforms.py`
- [ ] T015 [US1] Update `tools/base/manifest.yaml` to drop thin wrapper entries and map direct ops
- [ ] T016 [US1] Update direct function mappings in `tools/base/bioimage_mcp_base/entrypoint.py`
- [ ] T017 [US1] Implement OME metadata propagation in dynamic adapters (FR-007)

# Phase 4: User Story 2 - Essential Wrappers & Edge Cases (Priority: P2)

- [ ] T018 [US2] **TDD**: Write failing tests for reorganized wrapper namespace in `tests/unit/base/test_wrapper_namespace.py`
- [ ] T019 [US2] Implement IO wrappers in `tools/base/bioimage_mcp_base/wrapper/io.py`
- [ ] T020 [US2] Implement axis wrappers in `tools/base/bioimage_mcp_base/wrapper/axis.py`
- [ ] T021 [US2] Implement phasor wrappers in `tools/base/bioimage_mcp_base/wrapper/phasor.py`
- [ ] T022 [US2] Implement denoise wrapper in `tools/base/bioimage_mcp_base/wrapper/denoise.py`
- [ ] T023 [US2] Implement edge case transforms/preprocess in `tools/base/bioimage_mcp_base/wrapper/edge_cases.py` (crop, normalize, project, flip, pad)
- [ ] T024 [US2] Register wrapper functions in `tools/base/bioimage_mcp_base/entrypoint.py`
- [ ] T025 [US2] Add wrapper function entries in `tools/base/manifest.yaml`

# Phase 5: User Story 3 - Dynamic Functions Enriched with Overlays (Priority: P3)

- [ ] T026 [US3] **TDD**: Write failing integration tests to verify merged metadata (hints, tags) via `describe_function` in `tests/integration/test_overlay_discovery.py`
- [ ] T027 [US3] Add real-world overlay definitions for base tools in `tools/base/manifest.yaml`

# Phase 6: User Story 4 - Legacy Function Names Supported (Priority: P4)

- [ ] T028 [US4] **TDD**: Write failing integration tests for legacy redirects and deprecation logging in `tests/integration/test_legacy_redirects.py`
- [ ] T029 [US4] Add `LEGACY_REDIRECTS` mapping and resolution with logging in `tools/base/bioimage_mcp_base/entrypoint.py`
- [ ] T030 [US4] Ensure core server propagates tool-level deprecation warnings to logs.

# Phase 7: Polish & Final Validation

- [ ] T031 Update documentation in `specs/009-wrapper-elimination/quickstart.md` with final validation steps
- [ ] T032 Run full test suite and fix any regressions in `tests/`
- [ ] T033 Update manifest lockfile checksums if `manifest.yaml` changed
- [ ] T034 Run `quickstart.md` validation steps to verify all success criteria (SC-001 to SC-008)

---

## Parallel Execution Examples

```bash
# Launch foundational tests:
Task: T003, T004, T005, T006

# Launch foundational implementations once tests are written:
Task: T007, T008, T010
```
