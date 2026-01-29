---
status: investigating
trigger: "Investigate why `bioimage-mcp list` doesn't regenerate missing `introspection_cache.json` files if the CLI-level `list_tools.json` cache is still valid."
created: 2026-01-29T00:00:00Z
updated: 2026-01-29T00:00:00Z
---

## Current Focus

hypothesis: list_tools.json cache short-circuits registry introspection and never checks/repairs per-tool introspection_cache.json
test: inspect bootstrap list/cache flow to see if it validates per-tool dynamic cache existence or uses registry engine when list_tools cache hit
expecting: list_tools() returns cached payload without touching registry/engine, and fingerprint lacks dynamic cache state
next_action: document root cause and suggested fix

## Symptoms

expected: deleting introspection_cache.json should force regeneration on next bioimage-mcp list run, even if list_tools.json exists
actual: bioimage-mcp list is fast and does not regenerate missing introspection_cache.json when list_tools.json cache is valid
errors: none reported
reproduction: delete introspection_cache.json; keep ~/.bioimage-mcp/cache/cli/list_tools.json; run bioimage-mcp list
started: unknown

## Eliminated

## Evidence

- timestamp: 2026-01-29T00:00:00Z
  checked: src/bioimage_mcp/bootstrap/list.py cache fast path
  found: list_tools() returns cached payload when list_tools.json fingerprint matches, without invoking registry/engine or dynamic discovery
  implication: cache hit bypasses any regeneration of introspection_cache.json
- timestamp: 2026-01-29T00:00:00Z
  checked: src/bioimage_mcp/bootstrap/list_cache.py fingerprint inputs
  found: ListToolsCache fingerprint uses only manifest file stats + envs hash; no dynamic cache existence/mtime included
  implication: list_tools.json remains valid even if per-tool dynamic caches are deleted
- timestamp: 2026-01-29T00:00:00Z
  checked: src/bioimage_mcp/registry/engine.py meta.list caching
  found: runtime list uses MetaListCache stored under ~/.bioimage-mcp/cache/dynamic/<tool_id> with lockfile+manifest checksum
  implication: dynamic introspection_cache.json is only regenerated when discovery engine runs, which cached list_tools skips

## Resolution

root_cause: ""
fix: ""
verification: ""
files_changed: []
