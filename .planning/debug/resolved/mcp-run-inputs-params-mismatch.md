---
status: resolved
trigger: "Investigate issue: mcp-run-inputs-params-mismatch"
created: 2026-03-04T17:08:00+08:00
updated: 2026-03-04T19:37:18+08:00
---

## Current Focus

hypothesis: Human validation confirms the fix in the real workflow; the session can be archived and committed.
test: Archive debug record and create final code/docs commits per debug protocol.
expecting: Session moves to `.planning/debug/resolved/` and commits capture both code fix and debug resolution doc.
next_action: move debug file to resolved and commit code/docs changes.

## Symptoms

expected: `bioimage-mcp_run` should have a consistent and self-contained contract where valid invocation for `tttrlib.TTTR` does not require duplicated/dummy fields; session handling should tolerate parallel calls without uniqueness collisions.
actual: `params` only -> validation error (`inputs` missing). `inputs` only -> runtime error (`filename is required`). Passing both (`inputs` dummy + real `params`) succeeds. A parallel call run hit `UNIQUE constraint failed: sessions.session_id` once.
errors: Validation error about missing `inputs`; runtime error indicating required `filename`; intermittent SQLite/session DB unique constraint failure on `sessions.session_id` during parallel calls.
reproduction: 1) Call `bioimage-mcp_run` on `tttrlib.TTTR` with only `params` including `filename` -> validation fails for missing `inputs`. 2) Call with only `inputs` -> runtime fails (`filename is required`). 3) Call with both dummy `inputs` and real `params` -> succeeds. 4) Execute MCP calls in parallel and observe intermittent uniqueness failure on session insert.
started: Discovered during current testing cycle; workaround identified (provide both fields); parallel issue observed once and mitigated by running sequentially.

## Eliminated

## Evidence

- timestamp: 2026-03-04T17:08:54+08:00
  checked: Codebase-wide search for run/input/session definitions in `src/`
  found: `api/server.py` run entrypoint includes `inputs` in signature; execution and runtime layers also carry `params`; session persistence code in `sessions/store.py` manages `session_id` inserts.
  implication: The contract mismatch and session uniqueness error likely live in separate layers (API contract vs session creation race).

- timestamp: 2026-03-04T17:10:09+08:00
  checked: `src/bioimage_mcp/api/server.py` `run` tool definition
  found: `run` signature requires `inputs: dict[str, Any]` with no default; `params` is optional and defaults to `{}` only after validation.
  implication: MCP SDK validates missing required args before method body, matching observed `inputs`-missing validation error.

- timestamp: 2026-03-04T17:11:48+08:00
  checked: `src/bioimage_mcp/api/interactive.py` `call_tool` path
  found: `call_tool` accepts `inputs` and `params` and forwards both into workflow step; no extra requirement that `inputs` be non-empty.
  implication: Mandatory `inputs` is not needed by interactive execution itself and likely should default to `{}` at the MCP method boundary.

- timestamp: 2026-03-04T17:13:37+08:00
  checked: Search for concrete `filename` error and execution validation markers
  found: `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` emits `"filename is required"`; `api/execution.py` has multiple `validation_failed` exits.
  implication: Runtime failure on `inputs`-only calls is likely expected parameter validation inside tool execution, not proof that inputs are semantically required.

- timestamp: 2026-03-04T17:15:48+08:00
  checked: `tools/tttrlib/manifest.yaml`, `tools/tttrlib/.../entrypoint.py`, and `api/execution.py` step parsing
  found: `tttrlib.TTTR` declares `inputs: []` and `params_schema.required=[filename]`; handler reads only `params["filename"]`; execution normalizes missing step inputs via `inputs = step.get("inputs") or {}`.
  implication: `inputs` is truly optional for this function and should not be required by top-level `run` method signature.

- timestamp: 2026-03-04T17:18:39+08:00
  checked: `sessions/manager.py` and `sessions/store.py` session lifecycle
  found: `ensure_session` does `get_session` then `create_session`; `create_session` performs plain `INSERT` into `sessions` primary key without conflict handling.
  implication: Parallel callers can both miss then insert, yielding intermittent `UNIQUE constraint failed: sessions.session_id`.

