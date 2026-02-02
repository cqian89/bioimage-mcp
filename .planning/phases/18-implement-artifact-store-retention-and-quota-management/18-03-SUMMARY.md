---
phase: 18-implement-artifact-store-retention-and-quota-management
plan: 3
subsystem: storage
tags: [sqlite, cleanup, background-tasks, scheduling]

# Dependency graph
requires:
  - phase: 18-implement-artifact-store-retention-and-quota-management
    provides: StorageManager and StoragePolicy
provides:
  - Artifact cleanup engine with dry-run and safety skips
  - Background cleanup scheduler integrated into MCP server
affects:
  - CLI visibility of storage status

# Tech tracking
tech-stack:
  added: []
  patterns: [Background thread worker, SQLite-based mutex lock]

key-files:
  created:
    - src/bioimage_mcp/storage/cleanup.py
  modified:
    - src/bioimage_mcp/bootstrap/serve.py

key-decisions:
  - "Use a SQLite-based lock (registry_state key) to coordinate cleanup runs across potential multi-instance deployments."
  - "Run cleanup in a background daemon thread to avoid blocking the MCP stdio communication."
  - "Implement rename-to-trash (suffixing with .deleted.<timestamp>) before final unlinking for safer multi-step deletion."

patterns-established:
  - "Background Worker: Use threading.Event for clean shutdown signal and waitable intervals."
  - "Safe Deletion: Rename-to-trash for directory and file artifacts to handle partial deletions gracefully."

# Metrics
duration: 6 min
completed: 2026-02-02
---

# Phase 18 Plan 3: Cleanup Engine and Scheduler Summary

**Implemented the artifact cleanup engine with retention and quota triggers, safety skips (pinned/active), and a non-blocking background scheduler for the MCP server.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-02T21:51:40Z
- **Completed:** 2026-02-02T22:01:21Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- **Cleanup Engine**: Implemented `run_cleanup` and `maybe_cleanup` in `src/bioimage_mcp/storage/cleanup.py`.
- **Safety Mechanics**: Added cooldown enforcement, SQLite-based locking (`cleanup_lock_until`), and rename-to-trash deletion.
- **Background Scheduler**: Integrated a daemon thread into `bioimage-mcp serve` that periodically checks and triggers cleanup without impacting MCP request latency.
- **Event Logging**: Summary events are recorded in the `cleanup_events` table for every run.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement cleanup engine (retention + quota) with safety + event logging** - `355523b` (feat)
2. **Task 2: Add non-blocking periodic cleanup scheduler to `bioimage-mcp serve`** - `96987f2` (feat)

**Plan metadata:** `e093952` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/storage/cleanup.py` - Core cleanup logic and threshold checks.
- `src/bioimage_mcp/bootstrap/serve.py` - Background thread integration.
- `tests/unit/storage/test_cleanup.py` - Unit tests for retention, quota, and dry-run.

## Decisions Made
- Used a dedicated SQLite lock key `cleanup_lock_until` to ensure that even if multiple server instances are running against the same database, only one performs cleanup at a time.
- Chose `threading.Thread` for the background worker as it is simple and doesn't require modifying the `mcp.run` (FastMCP) internals.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - the implementation followed the research patterns and integrated cleanly with existing `StorageManager`.

## Next Phase Readiness
- Ready for 18-04-PLAN.md (CLI status/cleanup/pin commands).
- The foundation for storage management is now operational in the background.
