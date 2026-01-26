---
status: diagnosed
trigger: "Issue: Cellpose list output missing module and io_pattern."
created: 2026-01-25T00:00:00Z
updated: 2026-01-25T00:01:10Z
---

## Current Focus

hypothesis: Core registry persists only fn_id/name/description/ports, dropping module/io_pattern
test: Inspect registry schema + list output shaping
expecting: functions table and list payload omit module/io_pattern
next_action: Report root cause and affected files

## Symptoms

expected: Cellpose tool list entries include module and io_pattern fields
actual: Cellpose list output is missing module and io_pattern
errors: None reported
reproduction: Run list for cellpose tool (meta.list) and inspect entry fields
started: Unknown

## Eliminated

## Evidence

- timestamp: 2026-01-25T00:00:10Z
  checked: tools/cellpose/bioimage_mcp_cellpose/entrypoint.py handle_meta_list
  found: meta.list includes module and io_pattern fields for each function entry
  implication: Missing fields likely dropped or ignored in core registry parsing

- timestamp: 2026-01-25T00:01:10Z
  checked: src/bioimage_mcp/storage/sqlite.py and registry/index.py
  found: functions table schema and list_functions() omit module/io_pattern; ToolIndex payload only includes fn_id/name/description/io summary
  implication: module/io_pattern are not persisted or returned by list tooling, so they are dropped after meta.list

## Resolution

root_cause: "Core registry schema/list pipeline does not persist or return module/io_pattern from meta.list, so Cellpose fields are dropped after discovery."
fix: ""
verification: ""
files_changed: []
