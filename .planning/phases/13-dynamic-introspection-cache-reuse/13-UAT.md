---
status: complete
phase: 13-dynamic-introspection-cache-reuse
source: [13-01-SUMMARY.md, 13-02-SUMMARY.md, 13-03-SUMMARY.md, 13-04-SUMMARY.md, 13-05-SUMMARY.md, 13-06-SUMMARY.md, 13-07-SUMMARY.md]
started: 2026-01-29T10:30:00Z
updated: 2026-01-29T10:55:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Warm-cache CLI list speed
expected: Running `bioimage-mcp list` twice, the second run completes in under ~1.5s and is significantly faster than the first run.
result: pass

### 2. CLI Tool Filtering
expected: Running `bioimage-mcp list --tool trackpy` (or `trackpy`) works and shows only trackpy functions.
result: pass

### 3. Trackpy dynamic cache file
expected: After a `list` run, `~/.bioimage-mcp/cache/dynamic/tools.trackpy/introspection_cache.json` exists and contains discovery metadata.
result: pass

### 4. Manifest Invalidation
expected: Modifying a tool manifest (e.g. changing a description) and running `bioimage-mcp list` triggers a cache miss (slower run) and updates the cache with the new info.
result: pass

### 5. Cache Regeneration (Sentinel Fallback)
expected: If `introspection_cache.json` is deleted but the directory remains, the next `list` run regenerates it even if no environment lockfile is detected (portable sentinel fallback).
result: issue
reported: "If introspection_cache.json is deleted but ~/.bioimage-mcp/cache/cli/list_tools.json remains, the next bioimage-mcp list run is fast (~1s) and does not regenerate the missing introspection_cache.json. If both the CLI cache and the dynamic cache are deleted, list regenerates the file."
severity: major

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "If `introspection_cache.json` is deleted, the next `list` run regenerates it even if CLI cache exists."
  status: failed
  reason: "User reported: If introspection_cache.json is deleted but ~/.bioimage-mcp/cache/cli/list_tools.json remains, the next bioimage-mcp list run is fast (~1s) and does not regenerate the missing introspection_cache.json."
  severity: major
  test: 5
  root_cause: ""     # Filled by diagnosis
  artifacts: []      # Filled by diagnosis
  missing: []        # Filled by diagnosis
  debug_session: ""  # Filled by diagnosis
