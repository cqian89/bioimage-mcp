# Architecture Patterns: Unified Introspection

**Domain:** Bioimage-MCP Tool Registry
**Researched:** 2026-01-27

## Recommended Architecture: "Two-Stage Introspection Pipeline"

The engine utilizes a tiered strategy to maximize safety (no imports) while providing high fidelity (runtime probing).

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **UnifiedIntrospectionEngine** | Orchestrates Stage 1 (Static) and Stage 2 (Dynamic) probing. | `RegistryIndex`, `Runtimes`. |
| **Stage 1: Griffe (Static)** | Parses tool source code using AST to extract signatures/docstrings. | Tool source files. |
| **Stage 2: Subprocess (Dynamic)** | Executes `inspect` in the tool's conda env for factory-based tools. | `Runtime Workers`. |
| **SchemaCache (DiskCache)** | Persistent storage for generated JSON Schemas, keyed by content hashes. | `UnifiedIntrospectionEngine`. |

### Data Flow

1.  **Stage 1 (AST)**: `UnifiedIntrospectionEngine` uses **Griffe** to parse tool source files. It extracts function names, types, and docstrings (Google/NumPy/Sphinx) without importing the code. This is the default path for 90% of tools.
2.  **Stage 2 (Runtime Fallback)**: If Griffe fails (e.g., dynamic factories, complex decorators), the engine triggers a `meta.describe` call in a subprocess within the tool's conda environment.
3.  **Consolidation**: Both paths produce a unified `IntrospectionResult`.
4.  **Hashing**: The source file is hashed using **xxHash**. The result is cached in **DiskCache** with a key composed of `(tool_id, tool_version, source_hash)`.

## Patterns to Follow

### Pattern 1: AST-First Discovery
Always attempt to resolve a signature via AST (Griffe) before resorting to a runtime import. This drastically reduces server startup time and prevents "DLL Hell" in the core process.

### Pattern 2: Strong Invalidation via xxHash
Use the tool's source file content hash as part of the cache key. This ensures that any modification to the tool logic immediately triggers a schema refresh, even if the version number in `manifest.yaml` remains unchanged.

### Pattern 3: Leaf-Node Type Definitions
Define shared types like `ArtifactRef` and `BioImageRef` in a leaf-node package (e.g., `bioimage_mcp.types.refs`) with zero internal dependencies to prevent circular imports during runtime fallback.

## Anti-Patterns to Avoid

### Anti-Pattern 1: In-Process Tool Imports
Never import tool-pack code directly in the core server process. Heavy dependencies (PyTorch, TensorFlow) will cause OOMs or version conflicts with other tool-packs.

### Anti-Pattern 2: Volatile In-Memory Caching
Relying only on in-memory caches means every server restart triggers a full re-scan. Use **DiskCache** for persistence across sessions.

## Scalability Considerations

| Concern | 10 Tools | 100 Tools | 1000 Tools |
|---------|----------|-----------|------------|
| **Startup Time** | <200ms | ~1s (Cached) | ~2s (Requires background indexer) |
| **RAM Usage** | Low | ~50MB (Griffe overhead) | ~200MB |
| **Cache Reliability** | High | High (DiskCache/SQLite) | High |

## Sources
- [Griffe Architecture](https://mkdocstrings.github.io/griffe/reference/griffe/loader/)
- [DiskCache Memoization](http://www.grantjenks.com/docs/diskcache/tutorial.html#memoization)
- `src/bioimage_mcp/registry/` (Existing implementation)
