---
status: resolved
trigger: "I'm diagnosing issues in Phase 13 (Dynamic Introspection Cache Reuse)."
created: 2026-01-28T00:00:00Z
updated: 2026-01-28T00:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: list triggers dynamic discovery each run; cache use depends on lockfile hash and entrypoint meta.list
test: inspect list path (bootstrap list/load_manifests) and dynamic cache read/write paths
expecting: identify why cache read skipped or cache write never happens for trackpy
next_action: check manifests for dynamic sources + lockfile hash usage

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: list < 3s with warm cache; cache files present for tools.base and tools.trackpy
actual: list consistently ~17-18s; tools.base cache exists (1.3MB) but no speedup; tools.trackpy cache missing
errors: none in CLI output
reproduction: time bioimage-mcp list
started: first verification of Phase 13 caching

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-01-28T00:00:00Z
  checked: src/bioimage_mcp/bootstrap/list.py
  found: list_tools loads manifests via load_manifests() (DiscoveryEngine runs) and does not read any cache itself
  implication: CLI list speed depends on manifest discovery behavior, including any runtime meta.list calls

- timestamp: 2026-01-28T00:00:00Z
  checked: src/bioimage_mcp/registry/engine.py
  found: DiscoveryEngine._runtime_list always calls tool entrypoint meta.list when dynamic_sources require runtime listing (adapters trackpy/scipy or missing modules)
  implication: list can trigger tool entrypoints every run; cache only helps if meta.list uses it

- timestamp: 2026-01-28T00:00:00Z
  checked: tools/base/bioimage_mcp_base/entrypoint.py
  found: handle_meta_list builds IntrospectionCache at ~/.bioimage-mcp/cache/dynamic/{tool_id}/introspection_cache.json and passes it to discover_functions
  implication: base meta.list should write cache if lockfile hash is available

- timestamp: 2026-01-28T00:00:00Z
  checked: tools/trackpy/bioimage_mcp_trackpy/entrypoint.py
  found: handle_meta_list also wires IntrospectionCache to discover_functions with cache dir ~/.bioimage-mcp/cache/dynamic/{tool_id}
  implication: trackpy cache missing means cache.put not triggered (likely lockfile hash empty or discovery path bypassed)

- timestamp: 2026-01-28T00:00:00Z
  checked: src/bioimage_mcp/registry/dynamic/discovery.py
  found: cache get/put only runs when both cache and lockfile_hash are truthy; lockfile_hash is empty if envs/{env_id}.lock.yml missing
  implication: if lockfile missing or project_root not found, cache is skipped and no file is written

- timestamp: 2026-01-28T00:00:00Z
  checked: tools/base/manifest.yaml and tools/trackpy/manifest.yaml
  found: both tools have dynamic_sources; trackpy functions list is empty so list must rely on discovery
  implication: load_manifests will trigger DiscoveryEngine for each tool and may call runtime meta.list every time

- timestamp: 2026-01-28T00:00:00Z
  checked: envs/*.lock.yml
  found: lockfiles exist for bioimage-mcp-base and bioimage-mcp-trackpy
  implication: lockfile hash should be available if project_root is detected correctly

- timestamp: 2026-01-28T00:00:00Z
  checked: src/bioimage_mcp/registry/engine.py
  found: runtime list always called for sources with adapter in {scipy, trackpy} regardless of modules
  implication: meta.list will run on every manifest load (unless upstream caching is added)

- timestamp: 2026-01-28T00:00:00Z
  checked: tools/trackpy/bioimage_mcp_trackpy/entrypoint.py
  found: handle_meta_list uses IntrospectionCache but only writes cache when discover_functions uses lockfile hash; no cache path used in core list
  implication: if lockfile hash is empty or discovery bypassed, no trackpy cache file is created

- timestamp: 2026-01-28T00:00:00Z
  checked: src/bioimage_mcp/runtimes/executor.py
  found: execute_tool spawns a fresh subprocess per call; no persistent worker in list path
  implication: meta.list execution cost repeats every list invocation

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  1) `bioimage-mcp list` (CLI) loads manifests via `load_manifests()` which runs `DiscoveryEngine.discover()` every time. For dynamic sources with adapter `trackpy`/`scipy` (and any adapters in registry), `DiscoveryEngine._runtime_list()` always spawns the tool entrypoint via `execute_tool` to call `meta.list`. There is no core-side reuse of dynamic discovery results for list, so each `list` invocation re-runs entrypoints (process spawn + discovery), keeping runtime ~17s even when tool caches exist.

  2) The dynamic introspection cache is only written when a non-empty lockfile hash is available (`discover_functions` requires `project_root` and `envs/{env_id}.lock.yml`). If `project_root` can't be detected or the lockfile is not found from the entrypoint context, `lockfile_hash` is empty and cache read/write is skipped. This explains why `tools.trackpy` cache file is missing despite `meta.list` usage: cache is gated on lockfile hash and never written when the lockfile is not visible to the entrypoint.
fix: none (diagnosis only)
verification: code inspection of list path, discovery engine, and dynamic cache gate
files_changed: []
