---
phase: 25-add-missing-tttr-methods
plan: 03
subsystem: api
tags: [tttrlib, clsmimage, correlator, parity, smoke]
requires:
  - phase: 25-02
    provides: expanded TTTR strict-ID method mappings and export guardrails
provides:
  - CLSMImage metadata method handlers with NativeOutputRef output contracts
  - Correlator method-family handlers for curve, axis, and correlation values
  - Smoke-extended representative coverage linking parity inventory to live method IDs
affects: [tttrlib-runtime-parity, phase-25-closeout]
tech-stack:
  added: []
  patterns:
    - Correlator supported-subset handlers rebuild correlator instances from constrained constructor args
    - CLSM metadata getters serialize JSON payloads as NativeOutputRef artifacts
key-files:
  created:
    - tests/unit/test_tttrlib_entrypoint_clsm_methods.py
  modified:
    - tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py
    - tools/tttrlib/manifest.yaml
    - tools/tttrlib/schema/tttrlib_api.json
    - tools/tttrlib/schema/tttrlib_coverage.json
    - tests/contract/test_tttrlib_parity_inventory.py
    - tests/smoke/test_tttrlib_live.py
key-decisions:
  - "Classify Correlator getter-family methods as supported_subset with explicit constructor argument constraints."
  - "Expose CLSMImage metadata accessors as NativeOutputRef JSON to keep metadata artifact-safe."
  - "Gate parity closure on smoke test presence for representative plan-03 method IDs under smoke_extended runs."
patterns-established:
  - "Parity-to-smoke linkage: representative IDs must appear in live smoke file and coverage registry."
requirements-completed: [TTTR-02, TTTR-03, TTTR-05]
duration: 11 min
completed: 2026-03-05
---

# Phase 25 Plan 03: CLSM/Correlator Parity Closure Summary

**CLSM metadata and Correlator method-family coverage now expose strict IDs with artifact-safe outputs, plus smoke-linked parity checks for phase closure.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-05T14:45:30Z
- **Completed:** 2026-03-05T14:56:28Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added unit-tested CLSM metadata handlers (`get_image_info`, `get_settings`) returning `NativeOutputRef` JSON artifacts.
- Added Correlator family handlers (`get_curve`, `get_x_axis`, `get_corr`) with deterministic supported-subset validation and `TableRef` outputs.
- Updated manifest/schema/coverage entries for strict upstream IDs and subset status tracking.
- Tightened parity contract checks to enforce representative smoke coverage and added corresponding live smoke scenarios.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests for CLSM/Correlator method-family contracts** - `7d57053` (test)
2. **Task 1 (GREEN): Implement CLSM/Correlator subset handlers and registry metadata** - `d17ca08` (feat)
3. **Task 2 (RED): Tighten parity closure contract around representative smoke IDs** - `94b9580` (test)
4. **Task 2 (GREEN): Add representative live smoke coverage and finalize parity triggers** - `4b499da` (feat)

**Plan metadata:** pending

## Files Created/Modified
- `tests/unit/test_tttrlib_entrypoint_clsm_methods.py` - TDD coverage for CLSM metadata and Correlator subset behavior.
- `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` - New handlers and subset validation for CLSM/Correlator method families.
- `tools/tttrlib/manifest.yaml` - Declares newly exposed strict upstream method IDs.
- `tools/tttrlib/schema/tttrlib_api.json` - Aligns schema contracts for new method outputs.
- `tools/tttrlib/schema/tttrlib_coverage.json` - Promotes representative methods and updates parity revisit guidance.
- `tests/contract/test_tttrlib_parity_inventory.py` - Enforces representative smoke linkage in parity closure checks.
- `tests/smoke/test_tttrlib_live.py` - Adds live representative method-family scenarios.

## Decisions Made
- Kept Correlator method-family expansion in `supported_subset` mode so unsupported constructor shapes fail fast with stable errors.
- Used NativeOutputRef JSON for CLSM metadata methods instead of raw inline payloads to preserve artifact boundaries.
- Marked parity contract tests with `smoke_extended` so closure checks run in the same verification lane as representative live smoke tests.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `smoke_extended` verification in this workspace is environment-gated and skipped live execution, but contract linkage and unit verification passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 25 parity inventory now has representative live-scenario linkage for newly exposed CLSM/Correlator families.
- Plan 25-03 complete; phase is ready for transition once metadata commit updates planning state files.

## Self-Check: PASSED

- FOUND: `.planning/phases/25-add-missing-tttr-methods/25-03-SUMMARY.md`
- FOUND: `7d57053`
- FOUND: `d17ca08`
- FOUND: `94b9580`
- FOUND: `4b499da`
