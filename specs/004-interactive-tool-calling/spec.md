# Feature Specification: Interactive Tool Calling

**Feature Branch**: `004-interactive-tool-calling`  
**Created**: 2024-12-22  
**Status**: Draft  
**Input**: User description: "Switch from batch 'Plan-then-Execute' model to an interactive REPL-style tool calling model where the LLM executes tools one by one, observes results immediately, and retains reproducibility through session logging."

## Clarifications

### Session 2025-12-22
- Q: Long-running execution contract? → A: Hybrid: support MCP Tasks when requested/supported, plus tool-level `run_id` polling fallback; internally unify IDs.
- Q: Error transport contract (protocol vs execution)? → A: Hybrid: validation/preflight failures use JSON-RPC invalid params (e.g., `-32602`); execution/runtime failures return a tool result with `isError: true` and structured diagnostics (including log reference).
- Q: How are manifest functions exposed for interactive calling? → A: Selective native tools: register manifest functions as MCP tools but expose per-session via `activate_functions` + `notifications/tools/list_changed`; keep `call_tool` as a compatibility fallback.
- Q: Session resumption after server restart? → A: Add `resume_session(session_id)` MCP tool to attach an existing persisted session to the current connection; other tools remain implicit.
- Q: How does the client obtain the `session_id` for resumption? → A: Include `session_id` in `structuredContent` for all session-affecting tool responses (at least `call_tool`, native manifest tool calls, `activate_functions`, `deactivate_functions`, `export_session`, `resume_session`) and include it in error responses.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Step-by-Step Image Analysis (Priority: P1)

A researcher wants to analyze a microscopy image by trying different preprocessing filters and segmentation parameters. Instead of planning the entire workflow upfront, they want to execute one step at a time, inspect the results, and adjust their approach based on what they see.

**Why this priority**: This is the core value proposition of interactive tool calling—enabling exploratory, iterative analysis workflows that match how researchers naturally work. Without this, the feature has no value.

**Independent Test**: Can be fully tested by executing a sequence of 3+ tool calls in an interactive session, inspecting intermediate results, and verifying the session records all steps.

**Acceptance Scenarios**:

1. **Given** a user has loaded a microscopy image, **When** they request a Gaussian blur with sigma=2.0, **Then** the system executes the operation and returns the result artifact reference with a lightweight summary (dimensions, dtype, approximate size) and the current `session_id`.
2. **Given** a user has executed a preprocessing step, **When** they request a different preprocessing approach, **Then** the system executes the new operation on the original input without requiring a full workflow resubmission.
3. **Given** a user has executed multiple steps interactively, **When** they request to export their session, **Then** the system generates a reproducible workflow artifact containing all successful steps in order.

---

### User Story 2 - Error Recovery and Retry (Priority: P1)

A researcher encounters an error during tool execution (e.g., invalid parameters, incompatible artifact types). They want to understand what went wrong and retry with corrected parameters without losing their session progress.

**Why this priority**: Error recovery is essential for practical usability. The current batch model forces macro-retries of entire workflows; interactive mode must enable micro-retries at the step level.

**Independent Test**: Can be fully tested by intentionally triggering a tool error, receiving structured error feedback, and successfully retrying the operation with corrected parameters.

**Acceptance Scenarios**:

1. **Given** a user submits invalid parameters for a tool, **When** the tool fails validation, **Then** the system returns structured error details (as a JSON-RPC invalid params error) including the specific validation failures, the current `session_id`, and how to correct them.
2. **Given** a tool execution fails, **When** the user retries with corrected parameters, **Then** the previous failed attempt is logged (not lost), and only the successful retry is marked as the canonical step for workflow export.
3. **Given** a user has completed 3 successful steps, **When** step 4 fails, **Then** the user can retry step 4 without re-executing steps 1-3.

---

### User Story 3 - Selective Tool Activation (Priority: P2)

A researcher working on cell segmentation wants to focus on segmentation-related tools without being overwhelmed by the full catalog of 50+ available tools. They want to activate only a relevant subset of tools for their current task.

