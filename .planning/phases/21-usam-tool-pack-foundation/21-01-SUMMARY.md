---
phase: 21-usam-tool-pack-foundation
plan: 01
subsystem: infra
tags: [microsam, sam, segmentation, tool-pack]

# Dependency graph
requires:
  - phase: 20-unified-introspection
    provides: Tool registry and discovery engine
provides:
  - Microsam tool pack scaffold (manifest + entrypoint)
  - Tool-local model installation helper script
affects:
  - Phase 21 Plan 02: Microsam conda environment
  - Phase 21 Plan 03: Installer wiring

# Tech tracking
tech-stack:
  added: [micro-sam]
  patterns: [tool-pack-scaffold, json-stdin-stdout-protocol]

key-files:
  created:
    - tools/microsam/manifest.yaml
    - tools/microsam/bioimage_mcp_microsam/entrypoint.py
    - tools/microsam/bioimage_mcp_microsam/install_models.py

key-decisions:
  - "Use vit_b variants as the minimum model requirement for initial installation"
  - "Implementing meta.describe in the entrypoint to support unified discovery"

patterns-established:
  - "One-shot JSON protocol for tool entrypoints"
  - "Isolated model installation helper scripts inside tool packs"

# Metrics
duration: 2 min
completed: 2026-02-04
---

# Phase 21 Plan 01: Microsam Tool Pack Foundation Summary

**Established the on-disk tool pack structure for `microsam` including manifest, entrypoint, and model installation helper.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-04T23:10:31Z
- **Completed:** 2026-02-04T23:11:57Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created `tools/microsam` directory structure following project standards.
- Defined `manifest.yaml` with `tools.microsam` ID and metadata.
- Implemented `entrypoint.py` with support for the standard JSON execution protocol and `meta.describe`.
- Added `install_models.py` to automate the download of required SAM models (vit_b variants for Generalist, LM, and EM).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add microsam tool pack manifest + entrypoint skeleton** - `de2b2b3` (feat)
2. **Task 2: Add tool-local model ensure-cached script used by the installer** - `204b706` (feat)

**Plan metadata:** `2df9ed2` (docs: complete plan)

## Files Created/Modified
- `tools/microsam/manifest.yaml` - Tool pack declaration
- `tools/microsam/bioimage_mcp_microsam/__init__.py` - Package initialization
- `tools/microsam/bioimage_mcp_microsam/entrypoint.py` - Tool execution entrypoint
- `tools/microsam/bioimage_mcp_microsam/install_models.py` - Model cache management script

## Decisions Made
- Used `vit_b` versions of Generalist, LM, and EM models as the baseline for installation readiness.
- Chose to implement `meta.describe` manually in the entrypoint for now, aligning with the Phase 21 goal of foundational support before full dynamic discovery integration.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Ready for Phase 21 Plan 02: Microsam conda environment and lockfile generation.
- The `install_models.py` script is ready to be invoked once the environment is created.

---
*Phase: 21-usam-tool-pack-foundation*
*Completed: 2026-02-04*
