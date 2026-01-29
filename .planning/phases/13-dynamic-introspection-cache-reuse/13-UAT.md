---
status: complete
phase: 13-dynamic-introspection-cache-reuse
source: [13-01-SUMMARY.md, 13-02-SUMMARY.md, 13-03-SUMMARY.md, 13-04-SUMMARY.md, 13-05-SUMMARY.md]
started: 2026-01-29T08:00:00Z
updated: 2026-01-29T08:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Warm-cache CLI list speed
expected: Running `bioimage-mcp list` twice, the second run completes in under ~2s (ideally <1.5s) and is significantly faster than the first run.
result: pass

### 2. tools.base dynamic cache file
expected: After a `bioimage-mcp list`, file `~/.bioimage-mcp/cache/dynamic/tools.base/introspection_cache.json` exists and is non-empty.
result: pass

### 3. tools.trackpy dynamic cache file
expected: After `bioimage-mcp list` (or `bioimage-mcp list --tool trackpy`), file `~/.bioimage-mcp/cache/dynamic/tools.trackpy/introspection_cache.json` exists and is non-empty.
result: issue
reported: "`bioimage-mcp list --tool trackpy` is not implemented in CLI. but introspection_cache.json exists"
severity: minor

### 4. trackpy project root override
expected: From outside the repo, running `BIOIMAGE_MCP_PROJECT_ROOT=/mnt/c/Users/meqia/bioimage-mcp bioimage-mcp list` still creates or updates `~/.bioimage-mcp/cache/dynamic/tools.trackpy/introspection_cache.json`.
result: issue
reported: "This only recreates the cache file if the entire cache directory is deleted. If only the introspection_cache.json is deleted, it is not regenerated."
severity: major

### 5. Core-side cache invalidation
expected: Modifying a tool manifest (e.g. changing a description) and running `bioimage-mcp list` triggers a cache miss (slower run) and updates the cache with the new info.
result: issue
reported: "Modifying the manifest triggered a slower run (cache miss), but the cache file on disk was not updated with new metadata/timestamp."
severity: major

## Summary

total: 5
passed: 2
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: "After `bioimage-mcp list` (or `bioimage-mcp list --tool trackpy`), file `~/.bioimage-mcp/cache/dynamic/tools.trackpy/introspection_cache.json` exists and is non-empty."
  status: failed
  reason: "User reported: `bioimage-mcp list --tool trackpy` is not implemented in CLI. but introspection_cache.json exists"
  severity: minor
  test: 3
  artifacts: []
  missing: []

- truth: "From outside the repo, running `BIOIMAGE_MCP_PROJECT_ROOT=/mnt/c/Users/meqia/bioimage-mcp bioimage-mcp list` still creates or updates `~/.bioimage-mcp/cache/dynamic/tools.trackpy/introspection_cache.json`."
  status: failed
  reason: "User reported: This only recreates the cache file if the entire cache directory is deleted. If only the introspection_cache.json is deleted, it is not regenerated."
  severity: major
  test: 4
  artifacts: []
  missing: []

- truth: "Modifying a tool manifest (e.g. changing a description) and running `bioimage-mcp list` triggers a cache miss (slower run) and updates the cache with the new info."
  status: failed
  reason: "User reported: Modifying the manifest triggered a slower run (cache miss), but the cache file on disk was not updated with new metadata/timestamp."
  severity: major
  test: 5
  artifacts: []
  missing: []
