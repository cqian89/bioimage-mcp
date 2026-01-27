# Phase 12: Core Engine + AST-First - Research

**Researched:** 2026-01-27
**Domain:** Unified Discovery and Introspection Engine
**Confidence:** HIGH

## Summary

Phase 12 shifts the introspection pipeline to AST-first discovery with isolated runtime fallback. The recommended approach uses `griffe` to load modules without importing, then falls back to a dedicated worker for runtime introspection when signatures are dynamic or complex. JSON Schema should be generated via Pydantic v2 `TypeAdapter`, replacing manual type mapping. Diagnostics should record `introspection_source`, overlay application, and missing doc issues as log-only output.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
| --- | --- | --- | --- |
| `griffe` | 1.0+ | AST static analysis | De facto standard for loading Python APIs without importing; used by `mkdocstrings`. |
| `pydantic` | 2.0+ | JSON Schema generation | Industry standard for type-hint to JSON conversion. |
| `diskcache` | 5.6+ | Persistent cache | Disk-backed cache with TTL and invalidation hooks. |
| `docstring-parser` | 0.16+ | Docstring parsing | Handles Google, NumPy, and Sphinx styles in one API. |

### Supporting

| Library | Version | Purpose | When to Use |
| --- | --- | --- | --- |
| `hashlib` | Stdlib | Fingerprinting | Use source hash for `callable_fingerprint`. |
| `typing_extensions` | 4.9+ | Rich typing metadata | Support `Annotated[T, Doc(...)]` patterns. |

## Architecture Patterns

### Recommended Project Structure

```
src/bioimage_mcp/registry/
├── engine.py           # DiscoveryEngine orchestrator
├── static/
│   ├── inspector.py    # Griffe-based static analysis
│   └── mapper.py       # Static AST to JSON Schema (simple cases)
├── runtime/
│   ├── worker.py       # Isolated introspection worker
│   └── adapter.py      # Pydantic-based schema generator
└── persistence/
    └── cache.py        # DiskCache management
```

### Static-First Orchestrator

1. **Cache hit:** Use `callable_fingerprint` + `tool_version` + env hash to fetch cached schema.
2. **AST sweep:** `griffe` loads module and extracts signature, docstring, and source.
3. **Fallback check:** If types are dynamic or unresolved, run isolated worker.
4. **Runtime worker:** `conda run -n <env> python worker.py <fn_id>` produces high fidelity schema.

### Anti-Patterns

- **Greedy import:** Do not import tool code in the MCP server process; it pulls heavy deps.
- **Manual schema mapping:** Avoid hand-built JSON Schema; use `TypeAdapter(...).json_schema()`.

## Don't Hand-Roll

| Problem | Avoid | Use Instead | Why |
| --- | --- | --- | --- |
| Signature parsing | Custom AST/regex | `griffe` | Resolves imports, aliases, and forward refs. |
| JSON Schema | Manual dicts | Pydantic v2 | Handles Union, Optional, Nested types. |
| Docstring parsing | Custom parsing | `docstring-parser` | Supports Google, NumPy, Sphinx. |
| Fingerprinting | File mtime | `hashlib` on source | Tracks real logic changes. |

## Common Pitfalls

1. **Circular type hints**
   - Failure: AST resolution fails on circular refs.
   - Fix: Load with `resolve_aliases=True`, use fallback when unresolved.
2. **Artifact/parameter collision**
   - Failure: Artifact ports appear in `params_schema`.
   - Fix: Detect `ArtifactRef` and omit in schema generation.
3. **Non-deterministic schemas**
   - Failure: Schema ordering varies between runs.
   - Fix: Normalize JSON schema output with deterministic sorting.

## Code Examples

### Static Discovery with Griffe

```python
import hashlib
import griffe

loader = griffe.GriffeLoader()
pkg = loader.load("tools.cellpose")
func = pkg["tools.cellpose.segment_image"]

params = func.parameters
fingerprint = hashlib.sha256(func.source.encode()).hexdigest()
```

### JSON Schema via Pydantic v2 (Worker)

```python
from pydantic import TypeAdapter
from pydantic.json_schema import GenerateJsonSchema, PydanticOmit


class OmitArtifacts(GenerateJsonSchema):
    def handle_invalid_for_json_schema(self, schema, error_info):
        if "ArtifactRef" in str(schema):
            raise PydanticOmit
        return super().handle_invalid_for_json_schema(schema, error_info)


adapter = TypeAdapter(FunctionParamsModel)
schema = adapter.json_schema(schema_generator=OmitArtifacts)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
| --- | --- | --- | --- |
| `inspect.signature` | `griffe` (AST) | 2024 | Zero-import discovery of heavy libraries. |
| Pydantic v1 | Pydantic v2 | 2023 | Faster and better JSON Schema support. |
| `numpydoc` | `docstring-parser` | 2023 | Unified docstring parsing. |

## Sources

### Primary (HIGH confidence)

- `mkdocstrings/griffe` (AST loader)
- `pydantic/pydantic` (JSON Schema generation)
- `grantjenks/python-diskcache` (persistent cache)

### Secondary (MEDIUM confidence)

- Python `ast` docs
- `docstring-parser` repository

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (mature, standard libraries)
- Architecture: HIGH (tiered discovery is standard for dynamic Python)
- Pitfalls: MEDIUM (runtime worker IPC needs careful design)

**Open question:** Whether to retain AST output alongside runtime output for diagnostics.
