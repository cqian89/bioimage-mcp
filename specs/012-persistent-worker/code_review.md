
## Code Review (2026-01-01T13:41:14.977399+00:00)

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | FAIL | `tasks.md` marks many items complete, but core execution still uses one-shot subprocesses and several task file paths no longer exist. |
| Tests    | FAIL | `tests/contract/test_worker_ipc_schema.py` PASS; `tests/unit/runtimes/test_worker_ipc.py` PASS; `tests/integration/test_worker_resilience.py` PASS; `tests/integration/test_persistent_worker.py` has failures and hangs. |
| Coverage | LOW | `pytest-cov` is not installed; API-level persistent-worker behavior is not covered; several integration tests do not complete due to deadlocks. |
| Architecture | FAIL | Persistent workers are not wired into `ExecutionService` or `execute_tool`; worker spawn and queue semantics do not match `spec.md` goals. |
| Constitution | FAIL | Core imports and uses `bioio` during materialization; base tool uses `tifffile` for I/O helpers; both conflict with Constitution III guidance. |

### Findings
- **CRITICAL**: Deadlock risk in `src/bioimage_mcp/runtimes/persistent.py` — `WorkerProcess.execute()` calls `_update_activity()` while already holding `self._lock` (see `_update_activity` at line 151 and call sites at lines 208 and 304). This causes hanging worker calls and breaks integration tests.
- **CRITICAL**: Constitution III violation — core imports and uses `bioio` for materialization fallback in `src/bioimage_mcp/api/execution.py` (see `import bioio` at line 580 and subsequent readers and writers). Spec requires Core remain free of heavy I/O stacks and delegate materialization to tool environments.
- **HIGH**: Persistent workers not actually used for tool execution — `_run_one_function` still calls `execute_tool()` (one-shot `subprocess.Popen(...).communicate`) and only touches `PersistentWorkerManager` without using it to execute.
- **HIGH**: Worker limit behavior diverges from spec — `PersistentWorkerManager.get_worker()` raises immediately when `max_workers` is reached (lines 700-707), while `spec.md` FR-016 says requests should queue.
- **HIGH**: IPC contract vs runtime semantics mismatch — contract and tests use `ref_id="mem://..."`, but `tools/base/bioimage_mcp_base/entrypoint.py` treats `ref_id` as an in-memory dict key (`artifact_id = ref_id`), so a real mem URI value will not be found.
- **HIGH**: Constitution III anti-pattern in tool env — `tools/base/bioimage_mcp_base/entrypoint.py` uses `tifffile` (lines 166, 181) for temporary OME-TIFF writes; guidance prefers `bioio.writers.*` and avoiding custom I/O wrappers.
- **MEDIUM**: No worker readiness handshake — `WorkerProcess` sets state to `READY` immediately after `Popen`, so early requests can race worker startup.
- **MEDIUM**: Crash detection is passive — no periodic monitoring thread; crashes are detected on next `is_alive()` or `get_worker()` call, which may not satisfy a strict detect-within-5s requirement without activity.
- **MEDIUM**: Config timeouts and limits not plumbed — `Config.worker_timeout_seconds`, `Config.max_workers`, and `Config.session_timeout_seconds` exist, but are not clearly enforced end-to-end by `ExecutionService` plus persistent manager.
- **LOW**: `tasks.md` references outdated paths (`tests/unit/config/test_schema.py`, `src/bioimage_mcp/storage/artifact_store.py`, `src/bioimage_mcp/artifacts/reference.py`), making traceability harder.

### Tests Run
- PASS: `pytest -q tests/contract/test_worker_ipc_schema.py`
- PASS: `pytest -q tests/unit/runtimes/test_worker_ipc.py`
- PASS: `timeout 120s pytest -q tests/integration/test_worker_resilience.py`
- FAIL: `timeout 60s pytest -q tests/integration/test_persistent_worker.py::TestPersistentWorkerLifecycle::test_per_worker_request_queueing`
- FAIL: `timeout 60s pytest -q tests/integration/test_persistent_worker.py::TestPersistentWorkerLifecycle::test_max_worker_limit_enforcement`
- TIMEOUT: `timeout 20s pytest -vv tests/integration/test_persistent_worker.py::TestPersistentWorkerLifecycle::test_per_operation_timeout_enforcement`

### Remediation / Suggestions
- Fix `WorkerProcess.execute()` locking: avoid re-acquiring `self._lock` inside `_update_activity`, or use a re-entrant lock (`threading.RLock`) and ensure no nested acquisition patterns.
- Remove `bioio` usage from Core: delete the fallback materialization path and make worker-delegated materialization the only path for cross-env handoff.
- Wire persistent workers into execution: replace one-shot `execute_tool()` calls with NDJSON requests sent via `WorkerProcess` (and pass through allowlists and timeouts).
- Decide on IPC `ref_id` semantics (mem URI vs artifact_id) and align `contracts/worker-ipc.yaml`, `worker_ipc.py` models, and tool entrypoint handlers accordingly.
- Replace `tifffile` temp writes with `bioio.writers.OmeTiffWriter.save(...)` or rework functions to accept arrays so temporary files are not needed.
- Add an explicit no-bioio-in-core contract test (static scan) to prevent regressions.
