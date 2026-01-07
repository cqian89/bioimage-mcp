# Code Review: 017-cellpose-api
 
 **Review Date:** 2026-01-07
 **Reviewer:** Documentation Specialist
 
 ## Summary Table
 
 | Category | Status | Notes |
 | :--- | :--- | :--- |
 | **Tasks** | COMPLETED | 55/55 tasks marked finished in `tasks.md`. |
 | **Tests** | FAILING | 2 unit test failures in `test_cellpose_dynamic_dispatch.py`. |
 | **Coverage** | NOT_AVAILABLE | `pytest-cov` not available in the current environment. |
 | **Architecture** | PASS | ObjectRef and Worker IPC changes align with stateful tool requirements. |
 | **Constitution** | PASS | Isolated execution and MCP surface constraints respected. |
 
 ## Findings
 
 ### [HIGH] Unit Test Failures in `test_cellpose_dynamic_dispatch.py`
 Two tests are failing due to environment mismatch and refactoring regressions:
 1. `test_dynamic_dispatch_train_seg`: Fails with `ModuleNotFoundError: No module named 'torch'`. The test expects a specific error message about implementation status, but the code now attempts a torch import which fails in the core/base test environment.
 2. `test_meta_describe_eval`: Fails due to an `AttributeError` while patching `bioimage_mcp_cellpose.entrypoint`. The symbol `_introspect_cellpose_eval` was renamed/refactored to `_introspect_cellpose_fn`.
 
 ### [MEDIUM] Environment Routing Risk in `ExecutionService.reconstruct_object`
 The `reconstruct_object` method uses `_get_target_env(python_class)` to determine where to run the reconstruction. However, `_get_target_env` is designed to map `fn_id` (tool IDs) to environments. Passing a Python class name may result in a fallback to the `default` environment, potentially causing reconstruction to fail if the class requires a specific tool environment (e.g., `cellpose.models.CellposeModel` requiring the `cellpose` env).
 
 ### [MEDIUM] URI Scheme Inconsistency in Dynamic Adapter
 The `cellpose.py` adapter generates ObjectRef URIs using the pattern `obj://local/cellpose/{object_id}`, whereas the broader system design (and `models.py`) suggests a `obj://{session_id}/{env_id}/{object_id}` or `obj://{store_id}/...` scheme. This inconsistency may break artifact resolution across different contexts.
 
 ### [LOW] Reproducibility vs. Materialization
 ObjectRefs are currently stored in `_OBJECT_CACHE` (in-memory) and use `format: pickle` for transit, but are not materialized to persistent storage. Reproducibility relies entirely on the `init_params` stored in the workflow record to "reconstruct" the object. If the reconstruction logic or environment changes, the workflow replay may not yield bit-identical state.
 
 ## Remediation & Suggestions
 
 1.  **Update Unit Tests**:
     *   Modify `test_dynamic_dispatch_train_seg` to mock the `torch` dependency or catch the `ModuleNotFoundError` to verify the dispatch logic without requiring heavy libraries in the core environment.
     *   Update `test_meta_describe_eval` patching targets to match the new `entrypoint.py` internal API.
 2.  **Refine Reconstruction Routing**:
     *   Improve `ExecutionService.reconstruct_object` to look up the correct tool environment based on the `ObjectRef` provenance or a registry mapping of classes to tool packs.
 3.  **Unify URI Formatting**:
     *   Align the dynamic adapter's URI generation with the standard `ObjectRef` URI scheme to ensure compatibility with session-based artifact lookups.
 4.  **Validate Replay**:
     *   Add a contract test specifically for `session_replay` to ensure that `reconstruct_object` correctly restores state from `init_params` across worker boundaries.

---

## Code Review Entry: 2026-01-07 11:30 AM

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | FAIL   | T041 marked complete but full test suite fails (2 regressions). |
| Tests    | FAIL   | 2 unit tests failing: `test_dynamic_dispatch_train_seg` and `test_meta_describe_eval`. |
| Coverage | LOW    | Coverage tools (`pytest-cov`) missing from environment. |
| Architecture | FAIL   | Routing risk in `reconstruct_object` and URI scheme inconsistencies. |
| Constitution | FAIL   | CRITICAL: Isolation violation (torch required in core env for unit tests). |

