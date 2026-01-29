---
status: diagnosed
phase: 13-dynamic-introspection-cache-reuse
source: [13-01-SUMMARY.md, 13-02-SUMMARY.md, 13-03-SUMMARY.md, 13-04-SUMMARY.md]
started: 2026-01-28T23:45:15Z
updated: 2026-01-29T00:15:20Z
---

## Current Test

[testing complete]

## Tests

### 1. Warm-cache list speed
expected: Running `bioimage-mcp list` twice, the second run completes in under ~3s and is noticeably faster than the first run.
result: issue
reported: "Second run onwards still take more than 5s. Not much faster than first if any"
severity: major

### 2. tools.base dynamic cache file
expected: After a `bioimage-mcp list`, file `~/.bioimage-mcp/cache/dynamic/tools.base/introspection_cache.json` exists and is non-empty.
result: pass

### 3. tools.trackpy dynamic cache file
expected: After `bioimage-mcp list` (or `bioimage-mcp list --tool trackpy`), file `~/.bioimage-mcp/cache/dynamic/tools.trackpy/introspection_cache.json` exists and is non-empty.
result: pass

### 4. trackpy project root override
expected: From outside the repo, running `BIOIMAGE_MCP_PROJECT_ROOT=/mnt/c/Users/meqia/bioimage-mcp bioimage-mcp list --tool trackpy` still creates or updates `~/.bioimage-mcp/cache/dynamic/tools.trackpy/introspection_cache.json`.
result: pass

## Summary

total: 4
passed: 3
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Running `bioimage-mcp list` twice, the second run completes in under ~3s and is noticeably faster than the first run."
  status: failed
  reason: "User reported: Second run onwards still take more than 5s. Not much faster than first if any"
  severity: major
  test: 1
  root_cause: "CLI `bioimage-mcp list` lacks persistent caching for manifest discovery and environment listing (only has in-memory cache)."
  artifacts:
    - path: "src/bioimage_mcp/cli.py"
      issue: "CLI list calls bootstrap.list.list_tools in a fresh process."
    - path: "src/bioimage_mcp/bootstrap/list.py"
      issue: "list path always loads manifests and calls env manager subprocess."
    - path: "src/bioimage_mcp/registry/loader.py"
      issue: "_MANIFEST_CACHE is process-local only."
  missing:
    - "Persistent cache for CLI list (manifest discovery + env list results)."
  debug_session: ".planning/debug/warm-cache-slow.md"
