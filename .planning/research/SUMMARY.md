# Research Summary: Unified Introspection Engine

**Domain:** bioimage-mcp Core Registry & Introspection
**Researched:** 2026-01-27
**Overall confidence:** HIGH

## Executive Summary

The **Unified Introspection Engine** milestone consolidates fragmented schema derivation paths across the `bioimage-mcp` core server and its tool-pack runtimes. Current discovery relies on inconsistent logic that often requires executing heavy tool dependencies just to describe their parameters.

Research confirms a **Static-First (AST-first) approach** using **Griffe (1.15.0)** is the optimal path. This allows the server to extract function signatures and high-fidelity docstrings (Google/NumPy/Sphinx) from tool source code without module execution, avoiding environment-related import errors. For dynamic tools, a **Stage 2 Runtime Fallback** triggers isolated introspection within the tool's specific conda environment. 

To ensure performance and reliability, a **Persistent Schema Cache** (using **DiskCache 5.6.3**) with **Strong Invalidation** (via **xxHash 3.6.0** content hashing) will replace current volatile caches. This ensures that LLMs always see accurate, up-to-date `params_schema` without the latency of repeated introspection.

## Key Findings

- **Stack (STACK.md):** Recommends **Griffe 1.15.0** for static analysis, **DiskCache 5.6.3** for persistence, and **xxHash 3.6.0** for invalidation. Pydantic v2.12.5 remains the standard for JSON Schema emission.
- **Features (FEATURES.md):** Key differentiators include **Stage 1 (AST) vs Stage 2 (Runtime)** analysis, **Metadata Overlays** for manual overrides, and **Actionable Diagnostics** for environment readiness.
- **Architecture (ARCHITECTURE.md):** Employs a **Two-Stage Introspection Pipeline**. The `UnifiedIntrospectionEngine` orchestrates AST parsing (static) and cross-process `meta.describe` (runtime), storing results in a consolidated registry.
- **Pitfalls (PITFALLS.md):** Identified **Decorator Erasure** (solved by Griffe), **Environment-Blind Imports** (solved by the two-stage pipeline), and **Cache Drift** (solved by content-based hashing) as critical focus areas.

## Implications for Roadmap

Based on research, the suggested phase structure is:

1. **Phase 1: Core Engine & AST Implementation** - Implement the `UnifiedIntrospectionEngine` using Griffe. Establish the static-first pipeline for standard Python tools.
   - Addresses: Automatic Schema Derivation, Static signatures.
   - Avoids: Environment-Blind Introspection crashes.

2. **Phase 2: Persistent Caching & Invalidation** - Integrate DiskCache and xxHash. Implement the composite cache key `(tool_id, version, source_hash)`.
   - Addresses: Stale Schema Invalidation, consolidated cache.
   - Avoids: Performance bottlenecks during server restart.

3. **Phase 3: Runtime Fallback & Overlay Pipeline** - Implement the Stage 2 (Subprocess) fallback for dynamic tools (Trackpy) and the YAML patch/overlay logic.
   - Addresses: Metadata Overlays, SWIG/C++ binding support.
   - Avoids: Missing metadata for non-pure-Python tools.

4. **Phase 4: Metadata Cleanup & Diagnostics** - Implement `rich`-based diagnostics for `fn_id` conflicts and module resolution errors.
   - Addresses: Cleanup + Diagnostics.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Griffe and DiskCache are industry standards for these tasks. |
| Features | HIGH | Clear mapping of requirements to technical capabilities. |
| Architecture | HIGH | Two-stage pipeline solves the isolated import conflict. |
| Pitfalls | HIGH | Circular dependencies and environment leaks are well-understood. |

## Gaps to Address

- **SWIG/C++ Extensions**: Griffe may struggle with binary extensions; the Phase 3 fallback to `manifest.yaml` is essential.
- **Complex Annotated Types**: Handling cross-environment type resolution for custom Pydantic types needs validation.

## Sources
- [Griffe Documentation](https://mkdocstrings.github.io/griffe/)
- [Pydantic v2 JSON Schema Guide](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [DiskCache Tutorial](http://www.grantjenks.com/docs/diskcache/tutorial.html)
- [PyPI Package Metadata (Verified 2026-01-27)](https://pypi.org/)
