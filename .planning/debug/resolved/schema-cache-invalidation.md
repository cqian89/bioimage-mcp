---
status: resolved
trigger: "Investigate issue: schema-cache-invalidation"
created: 2026-02-02T00:00:00Z
updated: 2026-02-02T00:14:40Z
---

## Current Focus

hypothesis: list_tools cache invalidates because it checks for introspection_cache.json under ~/.bioimage-mcp/cache/dynamic/<tool_id without tools.>, while IntrospectionCache writes under ~/.bioimage-mcp/cache/dynamic/<full tool_id> (e.g., tools.base).
test: Verify tool entrypoints use manifest.tool_id for cache dir; compare with list_tools path usage.
expecting: Path mismatch explains missing cache file and persistent cache miss.
next_action: Update list_tools to use full tool_id for dynamic cache check (store in payload), then verify list cache warm path.

## Symptoms

expected: Fast (<2s) on 2nd runs; startup faster after warm cache.
actual: Same as cold; no speedup.
errors: None.
reproduction: Run `bioimage-mcp list` twice and start server; both remain slow (exact steps pending).
started: Recent change.

## Eliminated

## Evidence

- timestamp: 2026-02-02T00:02:30Z
  checked: src/bioimage_mcp/bootstrap/list.py
  found: list_tools uses InstalledEnvsCache/ListToolsCache and also invalidates cached_payload if any tool with dynamic_discovery lacks ~/.bioimage-mcp/cache/dynamic/<tool_id>/introspection_cache.json
  implication: cache hit can be forced to miss if dynamic cache file is missing, even when tools cache exists.

- timestamp: 2026-02-02T00:02:50Z
  checked: src/bioimage_mcp/registry/cache_version.py
  found: cache version key includes schema version + package version, and optionally a critical source hash when BIOIMAGE_MCP_DEV_CACHE_CHECK=1.
  implication: vkey changes can invalidate caches across runs, especially in editable/dev mode or when env var is set.

- timestamp: 2026-02-02T00:03:10Z
  checked: src/bioimage_mcp/registry/dynamic/cache.py and discovery.py
  found: IntrospectionCache stores entries keyed by get_cache_version_key + adapter/prefix + composite key including lockfile hash and manifest checksum; no caller found yet that initializes IntrospectionCache.
  implication: dynamic_discovery caches may never be written, causing list_tools to invalidate cached payload every run.

- timestamp: 2026-02-02T00:04:30Z
  checked: src/bioimage_mcp/registry/engine.py
  found: DiscoveryEngine handles dynamic_sources via AST/runtime but does not use IntrospectionCache; only MetaListCache is used for runtime list.
  implication: introspection_cache.json likely never created, so list_tools missing_dynamic check forces cache miss.

- timestamp: 2026-02-02T00:08:10Z
  checked: tools/base/manifest.yaml and tools/trackpy/manifest.yaml
  found: both define dynamic_sources; trackpy functions list is empty and relies on dynamic discovery.
  implication: list_tools will mark these as dynamic_discovery sources without ensuring introspection_cache exists.

- timestamp: 2026-02-02T00:09:30Z
  checked: tests/unit/bootstrap/test_list_cache.py
  found: test_list_tools_dynamic_cache_fallback expects cache miss when introspection_cache.json is missing and cache hit only after creating the file.
  implication: current logic intentionally forces cache miss unless dynamic cache file exists; if not created by normal list runs, list remains slow.

- timestamp: 2026-02-02T00:10:50Z
  checked: tools/base/bioimage_mcp_base/entrypoint.py and tools/trackpy/bioimage_mcp_trackpy/entrypoint.py
  found: IntrospectionCache uses cache_dir ~/.bioimage-mcp/cache/dynamic/<manifest.tool_id> (e.g., tools.base, tools.trackpy).
  implication: list_tools checks a different path if it strips "tools." from tool_id, causing false cache misses.

## Resolution

root_cause: "list_tools checked dynamic cache under ~/.bioimage-mcp/cache/dynamic/<tool_id without tools.>, but IntrospectionCache writes under ~/.bioimage-mcp/cache/dynamic/<full tool_id>, so dynamic cache was always considered missing and list cache invalidated every run."
fix: "Updated list_tools dynamic cache check to consider full tool_id path and stored full tool_id in cached payload."
verification: "pytest tests/unit/bootstrap/test_list_cache.py::test_list_tools_dynamic_cache_fallback -v"
files_changed: ["src/bioimage_mcp/bootstrap/list.py"]
