---
status: investigating
trigger: "Investigate why `bioimage-mcp list --tool trackpy` is not implemented or not working in the CLI, as reported by the user."
created: 2026-01-29T00:00:00Z
updated: 2026-01-29T00:00:01Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: CLI list subcommand lacks --tool option and list_tools has no filtering path, so `--tool trackpy` is not implemented at all.
test: inspect cli.py for list parser options and list_tools signature
expecting: no --tool arg in CLI and list_tools has no tool filter param
next_action: document evidence from cli.py and bootstrap/list.py

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: `bioimage-mcp list --tool trackpy` should list trackpy tools (at least from cache) when introspection cache exists.
actual: user reports CLI says not implemented or not working for `--tool trackpy`.
errors: none provided.
reproduction: run `bioimage-mcp list --tool trackpy`.
started: unknown.

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-01-29T00:00:01Z
  checked: src/bioimage_mcp/cli.py list subcommand
  found: list command only defines --json and calls list_tools(json_output=args.json); no --tool option parsed or forwarded.
  implication: CLI cannot accept `--tool trackpy` or pass a tool filter to the list handler.

- timestamp: 2026-01-29T00:00:01Z
  checked: src/bioimage_mcp/bootstrap/list.py list_tools
  found: list_tools only accepts json_output; it always lists all manifests and has no tool filtering logic.
  implication: even if CLI accepted --tool, list_tools has no implementation to filter to a specific tool.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: 
fix: 
verification: 
files_changed: []
