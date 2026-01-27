# Research Summary: Unified Introspection Engine

**Domain:** bioimage-mcp Core Registry & Introspection
**Researched:** 2026-01-27
**Overall confidence:** HIGH

## Executive Summary

This milestone consolidates fragmented discovery/introspection into a single engine shared by the core server and tool-pack runtimes. Research supports a **static-first (AST-first)** pipeline using **Griffe** to extract signatures and docstrings without importing heavy dependencies, paired with a **runtime fallback** in isolated tool environments for dynamic or factory-generated tools. Schema emission should remain **Pydantic v2** based, with strict separation between params_schema and artifact ports. A **persistent cache** backed by SQLite/DiskCache and **content hashing (xxHash)** is required to prevent stale metadata and avoid repeated introspection across restarts.

## Key Findings

- **Stack (STACK.md):** Griffe 1.15+, docstring-parser 0.17+, Pydantic v2.10+, DiskCache 5.6+, xxHash 3.6+, SQLite 3.x, Python 3.13, Micromamba.
- **Features (FEATURES.md):** Table stakes include automatic schema derivation, AST-first discovery, environment readiness diagnostics, and consolidated list/describe output. Differentiators include a two-stage pipeline, persistent caching, strong invalidation, metadata overlays, and actionable diagnostics.
- **Architecture (ARCHITECTURE.md):** A UnifiedIntrospectionEngine orchestrates AST parsing (Stage 1) and runtime fallback (Stage 2), storing schemas in a consolidated cache and registry index. Shared types must move to leaf-node modules to prevent circular imports.
- **Pitfalls (PITFALLS.md):** Environment-blind imports, decorator erasure, stale caches, SWIG/compiled bindings, and circular type definitions are the primary risks.

## Implications for Roadmap

1. **Core Engine + AST First**: Implement the UnifiedIntrospectionEngine with Griffe and docstring parsing; align schema emission to meta.describe requirements.
2. **Cache Consolidation + Invalidation**: Migrate schema caching into SQLite/DiskCache with content-hash invalidation.
3. **Runtime Fallback + Overlays**: Add subprocess-based fallback for dynamic tools and implement metadata overlay/patch handling.
4. **Metadata Cleanup + Diagnostics**: Enforce full module paths, callable fingerprinting, and user-facing diagnostics.

## Gaps / Open Questions

- **SWIG/C++ Extensions**: Static analysis cannot introspect compiled bindings; manifest overrides must remain authoritative.
- **Complex Type Resolution**: Cross-file type aliases and forward refs need validation with Griffe + Pydantic v2.
- **Schema Namespacing**: Avoid Pydantic `$defs` collisions by namespacing per tool/function.

## Sources

- [Griffe Documentation](https://mkdocstrings.github.io/griffe/)
- [Pydantic JSON Schema Guide](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [DiskCache Tutorial](http://www.grantjenks.com/docs/diskcache/tutorial.html)
- [Python inspect Module](https://docs.python.org/3/library/inspect.html)
