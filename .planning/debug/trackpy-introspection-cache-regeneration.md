---
status: investigating
trigger: "Investigate why deleting introspection_cache.json does not trigger regeneration unless the entire parent directory is deleted."
created: 2026-01-29T00:00:00Z
updated: 2026-01-29T00:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: cache regeneration is gated by lockfile_hash; when hash is empty, discover_functions skips cache read/write so deleting cache file has no effect
test: confirm adapter doesn't add additional cache guards
expecting: adapter just introspects modules, so cache behavior entirely controlled by discover_functions
next_action: record root cause and return diagnosis

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: deleting ~/.bioimage-mcp/cache/dynamic/tools.trackpy/introspection_cache.json should cause meta.list to regenerate cache file
actual: cache file only recreated when entire directory ~/.bioimage-mcp/cache/dynamic/tools.trackpy is deleted
errors: none reported
reproduction: delete introspection_cache.json only; run bioimage-mcp list from outside repo; cache not recreated
started: user report

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-01-29T00:00:00Z
  checked: tools/trackpy/bioimage_mcp_trackpy/entrypoint.py
  found: handle_meta_list builds IntrospectionCache in ~/.bioimage-mcp/cache/dynamic/{tool_id} and calls discover_functions with project_root derived from BIOIMAGE_MCP_PROJECT_ROOT/cwd/manifest
  implication: cache usage depends on discover_functions behavior and lockfile hash availability

- timestamp: 2026-01-29T00:00:00Z
  checked: src/bioimage_mcp/registry/dynamic/cache.py
  found: IntrospectionCache.get returns None when cache file missing; put always writes cache_file if called
  implication: if cache file isn't recreated, discover_functions likely never calls put (not a cache implementation bug)

- timestamp: 2026-01-29T00:00:00Z
  checked: src/bioimage_mcp/registry/dynamic/discovery.py
  found: cache get/put only executed when both cache and lockfile_hash are truthy; lockfile_hash empty if lockfile missing or project_root not provided
  implication: if entrypoint fails to resolve project_root/lockfile, cache is bypassed entirely and file deletion has no effect

- timestamp: 2026-01-29T00:00:00Z
  checked: tests/unit/tools/test_trackpy_dynamic_introspection_cache.py
  found: tests document that when project_root is not found, lockfile_hash="" and discovery bypasses cache; cache reuse only occurs when env var or cwd finds project_root
  implication: reported behavior aligns with empty lockfile_hash path (no cache read/write)

- timestamp: 2026-01-29T00:00:00Z
  checked: tools/trackpy/bioimage_mcp_trackpy/dynamic_discovery.py
  found: adapter simply introspects modules and returns FunctionMetadata; no cache behavior in adapter
  implication: cache regeneration depends solely on discover_functions gate (lockfile_hash)

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  `discover_functions()` only reads/writes `IntrospectionCache` when `lockfile_hash` is truthy. If `project_root` can't be resolved (e.g., running outside repo without `BIOIMAGE_MCP_PROJECT_ROOT` pointing to the repo), `_calculate_lockfile_hash()` returns "" and caching is bypassed entirely. In that path, deleting `introspection_cache.json` does nothing because `put()` is never called. Deleting the entire cache directory only appears to “fix” it when the run also happens to resolve `project_root` (e.g., different CWD/env), yielding a non-empty lockfile hash and enabling cache writes.
fix: ""
verification: ""
files_changed: []
