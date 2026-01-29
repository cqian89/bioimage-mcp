---
status: investigating
trigger: "Investigate why modifying a manifest triggers a cache miss (slower run) but fails to update the persistent cache file with new metadata."
created: 2026-01-29T10:41:22+01:00
updated: 2026-01-29T10:41:22+01:00
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: `bioimage-mcp list` cache miss is for CLI list cache (list_tools.json); meta_list_cache.json only updates when runtime meta.list runs with project_root+env_id+lockfile, so manifest-only changes can trigger list cache miss without touching meta_list_cache
test: map list cache path vs meta.list cache path and runtime list conditions
expecting: confirm list cache invalidation uses manifest mtime/size; meta_list_cache only written on successful runtime meta.list
next_action: return diagnosis and ask if you want a code change to persist manifest updates into cache

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: modifying a tool manifest and running `bioimage-mcp list` should update cache on disk with new metadata/timestamp
actual: `bioimage-mcp list` is slower (cache miss) but cache file on disk does not reflect new metadata/timestamp
errors: none reported
reproduction: modify a manifest (e.g., description) then run `bioimage-mcp list`
started: user report

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-01-29T10:41:22+01:00
  checked: src/bioimage_mcp/registry/engine.py::_runtime_list
  found: cache is only used when project_root and manifest.env_id set; cache key uses lockfile hash + manifest.manifest_checksum; cache.put is called after successful runtime meta.list
  implication: if manifest.env_id missing, project_root missing, or meta.list fails, cache file will not be updated despite runtime execution

- timestamp: 2026-01-29T10:41:22+01:00
  checked: src/bioimage_mcp/registry/dynamic/meta_list_cache.py
  found: cache file is ~/.bioimage-mcp/cache/dynamic/<tool_id>/meta_list_cache.json; cache is a dict keyed by "<lockfile_hash>:<manifest_checksum>"; get/put only use that file
  implication: cache file update depends on correct key inputs and successful put; different cache file name than introspection_cache.json

- timestamp: 2026-01-29T10:41:22+01:00
  checked: src/bioimage_mcp/bootstrap/list.py and list_cache.py
  found: `bioimage-mcp list` uses CLI cache at ~/.bioimage-mcp/cache/cli/list_tools.json keyed by manifest mtime/size + envs hash; on cache miss it recomputes tool_details and writes list_tools.json unless BIOIMAGE_MCP_DISABLE_LIST_CACHE=1
  implication: a manifest edit invalidates the CLI list cache, but does not necessarily update meta_list_cache.json (which is a separate cache used only for runtime meta.list)

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: ""
fix: ""
verification: ""
files_changed: []
