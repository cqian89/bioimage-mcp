# Quickstart: Interactive Tool Calling

**Branch**: `004-interactive-tool-calling`  
**Date**: 2025-12-22  

This quickstart is a design-time guide for the interactive (REPL-style) tool calling model: execute tools one-by-one, inspect results, retry on errors, and export a reproducible workflow.

## Prerequisites

- Core server (Python 3.13) available.
- Tool manifests configured and discoverable.
- Artifact store and filesystem allowlists configured for your data.

## 1) Start the server

- `python -m bioimage_mcp serve`

## 2) Find a tool to use (summary-first discovery)

Use summary-first discovery to avoid pulling large schemas into context:

1. Call `search_functions(query="gaussian", limit=20, cursor=None)`
2. Select a `fn_id` from the returned summaries.
3. Call `describe_function(fn_id)` only when you need the parameter schema.

## 3) Activate a focused tool subset (optional)

If your client supports dynamic tool discovery, activate only relevant functions:

- Call `activate_functions(["base.gaussian", "base.threshold_otsu", ...])`
- Server emits `notifications/tools/list_changed` so the client refreshes visible tools.

If your client does not support dynamic tool discovery, skip activation and use `call_tool`.

## 4) Execute one step at a time

Preferred paths:

- Native tool call (when visible/activated): call the function tool directly (e.g., `base.gaussian`).
- Compatibility fallback: call `call_tool(fn_id=..., inputs=..., params=..., dry_run=False)`.

Expected response shape (conceptual):
- Always includes `session_id` (in structured content).
- Returns artifact refs for outputs.
- Returns lightweight output summaries (dimensions/dtype/size) for fast iteration.

## 5) Handle validation errors vs runtime errors

- Validation/preflight errors: returned as JSON-RPC invalid params (`-32602`) with structured validation errors and `session_id`.
- Runtime execution errors: returned as a tool result with `isError: true`, structured `error` details, and a `LogRef` for debugging.

## 6) Retry without losing history

When a step fails:
- Adjust parameters.
- Retry the same step.
- The failed attempt remains in session history; only the successful attempt becomes canonical for export.

## 7) Export the session as a reproducible workflow

- Call `export_session()`
- Result is a `NativeOutputRef` with `format="workflow-record-json"`, containing canonical successful steps.

## 8) Resume after restart

If the server restarts:
- Call `resume_session(session_id)`
- Continue tool calls and export as normal.
