# Implementation Plan: Interactive Tool Calling

**Branch**: `004-interactive-tool-calling` | **Date**: 2025-12-22 | **Spec**: `specs/004-interactive-tool-calling/spec.md`
**Input**: Feature specification from `specs/004-interactive-tool-calling/spec.md`

## Summary

Add an interactive (REPL-style) tool calling mode to Bioimage-MCP by introducing a **persisted per-connection Session** with a **linear step history** and a **compatibility wrapper (`call_tool`)**. Optionally expose manifest functions as **native MCP tools per-session** via `activate_functions` / `deactivate_functions`, emitting `notifications/tools/list_changed` for clients that support dynamic discovery.

Primary outcomes:
- Step-by-step execution with immediate feedback (artifacts + lightweight summaries).
- Micro-retry on failures without losing session history.
- Export a session to a reproducible workflow artifact (canonical steps only).
- Resume a persisted session after server restart.

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may differ)

**Primary Dependencies**:
- MCP Python SDK (`mcp`) using `FastMCP` (`mcp.server.fastmcp.server.FastMCP`)
- `pydantic` v2 (validation + wire models)
- SQLite (local state) via `src/bioimage_mcp/storage/sqlite.py`

**Current execution primitives (existing)**:
- `ExecutionService.run_workflow(spec)` runs exactly 1 step today and persists a `Run` plus a `workflow-record-json` artifact (`src/bioimage_mcp/api/execution.py`).
- Tool schemas are summary-first and fetched on demand via `describe_function(fn_id)` which uses `meta.describe` + schema cache (`src/bioimage_mcp/api/discovery.py`).
- Workflow compatibility (artifact type checks) happens pre-execution via `validate_workflow_compatibility` (`src/bioimage_mcp/runtimes/protocol.py`).

**New primitives to add (this feature)**:
- **SessionManager**: persisted session + step history + active tool set.
  - Storage: extend SQLite schema in `src/bioimage_mcp/storage/sqlite.py` with new tables.
  - Session ID source: MCP SDK `ServerSession.session_id` (unique per connection) + allow reattachment via `resume_session(session_id)`.
- **Step history**: record every attempt (success/failure), maintain canonical step selection for export.
  - Recommended modeling: store session steps separately and reference `run_id` (runs already capture execution outcomes + logs + outputs).
- **Selective native tool exposure**:
  - Track `active_fn_ids` per session.
  - Emit `notifications/tools/list_changed` via MCP SDK `ServerSession.send_tool_list_changed()` when active set changes.
  - Keep `call_tool` available for compatibility clients and for calling non-activated functions.

**Error transport contract (hybrid, per spec)**:
- Preflight/validation failures → JSON-RPC invalid params (`-32602`) with structured diagnostics, including `session_id`.
- Execution/runtime failures → tool result with `isError: true` + structured diagnostics + `LogRef`, including `session_id`.

**Long-running contract (hybrid, per spec)**:
- Preserve existing `run_id` polling via `get_run_status(run_id)`.
- When client requests MCP Tasks, return `taskId` and provide task polling; internally unify `taskId` == `run_id`.

**Constraints**:
- Artifact references only (no large payloads in MCP messages).
- Preserve per-tool conda env isolation (`bioimage-mcp-*`).
- Summary-first discovery remains paginated; schema fetched on demand.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Stable MCP surface: new MCP tools are additive and justified (`activate_functions`, `deactivate_functions`, `export_session`, `resume_session`, `call_tool`). No breaking changes.
- [x] Summary-first responses: keep existing discovery contract (`list_tools`/`search_functions` summary-only; schemas via `describe_function`). New tools return compact payloads.
- [x] Tool execution isolated: no change to subprocess/env boundary; interactive calls still execute tools via existing executor.
- [x] Artifact references only: outputs continue to be `ArtifactRef` payloads; lightweight summaries derived from metadata only.
- [x] Reproducibility: session steps persist (including failures); export produces `NativeOutputRef(format="workflow-record-json")` with canonical successful steps.
- [x] Safety + debuggability: persist step logs as `LogRef`; apply TTL cleanup; add automated tests for session/step semantics.

(Reference: `.specify/memory/constitution.md`)

## Project Structure

### Documentation (this feature)

```text
specs/004-interactive-tool-calling/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks) - NOT created by /speckit.plan
```

### Source Code (repository root)

```text
src/bioimage_mcp/
├── api/
│   ├── server.py         # MCP tool registrations
│   ├── discovery.py      # summary-first discovery + describe_function
│   └── execution.py      # run_workflow/run status + workflow record artifacts
├── config/
├── registry/
├── runtimes/
│   ├── executor.py       # subprocess execution boundary
│   └── protocol.py       # workflow compatibility validation
├── runs/
├── storage/
│   └── sqlite.py         # SQLite schema + connect/init
└── ...

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Single Python project with core server under `src/bioimage_mcp/` and tests under `tests/`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
