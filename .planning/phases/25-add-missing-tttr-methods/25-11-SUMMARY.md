---
phase: 25-add-missing-tttr-methods
plan: 11
subsystem: api
tags: [tttrlib, clsmimage, metadata, swig, smoke-tests]
requires:
  - phase: 25-08
    provides: Prior CLSM settings transport-field cleanup contract and regression pattern
provides:
  - CLSM settings JSON artifacts with recursive SWIG transport-field filtering restored
  - Unit coverage proving only this and thisown are removed while nested metadata stays JSON-safe
  - Live smoke assertions that fail loudly if get_settings leaks SWIG transport keys
affects: [phase-25-closeout, tttrlib-runtime-parity, clsm-metadata-cleanliness]
tech-stack:
  added: []
  patterns:
    - Recursive CLSM settings normalization skips only SWIG transport attrs while preserving nested domain metadata.
    - CLSM smoke checks pair negative transport-key assertions with positive domain-field checks.
key-files:
  created:
    - .planning/phases/25-add-missing-tttr-methods/25-11-SUMMARY.md
  modified:
    - tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py
    - tests/unit/test_tttrlib_entrypoint_clsm_methods.py
    - tests/smoke/test_tttrlib_live.py
key-decisions:
  - "Restore a narrow SWIG transport-attribute blocklist in recursive CLSM settings normalization instead of replacing the rich metadata serializer."
  - "Name the live smoke around the user-observed get_settings leak so CI clearly reports transport-field regressions."
patterns-established:
  - "Transport-attr filter pattern: skip only this and thisown during recursive SWIG proxy traversal."
  - "Payload-cleanliness regression pattern: prove cleaned CLSM settings still include at least one useful domain field."
requirements-completed: [TTTR-03, TTTR-05]
duration: 4 min
completed: 2026-03-07
---

# Phase 25 Plan 11: CLSM settings payload-cleanliness regression Summary

**Restored recursive CLSM settings JSON serialization that strips only SWIG transport fields while preserving nested domain metadata and explicit live regression checks.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-07T08:15:31Z
- **Completed:** 2026-03-07T08:20:23Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Reintroduced failing regression coverage for CLSM settings objects carrying `this` and `thisown` at multiple nesting levels.
- Restored serializer filtering so `tttrlib.CLSMImage.get_settings` drops only SWIG transport attrs and keeps JSON-safe domain metadata.
- Strengthened live smoke coverage to reject the exact user-reported leak while still requiring useful CLSM settings fields.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Restore transport-field filtering in CLSM settings serialization** - `1364c47` (test)
2. **Task 1 (GREEN): Restore transport-field filtering in CLSM settings serialization** - `922dd1e` (fix)
3. **Task 2: Reinstate live smoke checks for CLSM payload cleanliness** - `811de5f` (test)

**Plan metadata:** pending

_Note: Task 1 followed TDD and produced separate RED and GREEN commits._

## Files Created/Modified
- `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` - Reintroduces the SWIG transport-attribute blocklist used during recursive CLSM settings normalization.
- `tests/unit/test_tttrlib_entrypoint_clsm_methods.py` - Models fake nested CLSM settings objects with `this`/`thisown` and verifies they are removed while domain values stay intact.
- `tests/smoke/test_tttrlib_live.py` - Fails explicitly when live `get_settings` payloads leak SWIG transport keys and still checks for preserved domain metadata.

## Decisions Made
- Restored the earlier narrow blocklist approach because the regression was wrapper transport leakage, not a problem with the broader recursive serializer.
- Kept the smoke assertions focused on top-level leaked keys plus domain-field presence, matching the actual UAT report without weakening usefulness guarantees.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `pytest tests/smoke/test_tttrlib_live.py -m smoke_extended -q -k "clsm_metadata_methods"` and the full smoke command remained skipped in this workspace by dataset/environment gating, so the regression assertions were verified structurally while the live harness reported skips.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The final Phase 25 CLSM metadata cleanliness regression is re-guarded by both unit and smoke assertions.
- Phase 25 is ready for closeout metadata updates and transition handling.

## Self-Check: PASSED

- FOUND: `.planning/phases/25-add-missing-tttr-methods/25-11-SUMMARY.md`
- FOUND: `1364c47`
- FOUND: `922dd1e`
- FOUND: `811de5f`
