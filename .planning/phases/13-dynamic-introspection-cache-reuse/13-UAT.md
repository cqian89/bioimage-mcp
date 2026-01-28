---
status: complete
phase: 13-dynamic-introspection-cache-reuse
source: [13-01-SUMMARY.md, 13-02-SUMMARY.md]
started: 2026-01-28T20:35:46Z
updated: 2026-01-28T21:40:00Z
---

## Current Test

[testing complete]

## Tests

### 1. bioimage-mcp list timing
expected: Second run of `bioimage-mcp list` is significantly faster (< 3s).
result: issue
reported: "both runs take the same time at around 15-16 s"
severity: major

### 2. tools.base dynamic cache existence
expected: File `~/.bioimage-mcp/cache/dynamic/tools.base/introspection_cache.json` exists and contains cached schemas.
result: pass

### 3. tools.trackpy dynamic cache existence
expected: File `~/.bioimage-mcp/cache/dynamic/tools.trackpy/introspection_cache.json` exists and contains cached schemas.
result: issue
reported: "ls: cannot access '/home/qianchen/.bioimage-mcp/cache/dynamic/tools.trackpy/introspection_cache.json': No such file or directory"
severity: major

## Summary

total: 3
passed: 1
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "Second run of bioimage-mcp list is significantly faster (< 3s)"
  status: failed
  reason: "User reported: both runs take the same time at around 15-16 s"
  severity: major
  test: 1
  root_cause: "DiscoveryEngine._runtime_list always spawns a subprocess for dynamic adapters; warm cache in tool is bypassed by subprocess overhead in core."
  artifacts:
    - path: "src/bioimage_mcp/registry/engine.py"
      issue: "Lack of core-side caching for dynamic discovery results."
  missing:
    - "Core-side memoization/caching for DiscoveryEngine._runtime_list results."
- truth: "File ~/.bioimage-mcp/cache/dynamic/tools.trackpy/introspection_cache.json exists"
  status: failed
  reason: "User reported: file missing after list command"
  severity: major
  test: 3
  root_cause: "IntrospectionCache bypasses write when lockfile_hash is empty; trackpy entrypoint fails to detect project root/lockfile."
  artifacts:
    - path: "tools/trackpy/bioimage_mcp_trackpy/entrypoint.py"
      issue: "Inaccurate project_root detection in trackpy environment."
  missing:
    - "Relaxed cache gating or improved lockfile detection in trackpy."
