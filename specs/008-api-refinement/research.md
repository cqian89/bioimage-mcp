# Research & Design Decisions: API Refinement & Permission System

**Date**: 2025-12-28  
**Spec**: [spec.md](./spec.md)

## Research Questions & Findings

### 1. Hierarchical Discovery Semantics

**Question**: How to implement navigable discovery without bloating the MCP surface or breaking existing agents?

**Decision**: Introduce an optional `path` parameter to `list_tools` that filters children by dot-notated prefix.

**Rationale**:
- Mimics filesystem and Python package navigation, which is intuitive.
- Single-level retrieval (the default for a given path) keeps context window usage low.
- Batch support via `paths: list[str]` allows agents to "peek" into multiple sub-trees (e.g., `skimage.filters` and `skimage.morphology`) in one round-trip.

**Implementation Pattern**:
```python
# list_tools(path="") -> Root (Environments)
# [ {name: "base", type: "env", has_children: true}, ... ]

# list_tools(path="base") -> Base environment packages
# [ {name: "skimage", type: "package", has_children: true}, ... ]

# list_tools(path="base.skimage.filters") -> Filter functions
# [ {name: "gaussian", type: "function", fn_id: "base.skimage.filters.gaussian"}, ... ]
```

**Alternatives Considered**:
- Separate `list_environments`, `list_packages` tools: Rejected as it bloats the tool catalog.
- Flat listing with client-side filtering: Rejected for >100 functions (context bloat).

---

### 2. Multi-Keyword Search Ranking

**Question**: How to rank search results when multiple keywords are provided?

**Decision**: Two-stage ranking: (1) Primary sort by number of keywords matched, (2) Secondary sort by weighted score.

**Rationale**:
- Matches for "gaussian blur" should prioritize functions containing *both* words.
- Weighting fields ensures that name matches (intentionality) outrank tag matches (contextual).

**Weights**:
- `Name`: 3.0
- `Description`: 2.0
- `Tags`: 1.0

**Implementation Pattern**:
```python
def rank_functions(functions, keywords):
    scored = []
    for fn in functions:
        match_count = sum(1 for k in keywords if k in fn.full_text)
        weight_score = sum(field_weight * (1 if k in fn.field else 0))
        scored.append((fn, match_count, weight_score))
    
    return sorted(scored, key=lambda x: (-x[1], -x[2]))
```

---

### 3. Canonical Naming & Alias Migration

**Question**: How to transition from flat names to hierarchical names without breaking legacy scripts?

**Decision**: Implement a `FunctionAlias` system in the registry.

**Rationale**:
- Standardizing on `env.package.module.function` provides long-term scalability.
- `builtin` functions are moved to `base` (e.g., `builtin.gaussian` -> `base.skimage.filters.gaussian`).
- Aliases (e.g., `base.gaussian`) are preserved for backward compatibility but marked as `deprecated` in `describe_function`.
- Legacy unprefixed dynamic IDs like `skimage.filters.gaussian` (from v0.5 registry) are supported as deprecated aliases to the canonical `base.skimage.filters.gaussian`.
- Calls to `call_tool` (deprecated) or aliases log warnings to the server log, but do not return them in the response payload.

**Migration Path for Builtins**:
| Old Function | New Canonical ID |
|--------------|------------------|
| `builtin.gaussian_blur` | `base.skimage.filters.gaussian` |
| `builtin.convert_to_ome_zarr` | `base.convert_to_ome_zarr` |
| `builtin.threshold_otsu` | `base.skimage.filters.threshold_otsu` |

---

### 4. Permission Inheritance via MCP Roots

**Question**: How to implement `inherit` mode safely and transparently?

**Decision**: Call `list_roots()` at session start and whenever a path check is needed (with short-term caching).

**Rationale**:
- Provides a "zero-config" experience for users working in standard IDEs (VS Code, Cursor).
- `hybrid` mode allows adding network drives or data lakes that might not be in the IDE workspace.
- Logging inherited roots at session start ensures auditability.

**Safety Fallbacks**:
- If client lacks `Roots` capability: Fall back to `explicit` mode (only use config allowlist).
- If client returns empty roots: Deny all operations unless in `hybrid` mode.

---

### 5. Overwrite Protection via MCP Elicitation

**Question**: How to handle "ask on overwrite" without custom UI?

**Decision**: Use `ServerSession.elicit_form` (or `elicit` for simple strings) to prompt the user.

**Rationale**:
- Standard MCP mechanism for gathering user input.
- `ServerSession.elicit*` returns an `ElicitResult` containing `action` (`accept`, `decline`, or `cancel`) and optional `content`.
- Decouples server logic from specific client UI implementations.
- If client lacks `Elicitation` capability, fall back to `permissions.on_overwrite` default (`deny`).

---

### 6. Summary of Decisions

| Feature | Decision | Implementation |
|---------|----------|----------------|
| Hierarchy | Dot-prefix navigation | `list_tools(path="base.skimage")` |
| Search | Multi-keyword weighted | Count matches, then sum weights |
| Naming | 4-part canonical | `base.skimage.filters.gaussian` |
| Aliases | Registry-level mapping | `base.gaussian` -> `base.skimage...` |
| Permissions | Root inheritance | `inherit` mode via `list_roots()` |
| Overwrites | MCP Elicitation | `elicit_form` returns `ElicitResult` |

All research items are resolved. No open blockers for implementation.
