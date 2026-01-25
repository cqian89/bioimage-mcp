---
phase: 06-infrastructure-n-d-foundation
plan: 2
subsystem: infra
tags: [scipy, dynamic-discovery, manifest]

# Dependency graph
requires:
  - phase: 05.1-discovery
    provides: [Standardized discovery protocol]
provides:
  - Configurable blacklist for scipy discovery
  - Deprecated function filtering in discovery
  - Manifest context injection for path resolution
affects: [06-03, 07-transforms]

# Tech tracking
tech-stack:
  added: [PyYAML (usage in adapter)]
  patterns: [Config-driven discovery filtering]

key-files:
  created: [tools/base/scipy_ndimage_blacklist.yaml, tests/unit/registry/dynamic/test_scipy_ndimage_discovery_config.py]
  modified: [src/bioimage_mcp/registry/manifest_schema.py, src/bioimage_mcp/registry/dynamic/discovery.py, src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py, tools/base/manifest.yaml]

key-decisions:
  - "Inject _manifest_path into adapter config to allow resolution of relative paths (like blacklists) without global state."
  - "Automatically filter functions marked as 'Deprecated' or using the Sphinx '.. deprecated::' directive in docstrings."

# Metrics
duration: 4 min
completed: 2026-01-25
---

# Phase 6 Plan 2: Harden scipy.ndimage discovery Summary

**Harden scipy.ndimage discovery with a config-driven blacklist and deprecated filtering, while passing manifest context into adapters for path resolution.**

## Performance
- **Duration:** 4 min
- **Started:** 2026-01-25T19:29:58Z
- **Completed:** 2026-01-25T19:34:01Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Extended `DynamicSource` schema with `blacklist_path`.
- Implemented `_manifest_path` injection in `discover_functions` to allow adapters to resolve local config files.
- Updated `ScipyNdimageAdapter` to respect external blacklists and filter out deprecated functions based on docstrings.
- Added a robust unit test verifying filtering logic with a mock module.

## Task Commits
1. **Task 1: Manifest schema: add blacklist_path to DynamicSource** - `18c4960` (feat)
2. **Task 2: Discovery context: pass manifest_path into adapter.discover config** - `1c92192` (feat)
3. **Task 3: Scipy ndimage discovery: blacklist + deprecated filtering + unit test** - `9c940e6` (feat)

## Files Created/Modified
- `src/bioimage_mcp/registry/manifest_schema.py` - Added `blacklist_path` to `DynamicSource`
- `src/bioimage_mcp/registry/dynamic/discovery.py` - Injected `_manifest_path` into adapter config
- `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py` - Implemented filtering logic
- `tools/base/manifest.yaml` - Configured scipy blacklist path
- `tools/base/scipy_ndimage_blacklist.yaml` - Initial blacklist configuration
- `tests/unit/registry/dynamic/test_scipy_ndimage_discovery_config.py` - New unit tests

## Decisions Made
- Used docstring parsing for best-effort deprecated filtering, matching SciPy's convention.
- Resolved blacklist paths relative to the manifest directory to ensure portability.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Missing `pandas` in test environment required installing dev dependencies (`pip install -e ".[dev]"`).

## Next Phase Readiness
- Infrastructure for stable scipy discovery is ready.
- Ready for Task 3 or next plan (Phase 6 Plan 3).

---
*Phase: 06-infrastructure-n-d-foundation*
*Completed: 2026-01-25*
