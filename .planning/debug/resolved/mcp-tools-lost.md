---
status: resolved
trigger: "Investigate issue: mcp-tools-lost"
created: 2026-01-24T15:24:02+01:00
updated: 2026-01-24T15:35:41+01:00
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: Tool availability loss is triggered by client-side request timeouts (MCP error -32001 / HTTP 408) when bioimage-mcp tool calls exceed client timeouts; the client then marks tools unavailable. Server never deregisters tools.
test: Validate new timeout propagation and default worker timeout enforcement, then verify tool calls don't hang without configured timeouts.
expecting: ExecutionService uses worker_timeout_seconds by default; run supports timeout overrides.
next_action: Archive debug session and report summary.

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: bioimage-mcp_* tools (run, status, list, etc.) should remain available and functional throughout the session.
actual: Tools disappear from the agent's context; manual calls fail; subagents lack access.
errors: MCP error -32001 (timeouts), "tools not in available toolset".
reproduction: Use bioimage-mcp tools for a while; observe timeouts, then tool loss. Persists across subagents.
started: Started after successful calls, preceded by timeouts. Server process remains active (verified by ps aux and bioimage-mcp doctor).

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-01-24T15:24:20+01:00
  checked: Searched codebase for error strings ("tools not in available toolset", "toolset", -32001)
  found: No occurrences in src/; only in debug notes
  implication: Error likely originates from MCP framework/agent tooling layer, not explicit server string constants.

- timestamp: 2026-01-24T15:24:52+01:00
  checked: src/bioimage_mcp/api/server.py
  found: Tool registration is static via FastMCP decorators; no dynamic tool removal logic in server definition.
  implication: Tool loss likely not caused by explicit tool deregistration in server module.

- timestamp: 2026-01-24T15:26:35+01:00
  checked: Discovery/session/worker execution code (api/discovery.py, sessions/manager.py, runtimes/persistent.py)
  found: No code path removes tools from registry post-startup; worker timeouts kill worker processes but not server.
  implication: Tool disappearance is likely outside registry lifecycle; investigate MCP transport/client timeout behavior.

- timestamp: 2026-01-24T15:28:45+01:00
  checked: MCP SDK error codes and tool cache logic (mcp/types.py, mcp/shared/session.py, mcp/server/lowlevel/server.py)
  found: -32001 is documented as request timeout (client-side); server tool list is cached but only refreshed via list_tools; no server code clears tools on timeout.
  implication: Timeouts likely originate from client-side request read timeouts; tool loss likely due to client/tooling layer state reset after repeated timeouts.

- timestamp: 2026-01-24T15:30:41+01:00
  checked: tests/smoke/utils/mcp_client.py and FastMCP API surface
  found: client wraps tool calls in asyncio.timeout with default 60s; server has no task support or long-running async responses.
  implication: Long-running tool calls can exceed 60s, causing client-side timeouts (-32001) and subsequent loss of tool availability in the agent.

- timestamp: 2026-01-24T15:31:27+01:00
  checked: mcp/server/fastmcp and server.py tool definitions
  found: FastMCP tool registry is static; bioimage-mcp does not expose activate/deactivate or task support in server.py.
  implication: Tool list should remain constant server-side; client-side timeout handling remains primary culprit.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: "Client tool calls exceeded request timeouts (MCP -32001), while the server lacked task support and did not enforce default per-operation timeouts for runs, leading clients to drop tool availability after repeated timeouts."
fix: "Propagate timeout_seconds through run -> InteractiveExecutionService -> ExecutionService, and default to Config.worker_timeout_seconds when no run_opts timeout is provided."
verification: "pytest tests/unit/api/test_interactive.py -q"
files_changed:
  - src/bioimage_mcp/api/server.py
  - src/bioimage_mcp/api/interactive.py
  - src/bioimage_mcp/api/execution.py
  - tests/unit/api/test_interactive.py
