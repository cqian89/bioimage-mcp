# Proposal: Interactive Tool Calling

## 1. Context & Problem
The current Bioimage-MCP architecture (v0.2) relies on a **"Plan-then-Execute" (Batch)** model:
1. User asks for analysis.
2. LLM plans the *entire* pipeline into a JSON workflow spec.
3. LLM calls `run_workflow(spec)`.

**Issues:**
- **Cognitive Load**: The LLM must "hallucinate" the valid parameter combinations for *all* steps at once.
- **Brittleness**: If step 3 of 5 fails, the entire run fails. The LLM must edit the JSON and retry.
- **Rigidity**: It discourages exploratory analysis ("Let's try filter A, oh that looks bad, let's try filter B").

## 2. Proposed Solution: Interactive Tool Calling (Best Practices Aligned)
We propose an **Interactive (REPL)** model where the LLM executes tools one by one, observing results immediately, while retaining reproducibility.

### 2.1 Preferred MCP Pattern: Selective Native Tool Calls + Session Capture (Recommended)
Register manifest functions as first-class MCP tools (to preserve per-tool schemas), but expose them **selectively** to avoid tool bloat.
- Preserves MCP schemas for validation and client compatibility.
- Uses an implicit `session_id` derived from the MCP/LLM session to group steps.
- Introduces `activate_functions` / `deactivate_functions` to control which tools are visible in `list_tools`.
- Emits `notifications/tools/list_changed` when the active tool set changes (for clients that support it).
- Records tool call metadata, inputs, params, outputs, and logs per step.

**Implementation difficulty:** Medium-High (session store + selective tool registry + list_changed notification).

### 2.2 Optional Compatibility Wrapper: `call_tool`
For clients that cannot dynamically register tools, provide a generic wrapper as a fallback.

```python
@mcp.tool()
def call_tool(
    fn_id: str,
    inputs: dict[str, str],
    params: dict[str, Any],
    *,
    session_id: str | None = None,
    dry_run: bool = False,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """Execute one tool with validation and session logging."""
```

Best-practice adjustments:
- If `session_id` is omitted, derive it from the MCP/LLM session.
- Validate `fn_id`, `inputs`, and `params` against the manifest schema before executing (use `dry_run` for validation-only).
- Return structured errors with `error.code`, `error.message`, `validation_errors`, and `log_ref_id` for fast retries.
- Return `run_id`, `status`, and lightweight `outputs_summary` (dimensions, dtype, size) alongside artifact refs.

**Implementation difficulty:** Medium (schema validation + structured responses).

### 2.3 The Interactive Loop
1. **Discovery**: LLM calls `list_tools` / `search_functions` / `describe_function`.
2. **Activation**: LLM calls `activate_functions([...])` to expose a small, task-relevant subset of tools (server emits `notifications/tools/list_changed` when supported).
3. **Step Execution**: LLM calls the tool (native or `call_tool`) and inspects outputs.
4. **Correction**: If a step errors, LLM retries with adjusted params.
5. **Export**: LLM calls `export_session` to emit a workflow artifact.

Best practices:
- Pre-flight validation at the API layer (input artifact type checks).
- Return minimal summaries alongside refs for fast feedback.
- Support async/long-running steps via `run_id` + `get_run_status` polling.
- Mitigate latency with warm process pools or cached env startup per session.

**Implementation difficulty:** Medium-High (process pooling + async status).

### 2.4 Preserving Reproducibility (Session Logs)
"Interactive" does not mean "ephemeral."
- The server maintains a **Session** (implicit, tied to the MCP/LLM session).
- Every successful call is appended to the Session's **Linear History**.
- Exporting a Session yields a **Workflow** artifact identical to the batch JSON format.
- Track retries explicitly and mark the final "canonical" step used for export.
- Persist session state incrementally and apply TTL/cleanup for abandoned sessions.

**Implementation difficulty:** Medium (session persistence + export mapping).

## 3. Architecture Changes

### 3.1 API Layer (`src/bioimage_mcp/api/server.py`)
- Add `export_session` (optional `end_session`); session is implicit per MCP/LLM connection.
- Add `activate_functions` / `deactivate_functions` to manage the per-session active tool set.
- Emit `notifications/tools/list_changed` when the active tool set changes (clients with "Discovery" support will refresh automatically).
- Register manifest functions as MCP tools; keep `call_tool` as a fallback wrapper.
- Add preflight validation and structured error payloads.

### 3.2 Execution Layer (`src/bioimage_mcp/api/execution.py`)
- Introduce `SessionManager` backed by the run/artifact stores (or a new store).
- Generalize `run_workflow` to support N steps (current implementation is 1 step).
- Reuse `execute_step` for both batch and interactive paths.

### 3.3 Runtime Layer (`src/bioimage_mcp/runtimes/executor.py`)
- Optional warm pools or cached env startup for interactive latency.
- Add a queued/running status path for long-running tasks.

## 4. Pros vs Cons

