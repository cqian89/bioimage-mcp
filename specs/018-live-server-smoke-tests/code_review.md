# Code Review: 018-live-server-smoke-tests

**Review Date/Time**: 2026-01-08T19:54:20+01:00

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | FAIL | Multiple tasks marked complete in `specs/018-live-server-smoke-tests/tasks.md` are only partially implemented (notably T012/T014/T015/T021/T030). |
| Tests    | FAIL | Ran `pytest -p no:cacheprovider tests/smoke/utils/test_interaction_logger.py tests/smoke/utils/test_mcp_client.py` (PASS). Live smoke tests (`tests/smoke/test_*.py`) not executed in this review due to strict read-only constraints and likely on-disk side effects from starting a real server. |
| Coverage | LOW | Good unit coverage for `tests/smoke/utils/*`; insufficient assertion depth/coverage for live smoke scenarios and for the “recording/logging” contract. |
| Architecture | FAIL | Implementation diverges from `specs/018-live-server-smoke-tests/plan.md` goals around time budgets, automatic logging, and server stderr capture. |
| Constitution | PASS | No changes to the 8-tool MCP surface were found. However, the new smoke tests do not yet validate key Constitution I constraints (counts + describe shape) as intended. |

## Findings

### **CRITICAL**

1. **Smoke tests do not validate Constitution I requirements (counts + describe shape).**
   - `tests/smoke/test_smoke_basic.py` only checks that `list()` returns “something” and that `describe()` returns either `inputs` or `summary`, but does not validate:
     - `list()` child counts (`total`, `by_type`) for non-leaf nodes.
     - `describe()` shape with separate `inputs`, `outputs`, and `params_schema`.
   - This undermines SC-005 (“protocol/schema drift” detection) and the core stated purpose of the smoke suite.

2. **Interaction log generation is not aligned with docs/spec expectations.**
   - `specs/018-live-server-smoke-tests/quickstart.md` states logs are saved “after each test run”, but `tests/smoke/conftest.py` only writes logs when `--smoke-record` is enabled.
   - If the intent is “logs always,” this is a functional gap; if the intent is “logs only in recording mode,” the docs/spec need to be updated for consistency.

3. **Server stderr capture is not implemented (T021).**
   - `tests/smoke/utils/mcp_client.py` defines `self._stderr_buffer` and `get_stderr()` but does not populate it.
   - `InteractionLog.server_stderr` exists in `tests/smoke/utils/interaction_logger.py` but is never set.

4. **Recording-mode test does not assert that a log file is written or that required fields exist (T030).**
   - `tests/smoke/test_smoke_recording.py` only asserts the directory exists; it does not check that a `.json` log file is produced or validate required log fields.

### **HIGH**

1. **Live scenario assertions are too weak and may pass on broken behavior.**
   - `tests/smoke/test_cellpose_pipeline_live.py` does not fail if no artifact reference is present in outputs (it only asserts when it happens to find one).
   - `tests/smoke/test_smoke_basic.py` uses string containment checks like `"ref_id" in str(load_result)` which can pass for incorrect formats and does not validate `uri`.

2. **Time budgets are declared but not enforced as specified.**
   - `tests/smoke/conftest.py` defines `SmokeConfig.minimal_suite_budget_s` and `scenario_timeout_s`, but does not enforce a per-session suite budget or per-scenario timeout in a way aligned with `specs/018-live-server-smoke-tests/tasks.md` (T012/T015).

### **MEDIUM**

1. **Minimal vs full mode is not configurable.**
   - `tests/smoke/conftest.py:SmokeConfig.minimal_mode` is always `True`, and there is no CLI option/marker-driven logic to switch the default dataset selection (T009/T013 intent).

2. **`requires_env` checks depend on `conda` being on PATH and runnable.**
   - `_env_available()` shells out to `conda run ...` and will skip if it fails. This is reasonable, but it may create confusing skips in environments where conda is intentionally unavailable.

### **LOW**

1. **Untracked log directory present in repo working tree.**
   - `git status` reports `?? .bioimage-mcp/smoke_logs/`. Consider ensuring this is gitignored (or created under a temp directory) to reduce noise.

## Remediation / Suggestions

- **Make `tests/smoke/test_smoke_basic.py` a real Constitution I gate**:
  - Assert `list()` returns `items` with counts (`total`, `by_type`) for non-leaf nodes.
  - Assert `describe(fn_id=...)` returns separate `inputs`, `outputs`, and `params_schema` keys.

- **Decide and enforce the logging contract**:
  - If logs are required for CI traceability (US1 acceptance), generate logs by default for smoke tests and upload them in CI.
  - If logs are only for debugging, update `specs/018-live-server-smoke-tests/quickstart.md` to say logs require `--smoke-record`, and adjust acceptance language accordingly.

- **Implement stderr capture + wire it into logs**:
  - Populate `InteractionLog.server_stderr` from the server process stderr stream, and include it in saved logs on failures.

- **Strengthen scenario assertions**:
  - For every `run()` step that claims “artifact references only,” assert `ref_id` is non-empty and `uri` is present and usable.
  - Ensure tests fail if no artifact reference is present.

