---
status: verifying
trigger: "Investigate issue: server-startup-slowness"
created: 2026-02-02T11:06:30Z
updated: 2026-02-02T11:15:40Z
---

## Current Focus

hypothesis: serve startup slowness is caused by load_manifests discovery (runtime meta.list/AST), not DB writes
test: verify fingerprint persistence helpers work
expecting: registry_state stores/retrieves fingerprint and functions exist check works
next_action: describe verification outcome and close out session

## Symptoms

expected: Server should start and respond quickly (<2s) if manifests haven't changed.
actual: Startup/first response takes >10s.
errors: None.
reproduction: Run `bioimage-mcp serve --stdio` and measure time to first MCP response (or use a script to measure startup).
started: Recent change (after adding more tools/functions).

## Eliminated

## Evidence

- timestamp: 2026-02-02T00:00:50Z
  checked: src/bioimage_mcp/bootstrap/serve.py
  found: serve() calls load_manifests(), then upserts every tool/function into discovery store and prunes stale entries before starting MCP run loop.
  implication: any slow manifest loading/introspection or DB upsert loop happens on startup before first response.

- timestamp: 2026-02-02T00:02:40Z
  checked: src/bioimage_mcp/registry/loader.py
  found: load_manifest_file always instantiates DiscoveryEngine and runs engine.discover(manifest) for every manifest; no persistent cache beyond in-process _MANIFEST_CACHE.
  implication: each serve startup redoes full discovery, including dynamic sources and any runtime meta.list/describe work.

- timestamp: 2026-02-02T00:02:50Z
  checked: src/bioimage_mcp/registry/engine.py
  found: DiscoveryEngine.discover can call runtime meta.list (execute_tool) and runtime meta.describe fallbacks during discovery for dynamic sources.
  implication: serve startup may spawn tool runtimes per manifest, causing >10s startup even with warm cache if discovery isn't persisted.

- timestamp: 2026-02-02T00:04:10Z
  checked: src/bioimage_mcp/bootstrap/list.py
  found: CLI list uses InstalledEnvsCache/ListToolsCache; when caches hit and dynamic cache exists, it returns without calling load_manifests.
  implication: list can be fast via CLI caches, while serve always calls load_manifests and redoes discovery.

- timestamp: 2026-02-02T11:08:15Z
  checked: tools/*/entrypoint.py (base)
  found: tool entrypoint meta.list/describe uses IntrospectionCache and dynamic discovery cache keyed by lockfile+manifest checksum.
  implication: runtime discovery may be cached within tool process, but serve still spawns runtime per tool to call meta.list, which can be slow.

- timestamp: 2026-02-02T11:08:55Z
  checked: load_manifests timing
  found: load_manifests over tool_manifest_roots took 10.674s for 5 manifests and 1026 functions.
  implication: manifest discovery alone explains >10s startup; serve is doing full discovery before first response.

- timestamp: 2026-02-02T11:09:40Z
  checked: registry upsert/prune timing
  found: upsert/prune of 5 manifests and 1026 functions took 0.033s.
  implication: DB writes are not the bottleneck; startup delay is entirely discovery time.

## Resolution

root_cause: "serve() always calls load_manifests which triggers full discovery (including runtime meta.list/describe) on startup; this takes ~10.7s, while DB upserts are ~0.03s."
fix: "Added registry_state storage with a manifest/lockfile fingerprint and guarded serve startup to skip load_manifests when fingerprint matches and registry already populated."
verification: "Confirmed registry_state persistence (set/get) and has_functions check via script; serve guard relies on these." 
files_changed:
  - src/bioimage_mcp/storage/sqlite.py
  - src/bioimage_mcp/api/discovery.py
  - src/bioimage_mcp/bootstrap/serve.py