### Findings

#### [CRITICAL] Constitution Violation: Torch Dependency in Core Unit Tests
- **File**: `tests/unit/test_cellpose_dynamic_dispatch.py::test_dynamic_dispatch_train_seg`
- **Issue**: The test fails with `ModuleNotFoundError: No module named 'torch'`. Unit tests in the core environment should not depend on heavy tool-specific libraries like Torch. The test expects a "not implemented" error, but the implementation now exists and triggers a Torch import.
- **Impact**: Violates Principle 2 (Isolated Tool Execution) and breaks core CI/CD.

#### [HIGH] Architecture Risk: Incorrect Environment Routing for Reconstruction
- **File**: `src/bioimage_mcp/api/execution.py`
- **Issue**: `ExecutionService.reconstruct_object` passes a `python_class` string to `_get_target_env`, which expects a `fn_id`. This heuristic is unreliable and likely falls back to the `default` environment.
- **Impact**: Object reconstruction will fail for stateful tools requiring specific environments (e.g., Cellpose).

#### [MEDIUM] Unit Test Failure: Patch Target Drift
- **File**: `tests/unit/test_cellpose_dynamic_dispatch.py::test_meta_describe_eval`
- **Issue**: `AttributeError` caused by patching `_introspect_cellpose_eval`, which was refactored to `_introspect_cellpose_fn` in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`.
- **Impact**: Test suite remains red, obscuring other potential regressions.

#### [MEDIUM] URI Scheme Inconsistency
- **File**: `src/bioimage_mcp/registry/dynamic/adapters/cellpose.py`
- **Issue**: The adapter generates URIs like `obj://local/cellpose/{object_id}`, deviating from the canonical `obj://{session_id}/{env_id}/{object_id}` format described in the research/spec.
- **Impact**: Incompatibility with future artifact storage and session-based resolution logic.

### Remediation & Suggestions

1. **Mock Dependencies in Unit Tests**: Update `test_cellpose_dynamic_dispatch.py` to properly mock `torch` and the cellpose tool-pack functions to ensure they can run in the core environment without heavy dependencies.
2. **Refine Reconstruction Routing**: Modify `ExecutionService.reconstruct_object` to use a more robust lookup (e.g., registry-based mapping of class to environment) instead of passing the class name to a function ID lookup.
3. **Synchronize Patch Targets**: Update the `test_meta_describe_eval` to patch the correct refactored function name (`_introspect_cellpose_fn`).
4. **Standardize ObjectRef URIs**: Update `CellposeAdapter` to use the canonical URI scheme to ensure system-wide consistency and support for artifact materialization.
5. **Re-verify Tasks**: Correct `tasks.md` to show T041 as incomplete until the test suite is green and constitution/isolation concerns are addressed.

---

## Code Review Entry: 2026-01-07 02:00 PM

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | FAIL   | T041 claims completion but full test suite fails; inconsistent task marking. |
| Tests    | FAIL   | 2 regressions in `tests/unit/test_cellpose_dynamic_dispatch.py`. |
| Coverage | LOW    | `pytest-cov` unavailable; high-risk stateful code paths lack metrics. |
| Architecture | FAIL   | Reconstruction environment risks, metadata gaps for replay, and URI divergence. |
| Constitution | FAIL   | TDD quality gate failure; core test suite is in a broken state. |

### Findings

- **CRITICAL**: Unit test regression in `tests/unit/test_cellpose_dynamic_dispatch.py::test_dynamic_dispatch_train_seg`. The test expects a "not implemented" message but fails with `ModuleNotFoundError: No module named 'torch'`. This indicates a failure to mock heavy dependencies in the core environment.
- **HIGH**: Architecture Risk in `ExecutionService.reconstruct_object`. The method passes `python_class` to `_get_target_env` (which expects a `fn_id`) and ignores the returned environment. This risks running reconstruction in the wrong environment.
- **HIGH**: Metadata Inconsistency in Tool-pack. `tools/cellpose/.../handle_model_init` returns an `ObjectRef` without `init_params` in its metadata, yet the replay logic in `sessions.py` explicitly expects these params for reconstruction.
- **MEDIUM**: URI Schema Divergence. `src/bioimage_mcp/registry/dynamic/adapters/cellpose.py` uses `obj://local/cellpose/{id}`, which contradicts the canonical `obj://{session_id}/{env_id}/{object_id}` pattern used by worker identity checks.
- **MEDIUM**: Patch Target Drift. `test_meta_describe_eval` attempts to patch `_introspect_cellpose_eval`, but the implementation has been refactored to `_introspect_cellpose_fn`.

