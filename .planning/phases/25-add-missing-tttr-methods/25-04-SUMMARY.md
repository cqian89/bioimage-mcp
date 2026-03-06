---
phase: 25-add-missing-tttr-methods
plan: 04
subsystem: api
tags: [tttrlib, live-signatures, export-guardrails, smoke-tests]
requires:
  - phase: 25-02
    provides: TTTR method expansion baseline and export guardrails
provides:
  - Live-signature-aligned TTTR getter and selection contracts
  - File-backed TTTR subset artifacts that survive MCP execution registration
  - Positive specialized SPC export coverage across unit and live smoke paths
affects: [25-05, tttrlib-runtime-parity, tttrlib-uat-gap-closure]
tech-stack:
  added: []
  patterns:
    - Live tttrlib wrapper params stay synchronized across manifest, schema, and handlers.
    - TTTR subset outputs are materialized as sandboxed files when core execution only ingests path-backed TTTR artifacts.
    - Specialized tttrlib export writers receive the explicit upstream tttr argument and keep extension/path guardrails unchanged.
key-files:
  created: []
  modified:
    - tools/tttrlib/manifest.yaml
    - tools/tttrlib/schema/tttrlib_api.json
    - tools/tttrlib/schema/tttrlib_coverage.json
    - tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py
    - tests/unit/test_tttrlib_entrypoint_tttr_methods.py
    - tests/contract/test_tttrlib_manifest.py
    - tests/contract/test_tttrlib_schema_alignment.py
    - tests/smoke/test_tttrlib_live.py
key-decisions:
  - "Expose TTTR selection wrappers with the live tttrlib input/time_window/n_ph_max signatures and keep unsupported branches rejected instead of silently broadening support."
  - "Persist get_tttr_by_selection outputs as file-backed TTTRRef artifacts under work_dir because core execution currently only registers TTTR outputs that include a path."
  - "Call specialized write_spc132_events/write_hht3v2_events with the explicit tttr object and keep positive SPC export coverage in smoke to guard the SWIG-specific signature."
patterns-established:
  - "Contract triad pattern: manifest, schema JSON, and handler params change together from live runtime evidence."
  - "TTTR subset persistence pattern: normalize selection results to indices, then write subset TTTR files before returning TTTRRef."
requirements-completed: [TTTR-02, TTTR-03, TTTR-05]
duration: 17 min
completed: 2026-03-06
---

# Phase 25 Plan 04: TTTR gap-closure Summary

**TTTR getter/selection parity now matches live tttrlib signatures, subset outputs survive as file-backed artifacts, and specialized SPC export coverage closes the UAT blocker.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-03-06T09:07:34Z
- **Completed:** 2026-03-06T09:24:41Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Realigned TTTR getter and selection metadata plus handler calls to the live `tttrlib` signatures for intensity traces, channel selection, and count-rate selection.
- Changed `get_tttr_by_selection` to write sandboxed subset files and return usable file-backed `TTTRRef` outputs instead of non-registered memory artifacts.
- Preserved export guardrails while fixing specialized SPC/HHT3 writer calls to pass the explicit TTTR object and added positive SPC smoke coverage.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests for TTTR live signatures** - `a453528` (test)
2. **Task 1 (GREEN): Align TTTR contracts and subset materialization** - `62aec29` (feat)
3. **Task 2: Cover specialized TTTR exports end to end** - `db316b9` (feat)

**Plan metadata:** pending

## Files Created/Modified
- `tools/tttrlib/manifest.yaml` - Publishes live-signature TTTR params and corrected selection/subset contracts.
- `tools/tttrlib/schema/tttrlib_api.json` - Mirrors corrected live TTTR parameter names and table/output definitions.
- `tools/tttrlib/schema/tttrlib_coverage.json` - Documents the supported-subset rationale for the repaired TTTR methods.
- `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` - Executes live tttrlib call shapes, writes TTTR subsets to disk, and passes explicit TTTR objects to specialized writers.
- `tests/unit/test_tttrlib_entrypoint_tttr_methods.py` - TDD coverage for corrected params, subset file outputs, and explicit specialized-writer signatures.
- `tests/contract/test_tttrlib_manifest.py` - Guards live-signature parameter naming in the manifest.
- `tests/contract/test_tttrlib_schema_alignment.py` - Guards manifest/schema parity for the repaired TTTR params.
- `tests/smoke/test_tttrlib_live.py` - Adds successful sandboxed SPC export coverage.

## Decisions Made
- Kept the supported-subset policy strict: only the live-safe `input`, `time_window`, `n_ph_max`, and `invert` shapes are surfaced, while unsupported branches still fail with `TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN`.
- Used file materialization for `get_tttr_by_selection` because the existing core execution path only imports TTTR outputs that provide `path` metadata.
- Treated specialized export success as a regression-sensitive path and added explicit positive SPC smoke coverage rather than relying on negative guardrail tests alone.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Final live verification command `pytest tests/smoke/test_tttrlib_live.py -m smoke_extended -q` is currently blocked by a pre-existing MCP server startup timeout in the smoke harness. Evidence: a direct smoke-client startup reproduction times out during MCP initialization with empty stderr, while `python -m bioimage_mcp list --json` and `python -m bioimage_mcp doctor --json` both succeed in the same workspace.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- TTTR UAT gaps for live getter signatures, selection handling, subset artifact persistence, and specialized SPC export are closed at the unit/contract layer and covered by a dedicated SPC smoke scenario.
- Follow-up plan 25-05 can focus on the remaining CLSM/correlator UAT gaps plus the unrelated smoke-server startup timeout if it remains present.

## Self-Check: PASSED
