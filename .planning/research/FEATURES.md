# Feature Research

**Domain:** MCP tool registry & introspection
**Researched:** 2026-01-27
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Automatic schema derivation | LLMs require valid JSON Schema to call tools accurately. | MEDIUM | Use Pydantic v2 with docstring parsing. |
| AST-first discovery | Avoid importing heavy deps in core server. | MEDIUM | Use Griffe for static parsing. |
| Environment readiness diagnostics | Operators need to know if a tool can run. | MEDIUM | Check conda env existence and package presence. |
| Consolidated list/describe | MCP tools/list and meta.describe must match. | MEDIUM | Single engine feeds both endpoints. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Two-stage pipeline | Handles pure Python and dynamic factories safely. | HIGH | AST-first + runtime fallback. |
| Persistent schema cache | Eliminates re-introspection after restart. | LOW | DiskCache-backed store. |
| Strong cache invalidation | Zero stale schema issues. | MEDIUM | Use xxHash + env lock hash. |
| Metadata overlays | Manual fixes without code changes. | MEDIUM | function_overlays precedence rules. |
| Actionable diagnostics | Faster remediation for tool authors. | LOW | Emit hints for missing docs/fallback. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Runtime data introspection | Seeks higher fidelity schemas. | Slow and unsafe during discovery. | Use static signatures + docstrings. |
| Direct binary introspection | Desire to auto-cover compiled libs. | Fragile, opaque, error-prone. | Use manifest overlays/wrappers. |
| Implicit type guessing | Convenience when hints are missing. | Leads to incorrect schemas. | Require explicit hints + overlays. |

## Feature Dependencies

```
[Automatic schema derivation]
    └──requires──> [AST-first discovery]

[Two-stage pipeline] ──enhances──> [AST-first discovery]
[Persistent schema cache] ──enhances──> [Consolidated list/describe]
[Strong cache invalidation] ──enhances──> [Persistent schema cache]
[Metadata overlays] ──enhances──> [Schema emission]
[Runtime data introspection] ──conflicts──> [AST-first discovery]
```

### Dependency Notes

- **Automatic schema derivation requires AST-first discovery:** without safe parsing, schema derivation imports heavy deps.
- **Two-stage pipeline enhances AST-first discovery:** handles factories/dynamic tools safely.
- **Persistent cache enhances consolidated list/describe:** ensures consistent output across restarts.
- **Strong invalidation enhances cache:** prevents stale schemas.
- **Metadata overlays enhance schema emission:** manual overrides fill gaps.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] AST-first discovery (Griffe)
- [ ] Automatic schema derivation with docstring support
- [ ] Two-stage runtime fallback for dynamic tools
- [ ] Consolidated list/describe output
- [ ] Persistent cache + strong invalidation
- [ ] Metadata overlay pipeline
- [ ] Actionable diagnostics for missing docs/fallbacks

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Configurable cache policies (TTL/size limits)
- [ ] Diagnostics formatting polish (structured reports)

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Semantic array typing (dims/axes/units)
- [ ] Full runtime-generated signature support without imports
- [ ] Backward compatibility for legacy fn_id/cache shapes

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| AST-first discovery | HIGH | MEDIUM | P1 |
| Automatic schema derivation | HIGH | MEDIUM | P1 |
| Two-stage pipeline | HIGH | HIGH | P1 |
| Persistent cache | MEDIUM | LOW | P1 |
| Strong cache invalidation | HIGH | MEDIUM | P1 |
| Metadata overlays | MEDIUM | MEDIUM | P1 |
| Actionable diagnostics | MEDIUM | LOW | P2 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Competitor A | Competitor B | Our Approach |
|---------|--------------|--------------|--------------|
| Schema inference | LangChain StructuredTool | LlamaIndex FunctionTool | MCP-specific schema emission with artifact separation. |
| Docstring parsing | Partial | Partial | Docstring-parser + Griffe AST for higher fidelity. |

## Sources

- https://mkdocstrings.github.io/griffe/
- https://docs.pydantic.dev/latest/concepts/json_schema/
- https://modelcontextprotocol.io/specification/

---
*Feature research for: MCP tool registry & introspection*
*Researched: 2026-01-27*
