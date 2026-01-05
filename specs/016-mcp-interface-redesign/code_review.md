# Code Review: 016-mcp-interface-redesign

Reviewed at: 2026-01-05T15:28:21+01:00

## Summary Table

| Category | Status | Details |
|----------|--------|---------|
| Tasks | FAIL | `specs/016-mcp-interface-redesign/tasks.md` contains no completed (`[x]`) tasks, so there is no authoritative checklist to validate against the implemented commits (which reference many `T0xx` task IDs). |
| Tests | PASS | Targeted contract tests for the 8-tool surface + `tests/unit/api` + one `tests/integration/test_end_to_end.py::test_session_export_replay_flow` all passed. |
| Coverage | HIGH | No coverage tooling detected in `pyproject.toml` (no `pytest-cov`), but the feature is backed by contract + unit + integration tests across discovery/execution/artifacts/sessions. |
| Architecture | PASS | Code structure matches `specs/016-mcp-interface-redesign/plan.md` (handlers under `src/bioimage_mcp/api/`, contract/unit/integration tests added). Notable contract/implementation drift called out below. |
| Constitution | FAIL | Constitution III states heavy I/O libraries must not be installed into the core server env, but `pyproject.toml` lists `bioio`, `bioio-ome-zarr`, and `bioio-ome-tiff` as core dependencies. |

## Scope / Where Changes Landed

Key implementation areas (from recent commits on `016-mcp-interface-redesign`):

- `src/bioimage_mcp/api/server.py`: registers exactly 8 MCP tools (`list`, `describe`, `search`, `run`, `status`, `artifact_info`, `session_export`, `session_replay`).
- `src/bioimage_mcp/api/discovery.py`: implements `list`/`describe`/`search` handlers incl. pagination, child counts, I/O summaries, and basic structured errors.
- `src/bioimage_mcp/api/execution.py`: implements `run_workflow` (used by `run`) and `get_run_status` (`status`), plus validation and artifact materialization paths.
- `src/bioimage_mcp/api/sessions.py` + `src/bioimage_mcp/api/interactive.py`: session step tracking + export/replay wiring.
- `src/bioimage_mcp/api/artifacts.py`: `artifact_info` metadata + optional text preview.
- `tests/contract/`, `tests/unit/api/`, `tests/integration/`: broad test coverage for the redesigned surface.

## Findings

- **CRITICAL**: Constitution III dependency violation.
  - Evidence: `pyproject.toml` includes `bioio`, `bioio-ome-zarr`, `bioio-ome-tiff` in `[project].dependencies`.
  - Why it matters: Constitution III explicitly says heavy/fragile I/O stacks must not be installed in the core server environment; they belong in isolated tool envs.

- **HIGH**: Task tracking is not usable for verification.
  - Evidence: `specs/016-mcp-interface-redesign/tasks.md` has no `[x]` entries, but the branch history contains many commits referencing task IDs (e.g., `T043-T054`, `T083-T101`).
  - Why it matters: Review cannot map “completed tasks” to code/behavior as required by the process.

- **HIGH**: Contract document drift vs implemented MCP tool shapes.
  - Evidence: `specs/016-mcp-interface-redesign/contracts/mcp-tools.yaml` defines request/response schemas that differ from the runtime surface in several places:
    - `run` uses `fn_id` parameter in `src/bioimage_mcp/api/server.py`, while the contract uses `RunRequest.id`.
    - `list` accepts `paths` and `flatten` in `src/bioimage_mcp/api/server.py`, but the contract `ListRequest` does not.
    - `session_export` is exposed as a tool, but `InteractiveExecutionService.export_session()` returns only the `workflow_ref` dict (not a `SessionExportResponse` with `session_id`).
  - Why it matters: External clients (and future docs/tests) will disagree on the canonical payloads.

- **MEDIUM**: Path allowlist check is string-prefix based.
  - Evidence: `src/bioimage_mcp/api/sessions.py` checks `str(dest_path.absolute()).startswith(str(Path(root).absolute()))`.
  - Risk: prefix checks can be tricked by paths like `/allowed/root2/...` when `/allowed/root` is allowed; prefer `Path.resolve()` + `is_relative_to()` style checks.

- **MEDIUM**: Some Pydantic models use mutable defaults.
  - Evidence: `src/bioimage_mcp/api/schemas.py` contains fields like `tags: list[str] = []`, `checksums: list[ArtifactChecksum] = []`, etc.
  - Risk: depending on Pydantic handling and usage patterns, mutable defaults can lead to surprising shared state; `Field(default_factory=list)` is safer.