- **Add enforcement for time budgets**:
  - Track session start time in the session fixture and fail fast when the minimal suite exceeds `minimal_suite_budget_s`.

- **Improve recording-mode test**:
  - Assert a `.json` file is created in `.bioimage-mcp/smoke_logs/` and validate required fields (`test_run_id`, `scenario`, `interactions[*].timestamp/direction/tool`, `duration_ms`, and diagnostics fields).

---

## Code Review Addendum

**Review Date/Time**: 2026-01-08T23:36:23+01:00

This addendum reflects the current code in this branch. Some statements earlier in this file appear to be from an earlier iteration (e.g., `TestMCPClient` now does capture stderr via `_read_stderr()`, and `--smoke-full` exists).

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | FAIL | Several `[X]` items in `specs/018-live-server-smoke-tests/tasks.md` are incomplete or mismatched (notably T014, T020, T021, T030). |
| Tests    | FAIL | `18 passed` for `tests/smoke/utils/test_interaction_logger.py` + `tests/smoke/utils/test_mcp_client.py`. Live smoke scenarios were not executed here (they can start a real server and write artifacts). Also, `tests/smoke/test_smoke_basic.py::test_smoke_discovery` appears to have an assertion that does not match the actual `list()` response shape. |
| Coverage | LOW | Good unit coverage for `tests/smoke/utils/*`. Coverage is weak for the intended “live interaction logging” behavior (logger is not wired into `TestMCPClient` calls). |
| Architecture | FAIL | Implementation diverges from `specs/018-live-server-smoke-tests/plan.md` around transport usage (`stdio_client`) and around automatic per-test interaction logging. |
| Constitution | PASS | Feature adds tests/config only (no MCP tool surface changes). However, the new smoke tests do not yet reliably enforce Constitution I invariants (counts + drift detection). |

## Findings

### **CRITICAL**

1. **Minimal smoke discovery test likely fails due to wrong `list()` assertions.**
   - `src/bioimage_mcp/api/discovery.py` returns `{"items": [...], "next_cursor": ..., "expanded_from": ...}`.
   - `tests/smoke/test_smoke_basic.py` currently asserts `"total" in list_result or "by_type" in list_result`, but those counts live under each non-leaf item’s `children` field.
   - Result: the supposed CI gate (`-m smoke_minimal`) is likely broken.

2. **Recording/logging contract is not implemented end-to-end.**
   - `InteractionLogger` exists, but `TestMCPClient.call_tool*()` does not call `log_request()` / `log_response()`.
   - `tests/smoke/conftest.py` saves logs only when `--smoke-record` is enabled, and even then most scenario tests never populate the logger.
   - `tests/smoke/test_smoke_recording.py` manually fabricates interactions after a call and uses a dummy duration; it does not validate “automatic capture of real requests/responses + timings + diagnostics.”

### **HIGH**

1. **Stderr capture is not wired into saved logs (partial T021).**
   - `tests/smoke/utils/mcp_client.py` captures stderr lines into `_stderr_buffer`, but `InteractionLog.server_stderr` is never set from it.

2. **Timeout enforcement is weak.**
   - `pytest.mark.timeout(300)` is only effective if `pytest-timeout` is installed; it is not listed in `pyproject.toml` optional `test` deps.
   - `pytest_runtest_makereport` mutating `rep.outcome` after-the-fact does not stop a hung scenario; it only changes reporting.

3. **FLIM scenario does not consistently validate artifact-ref outputs at each step.**
   - `tests/smoke/test_flim_phasor_live.py` validates artifact refs mainly at the final phasor step; earlier steps (`load`, `rename`) should also assert `ref_id` + `uri`.

### **MEDIUM**

1. **Docs mismatch in `specs/018-live-server-smoke-tests/quickstart.md`.**
   - Several examples mention `base.io.bioimage.read`, but the tests/spec use `base.io.bioimage.load`.
   - Quickstart recommends `--timeout=120`, which requires `pytest-timeout`.

2. **Transport implementation diverges from the plan.**
   - Plan calls for using MCP SDK `stdio_client`/`StdioServerParameters`; current `TestMCPClient` implements a custom stdio adapter using `anyio.create_memory_object_stream`.

## Remediation / Suggestions

- Fix `tests/smoke/test_smoke_basic.py::test_smoke_discovery` to validate counts per item: for every item where `has_children` is true, assert `children.total > 0` and `children.by_type` exists.
- Decide the logging contract:
  - If CI must always upload logs, save an interaction log per test by default (at least on failure) and ensure the logger is populated automatically.
  - If logs are debug-only, make that explicit in `spec.md`/`tasks.md`/`quickstart.md` and ensure `--smoke-record` produces correct real logs.
- Wire `TestMCPClient` into `InteractionLogger`:
  - Record request params before calling `session.call_tool`.
  - Measure real duration and record the parsed result.
  - On failure/timeouts, include `get_stderr()` into `InteractionLog.server_stderr` and set `error_summary`.
- Add a small unit test that ensures `TestMCPClient.call_tool_checked()` logs a request+response pair (and logs errors) when a logger is provided.
