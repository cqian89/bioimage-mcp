# Technology Stack: Unified Introspection Engine

**Project:** Bioimage-MCP
**Researched:** 2026-01-27

## Recommended Stack

### Core Introspection & Analysis
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Griffe** | 1.15+ | AST-based Static Analysis | Extracts signatures and docstrings without executing code. Avoids `ImportError` and OOM in the server process. |
| **Pydantic** | v2.10+ | Schema Emission | Standard for generating MCP-compatible JSON Schemas. |
| **docstring-parser** | 0.17+ | Documentation Parsing | High-fidelity extraction of parameter descriptions from NumPy/Google docstrings. |

### Metadata & Caching
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **SQLite** | 3.x | Unified Registry Index | Fast, relational storage for function metadata and cached schemas. |
| **DiskCache** | 5.6+ | Schema Storage | SQLite-backed, thread-safe persistent cache for derived schemas. |
| **xxHash** | 3.6+ | Content Invalidation | Extremely fast hashing of tool source files to detect changes. |

### Isolation & Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Python** | 3.13 | Base Runtime | Modern typing and performance improvements. |
| **Micromamba** | Latest | Environment Isolation | Reliable management of tool-pack environments. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Analysis | **Griffe** | `inspect` (Stdlib) | `inspect` requires importing the code, which leaks dependencies and causes crashes in the server process. |
| Caching | **DiskCache** | JSON Files | File-per-schema is hard to manage and prone to race conditions. |
| Type System | **Pydantic v2** | Marshmallow | Pydantic is already the internal standard for bioimage-mcp. |

## Installation

```bash
# Core server requirements
python -m pip install griffe pydantic diskcache xxhash docstring-parser
```

## Sources

- [Griffe Project Page](https://github.com/mkdocstrings/griffe)
- [Pydantic JSON Schema Guide](https://docs.pydantic.dev/latest/concepts/json_schema/)
- `src/bioimage_mcp/config/` (Existing configuration)
