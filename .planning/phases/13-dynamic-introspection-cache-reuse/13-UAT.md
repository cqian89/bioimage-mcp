---
status: complete
phase: 13-dynamic-introspection-cache-reuse
source: 13-01-SUMMARY.md, 13-02-SUMMARY.md, 13-03-SUMMARY.md, 13-04-SUMMARY.md, 13-05-SUMMARY.md, 13-06-SUMMARY.md, 13-07-SUMMARY.md, 13-08-SUMMARY.md
started: 2026-01-29T11:56:09Z
updated: 2026-01-29T12:18:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Fast Warm List
expected: Running `bioimage-mcp list` a second time (warm run) is significantly faster than the first (cold run), completing in under 2 seconds.
result: pass

### 2. Lockfile Invalidation
expected: Modifying a conda lockfile in `envs/` causes the next `bioimage-mcp list` to perform a fresh discovery for tools using that environment, rather than hitting the cache.
result: pass

### 3. Manifest Invalidation
expected: Modifying a tool's `manifest.yaml` (e.g., changing a description) causes the next `bioimage-mcp list` to reflect the change immediately by invalidating the cache.
result: pass

### 4. Tool Filtering
expected: Running `bioimage-mcp list --tool trackpy` (or `tools.trackpy`) only displays functions from the trackpy tool pack.
result: pass

### 5. Persistent Trackpy Cache
expected: Trackpy functions appear quickly in the list even after a fresh install or server restart, indicated by `runtime:dynamic_discovery` in JSON output showing they were retrieved from the dynamic cache.
result: pass

### 6. Sentinel Fallback (No Lockfile)
expected: If a tool is installed in an environment where the lockfile cannot be found, caching still functions using the "no-lockfile" sentinel, ensuring performance isn't degraded.
result: pass

### 7. Cache Repair
expected: Deleting a per-tool dynamic cache file in `~/.bioimage-mcp/cache/dynamic/` and running `bioimage-mcp list` causes the file to be regenerated, ensuring the system can recover from corrupted or missing cache files.
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
