---
phase: 25-add-missing-tttr-methods
plan: 05
subsystem: api
tags: [tttrlib, clsmimage, correlator, payload-verification, smoke-tests]
requires:
  - phase: 25-03
    provides: CLSMImage and Correlator method-family baseline handlers
  - phase: 25-04
    provides: UAT-driven TTTR gap-closure workflow and payload verification patterns
provides:
  - JSON-safe CLSM settings artifacts with nested SWIG values normalized to Python data
  - Correlator getter handlers aligned to live CorrelatorCurve x/y runtime shape
  - Unit and smoke assertions that open returned artifacts and verify payload content
affects: [tttrlib-runtime-parity, tttrlib-uat-gap-closure, phase-25-closeout]
tech-stack:
  added: []
  patterns:
    - CLSM metadata exports normalize SWIG-backed objects before JSON persistence.
    - Correlator constructor and getter handlers share one table artifact builder for consistent metadata.
key-files:
  created: []
  modified:
    - tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py
    - tests/unit/test_tttrlib_entrypoint_clsm_methods.py
    - tests/smoke/test_tttrlib_live.py
key-decisions:
  - "Serialize CLSMImage.get_settings by walking public CLSMSettings attributes and converting nested SWIG containers to JSON-safe values instead of relying on json default=str."
  - "Treat CorrelatorCurve as an object with x/y accessors and reuse a shared TableRef writer so constructor and getter outputs keep the same metadata contract."
patterns-established:
  - "Payload-proof smoke pattern: open artifact files in smoke tests and assert content, not just ref shape."
  - "Runtime-shape fallback pattern: accept legacy tuple-like doubles in tests while prioritizing live x/y getter objects in production handlers."
requirements-completed: [TTTR-02, TTTR-03, TTTR-05]
duration: 12 min
completed: 2026-03-06
---

# Phase 25 Plan 05: CLSM settings and Correlator UAT gap-closure Summary

**CLSM settings now persist as inspectable JSON metadata and Correlator getter artifacts match the live CorrelatorCurve shape with content-level verification.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-06T09:33:04Z
- **Completed:** 2026-03-06T09:45:58Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added explicit CLSM settings normalization so `tttrlib.CLSMImage.get_settings` no longer writes a stringified SWIG proxy.
- Unified Correlator table emission and fixed `get_curve` to read the live `CorrelatorCurve.x/.y` shape.
- Strengthened unit and smoke coverage to open returned artifacts and assert JSON/CSV payload content directly.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing coverage for CLSM settings artifacts** - `2915815` (test)
2. **Task 1 (GREEN): Serialize CLSM settings as JSON metadata** - `b2204e0` (feat)
3. **Task 2 (RED): Add failing correlator curve-shape coverage** - `26027a8` (test)
4. **Task 2 (GREEN): Normalize correlator getter table outputs** - `1452181` (feat)

**Plan metadata:** pending

## Files Created/Modified
- `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` - Normalizes CLSM settings payloads and shares Correlator table artifact construction across constructor/getter handlers.
- `tests/unit/test_tttrlib_entrypoint_clsm_methods.py` - Covers JSON-safe CLSM settings serialization plus non-iterable CorrelatorCurve getter behavior and metadata.
- `tests/smoke/test_tttrlib_live.py` - Opens NativeOutputRef/TableRef artifacts and validates payload content for CLSM metadata and Correlator getters.

## Decisions Made
- Serialized `CLSMSettings` via public-attribute traversal because the live runtime returns a SWIG proxy rather than a dict.
- Kept Correlator getter support within the existing constructor subset while normalizing only the output writer and runtime-shape extraction.
- Expanded smoke assertions to inspect returned files directly so UAT-relevant payload regressions cannot hide behind valid artifact refs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `pytest tests/smoke/test_tttrlib_live.py -m smoke_extended -q` completed with all scenarios skipped in this workspace due existing dataset/environment gating, so payload-level smoke assertions were updated and exercised only where the live harness can run.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 25 UAT gaps for CLSM settings payloads and Correlator getter runtime-shape handling are closed at the implementation and unit-verification layers.
- Planning metadata can now mark Phase 25 complete once roadmap/state updates are recorded.

## Self-Check: PASSED

- FOUND: `.planning/phases/25-add-missing-tttr-methods/25-05-SUMMARY.md`
- FOUND: `2915815`
- FOUND: `b2204e0`
- FOUND: `26027a8`
- FOUND: `1452181`
