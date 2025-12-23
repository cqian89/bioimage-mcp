# Phase 1 Data Model: Interactive Tool Calling

**Branch**: `004-interactive-tool-calling`  
**Date**: 2025-12-22  
**Spec**: `specs/004-interactive-tool-calling/spec.md`

This document describes the core entities required for interactive, step-by-step execution with session persistence, retries, and export.

## Entities

### Session

- Purpose: Group a user’s interactive tool executions for a single exploratory workflow, tied to an MCP connection by default but resumable via `session_id`.
- Storage: SQLite table `sessions` (proposed).

Fields (proposed):
- `session_id` (string, primary key): Stable identifier returned to clients.
- `created_at` (ISO timestamp)
- `last_activity_at` (ISO timestamp): Used for TTL cleanup.
- `status` (string): `active|expired|exported` (exact set can be minimal for MVP).
- `connection_hint` (string|null): Best-effort, non-authoritative (for debugging only).

Validation rules:
- `session_id` is opaque and stable.
- Session TTL uses `last_activity_at` and configured TTL hours.

### Session Step Attempt (`SessionStep`)

- Purpose: Record a single tool execution attempt within a session, including failures and retries.
- Storage: SQLite table `session_steps` (proposed).

Fields (proposed):
- `session_id` (FK)
- `step_id` (string or integer PK)
- `ordinal` (integer): Strictly increasing order for the session’s linear history.
- `fn_id` (string)
- `inputs_json` (dict): Artifact ref payloads or references.
- `params_json` (dict)
- `started_at`, `ended_at` (ISO timestamps)
- `status` (string): `succeeded|failed|running|cancelled`.
- `run_id` (string|null): Links to existing `runs` table when execution is performed via the existing run lifecycle.
- `error_json` (dict|null): Structured error for failures.
- `outputs_json` (dict|null): Output artifact refs for successes.
- `log_ref_id` (string|null): `LogRef` artifact for debugging.
- `canonical` (bool): Whether this attempt is the canonical attempt for export.

Validation rules:
- Every attempt must be recorded (FR-002).
- Failed attempts must remain addressable and visible in history.
- Only one canonical attempt per logical “step slot” (modeling may use `logical_step_key` if needed); minimally, canonical can be “last succeeded for a given ordinal grouping”.

### Active Tool Set (`ActiveToolSet`)

- Purpose: The subset of manifest functions exposed for discovery and direct calling in a given session.
- Storage: SQLite table `session_active_functions(session_id, fn_id)` (proposed).

Validation rules:
- `fn_id` must exist in the registry index.
- Activation changes update `sessions.last_activity_at`.

### Session Export (`SessionExport`)

- Purpose: A reproducible workflow artifact generated from canonical steps.
- Storage: `NativeOutputRef` artifact with `format="workflow-record-json"`.

Fields (in the exported JSON, proposed):
- `schema_version`
- `created_at`
- `session_id`
- `steps`: canonical steps only, in order, each containing:
  - `fn_id`
  - `inputs` (artifact refs)
  - `params`
  - `outputs` (artifact refs)
  - `tool_version` and manifest checksum / env fingerprint references
- `attempts`: optional full history reference or counts (full attempts remain in DB for audit)

## Relationships

- A `Session` has many `SessionStep` rows.
- A `Session` has many active `fn_id`s in `session_active_functions`.
- A `SessionExport` references a `Session` and includes only canonical steps.
- A `SessionStep` may reference a `Run` (via `run_id`) when execution is tracked in the existing run subsystem.

## State transitions

- Session: `active` → `exported` (on explicit export) or `active` → `expired` (TTL cleanup).
- Step attempt: `running` → `succeeded|failed|cancelled`.
