---
status: resolved
trigger: "CLI `bioimage-mcp list` lacks `tool_version` and `introspection_source` columns/fields."
created: 2026-01-25T13:50:38+01:00
updated: 2026-01-25T13:53:28+01:00
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: CLI list command formats output without including tool_version/introspection_source fields.
test: Locate CLI list implementation and compare fields available from API vs. fields printed.
expecting: CLI list formatting omits tool_version/introspection_source even when present in data.
next_action: None (root cause identified).

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: CLI `bioimage-mcp list` should include tool_version and introspection_source columns/fields.
actual: CLI output lacks tool_version and introspection_source.
errors: none reported.
reproduction: run `bioimage-mcp list`.
started: unknown.

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-01-25T13:51:34+01:00
  checked: src/bioimage_mcp/bootstrap/list.py list_tools()
  found: tool_details only includes id/status/function_count/env_id; output headers are Tool/Status/Functions; json output uses same fields
  implication: CLI list formatting never includes tool_version or introspection_source fields, so they cannot appear in output even if data exists elsewhere.

- timestamp: 2026-01-25T13:52:02+01:00
  checked: search for tool_version/introspection_source in src
  found: fields exist in registry/manifest/schema and API discovery/index layers
  implication: data is available in registry models; CLI list simply doesn't surface it.

- timestamp: 2026-01-25T13:53:09+01:00
  checked: src/bioimage_mcp/bootstrap/list.py list_tools loop
  found: list_tools only reads m.tool_id, m.env_id, len(m.functions); never accesses m.tool_version or function introspection_source
  implication: root cause is missing field extraction/formatting in CLI list implementation.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: "CLI list implementation (bootstrap/list.py list_tools) only builds tool_details with id/status/function_count/env_id and formats columns Tool/Status/Functions, so tool_version and introspection_source are never extracted or printed."
fix: "Add tool_version to tool_details and include introspection_source (likely aggregate per tool) in JSON/table output."
verification: "Not applied (diagnosis only)."
files_changed: []
