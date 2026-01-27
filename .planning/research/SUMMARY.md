# Project Research Summary

**Project:** Bioimage-MCP
**Domain:** MCP tool registry & introspection
**Researched:** 2026-01-27
**Confidence:** HIGH

## Executive Summary

Bioimage-MCP needs a unified introspection engine to prevent schema drift and to keep MCP list/describe endpoints consistent. Research supports a static-first discovery model using Griffe to parse signatures and docstrings without importing heavy dependencies, with runtime fallback reserved for dynamic or factory-generated tools in isolated tool-pack environments.

The main risks are environment-blind imports (crashing the server), stale schema caches, and signature loss from decorators. These are mitigated by an AST-first pipeline, content-hash invalidation, and a deterministic overlay/patch pipeline that logs applied changes.

## Key Findings

### Recommended Stack

The recommended stack centers on Griffe for AST parsing, Pydantic v2 for schema emission, docstring-parser for docstring extraction, and DiskCache/SQLite with xxHash for persistent caching and invalidation. See `.planning/research/STACK.md` for full details.

**Core technologies:**
- Griffe: AST-first static analysis
- Pydantic v2: JSON Schema emission
- docstring-parser: docstring parsing
- DiskCache + xxHash: persistent cache + invalidation

### Expected Features

Table stakes include automatic schema derivation, AST-first discovery, readiness diagnostics, and consolidated list/describe output. Differentiators include a two-stage pipeline, persistent caching with strong invalidation, overlays, and actionable diagnostics. See `.planning/research/FEATURES.md` for details.

**Must have (table stakes):**
- Automatic schema derivation
- AST-first discovery
- Environment readiness diagnostics
- Consolidated list/describe

**Should have (competitive):**
- Two-stage pipeline
- Persistent schema cache
- Strong cache invalidation
- Metadata overlays
- Actionable diagnostics

**Defer (v2+):**
- Semantic array typing
- Full runtime-generated signature support
- Backward compatibility for legacy fn_id/cache shapes

### Architecture Approach

Adopt a UnifiedIntrospectionEngine that orchestrates AST parsing, optional runtime fallback, overlay application, and schema emission, while storing outputs in a consolidated cache and registry index. See `.planning/research/ARCHITECTURE.md`.

**Major components:**
1. UnifiedIntrospectionEngine — orchestrates introspection and overlays
2. SchemaCache (DiskCache/SQLite) — persists derived schemas
3. Runtime fallback (tool-pack meta.describe) — handles dynamic tools

### Critical Pitfalls

1. **Environment-blind imports** — avoid by AST-first parsing.
2. **Decorator erasure** — mitigate with Griffe and __wrapped__ support.
3. **Stale cache** — prevent with content-hash invalidation.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Core Engine + AST-First
**Rationale:** Establish safe static introspection before any runtime probing.
**Delivers:** Griffe-based extraction, normalized FunctionSpec, consistent list/describe source.
**Addresses:** AST-first discovery, automatic schema derivation, consolidated list/describe.
**Avoids:** environment-blind imports, decorator erasure.

### Phase 2: Cache Consolidation + Invalidation
**Rationale:** Prevent repeated introspection and schema drift.
**Delivers:** DiskCache/SQLite schema store with content-hash invalidation.
**Uses:** DiskCache, xxHash.
**Implements:** schema cache integration with RegistryIndex.

### Phase 3: Runtime Fallback + Overlays
**Rationale:** Support dynamic tools and compiled bindings.
**Delivers:** tool-pack meta.describe fallback, overlay pipeline with precedence.
**Addresses:** two-stage pipeline, metadata overlays.
**Avoids:** compiled binding blind spots.

### Phase 4: Metadata Cleanup + Diagnostics
**Rationale:** Hardening and operator feedback.
**Delivers:** fn_id/module cleanup, callable fingerprints, diagnostics output.

### Phase Ordering Rationale

- Static parsing and schema consistency are prerequisites for caching and fallback.
- Cache consolidation must precede fallback to avoid rework.
- Overlay precedence needs a stable core spec to target.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3:** runtime fallback across conda envs and compiled bindings

Phases with standard patterns (skip research-phase):
- **Phase 1:** AST-first parsing with Griffe
- **Phase 2:** DiskCache + hash-based invalidation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Standard libraries with official docs. |
| Features | HIGH | Directly derived from MCP discovery requirements. |
| Architecture | HIGH | Two-stage pipeline fits isolation constraints. |
| Pitfalls | HIGH | Risks match current failure modes. |

**Overall confidence:** HIGH

### Gaps to Address

- **SWIG/C++ extensions:** rely on manifest overlays for compiled bindings.
- **Complex type resolution:** validate Griffe + Pydantic handling of forward refs.
- **Schema namespacing:** ensure `$defs` keys are tool-scoped.

## Sources

### Primary (HIGH confidence)
- https://mkdocstrings.github.io/griffe/
- https://docs.pydantic.dev/latest/concepts/json_schema/
- https://modelcontextprotocol.io/specification/
- http://www.grantjenks.com/docs/diskcache/tutorial.html

### Secondary (MEDIUM confidence)
- https://docs.python.org/3/library/inspect.html

### Tertiary (LOW confidence)
- https://pypi.org/project/xxhash/

---
*Research completed: 2026-01-27*
*Ready for roadmap: yes*