| Feature | Batch (Current) | Interactive (Proposed) |
| :--- | :--- | :--- |
| **LLM Reasoning** | Hard (requires planning ahead) | **Natural** (step-by-step) |
| **Error Recovery** | Poor (macro-retry) | **Excellent** (micro-retry) |
| **Latency** | Low (single run) | Higher (round-trips; mitigate with warm pools) |
| **Safety/Validation** | High (pre-validated graph) | Medium-High (per-step validation + type checks) |
| **Observability** | Moderate | **High** (step-level logs) |

## 5. Best Practices & Implementation Difficulty Summary

| Change | Best-Practice Alignment | Difficulty |
| :--- | :--- | :--- |
| Native tool calls + session capture | Uses MCP schemas and standard tool discovery | Medium |
| `call_tool` wrapper with schema validation | Compatibility for non-dynamic clients | Medium |
| Structured errors + output summaries | Improves retryability and fast feedback | Low |
| Session logs + workflow export | Preserves reproducibility and audit trails | Medium |
| Multi-step `run_workflow` | Matches workflow model and replay needs | Medium |
| Async status + warm pools | Needed for REPL latency and long runs | High |
| Session TTL/cleanup | Prevents abandoned-session resource leaks | Low |

## 6. Current Implementation Alignment & Improvement Opportunities

**Aligns well:**
- Tool discovery endpoints are MCP tools (`list_tools`, `describe_tool`, `search_functions`, `describe_function`).
- `run_workflow` records workflow artifacts with manifest checksums and environment fingerprints.
- `execute_tool` isolates tool execution and captures logs/timeouts.
- Workflow compatibility validation is implemented prior to execution.

**Opportunities to improve:**
- `run_workflow` only supports a single step, limiting replay and inter-tool chaining.
- No session concept for interactive exploration or linear histories.
- Error payloads are minimal; add structured validation errors and log references on failure.
- No preflight artifact type validation or inline output summaries for fast feedback.
- Interactive latency will be high without warm pooling or async status handling.
- `export_artifact` allows arbitrary destination paths; consider path allowlists/sandboxing.

## 7. Client Compatibility: Dynamic Tool Discovery (`notifications/tools/list_changed`)
Selective native-tool exposure works best when clients support dynamic tool discovery.

The MCP community docs use a **"Discovery"** capability tag to indicate support for `notifications/tools/list_changed` (see `https://modelcontextprotocol.io/clients` and `https://github.com/modelcontextprotocol/modelcontextprotocol/pull/473`). The registry is community-maintained, so treat it as a strong signal, not a guarantee.

| Client | Supports `tools/list_changed` auto-refresh? | Evidence | Notes |
| :--- | :--- | :--- | :--- |
| VS Code GitHub Copilot | Yes (verified) | `https://raw.githubusercontent.com/microsoft/vscode/2365ea12ec47729ab54e257313180c868d1073a7/src/vs/workbench/contrib/mcp/common/mcpServer.ts` | Refreshes tools on tool-list changes. |
| Zed | Yes (verified) | `https://github.com/zed-industries/zed/pull/42453` | Explicitly implements `notifications/tools/list_changed`. |
| Windsurf Editor | Yes (per registry: Discovery) | `https://modelcontextprotocol.io/clients` | Windsurf also documents a 100-tool limit in its MCP UI, making selective activation important: `https://docs.windsurf.com/windsurf/cascade/mcp`. |
| Warp | Yes (per registry: Discovery) | `https://modelcontextprotocol.io/clients` | Good candidate for dynamic activation flows. |
| Cline | Yes (per registry: Discovery) | `https://modelcontextprotocol.io/clients` | Treat as "likely" until tested; keep `call_tool` fallback. |
| OpenCode (sst/opencode) | In progress | `https://github.com/sst/opencode/pull/5913` | PR open to handle `notifications/tools/list_changed`. |
| Cursor | No / unreliable (reports) | `https://forum.cursor.com/t/cursor-not-respecting-mcp-notifications-prompts-list-changed-messages/126689` | Keep `call_tool` fallback. |
| Claude Code | No (requested) | `https://github.com/anthropics/claude-code/issues/4118` | Keep `call_tool` fallback. |
| Continue | No (not marked Discovery) | `https://modelcontextprotocol.io/clients` | Continue MCP docs focus on config and tool usage, not dynamic discovery: `https://docs.continue.dev/customize/deep-dives/mcp`. |
| Antigravity | Unknown / unverified | N/A | Name is ambiguous; not found in the official MCP client registry. |

**Implications for this proposal:**
- Keep `call_tool` as a compatibility fallback so interactive flows still work when clients do not refresh tool lists.
- Prefer **selective activation** plus client-side limits.
- Maintain a small, tested compatibility matrix for the clients you target.

## 8. Recommendation
Adopt **Interactive Tool Calling** as the primary LLM interaction mode once session logging, validation, client-compatibility, and latency mitigations are in place. Keep **Batch** for:
1. Replaying saved workflows.
2. High-throughput processing (where round-trips are too slow).