- **LOW**: Some error responses do not consistently include `details`/`hint`.
  - Evidence: several `NOT_FOUND` paths return only `{code, message}` (e.g., `src/bioimage_mcp/api/artifacts.py`).
  - Impact: this is less LLM-actionable than the stated FR-024..FR-026 model; tests currently only assert `error.code`.

## Tests Run

- Contract (targeted):
  - `pytest -p no:cacheprovider -q tests/contract/test_tool_surface.py tests/contract/test_list.py tests/contract/test_describe.py tests/contract/test_search.py tests/contract/test_run.py tests/contract/test_status.py tests/contract/test_artifact_info.py tests/contract/test_session_export.py tests/contract/test_session_replay.py`
- Unit:
  - `pytest -p no:cacheprovider -q tests/unit/api`
- Integration (targeted):
  - `pytest -p no:cacheprovider -q tests/integration/test_end_to_end.py::test_session_export_replay_flow`

All of the above passed in this environment.

## Remediation / Suggestions

1. Align Constitution III with packaging:
   - Either remove `bioio*` from core `[project].dependencies` (move to tool-pack env specs / optional extras), or amend Constitution III explicitly if the intent is to ship them in-core.

2. Resolve contract drift:
   - Pick a canonical request/response shape for each tool (especially `run` and `session_export`) and make the contract (`specs/016-mcp-interface-redesign/contracts/mcp-tools.yaml`), `server.py` signatures, and docs/tests converge.

3. Improve filesystem allowlist safety:
   - Replace prefix checks with path-aware containment checks (`resolve()` + `is_relative_to()`), and add a contract test for the bypass scenario.

4. Tighten structured errors:
   - Ensure all tool errors return `{code, message, details:[{path,hint,...}]}` consistently, including `NOT_FOUND` cases.

5. Make tasks verifiable:
   - Update `specs/016-mcp-interface-redesign/tasks.md` to reflect completion state (or add an authoritative “Done” checklist) so review can be traced to requirements.

---

# Addendum (per follow-up): Spec takes precedence

Reviewed at: 2026-01-05T16:08:43+01:00

## Updated Summary Table

| Category | Status | Details |
|----------|--------|---------|
| Tasks | FAIL | Implementation appears largely complete, but `specs/016-mcp-interface-redesign/tasks.md` still has no `[x]` items. See “Task tracking update” below for a proposed checklist update. |
| Tests | FAIL | Targeted 016 contract/unit/integration tests pass, but running the full repository test suite surfaces failures outside the targeted 016 surface and a few interface expectation mismatches. |
| Coverage | HIGH | No `pytest-cov` detected; however, 016 has strong contract + unit + integration coverage. |
| Architecture | FAIL | The implementation currently diverges from `specs/016-mcp-interface-redesign/quickstart.md` request/response shapes (notably `run` and `session_export`), which are part of the spec package. |
| Constitution | PASS | The `bioio*` dependencies are explicitly allowed per current spec decisions; the constitution text should be updated to reflect this policy and avoid false positives. |

## Constitution alignment (correction)

- The prior “Constitution III dependency violation” is reclassified as a **documentation conflict**, not an implementation violation.
- Recommendation: Update `.specify/memory/constitution.md` to clarify that `bioio` / `bioio-ome-*` are permitted in the core server environment (at least for lightweight metadata extraction), while still disallowing heavy/fragile stacks (e.g. PyTorch, TensorFlow, Java/Fiji).

## Task tracking update (verification + proposed checkbox changes)

### What I verified

- There are 121 task IDs in `specs/016-mcp-interface-redesign/tasks.md`.
- 92/121 task IDs are referenced by commits on this branch (since `origin/016-mcp-interface-redesign`), and the remaining 29 are not referenced in commit messages.
- For many of the “not referenced” tasks, the tests/code still exist (e.g. `T102`–`T104` and `T120`–`T121` are present in `tests/integration/test_end_to_end.py`).

### Proposed updates to `specs/016-mcp-interface-redesign/tasks.md`

If the intent is “016 is implemented”, the following are the items that appear **done** based on code + tests:

