---
phase: 12-core-engine-ast-first
plan: 06
subsystem: testing
tags: [diagnostics, doctor, readiness, introspection]

# Dependency graph
requires:
  - phase: 12-core-engine-ast-first
    provides: [Unified discovery engine with AST-first introspection]
provides:
  - Engine diagnostics events (fallback, overlays, missing docs)
  - Doctor output with tool environment readiness diagnostics and remediation
affects: [v0.4.0 release readiness]

# Tech tracking
tech-stack:
  added: []
  patterns: [Diagnostic event emission during discovery]

key-files:
  created: 
    - tests/integration/test_doctor.py
  modified:
    - src/bioimage_mcp/registry/diagnostics.py
    - src/bioimage_mcp/registry/engine.py
    - src/bioimage_mcp/registry/loader.py
    - src/bioimage_mcp/bootstrap/checks.py
    - src/bioimage_mcp/bootstrap/doctor.py
    - src/bioimage_mcp/config/schema.py

key-decisions:
  - "Extended ManifestDiagnostic to include engine_events for unified reporting."
  - "Added diagnostic_level to Config to allow filtering of discovery events (minimal/standard/full)."
  - "Implemented tool_environments check in doctor to detect missing conda environments referenced by manifests."

patterns-established:
  - "Deterministic ordering of diagnostics in doctor output (by fn_id, then event type)."

# Metrics
duration: 35 min
completed: 2026-01-27
---

# Phase 12 Plan 06: Diagnostics and Readiness Summary

**Enhanced registry diagnostics with engine events and added doctor readiness checks for tool environments.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-01-27T14:17:17Z
- **Completed:** 2026-01-27T14:52:00Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Extended `ManifestDiagnostic` to support `EngineEvent` recording (fallback, overlays, docs, skipped callables).
- Integrated diagnostic emission into `DiscoveryEngine` and `load_manifests`.
- Added `check_tool_environments` to `bioimage-mcp doctor` to provide actionable remediation for missing conda envs.
- Added `diagnostic_level` configuration to control the verbosity of engine diagnostics.
- Added integration test coverage for `bioimage-mcp doctor --json` output stability.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend registry diagnostics to cover engine events** - `7768454` (feat)
2. **Task 2: Add doctor readiness checks for tool env availability** - `657a0a7` (feat)
3. **Task 3: Add integration coverage for doctor output stability** - `80ab10b` (test)

**Plan metadata:** `docs(12-06): complete diagnostics and readiness plan`

## Files Created/Modified
- `src/bioimage_mcp/registry/diagnostics.py` - Extended models for engine events.
- `src/bioimage_mcp/registry/engine.py` - Emits engine events during discovery.
- `src/bioimage_mcp/registry/loader.py` - Collects diagnostics for all manifests.
- `src/bioimage_mcp/bootstrap/checks.py` - New tool environment check.
- `src/bioimage_mcp/bootstrap/doctor.py` - Enhanced summary with engine events.
- `src/bioimage_mcp/config/schema.py` - Added diagnostic_level config.
- `tests/integration/test_doctor.py` - Integration tests for doctor output.
- `tests/unit/bootstrap/test_checks.py` - Updated check count expectation.

## Decisions Made
- Used an internal `_events` list in `DiscoveryEngine` to accumulate events during a `discover()` call.
- Registry summary in `doctor` now includes `engine_events` filtered by `diagnostic_level`.
- `load_manifests` now returns diagnostics even for valid manifests if they produced discovery events.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Whitespace issue in `test_introspect_numpy_style_docstring` was noted but determined to be pre-existing and unrelated to the introspection engine consolidation.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Introspection engine is now robust, observable, and validated.
- Diagnostics are actionable for operators.
- Ready for v0.4.0 release.

---
*Phase: 12-core-engine-ast-first*
*Completed: 2026-01-27*
