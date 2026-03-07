---
phase: 25-add-missing-tttr-methods
plan: 10
subsystem: api
tags: [tttrlib, export-runtime, execution-routing, guardrails]
requires:
  - phase: 25-07
    provides: reduced TTTR export discovery and post-write guardrail baseline
  - phase: 25-09
    provides: current UAT-confirmed export regression reproduction state
provides:
  - Run-only fallback for hidden tttrlib export IDs that now fail with stable unsupported-method errors
  - Canonical TTTR.write format mapping aligned with TTTRRef schema values
  - Deterministic generic write rejection when extensions are unsupported or no export file is produced
affects: [25-11, tttrlib-runtime-parity, execution-routing, export-guardrails]
tech-stack:
  added: []
  patterns:
    - hidden tttrlib methods can remain runnable only through coverage-aware core fallback
    - generic TTTR.write success requires canonical format mapping plus on-disk file existence
key-files:
  created:
    - .planning/phases/25-add-missing-tttr-methods/25-10-SUMMARY.md
  modified:
    - src/bioimage_mcp/api/execution.py
    - tools/tttrlib/schema/tttrlib_coverage.json
    - tests/contract/test_tttrlib_manifest.py
    - tests/contract/test_tttrlib_schema_alignment.py
    - tests/unit/api/test_execution.py
    - tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py
    - tests/unit/test_tttrlib_entrypoint_tttr_methods.py
key-decisions:
  - "Keep removed TTTR export IDs hidden from discovery while routing known denied/deferred IDs to the tttrlib worker for stable TTTRLIB_UNSUPPORTED_METHOD failures."
  - "Map generic TTTR.write suffixes to canonical TTTRRef formats such as SPC-130 and PHOTON-HDF5 instead of raw uppercase extensions."
  - "Treat TTTR.write success as requiring both a non-failing upstream call and a real file under work_dir before returning tttr_out."
patterns-established:
  - "Run-only unsupported routing: coverage metadata may extend execution lookup without widening manifest/schema discovery."
  - "Canonical TTTR export mapping: file suffix validation happens before artifact creation so invalid formats never reach TTTRRef validation."
requirements-completed: [TTTR-02, TTTR-03, TTTR-04, TTTR-05]
duration: 18 min
completed: 2026-03-07
---

# Phase 25 Plan 10: TTTR export regression restoration Summary

**TTTR export routing again preserves stable unsupported-method errors, and generic `tttrlib.TTTR.write` now returns only canonical schema-valid TTTR artifacts backed by real files.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-07T07:34:00Z
- **Completed:** 2026-03-07T07:52:43Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Restored run-only fallback for hidden `tttrlib` export IDs so removed methods now fail with `TTTRLIB_UNSUPPORTED_METHOD` instead of `NOT_FOUND`.
- Re-aligned TTTR export coverage metadata and contract tests around the reduced runtime-safe discovery surface.
- Hardened generic `TTTR.write` so unsupported extensions, false upstream returns, and missing output files fail before bogus `TTTRRef` creation.

## Task Commits

Each task was committed atomically:

1. **Task 1: Restore reduced export discovery and run-only unsupported routing** - `780074f` (feat)
2. **Task 2: Re-harden generic TTTR.write output validation and canonical format mapping** - `4218b10` (fix)

**Plan metadata:** pending

## Files Created/Modified
- `src/bioimage_mcp/api/execution.py` - Restores coverage-aware fallback for denied/deferred `tttrlib.*` IDs during `run()` lookup.
- `tools/tttrlib/schema/tttrlib_coverage.json` - Reclassifies removed specialized exports as deferred/denied while keeping generic write supported.
- `tests/contract/test_tttrlib_manifest.py` - Guards the reduced export discovery surface and unsupported coverage statuses.
- `tests/contract/test_tttrlib_schema_alignment.py` - Guards manifest/schema exclusion for removed export IDs.
- `tests/unit/api/test_execution.py` - Verifies removed export IDs still reach the worker and unknown IDs remain `NOT_FOUND`.
- `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` - Adds canonical TTTR.write format mapping and post-write file existence checks.
- `tests/unit/test_tttrlib_entrypoint_tttr_methods.py` - Covers canonical-format, wrong-extension, false-return, and missing-file write regressions.

## Decisions Made
- Preserved the locked reduced export surface instead of re-exposing specialized export methods through the manifest.
- Used coverage metadata as the execution-layer source of truth for hidden unsupported tttrlib method routing.
- Kept generic `TTTR.write` as the only surfaced export path and tightened it to schema-valid formats with explicit postconditions.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `pytest tests/smoke/test_tttrlib_live.py -m smoke_extended -q` was fully environment-gated in this workspace (`12 skipped`), so live verification evidence came from the committed smoke assertions plus the fast contract/unit suites.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- TTTR export regression gap 3 is closed at the execution and worker layers for the supported public surface.
- Phase 25 plan 11 can build on deterministic unsupported routing and schema-valid generic export behavior without revisiting these guardrails.

## Self-Check: PASSED
