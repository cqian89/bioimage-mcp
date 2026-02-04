# Phase 20: Strategize and execute test consolidation - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Consolidate how tests are organized and executed (unit/contract/integration/smoke + env-gated tool-pack tests) so the suite is coherent and predictable in both local runs and CI.

In-scope: reorganizing/renaming tiers, standardizing markers, tightening or relaxing assertions to match contract policy, and selecting a small PR-gating smoke set vs fuller/nightly coverage.

Out-of-scope: adding new product capabilities.

</domain>

<decisions>
## Implementation Decisions

### Test tiers + naming
- Keep top-level test directories as the primary structure: `tests/unit/`, `tests/contract/`, `tests/integration/`, `tests/smoke/`.
- Keep `tests/contract/` as its own tier (revises earlier “3 dirs” preference).
- Enforce strict alignment between directory and marker intent (so selection by directory and by marker are consistent).
- Keep tool-pack specific tests centralized under `tests/` (not co-located under `tools/<pack>/...`).
- Keep smoke split into two modes (minimal vs fuller), but adjust naming/tiers so PR gating vs “everything” are clearly separated.

### Env-gated test policy
- CI should include optional tool environment smoke coverage (not base-only).
- If a required conda env is missing/unavailable, tests should SKIP with a clear, actionable message (not hard-fail).
- Standardize env requirements on `@pytest.mark.requires_env("bioimage-mcp-...")` (keep any convenience markers only as aliases, or remove them during consolidation).
- LFS datasets are acceptable for the heavier smoke tier (not necessarily for minimal smoke).

### Baseline/contract expectations
- Contract strictness depends on the surface:
  - Strict: worker IPC protocol/schema (no silent drift).
  - Additive-compatible: user-facing discovery surfaces (e.g., list/describe) may add fields without breaking tests.
- Smoke equivalence comparisons: exact where outputs are discrete/deterministic; use tolerances for float/numeric comparisons.
- Previews (e.g., base64 PNG from `artifact_info`) are NOT a byte-stable contract: test presence/shape/metadata, not exact bytes/hashes.
- Relax overly strict contract assertions that block additive evolution or tool-pack realities:
  - Allow extra keys in user-facing describe/list instead of allowlisting exact key sets.
  - Treat params_schema property descriptions as best-effort (not required for every property).

### CI/local run experience
- PR-required gate includes: unit + contract + smoke_minimal + the PR-gating smoke tier (currently called smoke_full, but see “rename tiers” decision).
- In CI, only 1-2 representative optional tool env equivalence checks should be required on PRs (full matrix can run nightly/extended).
- Golden-path local execution should be documented for both styles:
  - Directory-driven (e.g., `pytest tests/unit`, `pytest tests/contract`)
  - Marker-driven (e.g., `pytest -m smoke_minimal`, `pytest -m integration`)
- When optional envs aren’t installed locally: default `pytest` should still pass, but it should WARN loudly that coverage is incomplete (not silently skip).

### Redundancy/over-restrictiveness evaluation outcomes
- Rename/split smoke tiers so the PR-gating “full” suite is clearly distinct from “everything” (current `smoke_full` includes too much to be a practical PR gate).
- PR-gating base equivalence should focus on ONE representative image filter equivalence theme; other base equivalence tests move to extended/nightly.
- PR-gating optional env representatives: Cellpose + Trackpy.

### Claude's Discretion
- Exact marker/tier naming for the renamed smoke tiers (must clearly separate PR-gating vs extended/nightly and keep minimal vs fuller semantics).
- Which specific image-filter equivalence test(s) represent the base env (e.g., scipy.ndimage vs skimage), as long as it matches the “image filter equivalence” theme.
- Which existing base equivalence tests get moved to extended/nightly vs removed (as long as PR gate stays small and confidence remains reasonable).

</decisions>

<specifics>
## Specific Ideas

- Fix/relax known overly strict tests during consolidation:
  - Discovery contract tests that forbid extra keys in describe/list responses (should allow additive fields).
  - Meta-describe contract tests that require every params_schema property to have a description (breaks for trackpy).
  - Equivalence tests doing bit-for-bit equality on float outputs should use tolerances.
- Align equivalence test markers to the standardized `requires_env(...)` policy and dataset marker conventions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 20-strategize-and-execute-test-consolidation*
*Context gathered: 2026-02-04*
