# Requirements: Bioimage-MCP Unified Introspection Engine

**Defined:** 2026-01-27
**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Introspection Pipeline

- [ ] **INT-01**: Agent can discover tools with params_schema derived from AST without importing tool code.
- [ ] **INT-02**: Engine falls back to isolated runtime introspection when AST signatures are missing or dynamic.
- [ ] **INT-03**: MCP tools/list and meta.describe share a single introspection source so metadata is consistent.

### Schema Emission

- [ ] **SCHEMA-01**: Agent receives params_schema derived from type hints and docstrings with required fields populated.
- [ ] **SCHEMA-02**: params_schema excludes artifact ports; artifact I/O remains separate from parameters.
- [ ] **SCHEMA-03**: meta.describe includes tool_version and introspection_source for each function.

### Environment Readiness

- [ ] **ENV-01**: Operator can see readiness diagnostics for missing tool environments or packages with remediation.

### Caching

- [ ] **CACHE-01**: Schema cache persists across server restarts.
- [ ] **CACHE-02**: Cache invalidates on tool_version, env lock hash, or source hash changes.

### Overlays and Patches

- [ ] **OVERLAY-01**: Tool authors can apply overlays to rename/drop/annotate parameters without code changes.
- [ ] **OVERLAY-02**: Overlay precedence is deterministic across built-in, manifest, and user overrides.

### Metadata and Diagnostics

- [ ] **META-01**: Functions report full module paths with stable fn_id metadata.
- [ ] **META-02**: callable_fingerprint is recorded and exposed for cache/diagnostic use.
- [ ] **DIAG-01**: Diagnostics report missing docs, runtime fallback usage, and patch application.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Types and Compatibility

- **TYPE-01**: Semantic array typing (dims/axes/units) beyond FunctionHints.
- **RUNTIME-01**: Full support for runtime-generated signatures without imports.
- **COMPAT-01**: Backward compatibility for legacy fn_id or cache shapes.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Runtime data introspection | Too slow and unsafe during discovery; use static signatures instead. |
| Direct binary introspection | Compiled bindings require manual manifests or wrappers. |
| Implicit type guessing | Leads to incorrect schemas; require explicit type hints. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 0
- Unmapped: 14 ⚠️

---
*Requirements defined: 2026-01-27*
*Last updated: 2026-01-27 after initial definition*
