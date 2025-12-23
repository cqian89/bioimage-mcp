# Phase 0 Research: Interactive Tool Calling

**Branch**: `004-interactive-tool-calling`  
**Date**: 2025-12-22  
**Spec**: `specs/004-interactive-tool-calling/spec.md`

This document resolves Phase 0 unknowns and records decisions with rationale and alternatives.

## 1) Session persistence storage model

- Decision: Add a dedicated `sessions` table and `session_steps` table in the existing SQLite database (under `artifact_store_root/state/bioimage_mcp.sqlite3`). Store interactive attempts in `session_steps`, and optionally link a step attempt to a `run_id` (execution record) for status/provenance.
- Rationale: The existing `runs` table already models batch workflow executions and stores a workflow spec + outputs. Interactive sessions require (a) a linear history of *attempts* (including failures), (b) canonical step selection for export, (c) TTL cleanup, and (d) per-session active tool set. Modeling these as first-class session entities keeps concerns separated and avoids overloading `runs` semantics.
- Alternatives considered:
  - Extend `runs` with `session_id` and “canonical” flags: rejected because it conflates batch workflow runs with interactive step attempts, and makes session TTL/activation state awkward.
  - Persist sessions only as JSON artifacts: rejected because querying (TTL cleanup, step selection, resume) becomes expensive and brittle.

## 2) Per-connection session identity

- Decision: Use the MCP `ServerSession` (connection) identity as the default session key, but persist a stable `session_id` string that can be returned to clients and re-attached via `resume_session(session_id)` after restart.
- Rationale: The spec requires an implicit session per connection (FR-001) and resumption by explicit ID (FR-017). Persisting a stable `session_id` allows restart-safe resumption while still auto-creating sessions for new connections.
- Alternatives considered:
  - Client-provided session IDs only: rejected because it breaks “implicit session per connection” and increases client burden.
  - Derive ID from transport-level metadata only: rejected because the server must support restart resumption independent of a specific live connection.

## 3) Active tool set persistence

- Decision: Persist the active tool set per session as a normalized mapping table (e.g., `session_active_functions(session_id, fn_id)`), not as a JSON blob.
- Rationale: Activations are frequently updated and must be queryable to filter tool discovery, enforce activation checks, and emit `notifications/tools/list_changed` accurately.
- Alternatives considered:
  - JSON list in `sessions.active_fn_ids_json`: acceptable for MVP but rejected in favor of normalized rows for easier query/update and less JSON churn.

## 4) Selective exposure + `notifications/tools/list_changed`

- Decision: Implement selective exposure at the MCP discovery layer by filtering the *protocol tool list* per session and emitting `notifications/tools/list_changed` on activation changes.
- Rationale: The spec’s P2 story explicitly targets client-side tool limits and requires dynamic tool list change notification. The MCP Python SDK `ServerSession` supports `send_tool_list_changed()`, and `FastMCP` exposes `get_context()` to obtain the current session.
- Alternatives considered:
  - Only filter via the project’s custom discovery tools (`search_functions`): rejected because it does not satisfy the requirement to use `notifications/tools/list_changed` for MCP clients.
  - Register/unregister tools globally on activate/deactivate: rejected because activation is per-session, not global.

## 5) Enforcing activation vs compatibility fallback

- Decision: Enforce activation for direct native tool calls: if a user calls a non-activated manifest function directly, return a clear “not activated” error instructing to call `activate_functions` or use `call_tool`. Always keep `call_tool` available as a compatibility wrapper.
- Rationale: The spec allows either wrapper usage or clear activation feedback. Enforcing activation preserves the point of selective exposure while still enabling universal access via wrapper.
- Alternatives considered:
  - Allow native calls regardless of activation: rejected because it makes activation meaningless.

## 6) Error transport contract (validation vs runtime)

- Decision: Split failures into:
  - Validation/preflight failures → JSON-RPC invalid params (`-32602`) with structured diagnostics and `session_id`.
  - Execution/runtime failures → successful tool response envelope with `isError: true` and structured `error` details (including a `LogRef`).
- Rationale: This matches the feature clarifications and provides actionable retries without losing session history.
- Alternatives considered:
  - Always return `isError: true`: rejected because invalid-params is a protocol-aligned, strongly-typed failure mode and should be used for deterministic validation errors.

## 7) Output summaries (fast feedback)

- Decision: Return lightweight output summaries alongside artifact refs for interactive calls (dimensions, dtype, approximate size bytes) while keeping artifact payloads reference-only.
- Rationale: This satisfies FR-004 and maintains constitution constraints (no large payloads).
- Alternatives considered:
  - Return full arrays/preview thumbnails inline: rejected (violates Artifact References Only and Stable MCP Surface constraints).

## 8) Long-running execution contract (`taskId` vs `run_id`)

- Decision: Unify identifiers internally by using the existing `run_id` as the `taskId` when the MCP Tasks pattern is requested. Keep existing `get_run_status(run_id)` as the polling fallback for clients that do not use Tasks.
- Rationale: The codebase already has durable `run_id` lifecycle tracking in SQLite via `RunStore` and `ExecutionService.get_run_status`. Reusing that ID avoids duplicative identifiers and improves observability.
- Alternatives considered:
  - Introduce a new `task_id` namespace: rejected due to redundant identifiers and additional persistence complexity.

## 9) Session export format

- Decision: Export a session as a `NativeOutputRef` with format `workflow-record-json`, containing only canonical successful steps in order, plus enough provenance to replay.
- Rationale: Aligns with existing workflow record artifact patterns in `ExecutionService.run_workflow` and satisfies FR-005/FR-013.
- Alternatives considered:
  - Export as a bespoke “session format”: rejected to preserve replay compatibility and stable contract reuse.
