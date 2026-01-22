# Codebase Concerns

**Analysis Date:** 2026-01-22

## Tech Debt

**Large Orchestration Modules:**
- Issue: Several core modules exceed 1,000 lines, handling too many responsibilities (execution logic, state management, materialization).
- Files: `src/bioimage_mcp/api/execution.py` (1302 lines), `src/bioimage_mcp/runtimes/persistent.py` (1282 lines)
- Impact: Increased cognitive load for maintainers and higher risk of regressions during refactoring.
- Fix approach: Split `execution.py` into separate handlers for materialization, step execution, and workflow orchestration. Extract IPC logic from `persistent.py` into a dedicated transport layer.

**Legacy Redirects:**
- Issue: Hardcoded function ID redirects for legacy support.
- Files: `src/bioimage_mcp/api/execution.py` (line 28)
- Impact: Accumulation of legacy baggage and potential confusion for users of the v1.0.0 API.
- Fix approach: Move redirects to a configuration-driven alias system or registry metadata.

**Dataset Metadata Gaps:**
- Issue: Numerous TODOs regarding provenance and licensing for sample datasets.
- Files: `datasets/FLUTE_FLIM_data_tif/LICENSE`, `datasets/samples/LICENSE`, `datasets/sample_czi/LICENSE`, `datasets/sample_data/LICENSE`, `datasets/synthetic/LICENSE`, `datasets/tttr-data/LICENSE`
- Impact: Compliance risk and lack of transparency for users of sample data.
- Fix approach: Conduct a metadata audit and populate LICENSE/README files with correct provenance and licensing information.

## Known Bugs

**Input Override Placeholder:**
- Issue: Input overrides in workflow replay are currently disabled or partially implemented.
- Files: `src/bioimage_mcp/api/execution.py` (line 1231)
- Symptoms: `override_inputs` parameter in `replay` might not behave as expected for all steps.
- Trigger: Attempting to replay a workflow with input overrides.
- Workaround: Manually edit workflow records before replay.

**Axis Independent Processing Gap:**
- Issue: Placeholder for T017 implementation in integration tests.
- Files: `tests/integration/test_axis_independent_processing.py` (line 91)
- Symptoms: Certain axis-independent processing features are untested or unimplemented.
- Trigger: Workflows requiring complex axis-independent manipulation.

## Security Considerations

**Subprocess IPC Sanitization:**
- Risk: While `_build_command` is used, the use of `subprocess.Popen` with environment variables inherited from the core process requires strict validation to prevent environment injection.
- Files: `src/bioimage_mcp/runtimes/persistent.py` (line 79)
- Current mitigation: Uses structured command building and limited environment variable passing (`BIOIMAGE_MCP_SESSION_ID`, `BIOIMAGE_MCP_ENV_ID`).
- Recommendations: Implement a strict allowlist for environment variables passed to workers and ensure `entrypoint` strings are strictly validated against a manifest.

**Filesystem Access Control:**
- Risk: Potential for unauthorized file access if FS policies are bypassed.
- Files: `src/bioimage_mcp/api/permissions.py`, `src/bioimage_mcp/config/loader.py`
- Current mitigation: `test_fs_policy_enforcement.py` verifies policy application.
- Recommendations: Audit all tool entrypoints to ensure they respect the `fs_policy` provided by the core server.

## Performance Bottlenecks

**Cross-Environment Materialization:**
- Problem: Materializing memory artifacts to disk for handoff between different conda environments (e.g., cellpose to base) involves disk I/O and process-to-process signaling.
- Files: `src/bioimage_mcp/api/execution.py` (`_materialize_memory_artifact_via_worker`)
- Cause: Isolation of tool environments necessitates serialization to a shared filesystem.
- Improvement path: Explore shared memory segments or more efficient zero-copy IPC if running on the same host.

**Registry Search Performance:**
- Problem: Dynamic discovery and search ranking may become slow as the number of tool packs and functions grows.
- Files: `src/bioimage_mcp/registry/index.py`, `tests/integration/test_discovery_perf.py`
- Cause: Complex ranking logic and lack of pre-computed indices for some dynamic attributes.
- Improvement path: Implement a more robust indexing strategy for dynamic adapter metadata.

## Fragile Areas

**Worker Lifecycle & IPC:**
- Files: `src/bioimage_mcp/runtimes/persistent.py`, `src/bioimage_mcp/runtimes/worker_ipc.py`
- Why fragile: Relies on line-buffered NDJSON over pipes; race conditions in session management are handled with locks but remain complex (`test_server_session_race.py`).
- Safe modification: Use a robust state machine for `WorkerProcess` and ensure all IPC messages are schema-validated at both ends.
- Test coverage: Good coverage in `tests/unit/runtimes` and `tests/integration/test_persistent_worker.py`.

**Dynamic Adapters (XArray/Phasorpy/Cellpose):**
- Files: `src/bioimage_mcp/registry/dynamic/adapters/`
- Why fragile: These adapters wrap external libraries with complex schemas, translating them to MCP-compatible artifacts. Any change in the underlying library's API could break the adapter.
- Safe modification: Maintain strict contract tests for each adapter against specific versions of the target libraries.

## Scaling Limits

**In-Memory Artifact Store:**
- Current capacity: Limited by the memory of the worker process (and the host machine).
- Limit: Large 3D/4D/5D bioimages can easily exceed available RAM if multiple artifacts are held concurrently.
- Scaling path: Implement LRU eviction policy for the `MemoryArtifactStore` (partially implemented) and favor streaming or chunked I/O for very large datasets.

**Subprocess Overhead:**
- Current capacity: One worker process per (session, environment) pair.
- Limit: High session counts or many concurrent environments can lead to process exhaustion or high CPU/memory overhead.
- Scaling path: Implement worker pooling or idle timeouts (partially implemented via `_last_activity_at`).

## Test Coverage Gaps

**Interactive Summarization:**
- What's not tested: Complex multi-step interaction summaries with diverse artifact types.
- Files: `src/bioimage_mcp/api/execution.py`
- Risk: LLM might receive insufficient or confusing summaries of tool outputs.
- Priority: Medium

**Async Task Error Propagation:**
- What's not tested: Deeply nested error scenarios in async worker execution.
- Files: `src/bioimage_mcp/runtimes/persistent.py`
- Risk: Workers might hang or fail silently if certain error paths aren't trapped and propagated via IPC.
- Priority: High

---

*Concerns audit: 2026-01-22*
