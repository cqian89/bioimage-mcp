---
phase: 01-core-runtime
plan: 01
subsystem: infra
tags: [python, gpu, cuda, mps, apple-silicon]

# Dependency graph
requires:
  - phase: 01-core-runtime
    provides: [Basic GPU detection (NVIDIA only)]
provides:
  - Unified GPU detection for both NVIDIA (CUDA) and Apple Silicon (MPS)
  - Detailed GPU hardware info (model, memory) in doctor output
affects: [future tool execution performance, local resource reporting]

# Tech tracking
tech-stack:
  added: []
  patterns: [System command probing for hardware detection]

key-files:
  created: []
  modified: [src/bioimage_mcp/bootstrap/checks.py, tests/unit/bootstrap/test_checks.py]

key-decisions:
  - "Unified GPU detection structure: Instead of separate checks, a single 'gpu' check now reports both CUDA and MPS status."
  - "System command probing: Using platform.system() and sysctl for MPS detection to avoid adding heavy dependencies like PyTorch to the core server."

patterns-established:
  - "Unified hardware capability reporting in CheckResult details."

# Metrics
duration: 15min
completed: 2026-01-22
---

# Phase 01: Core Runtime Plan 01 Summary

**Unified GPU detection implemented for NVIDIA (CUDA) and Apple Silicon (MPS) with detailed hardware reporting.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-01-22T12:55:00Z
- **Completed:** 2026-01-22T13:10:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Enhanced `check_gpu()` to detect Apple Silicon MPS using `sysctl`.
- Unified GPU info structure in `doctor` output to include both `cuda` and `mps` status.
- Added detailed hardware info extraction for NVIDIA GPUs (model name, total memory).
- Added comprehensive unit tests for different GPU availability scenarios (CUDA, MPS, both, none).

## Task Commits

Each task was committed atomically:

1. **Task 1: Enhance check_gpu() with MPS detection** - `202ef7b` (feat)
2. **Task 2: Add tests for MPS detection** - `878658c` (test)

**Plan metadata:** `[PENDING]` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/bootstrap/checks.py` - Enhanced `check_gpu()` implementation.
- `tests/unit/bootstrap/test_checks.py` - Added unit tests for MPS and unified GPU detection.

## Decisions Made
- **Unified GPU check**: Decided to keep a single "gpu" check in `doctor` that reports sub-details for different backends, making the output cleaner and more informative than having separate top-level checks.
- **Dependency-free detection**: Used `subprocess` to call `sysctl` for MPS detection rather than importing `torch` or `mlx`, keeping the core server lightweight.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Core GPU detection requirement (CORE-02) is now fully complete.
- Ready for advanced tool execution features that leverage this detection.

---
*Phase: 01-core-runtime*
*Completed: 2026-01-22*
