# Code Review: 019-artifact-management

**Review timestamp (UTC):** 2026-01-09T19:00:59Z

## Summary Table

| Category | Status | Details |
|----------|--------|---------|
| Tasks    | FAIL | Core storage models/service/migrations are present, but several spec/plan items are inconsistent (e.g., CLI contract mismatches; `--force` has no effect; missing confirmation behavior). |
| Tests    | FAIL | `pytest tests/unit tests/contract` has 8 failures (Cellpose + CLI parser tests). Storage-focused tests pass. |
| Coverage | LOW | No coverage tooling (`pytest-cov`) available; storage module has strong unit coverage, but critical cross-paths (quota -> interactive `run`) are not covered. |
| Architecture | FAIL | Deviations from `specs/019-artifact-management/plan.md` and CLI contract docs; new MCP tool added despite plan constraint. |
| Constitution | FAIL | `.specify/memory/constitution.md` mandates exactly 8 MCP tools; code/tests expose 9 (`session_complete`). |

## Scope / What Changed

Key implementation areas on this branch (relative to `main..HEAD`):

- Storage management:
  - `src/bioimage_mcp/storage/sqlite.py`: schema migration (`sessions.completed_at`, `sessions.is_pinned`, `artifacts.session_id` + index) and backfill.
  - `src/bioimage_mcp/storage/models.py`: `StorageStatus`, `QuotaCheckResult`, `PruneResult`, etc.
  - `src/bioimage_mcp/storage/service.py`: quota check, status breakdown, session listing, pruning, orphan scan/deletion.
  - `src/bioimage_mcp/cli.py`: `bioimage-mcp storage {status,prune,pin,list}`.

- Quota enforcement integration:
  - `src/bioimage_mcp/api/execution.py`: quota check added before running workflows.

- Session lifecycle integration:
  - `src/bioimage_mcp/sessions/store.py` + `src/bioimage_mcp/sessions/manager.py`: session completion stamped into DB.

- Documentation:
  - `specs/019-artifact-management/*` + updates in `README.md` and `AGENTS.md`.

## Findings

### CRITICAL

1) **Constitution violation: MCP tool surface is no longer 8 tools**
- Constitution I requires exactly 8 tools (`list`, `describe`, `search`, `run`, `status`, `artifact_info`, `session_export`, `session_replay`).
- Current code registers an additional tool: `session_complete`.
  - `src/bioimage_mcp/api/server.py` registers `session_complete`.
  - `tests/contract/test_tool_surface.py` asserts 9 tools.
  - `README.md` still documents 8 tools.

2) **Quota enforcement likely breaks interactive tool calls (runtime correctness issue)**
- `ExecutionService.run_workflow()` returns a quota failure with `run_id: "none"`.
- `InteractiveExecutionService.call_tool()` always calls `get_run_status(result["run_id"])`; for `run_id="none"`, that path returns a “run not found” payload and `call_tool` will KeyError when reading `run_status["status"]`.
- Result: quota-exceeded scenarios can surface as internal errors rather than structured quota errors.

3) **Test-suite cross-contamination causes deterministic failures**
- Running `pytest tests/unit tests/contract` fails in unit tests `tests/unit/test_cellpose_dynamic_dispatch.py`.
- Root cause is very likely `tests/contract/test_cellpose_introspection_types.py` deleting `sys.modules[...]` entries for `bioimage_mcp_cellpose*` at import time, which can invalidate already-imported symbols in other test modules.

### HIGH

4) **CLI command contract mismatches / incomplete safety behavior**
- `specs/019-artifact-management/contracts/cli.md` describes:
  - `storage prune --json` output (not implemented in `src/bioimage_mcp/cli.py`).
  - Confirmation prompt for destructive prune unless `--force` (current handler ignores `--force` and performs deletion without confirmation).
  - `storage list` default limit 50 (current default is 20).

5) **Unit test mismatch for `unpin` command**
- `tests/unit/test_cli_storage.py` expects `bioimage-mcp storage unpin <id>` subcommand.
- Actual CLI is `bioimage-mcp storage pin <id> --unpin`.

6) **Cross-platform concern: `fcntl` lock is not available on Windows**
- `src/bioimage_mcp/storage/service.py` uses `fcntl.flock` for prune locking. This will break on Windows if storage CLI is expected to work there.

### MEDIUM

7) **Dead code / unreachable return**
- `src/bioimage_mcp/storage/service.py` ends `_do_prune()` with duplicated `return res`.

8) **Status breakdown may omit “legacy/global” artifacts**
- `StorageService.get_status()` totals all artifacts, but per-state breakdown only includes artifacts joined to `sessions`. If `artifacts.session_id` is NULL (legacy/global), totals may not reconcile.

## Tests Run

- Full suite (unit + contract):
  - `pytest -p no:cacheprovider tests/unit tests/contract`
  - Result: **8 failures** (Cellpose + CLI parser tests), plus some skipped/xfail/xpass.

- Storage-focused subset:
  - `pytest -p no:cacheprovider tests/unit/storage tests/unit/config/test_storage_settings.py tests/contract/test_storage_migration.py tests/contract/test_storage_backfill.py tests/integration/cli/test_storage_cli.py tests/integration/test_storage_quota.py tests/integration/test_storage_pin_cli.py`
  - Result: **PASS**

## Coverage Notes

- `pytest-cov` is not installed in this environment, so no numeric coverage metric was produced.
- Storage feature has broad unit coverage for:
  - `get_status`, `check_quota`, `prune` (dry-run + deletion), pin/unpin behavior
  - edge cases: active sessions, missing files, directory artifacts, interrupted prune, concurrent locking
- Notably missing tests:
  - quota-exceeded path through `InteractiveExecutionService.call_tool()` / MCP `run` tool
  - CLI prune confirmation + `--force` behavior
  - `--json` output for prune per contract

## Remediation / Suggestions

1) **Resolve Constitution I conflict**
- Either:
  - remove `session_complete` from the MCP surface and keep session completion internal/CLI-only.

2) **Fix interactive quota error handling**
- Ensure quota failure returns a structured error through MCP without crashing.
  - Option A: Create a RunStore entry before quota check and return a real `run_id` even on failure.

3) **Stabilize test isolation for Cellpose tool pack**
- Avoid deleting `sys.modules` at module import time in contract tests.
- Prefer fixtures that temporarily modify `sys.path` and reload modules, and restore them after the test.

4) **Align CLI implementation with `specs/019-artifact-management/contracts/cli.md`**
- Add `--json` to `storage prune` and ensure output matches `PruneResult`.
- Implement confirmation prompt unless `--force`.
- Align defaults (e.g., list `--limit` default).

5) **Make locking cross-platform**
- Replace `fcntl` lock with a cross-platform lock strategy (e.g., `filelock` / `portalocker`)
