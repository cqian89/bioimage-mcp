---
phase: 21-usam-tool-pack-foundation
plan: 02
subsystem: infra
tags: [conda, conda-lock, micro-sam, microsam, pytorch]

# Dependency graph
requires:
  - phase: 21-usam-tool-pack-foundation
    provides: [Research for µSAM environment]
provides:
  - Conda environment spec for bioimage-mcp-microsam
  - Reproducible lockfile for linux-64 and osx-arm64
affects: [21-03-PLAN.md]

# Tech tracking
tech-stack:
  added: [micro_sam, napari]
  patterns: [isolated tool environment with conda-lock]

key-files:
  created: [envs/bioimage-mcp-microsam.yaml, envs/bioimage-mcp-microsam.lock.yml]
  modified: []

key-decisions:
  - "Used micro_sam (underscore) instead of micro-sam (dash) for the conda package name to match conda-forge registry."
  - "Pinned micro_sam to >=1.7.0 as it is the latest available version on conda-forge."

patterns-established:
  - "Standard foundation for µSAM tool pack with CPU-first lockable environment."

# Metrics
duration: 3 min
completed: 2026-02-05
---

# Phase 21 Plan 02: µSAM Tool Pack Foundation Summary

**Created foundational isolated conda environment and lockfile for µSAM (napari + micro-sam + torch).**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-04T23:10:33Z
- **Completed:** 2026-02-04T23:13:47Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `envs/bioimage-mcp-microsam.yaml` with core dependencies for µSAM.
- Generated `envs/bioimage-mcp-microsam.lock.yml` supporting `linux-64` and `osx-arm64`.
- Verified environment spec and lockfile integrity.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create microsam conda environment spec (CPU-first, cross-platform)** - `5ff1a28` (feat)
2. **Task 2: Generate and check in conda-lock lockfile for microsam** - `d0c4281` (feat)

**Plan metadata:** `pending` (docs: complete plan)

## Files Created/Modified
- `envs/bioimage-mcp-microsam.yaml` - Conda environment specification.
- `envs/bioimage-mcp-microsam.lock.yml` - Multi-platform lockfile.

## Decisions Made
- Used `micro_sam` (underscore) instead of `micro-sam` (dash) for the conda package name to match `conda-forge` registry.
- Target `linux-64` and `osx-arm64` platforms for the lockfile as per roadmap.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrected micro-sam package name to micro_sam**
- **Found during:** Task 2 (Lockfile generation)
- **Issue:** `conda-lock` failed to find `micro-sam`. Mamba search revealed the package name is `micro_sam` on conda-forge.
- **Fix:** Updated `envs/bioimage-mcp-microsam.yaml` to use `micro_sam`.
- **Files modified:** `envs/bioimage-mcp-microsam.yaml`
- **Verification:** `conda-lock` succeeded after fix.
- **Committed in:** `d0c4281` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for lockfile generation. No scope creep.

## Issues Encountered
- None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Foundational environment is ready.
- Ready for `21-03-PLAN.md` (µSAM Tool Pack Installation Orchestration).

---
*Phase: 21-usam-tool-pack-foundation*
*Completed: 2026-02-05*
