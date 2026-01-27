# Stack Research

**Domain:** MCP tool registry & introspection (bioimage-mcp)
**Researched:** 2026-01-27
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Griffe | 1.15+ | AST-based static analysis | Parses signatures/docstrings without importing tool code. |
| Pydantic | 2.10+ | JSON Schema emission | Standard for MCP-compatible params_schema output. |
| docstring-parser | 0.17+ | Docstring parsing | Extracts parameter descriptions (NumPy/Google/Sphinx). |
| SQLite | 3.x | Registry index storage | Existing store for ToolIndex and schema cache. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| DiskCache | 5.6+ | Persistent schema cache | Store derived schemas across restarts. |
| xxHash | 3.6+ | Content hashing | Cache invalidation on source changes. |
| inspect (stdlib) | Python 3.10+ | Runtime fallback signatures | Only inside tool-pack runtime fallback. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| ruff | Lint/format | Enforce consistent formatting. |
| pytest | Test runner | Use markers for env-gated tests. |

## Installation

```bash
# Core
python -m pip install "griffe>=1.15" "pydantic>=2.10" "docstring-parser>=0.17"

# Supporting
python -m pip install "diskcache>=5.6" "xxhash>=3.6"

# Dev dependencies
python -m pip install -e ".[dev]"
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Griffe | inspect (stdlib) | Only for runtime fallback in isolated tool envs. |
| DiskCache | JSON files | Only for tiny tool packs with no concurrency. |
| Pydantic v2 | Marshmallow | Only if the repo migrates away from Pydantic. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| In-process tool imports | Leaks heavy deps into core server | AST-first with Griffe; fallback in tool env. |
| File-per-schema JSON cache | Race-prone and hard to invalidate | Centralized SQLite/DiskCache. |
| Implicit type guessing | Unreliable schemas | Type hints + docstring parsing + overlays. |

## Stack Patterns by Variant

**If tool pack is pure Python:**
- Use AST-first only
- Because static parsing is faster and safer

**If tool pack uses compiled bindings:**
- Use manifest overlays and runtime fallback
- Because static parsing cannot see C++ signatures

**If tool pack has heavy deps (torch, cellpose):**
- Never import in core server
- Because dependency conflicts crash discovery

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Pydantic 2.10+ | Python 3.10+ | Aligns with bioimage-mcp runtime constraints. |
| Griffe 1.15+ | Python 3.10+ | AST parsing without import side-effects. |

## Sources

- https://mkdocstrings.github.io/griffe/
- https://docs.pydantic.dev/latest/concepts/json_schema/
- http://www.grantjenks.com/docs/diskcache/tutorial.html
- https://pypi.org/project/xxhash/

---
*Stack research for: MCP tool registry & introspection*
*Researched: 2026-01-27*
