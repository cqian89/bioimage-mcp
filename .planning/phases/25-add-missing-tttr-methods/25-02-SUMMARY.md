---
phase: 25-add-missing-tttr-methods
plan: 02
subsystem: api
tags: [tttrlib, method-parity, export-guardrails, contract-tests]
requires:
  - phase: 25-01
    provides: runtime parity inventory and unsupported routing baseline
provides:
  - Expanded TTTR getter, selection, and subset mappings with strict upstream IDs
  - Guarded TTTR export variants with work_dir path checks and stable error codes
  - Contract and unit coverage for schema/manifest parity and export guardrails
affects: [25-03, tttrlib-runtime-parity]
tech-stack:
  added: []
  patterns:
    - Supported-subset TTTR handlers return deterministic TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN errors
    - TTTR write-family handlers enforce work_dir-bounded output paths before export
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
key-decisions:
  - "Map scalar TTTR statistics to NativeOutputRef and tabular traces/selections to TableRef outputs."
  - "Treat channel and count-rate selection APIs as supported_subset with explicit argument allowlists and stable rejection errors."
  - "Constrain write_hht3v2_events to .ht3 and write_spc132_events to .spc while enforcing work_dir path boundaries for all exports."
patterns-established:
  - "Subset contract pattern: reject unsupported params with TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN before invoking tttrlib."
  - "Export safety pattern: resolve outputs under work_dir and fail traversal attempts with TTTRLIB_UNSAFE_OUTPUT_PATH."
requirements-completed: [TTTR-02, TTTR-03, TTTR-04]
duration: 15 min
completed: 2026-03-05
---

# Phase 25 Plan 02: TTTR Method Expansion Summary

**TTTR getter/selection/statistics and write-family parity now expose strict upstream IDs with artifact-safe outputs and deterministic export guardrails.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-05T14:20:18Z
- **Completed:** 2026-03-05T14:36:09Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added new TTTR method mappings (`get_count_rate`, `get_intensity_trace`, selection methods, and `get_tttr_by_selection`) with explicit MCP output contracts.
- Expanded manifest/schema/coverage metadata in lockstep for strict schema parity and runtime handler registration.
- Added write-family variants (`write_header`, `write_hht3v2_events`, `write_spc132_events`) and enforced path/format guardrails with stable remediation errors.
- Added/extended unit and contract tests to cover new IDs, subset argument rejection, and safe export behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests for TTTR method family expansion** - `b68b294` (test)
2. **Task 1 (GREEN): Implement getter/selection/statistics mappings** - `20d72f4` (feat)
3. **Task 2 (RED): Add failing tests for export guardrails** - `24acc44` (test)
4. **Task 2 (GREEN): Implement guarded write/export variants** - `22e5f4b` (feat)

**Plan metadata:** pending

## Files Created/Modified
- `tools/tttrlib/manifest.yaml` - Adds strict upstream TTTR methods and write variants with subset semantics.
- `tools/tttrlib/schema/tttrlib_api.json` - Mirrors new method contracts and export constraints.
- `tools/tttrlib/schema/tttrlib_coverage.json` - Promotes methods to supported/supported_subset and documents guardrail rationale.
- `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` - Implements handlers, subset validation, and export safety checks.
- `tests/unit/test_tttrlib_entrypoint_tttr_methods.py` - TDD coverage for artifact outputs and write guardrails.
- `tests/contract/test_tttrlib_manifest.py` - Contract assertions for expanded method surface.
- `tests/contract/test_tttrlib_schema_alignment.py` - Ensures new methods are present in both manifest and schema.

## Decisions Made
- Used `NativeOutputRef` for scalar count-rate output and `TableRef` for trace/selection outputs to keep payloads artifact-based.
- Classified selection/write variants as `supported_subset` and made unsupported combinations fail fast with stable error codes.
- Enforced write path containment under `work_dir` to keep exports sandboxed and deterministic.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 25 plan 03 can build on expanded TTTR method contracts and write guardrails for remaining parity slices.
- Contract drift checks now cover new strict IDs, reducing risk of manifest/schema mismatch in follow-up tasks.

## Self-Check: PASSED
