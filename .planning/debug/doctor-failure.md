---
status: diagnosed
trigger: "bioimage-mcp doctor fails with meta.list failed for tools.cellpose: ... {'error': {'message': 'Unknown fn_id: meta.list'}}"
created: 2026-01-23T20:14:07Z
updated: 2026-01-23T20:20:00Z
---

## Current Focus
hypothesis: The cellpose worker does not implement 'meta.list', but the registry loader expects it to.
test: Check src/bioimage_mcp/registry/loader.py and tool definitions.
expecting: To find a discrepancy in how tools are loaded or inspected.
next_action: report diagnosis

## Symptoms
expected: bioimage-mcp doctor passes or reports status correctly.
actual: bioimage-mcp doctor fails with Unknown fn_id: meta.list for tools.cellpose.
errors: "meta.list failed for tools.cellpose: ... {'error': {'message': 'Unknown fn_id: meta.list'}}"
reproduction: Run 'bioimage-mcp doctor'
started: Reported by user.

## Eliminated
- hypothesis: bioimage-mcp doctor is failing due to missing dependencies in core env.
  evidence: Core env should not have tool dependencies. Loader handles this by falling back to subprocess. The issue is the subprocess call fails.

## Evidence
- timestamp: 2026-01-23T20:15:00Z
  checked: src/bioimage_mcp/registry/loader.py
  found: _discover_via_subprocess sends 'meta.list' request if in-process discovery fails.
  implication: If in-process discovery fails (expected for isolated tools), worker MUST support meta.list.

- timestamp: 2026-01-23T20:16:00Z
  checked: tools/cellpose/bioimage_mcp_cellpose/entrypoint.py
  found: FUNCTION_HANDLERS does not contain 'meta.list'. process_execute_request returns "Unknown fn_id" for it.
  implication: The worker does not implement the required discovery protocol.

- timestamp: 2026-01-23T20:19:00Z
  checked: src/bioimage_mcp/registry/dynamic/adapters/cellpose.py
  found: In-process discovery returns [] because 'cellpose' cannot be imported in core.
  implication: This confirms why loader falls back to subprocess discovery.

## Resolution
root_cause: `tools.cellpose` relies on dynamic discovery but its worker does not implement `meta.list`. In-process discovery fails in the core environment (by design), triggering a fallback to `meta.list` via subprocess, which the worker rejects.
fix: Implement `meta.list` handler in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`.
verification:
files_changed: []
