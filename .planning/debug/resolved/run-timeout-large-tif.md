---
status: resolved
trigger: "Investigate issue: run-timeout-large-tif"
created: 2026-01-24T20:04:27+01:00
updated: 2026-01-24T20:24:39+01:00
---

## Current Focus

hypothesis: Slow plugin discovery in BioImage (bioio-bioformats import failure) causes long call time, leading to client timeout.
test: Run base.io.bioimage.load after fallback change to confirm success.
expecting: Load succeeds with tifffile reader and returns artifact without timeout.
next_action: Archive debug session.

## Symptoms

expected: Image load and artifact registration should complete successfully.
actual: McpError: MCP error -32001: Request timed out.
errors: McpError: MCP error -32001: Request timed out
reproduction: Call `base.io.bioimage.load` with `datasets/FLUTE_FLIM_data_tif/hMSC control.tif`.
started: Consistent failure across 5 attempts. dry_run works, execution fails.

## Eliminated

## Evidence

- timestamp: 2026-01-24T20:05:18+01:00
  checked: grep timeout in src
  found: Multiple timeout settings in api/execution.py, runtimes/persistent.py, config schema.
  implication: Timeout likely enforced in execution pipeline or worker runtime.

- timestamp: 2026-01-24T20:06:26+01:00
  checked: api/execution.py, api/server.py, api/interactive.py
  found: run() -> interactive.call_tool -> ExecutionService.run_workflow uses run_opts timeout_seconds or config.worker_timeout_seconds (default 600s).
  implication: Timeout config is applied per step; actual timeout error likely raised in worker/persistent or executor layer.

- timestamp: 2026-01-24T20:07:41+01:00
  checked: runtimes/persistent.py and runtimes/executor.py
  found: Persistent worker execute uses thread join with timeout_seconds; on timeout kills worker and raises TimeoutError. One-shot executor uses subprocess timeout and returns TIMEOUT error payload.
  implication: Timeout likely triggered in persistent worker layer; need to see how TimeoutError maps to MCP -32001 and why large TIFF exceeds default timeout.

- timestamp: 2026-01-24T20:12:08+01:00
  checked: mcp/shared/session.py and mcp/types.py
  found: BaseSession.send_request uses anyio.fail_after with request/session read timeout; on TimeoutError raises McpError with code httpx.codes.REQUEST_TIMEOUT (mapped to -32001).
  implication: -32001 can be client-side timeout while waiting for server response, not necessarily server timeout.

- timestamp: 2026-01-24T20:13:35+01:00
  checked: envs/bioimage-mcp-base.yaml and dataset size
  found: Base env includes bioio-bioformats plugin; dataset file is ~29MB.
  implication: Large TIFF may load slowly in worker; need client timeout configuration to see if it expires first.

- timestamp: 2026-01-24T20:17:13+01:00
  checked: MCP run execution via TestMCPClient and tool log
  found: Load call took ~50s and failed with UnsupportedFormatError; log shows ModuleNotFoundError for resource_backed_dask_array when importing bioio_bioformats plugin.
  implication: BioImage plugin discovery triggers failing bioio-bioformats import, causing long delay and format failure; timeouts likely due to slow plugin discovery on large TIFF.

- timestamp: 2026-01-24T20:20:06+01:00
  checked: BioImage with bioio_tifffile reader
  found: bioio_tifffile reader successfully reads TIFF metadata quickly (~0.3s) for hMSC control.tif.
  implication: Fallback to explicit tifffile reader can avoid slow plugin discovery and support problematic TIFFs.

## Resolution

root_cause: "BioImage plugin discovery attempted to import bioio-bioformats, which fails due to missing resource_backed_dask_array and causes long delays. This made base.io.bioimage.load fail (and hit client timeouts) for the 29MB TIFF."
fix: "Add tifffile reader fallback in base.io.bioimage.load to bypass slow/broken plugin discovery when BioImage fails."
verification: "Ran MCP client call to base.io.bioimage.load for hMSC control.tif with no timeout; load succeeded and returned BioImageRef + workflow_record."
files_changed:
- tools/base/bioimage_mcp_base/ops/io.py
