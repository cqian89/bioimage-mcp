## Code Review (2025-12-27 08:38:49 UTC)

| Category | Status | Details |
|----------|--------|---------|
| Tasks | FAIL | Multiple completed tasks appear only partially implemented vs `specs/007-workflow-test-harness/tasks.md` (notably US6–US8 hints exposure via `call_tool`, axis-tool validation/metadata behavior, and storage-type handling). |
| Tests | PASS | Feature-related tests passed (with 4 skips): `pytest ... tests/unit/base/test_axis_ops.py ... tests/integration/test_replay_workflow.py`; skips were due to unavailable image metadata extraction (`tests/contract/test_artifact_metadata_contract.py`). |
| Coverage | LOW | Mock-mode coverage for `src/bioimage_mcp/api` measured ~47% (and `src/bioimage_mcp/api/execution.py` ~76%), below the >=80% target referenced in tasks/spec (NFR-003) if interpreted as orchestration coverage. |
| Architecture | FAIL | Core design elements exist (axis tools, YAML harness, hints models), but key wiring is missing (hints not surfaced in MCP `call_tool`, storage-type materialization likely inert, unused workflow-case schema validation fixtures). |
| Constitution | PASS | No obvious MCP surface explosion, but there is a notable anti-context-bloat risk in unbounded artifact `file_metadata.custom_attributes` and some gaps in “metadata enough for I/O validation” expectations. |

### Findings

- **CRITICAL**: LLM hints are not exposed via MCP `call_tool`.
  - `src/bioimage_mcp/api/execution.py` returns `hints` for `run_workflow()`, but `src/bioimage_mcp/api/interactive.py` drops them when building the `call_tool` response.
  - Impact: US7/US8 (“next steps” and “corrective hints on errors”) are not actually delivered to clients using `call_tool`.

- **HIGH**: Axis-tool behavior does not meet multiple spec requirements.
  - `tools/base/bioimage_mcp_base/axis_ops.py` lacks several validations and behaviors called out in `specs/007-workflow-test-harness/spec.md` and `specs/007-workflow-test-harness/tasks.md`:
    - Reject relabel mappings for non-existent axes.
    - Reject relabel mappings that produce duplicate axis names.
    - Reject `expand_dims` when `new_axis_name` already exists.
    - Ensure NFR-004 style actionable error messages (fn name + invalid parameter + suggested correction).
    - Preserve/remap `physical_pixel_sizes` and update richer OME metadata beyond `dim_order`.

- **HIGH**: Error-hint routing ignores specific error codes.
  - `src/bioimage_mcp/api/execution.py` uses `error_hints.GENERAL` and does not select hints by an error code such as `AXIS_SAMPLES_ERROR`.
  - Impact: `tools/base/manifest.yaml` includes `AXIS_SAMPLES_ERROR` hints for `base.phasor_from_flim`, but those hints likely never surface.

- **HIGH**: Cross-environment storage-type handling is likely non-functional.
  - `src/bioimage_mcp/api/execution.py` checks `artifact_ref['storage_type']`, but `ArtifactRef`/`ArtifactStore` do not appear to set/persist `storage_type` anywhere.
  - Impact: auto-materialization from `zarr-temp` → `file` may never trigger in real workflows.

- **MEDIUM**: YAML workflow-case schema validation is not enforced in the running harness.
  - `tests/integration/conftest.py` defines `workflow_test_cases` using `WorkflowTestCase` validation, but no tests consume this fixture.
  - `tests/integration/test_workflows.py` loads YAML directly, so malformed cases may not be caught early/clearly.

- **MEDIUM**: Potential anti-context-bloat risk in artifact metadata.
  - `src/bioimage_mcp/artifacts/metadata.py` includes `file_metadata.custom_attributes` without size bounding; this can become large and conflict with Constitution Principle I.

- **LOW**: ResourceWarnings about unclosed sqlite connections in test runs.
  - Coverage runs surfaced `ResourceWarning: unclosed database in <sqlite3.Connection ...>` suggesting fixture/service teardown does not always close connections.

### Remediation / Suggestions

1. **Expose hints in MCP `call_tool`**: plumb `ExecutionService.run_workflow()`’s `hints` (success/failure) through `src/bioimage_mcp/api/interactive.py` and ensure `src/bioimage_mcp/api/server.py` returns them.
2. **Implement axis-tool validations & metadata behavior**: add explicit checks and user-facing errors in `tools/base/bioimage_mcp_base/axis_ops.py` for missing axes/duplicate axes/duplicate new axis name; preserve and remap `physical_pixel_sizes` and update OME metadata in outputs.
3. **Route error hints by error code**: standardize tool error payloads to include a `code`, then select `hints.error_hints[code]` (fallback to `GENERAL`). Ensure `AXIS_SAMPLES_ERROR` can be emitted by FLIM tools.
4. **Make storage types real**: add a `storage_type` field to artifact references (model + persistence) and set it on produced artifacts (e.g., zarr-temp outputs). Add an integration test that exercises auto-materialization.
5. **Use the validated workflow-case loader**: refactor `tests/integration/test_workflows.py` to use `workflow_test_cases` (or otherwise validate YAML against `WorkflowTestCase` on load) so schema errors fail fast.
6. **Bound metadata sizes**: cap `file_metadata.custom_attributes` (e.g., allowlist keys, truncate deep structures, or store full metadata as a separate artifact and keep only a summary in MCP responses).
7. **Fix sqlite teardown warnings**: ensure any sqlite connections created in fixtures are closed; consider making `DiscoveryService` own and close the connection when created for tests.