### Remediation & Suggestions

1. **Restore Test Integrity**: Immediately update `test_cellpose_dynamic_dispatch.py` to mock `torch` and align patch targets with the refactored implementation. Core tests must remain green regardless of tool-pack availability.
2. **Robust Reconstruction Routing**: Refactor `ExecutionService.reconstruct_object` to correctly map object classes to their originating tool environments and ensure the reconstruction command is dispatched to the correct worker.
3. **Align Metadata for Replay**: Update Cellpose initialization handlers to ensure all parameters necessary for reconstruction (`init_params`) are captured in the `ObjectRef` metadata at creation time.
4. **Standardize URI Formatting**: Harmonize the URI generation logic in dynamic adapters with the core system's `ObjectRef` models to ensure seamless artifact resolution and provenance tracking.
5. **Audit Task Status**: Update `tasks.md` to reflect that T041 ("Run full test suite") is currently failing and requires remediation.

---

## Code Review Entry: 2026-01-07 04:30 PM (Addendum)

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | FAIL   | T041 marked complete but full test suite currently FAILS due to regressions. |
| Tests    | FAIL   | 2 unit test failures in `test_cellpose_dynamic_dispatch.py`. |
| Coverage | LOW    | Coverage tools (`coverage`, `pytest-cov`) missing from the environment. |
| Architecture | FAIL   | Environment routing risk in reconstruction and URI scheme inconsistencies. |
| Constitution | FAIL   | Violation of Principle VI (Green Tests) and Principle II (Leakage via unit tests). |

### Findings

#### [CRITICAL] Constitution Violation: Torch Dependency in Core Unit Tests
- **File**: `tests/unit/test_cellpose_dynamic_dispatch.py`
- **Issue**: `test_dynamic_dispatch_train_seg` fails with `ModuleNotFoundError: No module named 'torch'`. The test expects a "not implemented" error, but the implementation now attempts a `torch` import which is unavailable in the core environment.
- **Impact**: Violates isolation constraints. Core tests must not depend on tool-specific heavy stacks.

#### [HIGH] Architecture Risk: Incorrect Environment Routing for Reconstruction
- **File**: `src/bioimage_mcp/api/execution.py`
- **Issue**: `ExecutionService.reconstruct_object` calls `_get_target_env(python_class)`, but `_get_target_env` expects a `fn_id` (e.g., `cellpose.segment`). Passing a class name (e.g., `cellpose.models.CellposeModel`) results in unreliable lookups and likely fallback to the "default" environment.
- **Impact**: Object reconstruction will fail for stateful tools requiring specific environments.

#### [HIGH] Task Inconsistency
- **File**: `specs/017-cellpose-api/tasks.md`
- **Issue**: T041 ("Run full test suite") is marked as complete despite the current broken state of the unit tests.

#### [MEDIUM] Unit Test Failure: Patch Target Drift
- **File**: `tests/unit/test_cellpose_dynamic_dispatch.py`
- **Issue**: `test_meta_describe_eval` tries to patch `bioimage_mcp_cellpose.entrypoint._introspect_cellpose_eval`, but this symbol was refactored to `_introspect_cellpose_fn`.
- **Impact**: Test suite remains red, masking other potential regressions.

#### [MEDIUM] URI Scheme Inconsistency
- **File**: `src/bioimage_mcp/registry/dynamic/adapters/cellpose.py`
- **Issue**: The adapter generates ObjectRef URIs as `obj://local/cellpose/{id}` (3-part with hardcoded literal), while the system design and persistent worker identity logic expect `obj://{session_id}/{env_id}/{object_id}`.
- **Impact**: Breaks cross-context artifact resolution and provenance tracking.

