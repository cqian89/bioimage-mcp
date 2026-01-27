# Phase 12: Core Engine + AST-First - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a unified discovery/introspection engine that is AST-first with runtime fallback, align meta.describe params_schema emission, consolidate overlays/patches and diagnostics, and clean up fn_id/module metadata. No new capabilities outside the introspection pipeline are added in this phase.

</domain>

<decisions>
## Implementation Decisions

### Fallback rules for AST-first discovery
- Runtime overrides AST on conflicts; full override allowed (names/types can change).
- Fallback triggers on any mismatch between AST and runtime.
- Record introspection source per function.
- If runtime fallback fails, skip the callable and record the error.
- Skipped callables do not appear in list/describe.
- No tool-pack summary; rely on per-function source tags.

### params_schema + metadata contract
- tool_version and introspection_source live in an adjacent metadata block in meta.describe.
- params_schema output is deterministic in ordering and stable in content.
- Artifact separation is explicit via artifact refs in the schema.
- Schema changes are signaled by tool_version only (no separate schema_version).

### Overlay/patch precedence & diagnostics
- Overlays are authoritative when they conflict with introspected schema.
- Conflicting overlays resolve as last-applied wins, with a warning.
- Diagnostics are log-only (server logs), not client-visible.
- Diagnostic detail is configurable (default minimal with opt-in detail).

### fn_id + module naming conventions
- fn_id uses fully qualified module path + callable name.
- callable_fingerprint is exposed in meta.describe for each function.
- Renamed/moved callables only expose the new fn_id (no aliasing).
- Always include full module path in module metadata.

### Claude's Discretion
- Whether to retain AST output alongside runtime output for diagnostics.

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

*Phase: 12-core-engine-ast-first*
*Context gathered: 2026-01-27*
