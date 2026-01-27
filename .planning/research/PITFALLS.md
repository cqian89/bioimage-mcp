# Domain Pitfalls: Unified Introspection & Registry Consolidation

**Domain:** Bioimage-MCP Tool Registry
**Researched:** 2026-01-27

## Critical Pitfalls

### 1. Environment-Blind Introspection (Import Isolation Leak)
**What goes wrong:** The engine attempts to introspect a tool (e.g., `cellpose`) by importing it in the core server process rather than inside the tool's isolated environment.
**Why it happens:** Attempting to consolidate logic by using `importlib` directly in the server.
**Consequences:** `ImportError` or DLL/CUDA library mismatches; server crash during startup if a tool pack is missing a heavy dependency.
**Prevention:** Use a **Two-Stage Pipeline**. Stage 1 (AST-first with **Griffe**) never imports code. Stage 2 (Dynamic Fallback) runs in a subprocess within the tool's environment.

### 2. Decorator Erasure (Signature Loss)
**What goes wrong:** Custom decorators (e.g., `@validate_call`, `@cache`) hide the original function signature or docstring.
**Why it happens:** `inspect.signature` often sees the decorator's wrapper instead of the original function.
**Consequences:** MCP `inputSchema` shows generic `*args` and `**kwargs` instead of actual parameters, making the tool unusable for LLMs.
**Prevention:** **Griffe** handles decorators much better statically by following the AST. For runtime fallback, use `functools.wraps` or access `__wrapped__` attributes explicitly.

### 3. Stale Schema Invalidation (Caching Blindness)
**What goes wrong:** The unified cache stores tool schemas but misses updates to the underlying tool-pack code or environment.
**Why it happens:** Relying on version numbers alone (which developers often forget to bump during development).
**Consequences:** LLMs receive stale tool definitions, leading to `ValidationError` when the tool is called.
**Prevention:** Include the **xxHash** of the tool's source file in the cache key. Any change to the code immediately invalidates the cache.

## Moderate Pitfalls

### 1. SWIG/Compiled Binding Blindness
**What goes wrong:** The unified engine assumes all tools are pure Python and relies on signatures, which fail on SWIG-wrapped C++ (e.g., `tttrlib`).
**Prevention:** Implement a fallback to `manifest.yaml` (manual schema) when dynamic introspection returns empty results. Ensure manual overrides take precedence.

### 2. Circular Type Definition Deadlocks
**What goes wrong:** Tools use system-wide types (like `ArtifactRef`) in their signatures, but the registry requires those tool signatures to build its own internal models.
**Prevention:** Move shared types to a leaf-node package with zero internal dependencies.

## Minor Pitfalls

### 1. Pydantic V2 Schema Collision
**What goes wrong:** Default Pydantic schema generation creates duplicate `$defs` keys for different tools.
**Prevention:** Use a custom `schema_generator` that prefixes definitions with the tool ID.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Core Engine** | Circular Imports | Decouple primitive types from registry logic. |
| **AST/Griffe** | Decorator Erasure | Use Griffe's AST traversal to find original signatures. |
| **Caching** | Stale Metadata | Include `xxHash` of source code in the cache key. |
| **Fallback** | Subprocess Overhead | Only use runtime fallback for tools that fail AST analysis. |

## Sources
- [Griffe Documentation](https://mkdocstrings.github.io/griffe/)
- [Pydantic V2 JSON Schema Guide](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [Python `inspect` Module Limitations](https://docs.python.org/3/library/inspect.html)
- `src/bioimage_mcp/registry/` (Existing implementation)
