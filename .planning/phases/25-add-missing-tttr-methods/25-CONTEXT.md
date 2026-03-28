# Phase 25: add-missing-tttr-methods - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose missing `tttrlib` callable coverage in MCP for the installed runtime while preserving existing bioimage-mcp contracts (artifact boundary, stable discovery/run behavior, and native dims metadata for image outputs). This phase clarifies how missing methods are added and surfaced; unrelated new capabilities stay out of scope.

</domain>

<decisions>
## Implementation Decisions

### Method coverage target
- Target near-full parity against the **installed `tttrlib` runtime** in this phase.
- Include both constructors and methods (instance/class/static) when MCP-safe.
- Prioritize `TTTR` + `CLSMImage` core workflows first, then include additional classes/method families discovered in the installed runtime.
- Keep strict upstream-style catalog IDs (for example `tttrlib.Class.method`) rather than aliases.
- Include missing write/export methods, but only with explicit path parameters and guardrails.
- Deprecated or experimental methods are skipped and documented.
- Completion criteria: discovered missing-method gap list is closed with each method either implemented or explicitly deferred with rationale.

### Output contract policy for new methods
- Non-image outputs use a hybrid contract: `TableRef` for tabular 2D-style results; `NativeOutputRef` JSON for irregular/nested data.
- New image-like outputs default to `BioImageRef` with `OME-Zarr` and native dims/axes metadata.
- Multi-value upstream returns should map to named MCP outputs (not opaque single bundles when names are meaningful).
- Heavy reusable runtime returns should use session-scoped `ObjectRef`.

### Unsupported and partial-support policy
- Methods that are not MCP-safe should be hidden from discovery and tracked in an explicit denylist.
- Calls that hit denied/unsupported behavior should return stable error codes with concise remediation guidance.
- Deny/defer documentation must be per-method with concrete rationale and revisit trigger.
- Partially mappable methods may be exposed as supported subsets with clear parameter/return limits and explicit fail-fast errors for unsupported parts.

### Validation and confidence bar
- Use contract-first validation for all additions (manifest/schema/handler alignment), plus selective live smoke coverage for representative or high-risk methods.
- Overloaded/ambiguous SWIG callables may use looser parameter surfaces where needed to preserve practical runtime parity.

### Claude's Discretion
- Exact ordering of non-core class/method additions after TTTR + CLSM core.
- Exact method-by-method mapping choice between `TableRef` and `NativeOutputRef` when both are reasonable.
- Exact wording of stable remediation messages, while preserving stable error codes and guidance.

</decisions>

<specifics>
## Specific Ideas

- Prefer practical parity for real runtime users over a narrow curated subset.
- Keep the public surface recognizable to `tttrlib` users by preserving strict upstream method naming.
- Treat unresolved edge methods as explicit, documented deferrals rather than silent omissions.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/tttrlib/manifest.yaml`: current curated callable registry and MCP I/O contracts to extend.
- `tools/tttrlib/schema/tttrlib_api.json`: parallel schema source (currently tagged `upstream_version: 0.25.0`) used for alignment checks.
- `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py`: explicit handler functions and `FUNCTION_HANDLERS` dispatch table for runtime execution.
- `tests/contract/test_tttrlib_manifest.py`: contract checks for expected surfaced callables and key params.
- `tests/contract/test_tttrlib_schema_alignment.py`: drift guard between manifest and schema JSON.
- `tests/smoke/test_tttrlib_live.py`: live end-to-end workflow coverage and cross-tool interoperability checks.

### Established Patterns
- `tttrlib` integration is manually curated (SWIG bindings) rather than introspected dynamically.
- New callable exposure requires synchronized updates across manifest, schema JSON, entrypoint handlers, and contract tests.
- Image outputs already follow OME-Zarr with metadata-rich refs; this is the expected continuation pattern.
- Existing workflows already use `ObjectRef` for CLSM objects and artifact refs for all protocol-visible data.

### Integration Points
- Tool discovery and MCP `list/describe` surface are driven by `tools/tttrlib/manifest.yaml` in the registry pipeline.
- Runtime execution maps `run(id=...)` to `entrypoint.py` handler functions through `FUNCTION_HANDLERS`.
- Contract and smoke suites in `tests/contract/` and `tests/smoke/` form the acceptance gate for new method additions.

</code_context>

<deferred>
## Deferred Ideas

- Methods identified during gap-closure as unstable, deprecated, or not MCP-safe are deferred to a future phase with per-method rationale.

</deferred>

---

*Phase: 25-add-missing-tttr-methods*
*Context gathered: 2026-03-05*
