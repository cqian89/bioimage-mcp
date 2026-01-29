---
status: diagnosed
trigger: "Investigate issue: warm-cache-slow"
created: 2026-01-29T00:12:38Z
updated: 2026-01-29T00:12:38Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: list command does not use any persistent cache for manifest discovery or env lookup; each invocation is cold
test: search for persistent cache usage in list path; confirm only schema/introspection caches exist elsewhere
expecting: no persistent cache for list itself; only runtime introspection caches used in discovery engine (not list CLI)
next_action: compare UAT Phase 13 test path to CLI list vs MCP list behavior

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: Running bioimage-mcp list twice, the second run completes in under ~3s and is noticeably faster than the first run.
actual: Second run onwards still take more than 5s. Not much faster than first if any
errors: None reported
reproduction: Test 1 in UAT (Phase 13)
started: Discovered during UAT

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-01-29T00:12:38Z
  checked: src/bioimage_mcp/bootstrap/list.py
  found: CLI list_tools loads config, load_manifests, and runs env manager "env list --json" each time
  implication: warm runs still invoke manifest loading and env discovery subprocess

- timestamp: 2026-01-29T00:12:38Z
  checked: src/bioimage_mcp/api/server.py list handler
  found: MCP list tool calls discovery.list_tools using active functions from session
  implication: list RPC path depends on discovery/registry index performance

- timestamp: 2026-01-29T00:12:38Z
  checked: src/bioimage_mcp/api/discovery.py list_tools
  found: list_tools always loads config, calls RegistryIndex.list_functions, builds ToolIndex hierarchy every call
  implication: no obvious in-memory caching of hierarchy; cost repeats per list

- timestamp: 2026-01-29T00:12:38Z
  checked: src/bioimage_mcp/registry/index.py
  found: RegistryIndex.list_functions selects all functions from sqlite and ToolIndex.build_hierarchy builds tree each call
  implication: list path is O(N) per call even with warm cache

- timestamp: 2026-01-29T00:12:38Z
  checked: src/bioimage_mcp/registry/loader.py
  found: load_manifests uses module-level _MANIFEST_CACHE keyed by roots; cache is in-memory only
  implication: cache does not persist across CLI invocations (new process)

- timestamp: 2026-01-29T00:12:38Z
  checked: src/bioimage_mcp/cli.py
  found: bioimage-mcp list command calls bootstrap.list.list_tools (CLI process)
  implication: list runs in fresh process each time; in-memory caches reset

- timestamp: 2026-01-29T00:12:38Z
  checked: src/bioimage_mcp/registry/dynamic/meta_list_cache.py and schema_cache.py
  found: persistent caches exist for runtime meta.list and schema but are used by discovery engine/describe, not CLI list
  implication: warm-cache expectation for list isn't met by existing caches

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: "CLI list runs in a fresh process each time and does not use any persistent cache for manifest discovery or env listing; only in-memory _MANIFEST_CACHE exists, so warm runs are effectively cold."
fix: ""
verification: ""
files_changed: []
