---
phase: 17-list-table-formatting
plan: 02
subsystem: cli
tags: [conda, lockfile, caching, versioning]

# Dependency graph
requires:
  - phase: 17-01
    provides: [hierarchical CLI list output foundation]
provides:
  - lockfile-first version resolution for primary libraries
  - cache invalidation on lockfile changes
  - unit coverage for version resolution logic
affects: [CLI user experience]

# Tech tracking
tech-stack:
  added: []
  patterns: [lockfile-first version resolution, fingerprinting with external files]

key-files:
  created: []
  modified:
    - src/bioimage_mcp/bootstrap/list.py
    - src/bioimage_mcp/bootstrap/list_cache.py
    - tests/unit/bootstrap/test_list_output.py

key-decisions:
  - "Use lockfiles as primary source of truth for library versions to avoid expensive conda subprocess calls."
  - "Include all lockfiles in CLI cache fingerprint to ensure output stays fresh when environments are updated."
  - "Prefer platform-matched entries in lockfiles but fallback to first match for robustness."

# Metrics
duration: 30 min
completed: 2026-02-01
---

# Phase 17 Plan 02: Lockfile-first library versions Summary

**Implemented lockfile-first library version reporting for `bioimage-mcp list`, with cache invalidation wired to lockfile changes.**

## Performance

- **Duration:** 30 min
- **Started:** 2026-02-01T23:03:37Z
- **Completed:** 2026-02-01T23:33:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Implemented `_resolve_version` helper that parses `envs/<env_id>.lock.yml` for actual library versions.
- Added fallback to live conda query if lockfile is missing or doesn't match.
- Integrated resolved versions into hierarchical `bioimage-mcp list` output (both table and JSON).
- Updated `ListToolsCache` to include lockfile stats in the fingerprint, ensuring cache invalidation on environment updates.
- Added comprehensive unit tests for version resolution and cache invalidation.

## Task Commits

Each task was committed atomically:

1. **Task 2: include lockfiles in CLI list cache fingerprint** - `1b3b98f` (feat)
2. **Task 1: implement lockfile-first library version resolution** - `0229334` (feat)
3. **Task 3: add unit tests for lockfile-derived versions and cache invalidation** - `1ca81b8` (test)

**Plan metadata:** `docs(17-02): complete lockfile-first library versions plan`

## Files Created/Modified
- `src/bioimage_mcp/bootstrap/list.py` - Main list logic with version resolution
- `src/bioimage_mcp/bootstrap/list_cache.py` - Updated fingerprinting logic
- `tests/unit/bootstrap/test_list_output.py` - New unit tests

## Decisions Made
- **Lockfile-first resolution:** Parsing YAML lockfiles is much faster than running `conda list`.
- **Global lockfile fingerprinting:** Fingerprinting all `envs/*.lock.yml` files simplifies implementation while maintaining correctness, as any change to an environment lock should potentially refresh the listing.
- **Platform matching:** Added logic to prefer lockfile entries matching the current platform (e.g., `linux-64`) for accuracy in multi-platform lockfiles.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- **Manifest Discovery in Tests:** Initial unit test failed because of missing required fields in the mock manifest (`entrypoint`, `name`, `description`). Resolved by adding these fields to match the `Manifest` model requirements.

## Next Phase Readiness
- CLI listing is now version-aware and hierarchical.
- Phase 17 is complete.
- Ready for v0.4.0 release.

---
*Phase: 17-list-table-formatting*
*Completed: 2026-02-01*