### Remediation & Suggestions

1. **Restore Core Test Isolation**: Update `test_cellpose_dynamic_dispatch.py` to mock `torch` and `cellpose` dependencies. Ensure tests verify dispatch logic without requiring tool-pack libraries.
2. **Synchronize Patch Targets**: Update `test_meta_describe_eval` to target the refactored `_introspect_cellpose_fn`.
3. **Refine Reconstruction Routing**: Update `ExecutionService.reconstruct_object` to use a robust mapping (e.g., class-to-env registry) or derive the environment from the ObjectRef's provenance.
4. **Standardize URI Formatting**: Update `CellposeAdapter` to generate URIs using the canonical session/env/id pattern to ensure compatibility with session-based resolution.
5. **Install Coverage Tools**: Ensure `pytest-cov` is available in the development environment to satisfy visibility requirements for stateful code paths.
6. **Correct Task Status**: Revert T041 in `tasks.md` to "incomplete" until a full green run is verified.

---

## Code Review Entry: 2026-01-07 05:45 PM

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | FAIL   | T041 marked completed in `tasks.md` but `pytest` run shows active failures. |
| Tests    | FAIL   | 2 failures in `tests/unit/test_cellpose_dynamic_dispatch.py` (regressions). |
| Coverage | N/A    | `coverage` and `pytest-cov` tools are missing from the current environment. |
| Architecture | FAIL   | URI scheme divergence and environment routing risks in `reconstruct_object`. |
| Constitution | FAIL   | TDD violation: tests are red. Isolation violation: `torch` leak in unit tests. |

### Findings

#### [CRITICAL] Constitution Violation: Torch Leakage in Unit Tests
- **File**: `tests/unit/test_cellpose_dynamic_dispatch.py::test_dynamic_dispatch_train_seg`
- **Issue**: Test fails with `No module named 'torch'`. The implementation now attempts to import `torch`, and the unit test fails to mock this dependency, violating the isolation principle (Principle II) where heavy stacks must not be in the core environment.
- **Impact**: Core test suite is broken for environments without GPU/Torch stacks.

#### [HIGH] Architecture Risk: Incorrect Environment Routing for Reconstruction
- **File**: `src/bioimage_mcp/api/execution.py`
- **Issue**: `ExecutionService.reconstruct_object` calls `_get_target_env(python_class)`, but `_get_target_env` expects a function ID (e.g., `cellpose.segment`). Passing a class name (e.g., `cellpose.models.CellposeModel`) results in unreliable routing, likely falling back to the `default` environment.
- **Impact**: Object reconstruction will fail when dispatched to workers lacking the required tool libraries.

#### [HIGH] Task Tracking Mismatch
- **File**: `specs/017-cellpose-api/tasks.md`
- **Issue**: Task T041 ("Run full test suite and verify all tests pass") is marked as completed (`[x]`), contradicting the reality of 2 active test failures.
- **Impact**: Misleading progress tracking and violation of TDD quality gates.

#### [MEDIUM] Unit Test Regression: Patch Target Drift
- **File**: `tests/unit/test_cellpose_dynamic_dispatch.py::test_meta_describe_eval`
- **Issue**: Test fails because it attempts to patch `_introspect_cellpose_eval`, which has been refactored to `_introspect_cellpose_fn` in the implementation.
- **Impact**: Inability to verify meta-description logic for Cellpose evaluation.

#### [MEDIUM] URI Scheme Inconsistency
- **File**: `src/bioimage_mcp/registry/dynamic/adapters/cellpose.py`
- **Issue**: The adapter uses `obj://local/cellpose/{id}`, whereas the system design and `ObjectRef` model expect `obj://{session}/{env}/{id}`.
- **Impact**: Breaks cross-session artifact resolution and provenance tracking consistency.

### Remediation & Suggestions