- timestamp: 2026-03-04T17:19:38+08:00
  checked: Test index under `tests/`
  found: Existing modules include `test_server_session_race.py` (race coverage) and server/session manager unit tests.
  implication: We can verify a minimal fix by extending focused tests instead of adding broad new suites.

- timestamp: 2026-03-04T17:20:30+08:00
  checked: `tests/unit/api/test_server_call_tool.py` and `tests/unit/sessions/test_session_manager.py`
  found: Current run-tool test only validates optional `params` while still providing `inputs={}`; session manager tests lack behavior for duplicate-create race (`create_session` raising integrity error).
  implication: Need explicit regression tests for omitted `inputs` and idempotent `ensure_session` under concurrent creation.

- timestamp: 2026-03-04T17:21:38+08:00
  checked: Focused test execution before fix
  found: `test_server_call_tool.py` currently fails with `NameError` (`_DummyArtifacts` undefined), masking run-contract coverage.
  implication: Test file needs correction before it can validate run API behavior; this likely allowed the contract mismatch to slip through.

- timestamp: 2026-03-04T17:34:16+08:00
  checked: Full read of `tests/unit/api/test_server_call_tool.py` and `api/server.py` run path
  found: `run` is async but test calls it synchronously; `_CapturingInteractive.call_tool` signature does not match positional invocation from `server.run`; typo `_DummyArtifacts` is undefined.
  implication: Existing test cannot exercise run-contract behavior until harness is corrected; regression coverage must include async invocation without `inputs`.

- timestamp: 2026-03-04T17:34:16+08:00
  checked: `sessions/store.py` create path and `sessions/manager.py` ensure logic
  found: `create_session` raises native `sqlite3.IntegrityError` on duplicate primary key and `ensure_session` has no retry/readback path.
  implication: A minimal race-safe fix is catching integrity errors in `ensure_session` and re-reading/updating the existing session.

- timestamp: 2026-03-04T17:37:36+08:00
  checked: `pytest tests/unit/api/test_server_call_tool.py tests/unit/sessions/test_session_manager.py -q`
  found: New regressions fail exactly as expected: `run()` raises missing required `inputs`, and `ensure_session()` propagates `sqlite3.IntegrityError` during duplicate create race.
  implication: Tests provide direct failing proof for both root-cause mechanisms before production changes.

- timestamp: 2026-03-04T17:39:59+08:00
  checked: `pytest tests/unit/api/test_server_call_tool.py tests/unit/sessions/test_session_manager.py -q` after patch
  found: Both regressions pass and the full two-module set is green (13 passed).
  implication: Defaulted `inputs` and integrity-retry logic address the identified failures in targeted scope.

- timestamp: 2026-03-04T17:40:46+08:00
  checked: `pytest tests/unit/api/test_server_session.py tests/unit/api/test_server_session_race.py -q`
  found: Adjacent server/session unit tests pass (6 passed), including the race-focused coverage module.
  implication: No immediate regressions detected in nearby API/session behavior.

## Resolution

root_cause: `api/server.py` declares `run(inputs: dict[str, Any])` as required even for functions with no input ports (e.g., `tttrlib.TTTR`), while execution treats missing inputs as `{}` and relies on `params`; additionally, `SessionManager.ensure_session` uses a non-atomic get-then-create path and does not handle concurrent duplicate insert conflicts.
fix: Defaulted `run.inputs` to optional `{}` in `api/server.py`, added `sqlite3.IntegrityError` recovery/readback path in `SessionManager.ensure_session`, and repaired/extended focused regressions in run/session unit tests.
verification: Self-verified with `pytest tests/unit/api/test_server_call_tool.py tests/unit/sessions/test_session_manager.py -q` (13 passed) and `pytest tests/unit/api/test_server_session.py tests/unit/api/test_server_session_race.py -q` (6 passed); user confirmed params-only `tttrlib.TTTR` run works without `inputs` and parallel same-session calls no longer hit `UNIQUE constraint failed: sessions.session_id`.
files_changed:
  - src/bioimage_mcp/api/server.py
  - src/bioimage_mcp/sessions/manager.py
  - tests/unit/api/test_server_call_tool.py
  - tests/unit/sessions/test_session_manager.py