**Why this priority**: Selective activation reduces cognitive load for the LLM and addresses client-side tool limits (e.g., Windsurf's 100-tool limit). However, interactive execution (P1) can work without this feature using the `call_tool` wrapper.

**Independent Test**: Can be fully tested by activating a subset of tools, verifying only those tools appear in tool discovery, and deactivating them when done.

**Acceptance Scenarios**:

1. **Given** the system has 50 registered tools, **When** a user activates only segmentation-related tools, **Then** tool discovery returns only the activated subset.
2. **Given** tools have been selectively activated, **When** the user attempts to call a non-activated tool directly, **Then** the system either allows it via the `call_tool` wrapper or provides clear feedback about activation requirements.
3. **Given** tools have been activated for a session, **When** the user deactivates them, **Then** the tools are no longer visible in subsequent discovery calls.

---

### User Story 4 - Workflow Export and Replay (Priority: P2)

A researcher has completed an exploratory analysis session and wants to save the final workflow for reproducibility, sharing with colleagues, or batch processing of similar images.

**Why this priority**: Preserving reproducibility is a core project principle, but it builds on top of the interactive session logging (P1 stories).

**Independent Test**: Can be fully tested by completing an interactive session, exporting it as a workflow, and replaying that workflow on a different input image.

**Acceptance Scenarios**:

1. **Given** a user has completed an interactive session with 5 successful steps, **When** they export the session, **Then** the system generates a workflow artifact in the same format as batch workflows.
2. **Given** an exported workflow from an interactive session, **When** a user replays it on a new input, **Then** the system executes all steps with the same parameters and tool versions.
3. **Given** a session with multiple retry attempts on a step, **When** the session is exported, **Then** only the final successful attempt for each step is included in the workflow.

---

### User Story 5 - Compatibility Fallback for Static Clients (Priority: P3)

A user's MCP client does not support dynamic tool discovery (e.g., `notifications/tools/list_changed`). They still want to use interactive tool calling through a generic wrapper.

**Why this priority**: Important for broad compatibility, but the primary use case (P1) works with clients that support dynamic discovery. This is a fallback path.

**Independent Test**: Can be fully tested by using the `call_tool` wrapper to execute tools in an interactive session without relying on dynamic tool registration.

**Acceptance Scenarios**:

1. **Given** a client that does not support dynamic tool discovery, **When** a user calls `call_tool` with a valid function ID and parameters, **Then** the system executes the tool and returns results in the same format as native tool calls (including `session_id`).
2. **Given** a user provides invalid parameters via `call_tool`, **When** validation fails, **Then** the system returns structured errors identical to native tool call failures (including `session_id`).
3. **Given** a user wants to validate parameters before execution, **When** they call `call_tool` with `dry_run=true`, **Then** the system validates inputs/params without executing and returns validation results.

---

### Edge Cases

- What happens when a session is abandoned without export (no explicit end)? System applies TTL-based cleanup after configurable idle period.
- What happens when a tool execution exceeds timeout? System returns timeout error with partial logs and allows retry with adjusted timeout.
- What happens when the server restarts mid-session? Session state is persisted incrementally; sessions can resume from last successful step via `resume_session(session_id)`.
- What happens when artifact references from a session become invalid (file deleted)? System detects invalid refs during replay and fails fast with clear error.
- What happens when a user activates conflicting tool versions? System validates compatibility and rejects activation with explanation.

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: Adds new MCP tools (`activate_functions`, `deactivate_functions`, `export_session`, `resume_session`, `call_tool`). Existing tools remain unchanged. Emits `notifications/tools/list_changed` when active tool set changes. No breaking changes to existing endpoints.
- **Artifact I/O**: All tool inputs/outputs continue to use typed artifact references (BioImageRef, LabelImageRef, etc.). Session exports produce NativeOutputRef with format `workflow-record-json`. No embedded large payloads.
- **Isolation**: Tool execution continues in isolated subprocess environments (`bioimage-mcp-*` conda envs). Session state managed in core server only. No changes to tool isolation model.
- **Reproducibility**: Sessions record linear history of all attempts (including failures) with timestamps, tool versions, lockfile hashes, and parameters. Exported workflows contain only canonical (successful) steps. Replay uses recorded environment fingerprints.
- **Safety/observability**: Structured logging for all session events. Per-step logs captured as LogRef artifacts. Session cleanup via TTL to prevent resource leaks. All changes require automated tests.

### Functional Requirements

- **FR-001**: System MUST maintain an implicit session for each MCP connection to group related tool executions.
- **FR-002**: System MUST record every tool execution attempt in the session's linear history, including failures and retries.
- **FR-003**: System MUST provide structured error feedback using MCP-aligned transports: preflight/validation failures as JSON-RPC invalid params (e.g., `-32602`), and execution/runtime failures as tool results with `isError: true`, including error code/message, validation errors (if any), and a log reference.
- **FR-004**: System MUST return lightweight output summaries (dimensions, dtype, approximate size) alongside artifact references for fast feedback.
- **FR-005**: System MUST provide an `export_session` tool that generates a workflow artifact from the session's canonical steps.
- **FR-006**: System MUST provide `activate_functions` and `deactivate_functions` tools to control which manifest functions appear in tool discovery.
- **FR-007**: System MUST emit `notifications/tools/list_changed` when the active tool set changes, for clients that support this notification.
- **FR-008**: System MUST register manifest functions as MCP tools but expose them selectively per-session via the active tool set.
- **FR-009**: System MUST provide a `call_tool` wrapper for clients that cannot use dynamically registered tools.
- **FR-010**: System MUST support `dry_run` mode in `call_tool` for validation-only execution.
- **FR-011**: System MUST apply configurable TTL-based cleanup for abandoned sessions to prevent resource leaks.
- **FR-012**: System MUST persist session state incrementally to survive server restarts.
- **FR-013**: System MUST distinguish between failed attempts and canonical successful steps when exporting sessions.
- **FR-014**: System MUST validate artifact type compatibility before tool execution (preflight validation).
- **FR-015**: System MUST support long-running tool executions via `run_id` with status/result polling tools (compatibility fallback).
- **FR-016**: System MUST support the MCP Tasks pattern for long-running tool calls when requested by the client (return `taskId`; support `tasks/get` and `tasks/result`), and MUST unify `taskId` and `run_id` internally for observability and export.
- **FR-017**: System MUST provide a `resume_session(session_id)` tool that attaches a persisted session to the current MCP connection so interactive workflows can continue after a server restart.
- **FR-018**: System MUST include `session_id` in `structuredContent` for all session-affecting tool responses (at least `call_tool`, native manifest tool calls, `activate_functions`, `deactivate_functions`, `export_session`, `resume_session`) and MUST include `session_id` in error responses.

### Key Entities

- **Session**: Represents a grouped sequence of tool executions tied to an MCP connection. Identified by a `session_id`. Contains a linear history of steps, timestamps, and active tool set.
- **Step**: A single tool execution attempt within a session. Includes function ID, inputs, params, outputs (or error), timing, and canonical flag.
- **ActiveToolSet**: The subset of manifest functions currently exposed via MCP tool discovery for a given session.
- **SessionExport**: A workflow artifact generated from a session's canonical steps, compatible with batch `run_workflow` format.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: LLM can execute a 5-step exploratory analysis workflow with at least one mid-workflow retry, completing within the same session without restarting.
- **SC-002**: Failed tool executions provide actionable feedback that enables successful retry in 90% of cases without human intervention.
- **SC-003**: Exported interactive session workflows can be successfully replayed via batch execution with identical results.
- **SC-004**: Session state persists across server restarts with zero data loss for sessions with activity in the last hour.
- **SC-005**: Abandoned sessions are cleaned up within the configured TTL window (default: 24 hours of inactivity).
- **SC-006**: Selective tool activation reduces visible tool count by at least 50% for task-focused sessions.
- **SC-007**: Interactive round-trip latency (tool call to response) remains under 5 seconds for typical image operations on standard hardware.

## Assumptions

- MCP clients that do not support `notifications/tools/list_changed` will use the `call_tool` wrapper fallback.
- Session TTL defaults to 24 hours but is configurable.
- Tool execution timeouts follow existing timeout configuration (default 2 minutes).
- Session persistence uses the existing artifact/run stores; no new external dependencies required.
- The `run_workflow` tool continues to support batch execution for saved/exported workflows.
- Clients that request MCP Tasks (via the protocol `task` parameter) will receive a `taskId` and can poll via `tasks/get` / `tasks/result`; other clients can rely on `run_id` polling.