1. **Fix Test Isolation**: Update `test_cellpose_dynamic_dispatch.py` to mock `torch` and the internal `bioimage_mcp_cellpose` package completely. The core environment should remain agnostic to heavy tool-pack dependencies.
2. **Synchronize Patching**: Update `test_meta_describe_eval` to target `_introspect_cellpose_fn`.
3. **Robust Environment Lookup**: Refactor `ExecutionService.reconstruct_object` to look up the correct target environment using a class-to-tool-pack mapping or by extracting the environment from the `ObjectRef` metadata.
4. **Align URI Schemes**: Standardize the `CellposeAdapter` to use the canonical `obj://{session}/{env}/{id}` URI format.
5. **Update Task Status**: Revert T041 in `tasks.md` to incomplete until the test suite is green and the above architectural risks are addressed.


## Review Entry (Automated) - 2026-01-07 11:04:45 UTC

### Summary Table

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | PASS | Completed tasks in `specs/017-cellpose-api/tasks.md` map to concrete code + tests across `src/`, `tools/cellpose/`, and `tests/`. Notable risk items called out below (adapter execution semantics, toolpack I/O schema mismatch, error-shape consistency). |
| Tests    | FAIL | `pytest -q` fails with many integration-level failures in this environment. Feature-specific subset also has failures (details below). |
| Coverage | LOW | No coverage run as part of this review; many failures prevent meaningful measurement. Manual review indicates new paths have tests, but several scenarios are untested/fragile (see Coverage notes). |
| Architecture | PASS (with notes) | Core design (ObjectRef + class_context + toolpack cache) matches `specs/017-cellpose-api/plan.md`. One architectural concern: core `CellposeAdapter.execute()` simulates `ObjectRef` creation and imports toolpack code in-core. |
| Constitution | FAIL (CRITICAL) | At least two likely constitution violations: (1) toolpack `cellpose.cache.clear` outputs a `NativeOutputRef` with inline `value` (not an artifact ref), (2) toolpack emits non-standard error shapes (dict with `path` not JSON pointer) instead of core `StructuredError` model. |

### Findings

#### CRITICAL
- **Constitution I/III (Artifact references only)**: `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py` `handle_cache_clear` returns `outputs.cleared_count` as a `NativeOutputRef` with an inline `value` field. This appears to embed payload data in the MCP response rather than returning a stored artifact reference.
  - **Why it matters**: Constitution III requires artifact references only; the core server expects bounded metadata + URIs for artifacts.
  - **Suggested fix**: Either return no outputs (empty), or write a small JSON artifact to `work_dir` and return a proper `NativeOutputRef` pointing to `file://...`.

- **Structured error model inconsistency**: Toolpack `handle_segment` returns an error dict shaped as `{"code": ..., "message": ..., "details": [{"path": "inputs.model", ...}]}` (no `ErrorDetail` shape guarantee, and `path` format differs from constitution examples which use JSON Pointer style like `/inputs/model`). Core has `bioimage_mcp.api.errors` helpers and `StructuredError` Pydantic model.
  - **Why it matters**: Constitution I/V requires consistent structured errors across tools.
  - **Suggested fix**: Standardize error shapes emitted by toolpacks to match `StructuredError` (including JSON Pointer paths). Consider sharing a small error helper module between core and toolpacks (or duplicating minimal schema in toolpacks).

#### HIGH
- **Toolpack import behavior breaks unit tests**: `tests/unit/test_cellpose_dynamic_dispatch.py::test_dynamic_dispatch_train_seg` currently fails because calling `process_execute_request` for `cellpose.train_seg` raises `ImportError: No module named 'cellpose'` rather than returning a graceful "not implemented"/"missing dependency" error.
  - **Impact**: Unit tests assume toolpack entrypoint can be imported/run in core env without cellpose installed.
  - **Suggested fix**: In `process_execute_request`, guard dispatch for `cellpose.train_seg` with a dependency check and return a structured error indicating the function requires the cellpose env.

- **Unit test patch mismatch**: `tests/unit/test_cellpose_dynamic_dispatch.py::test_meta_describe_eval` patches `_introspect_cellpose_eval`, but toolpack code exposes `_introspect_cellpose_fn` instead, causing AttributeError.
  - **Suggested fix**: Update test to patch the correct function or add a thin wrapper `_introspect_cellpose_eval` in entrypoint.

