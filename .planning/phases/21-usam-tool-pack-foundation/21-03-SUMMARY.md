---
phase: 21-usam-tool-pack-foundation
plan: 03
subsystem: infra
tags: [microsam, cli, conda, gpu, pytorch]

# Dependency graph
requires:
  - phase: 21-usam-tool-pack-foundation
    provides: [microsam tool pack scaffold, microsam conda environment]
provides:
  - CLI support for `install microsam [--profile cpu|gpu]`
  - Installer orchestration for microsam env + model bootstrap
  - Persisted model-cache record in `.bioimage-mcp/state/microsam_models.json`
affects: [Phase 21 Plan 04 (Doctor verification)]

# Tech tracking
tech-stack:
  added: [trackastra, MobileSAM]
  patterns: [Tool-specific post-install orchestration, GPU platform-aware semantics]

key-files:
  created: []
  modified: [src/bioimage_mcp/cli.py, src/bioimage_mcp/bootstrap/install.py, tests/integration/test_cli_doctor_install.py, tests/unit/bootstrap/test_install.py]

key-decisions:
  - "Default microsam install to CPU profile if unspecified"
  - "Use pytorch-cuda=12.1 for Linux GPU installs of microsam"
  - "Perform pip-only installs and model bootstrap as specialized post-install steps"

patterns-established:
  - "Tool-specific post-install hooks in the bootstrap installer"

# Metrics
duration: 25 min
completed: 2026-02-04
---

# Phase 21 Plan 03: µSAM Tool Pack Foundation Summary

**Integrated `microsam` installation into the bioimage-mcp CLI and bootstrap installer, including environment repair, GPU acceleration setup, and model bootstrapping.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-02-04T23:00:00Z
- **Completed:** 2026-02-04T23:25:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Extended CLI `install` subcommand to allow `microsam` to be combined with `--profile`.
- Implemented `_microsam_gpu_post_install` for platform-specific GPU acceleration (CUDA 12.1 on Linux, MPS on Apple Silicon).
- Implemented `_microsam_post_install` covering sanity imports, pip-only dependencies (`trackastra`, `MobileSAM`), and model set bootstrapping.
- Added persistence of model cache metadata to `.bioimage-mcp/state/microsam_models.json`.
- Relaxed `conda-lock` heuristic to allow its use for `microsam` despite pip-only dependencies.

## Task Commits

Each task was committed atomically:

1. **Task 1: support install microsam in CLI** - `d1a777e` (feat)
2. **Task 2: implement microsam install orchestration** - `43ad703` (feat)
3. **Task 3: keep install utility behavior stable** - (No changes needed, verified via existing tests)

**Plan metadata:** `8ed2073` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/cli.py` - Updated `_handle_install` to allow `microsam` + `--profile`.
- `src/bioimage_mcp/bootstrap/install.py` - Implemented microsam specific install logic and GPU post-install.
- `tests/integration/test_cli_doctor_install.py` - Added integration tests for CLI wiring.
- `tests/unit/bootstrap/test_install.py` - Added unit tests for microsam orchestration.

## Decisions Made
- **Default to CPU:** If no profile is provided for `microsam`, it defaults to `cpu`.
- **Modern PyTorch-CUDA:** Used `pytorch-cuda=12.1` for microsam on Linux to align with modern requirements.
- **Separate Pip/Model Step:** Handled `MobileSAM` and `trackastra` via pip post-install as they are not available on standard conda channels.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## Next Phase Readiness
- `bioimage-mcp install microsam` is fully functional.
- Ready for Phase 21 Plan 04: Doctor verification for µSAM environment and models.

---
*Phase: 21-usam-tool-pack-foundation*
*Completed: 2026-02-04*
