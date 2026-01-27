# Phase 10: Verification & Smoke Testing - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver end-to-end verification and smoke testing for the Scipy integration. This phase covers smoke tests for the four major submodules, parity checks against native SciPy results, and using existing datasets to ensure reproducible test runs.

</domain>

<decisions>
## Implementation Decisions

### Smoke test matrix
- Cover all four major submodules: ndimage, stats, spatial, and signal.
- Broad coverage per submodule (6-10 representative functions each).
- Artifact I/O roundtrip requirements vary by submodule (mixed per submodule).

### Parity criteria
- Mixed approach: strict parity for deterministic operations, tolerances for the rest.
- Deterministic operations must be bit-for-bit matches.
- Tolerance-based checks use default absolute + relative tolerances.
- Any randomized operations should use fixed seeds.

### Datasets & fixtures
- Use standard datasets only.
- Reuse existing datasets in `datasets/` subfolders.
- Keep existing fixture sizes (no new caps).

### Execution & reporting
- Execute smoke tests via a live MCP server.
- Allow optional GPU usage when available (not required).
- Reporting is standard pytest output only.
- Run all tests and collect all failures before reporting.

### Claude's Discretion
- Choose the input size mix for smoke tests (tiny vs small vs mixed).

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-verification-smoke-testing*
*Context gathered: 2026-01-27*
