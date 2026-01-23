# Phase 5: Trackpy Integration - Context

**Gathered:** 2026-01-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate the `trackpy` particle tracking library as a Bioimage-MCP tool pack so agents can discover and run trackpy functions via the MCP API, with dynamic signature introspection, broad API coverage, and a live smoke test that validates core tracking behavior. Anything beyond exposing trackpy itself (e.g., new analysis features outside trackpy) is out of scope.

</domain>

<decisions>
## Implementation Decisions

### API coverage scope
- Expose the full trackpy API (all major categories).
- Exclude underscore-prefixed/internal functions.
- Include diagnostic/visualization functions.
- If anything is excluded beyond underscore-prefixed, document exclusions explicitly (with justification).

### Introspection approach
- Signature/schema generation is auto-generated with a manual override mechanism available for fixes/tuning.
- Introspection happens at runtime (dynamic discovery).
- If introspection fails, degrade gracefully (expose partial API + warnings rather than hard-failing the whole tool pack).
- Pin trackpy compatibility to 0.7.x.
- Function/tool IDs follow the trackpy API path (e.g., `trackpy.link`, `trackpy.locate`).
- Schemas are permissive when docs are ambiguous.
- `describe` should include the full trackpy docstring.
- If optional dependency features are not available, hide those functions unless imports succeed.
- Include default values from Python signatures in schemas.
- Attach full per-parameter descriptions (docstring-derived) to schema fields.
- When inputs accept multiple types, allow multiple types in schema (union-like behavior).

### Test data strategy
- Base fixtures on upstream trackpy examples.
- Support both 2D and 3D time series fixtures.
- Avoid committed golden-output files; compute expectations in tests.
- Test assets can be large (up to ~100MB).
- Store vendored datasets under `datasets/*` tracked via Git LFS; keep original file types as downloaded.
- Include a short LICENSE/NOTICE note for any vendored upstream data/scripts.

### Validation criteria
- Smoke test validates via numeric checks (not strict output text matching).
- Comparisons are tolerance-based (not byte-for-byte exact).
- Deep tests focus on core functions; the rest get lighter smoke coverage.
- Smoke test is gated behind a marker (not run in default fast CI suite).

### OpenCode's Discretion
- Whether trackpy lives in the base env or a dedicated `bioimage-mcp-trackpy` env (decide after research).
- Whether to vendor upstream example scripts verbatim or re-implement them as local reference scripts.
- Exact marker choice/placement for smoke tests (e.g., `integration` vs `smoke_full`) based on runtime.

</decisions>

<specifics>
## Specific Ideas

- Keep the agent-facing function names aligned with trackpy docs (module path style).
- Prefer robustness for agents: permissive schemas, docstrings surfaced, partial availability rather than all-or-nothing failures.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-trackpy-integration*
*Context gathered: 2026-01-23*