- Mark **[x] Phase 1**: `T001`–`T003` (structure exists; pytest deps present; `tests/contract/` exists).
- Mark **[x] Phase 2**: `T004`–`T031` (new 8-tool models present; deprecated tool handlers removed from MCP surface; structured error helpers exist).
- Mark **[x] Phase 3**: `T032`–`T054` (list/describe/run/status contract tests exist; handlers implemented; params_schema filtering present).
- Mark **[x] Phase 4**: `T055`–`T066` plus `T112` (search contract tests exist; handler implements query/keywords exclusivity, tags and io filters, ranking).
- Mark **[x] Phase 5**: `T067`–`T072` (dry-run validation tests exist; `ExecutionService.run_workflow(..., dry_run=True)` path exists).
- Mark **[x] Phase 6**: `T073`–`T082` (artifact_info contract tests exist; handler supports checksums and text preview).
- Mark **[x] Phase 7**: `T083`–`T101` plus `T113`, `T117`, `T118` (session export/replay tests exist; allowlist enforcement exists, though safety improvement recommended).
- Mark **[x] Phase 8 Integration**: `T102`–`T104`, `T119`–`T121` (integration tests exist).

Items that appear **incomplete or inconsistent with the spec package**:

- Keep **[ ] `T105` / `T115` / `T116`**: migration + semver bump documentation looks incomplete (e.g., `docs/reference/tools.md` does not contain the “13-tool → 8-tool” MCP migration section described in `tasks.md`, and `pyproject.toml` still shows `version = "0.0.0"`).
- Treat **`T114` as PARTIAL**: the spec’s edge case says `session_replay` must validate missing functions before execution begins; current behavior defers to execution and does not clearly surface a pre-execution validation failure.

## Remaining issues to remediate (spec-first decisions)

### 1) API surface mismatch vs `specs/016-mcp-interface-redesign/quickstart.md`

`quickstart.md` is explicit that:
- `run` request uses `{ "id": <fn_id>, "inputs": {port: ref_id}, "params": {...}, "dry_run": ... }`.
- `session_export` response includes `{ "session_id": ..., "workflow_ref": ... }`.

However, `src/bioimage_mcp/api/server.py` currently exposes:
- `run(fn_id=..., inputs=..., params=..., ...)` (parameter name mismatch)
- `session_export(...)` returning only `workflow_ref` (missing `session_id` wrapper)

Remediation direction (spec-first): either align `server.py` signatures and return shapes to the quickstart, or update `quickstart.md` and `contracts/mcp-tools.yaml` to match the chosen runtime surface.

### 2) Structured error completeness

The spec package (`spec.md` + `quickstart.md`) describes error payloads with `details` including JSON Pointer `path` and actionable `hint` for all tools.

Current state: some tools return only `{code, message}` (e.g., `artifact_info` NOT_FOUND).

Remediation direction (spec-first): ensure all tool errors include `details[]` consistently and update contract tests to enforce this.

### 3) `session_replay` pre-validation for missing functions (Edge case / `T114`)

Spec edge case: “function no longer exists” should yield a validation error *before execution begins*.

Current state: `SessionService.replay_session()` executes step-by-step and relies on the underlying execution path; the contract test currently asserts a “running” status even when an error is attached.

Remediation direction (spec-first): add an explicit preflight validation step that verifies all `WorkflowRecord.steps[*].id` exist in the registry/manifest view; return `validation_failed` with a structured error if any are missing.

### 4) Filesystem allowlist safety

`SessionService.export_session()` uses a string-prefix allowlist check. This should be upgraded to path-aware containment checks.

Remediation direction: use `Path.resolve()` and `is_relative_to()` semantics (or an equivalent safe containment helper) and add a test covering the prefix-bypass class of issues.

### 5) Pydantic mutable defaults

Several models in `src/bioimage_mcp/api/schemas.py` use mutable defaults (`[]`, `{}`).

Remediation direction: switch to `Field(default_factory=list)` / `Field(default_factory=dict)` across models.

## Tests (additional evidence)

- Targeted 016 tests still pass (as previously recorded).
- Running the full repo suite (`pytest`) shows failures; the earliest failures include:
  - `scripts/test_materialize_real.py::test_materialize_real` (expects `_materialize_zarr_to_file` to return a file-backed ref; currently stubbed)
  - `scripts/test_materialize_zarr.py::test_materialize_zarr_dir` (fails inside `bioio_ome_zarr` reader on a minimally faked Zarr directory)
  - `tests/integration/test_call_tool_dry_run.py::test_call_tool_dry_run_validation_failure` (expects status `failed` but implementation returns `validation_failed`)
  - `tests/integration/test_call_tool_hints.py::test_run_workflow_error_includes_hints` (expects `suggested_fix.id` but schema/model uses `fn_id`)

These suggest there is remaining interface/test harmonization work across the broader repo beyond the 016-focused contract suite.

## Note on operating constraints

This addendum records remediation guidance only. Code/docs changes (including constitution and task checkbox updates) require a non-read-only run.