- **Core adapter execution semantics**: `src/bioimage_mcp/registry/dynamic/adapters/cellpose.py` contains an `execute()` path that fabricates an `ObjectRef` (using `obj://local/...`) and attempts to import `bioimage_mcp_cellpose.ops.segment` by manipulating `sys.path`.
  - **Why it matters**: Constitution II wants heavy stacks out of core env, and tool integration should be via manifests + runtime dispatch, not in-core imports. This execute() path also risks producing `ObjectRef` URIs that are not worker-bound (`obj://<session>/<env>/<id>`).
  - **Suggested fix**: Prefer `execute()` raising NotImplementedError for all cellpose functions in core (forcing runtime tool execution), or ensure `execute()` is only used in environments where the toolpack is active and uses proper session/env IDs.

#### MEDIUM
- **Training outputs not aligned with core artifact store**: `tools/cellpose/bioimage_mcp_cellpose/ops/training.py` returns dicts with `{"type": ..., "format": ..., "path": ...}` but not full ArtifactRef shape (`ref_id`, `uri`, `mime_type`, `created_at`, etc.). If `ExecutionService` expects tool outputs to already be full artifact refs, this can break pipeline execution.
  - **Suggested fix**: Use the toolpack’s established artifact creation convention (write to `work_dir`, return `uri` + required metadata) and/or rely on core to import files as artifacts (if supported), but make it consistent.

- **I/O anti-pattern in tests**: `tests/integration/test_cellpose_training.py` uses `tifffile.imwrite` directly rather than `bioio` writers. Tests are allowed to use tifffile, but this may mask format/metadata expectations.

#### LOW
- **Manifest schema completeness**: `tools/cellpose/manifest.yaml` functions declare empty `params_schema` for `cellpose.train_seg` and `cellpose.CellposeModel.eval`. Given `meta.describe` exists, this is likely OK, but consider ensuring `describe` outputs separate `inputs`/`outputs` ports per constitution I.

### Test Results (this environment)

- **Full suite**: `pytest -q` -> FAIL with many integration test failures (environment/tooling issues and unrelated failing tests), so global PASS cannot be asserted here.
- **Feature-focused subset** (ran):
  - FAIL: `tests/unit/test_cellpose_dynamic_dispatch.py::test_dynamic_dispatch_train_seg` (ImportError: cellpose missing; expected graceful message)
  - FAIL: `tests/unit/test_cellpose_dynamic_dispatch.py::test_meta_describe_eval` (patch target missing)
  - FAIL: `tests/integration/test_cellpose_cache.py` (worker startup fails due to libmamba lock: `/home/qianchen/.cache/mamba/proc/proc.lock`)
  - FAIL: `tests/integration/test_cellpose_training.py` (blocked by worker startup + tool env)
  - FAIL: `tests/integration/test_workflows.py::test_workflow_from_yaml[squeeze_expand_roundtrip]` (axes metadata mismatch: got `ZY` vs expected `TCZYX`)

### Coverage Notes

- New code paths have tests (ObjectRef contract tests, session export/replay tests, eviction tests), but coverage is likely skewed by reliance on mocking and by integration tests failing to run reliably.
- Suggested additions:
  - Add a unit test that `cellpose.cache.clear` returns constitution-compliant outputs (either none or a proper artifact ref).
  - Add unit tests for toolpack structured error shape (JSON pointer paths, `code/message/details[]`).
  - Add tests ensuring `CellposeAdapter.execute()` does not fabricate invalid `obj://` URIs.

### Remediation / Suggestions

1. **Fix constitution violations first**:
   - Make `cellpose.cache.clear` return either no outputs or a file-backed JSON artifact ref.
   - Standardize toolpack errors to core `StructuredError` format (including JSON Pointer paths).

2. **Make toolpack entrypoint unit-testable without cellpose installed**:
   - Defer importing `cellpose` until inside handlers and catch ImportError to emit a structured dependency error.

3. **Align tests with implementation**:
   - Update `tests/unit/test_cellpose_dynamic_dispatch.py` to patch existing introspection function(s), or add compatibility wrappers in entrypoint.

4. **Review `CellposeAdapter.execute()`**:
   - Either remove/disable the in-core simulation path, or ensure it never runs in core-only contexts and returns proper `ObjectRef` URIs.

