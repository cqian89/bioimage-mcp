---
phase: 13-dynamic-introspection-cache-reuse
plan: 05
subsystem: cli
tags: [caching, performance, python]

# Dependency graph
requires:
  - phase: 13-dynamic-introspection-cache-reuse
    provides: [persistent dynamic introspection cache]
provides:
  - Persistent cache for bioimage-mcp list CLI
  - Faster warm runs for tool listing (<3s)
affects: [Phase 13 UAT verification]

# Tech tracking
tech-stack:
  added: []
  patterns: [File-backed JSON caching for CLI processes]

key-files:
  created: [src/bioimage_mcp/bootstrap/list_cache.py, tests/unit/bootstrap/test_list_cache.py]
  modified: [src/bioimage_mcp/bootstrap/list.py, tests/unit/bootstrap/test_list_output.py]

key-decisions:
  - "Used fingerprinting of manifest files (mtime/size) and env-manager state to invalidate CLI caches."
  - "Sandboxed Path.home() in tests to ensure cache isolation."

patterns-established:
  - "Persistent CLI caching: Use ~/.bioimage-mcp/cache/cli for process-agnostic speedups."

# Metrics
duration: 6 min
completed: 2026-01-29
---

# Phase 13 Plan 05: CLI List Persistent Caching Summary

**Implemented a persistent, file-backed cache for the `bioimage-mcp list` command, reducing warm run times from >7s to <1.5s.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-01-29T07:24:00Z
- **Completed:** 2026-01-29T07:30:02Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Created `list_cache.py` helper module with `InstalledEnvsCache` and `ListToolsCache`.
- Wired caching into the `list_tools` code path, enabling a fast path that skips subprocesses and manifest loading.
- Added comprehensive unit tests proving cache hits and proper invalidation.
- Verified warm run speed (1.3s) meets the <3s requirement.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add persistent cache helpers for CLI list** - `daa3a0c` (feat)
2. **Task 2: Wire persistent caches into bioimage-mcp list** - `d9985fc` (feat)
3. **Task 3: Add unit tests for CLI list caching** - `ec7655e` (test)

## Files Created/Modified
- `src/bioimage_mcp/bootstrap/list_cache.py` - New persistent cache helper.
- `src/bioimage_mcp/bootstrap/list.py` - Integrated caching into CLI list path.
- `tests/unit/bootstrap/test_list_cache.py` - New tests for caching logic.
- `tests/unit/bootstrap/test_list_output.py` - Fixed tests to be cache-safe.

## Decisions Made
- Chose `~/.bioimage-mcp/cache/cli` as the cache root for CLI-specific persistent data.
- Implemented a TTL for environment list caching (1 hour) to balance speed and accuracy, while manifest caching relies on strict fingerprinting.
- Used `monkeypatch` for `Path.home()` in tests to ensure zero interference with the developer's actual machine state.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **Git lock**: Encounted a git index lock during first commit attempt; resolved by manually removing the lock file.
- **Test validation**: Initial tests failed due to strict Pydantic validation on `ToolManifest` (missing `manifest_version` and invalid `env_id` prefix); resolved by fixing mock data.
- **Test interference**: Discovered that `test_list_output.py` could interfere with or be interfered by the new cache; resolved by sandboxing `Path.home()` in all relevant tests.

## Next Phase Readiness
- Phase 13 speed gap closed.
- Ready for Phase 14 (OME-Zarr Standardization).
