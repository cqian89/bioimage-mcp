# Architecture Research

**Domain:** MCP tool registry & introspection
**Researched:** 2026-01-27
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────┐
│ MCP API (tools/list, tools/describe, run)                     │
├──────────────────────────────────────────────────────────────┤
│ DiscoveryService + RegistryIndex (SQLite)                     │
│  └─ UnifiedIntrospectionEngine                                │
│      ├─ AST Parser (Griffe)                                   │
│      ├─ Runtime Fallback (tool-pack meta.describe)            │
│      └─ Overlay/Patch Pipeline                                │
├──────────────────────────────────────────────────────────────┤
│ Schema Cache (DiskCache/SQLite)                               │
├──────────────────────────────────────────────────────────────┤
│ Tool-Pack Runtimes (conda envs, meta.list/meta.describe)      │
└──────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| UnifiedIntrospectionEngine | Orchestrates AST-first + runtime fallback, merges overlays, emits params_schema. | Python module in `registry/`. |
| RegistryIndex | Stores tools/functions/schema metadata. | SQLite-backed index. |
| SchemaCache | Persistent cache for derived schemas and fingerprints. | DiskCache (SQLite-backed). |
| Runtime Fallback | Introspects dynamic tools in isolated envs. | `meta.describe` via tool runtime. |
| Overlay Pipeline | Applies function_overlays with deterministic precedence. | Manifest overlay merger. |

## Recommended Project Structure

```
src/
└── bioimage_mcp/
    ├── registry/
    │   ├── introspection_engine/
    │   │   ├── engine.py          # Orchestrator
    │   │   ├── ast_griffe.py      # AST-first extraction
    │   │   ├── runtime_fallback.py# Tool-pack probing
    │   │   └── overlays.py        # Overlay merge + diagnostics
    │   ├── index.py               # RegistryIndex / ToolIndex
    │   └── schema_cache.py        # Consolidated cache adapter
    ├── runtimes/
    │   └── meta_describe.py       # Tool-pack runtime endpoint
    └── api/
        └── server.py              # MCP list/describe/run
```

### Structure Rationale

- **registry/introspection_engine/:** isolates the new engine and keeps discovery logic in one place.
- **registry/schema_cache.py:** centralizes caching to avoid parallel cache stores.

## Architectural Patterns

### Pattern 1: AST-First Discovery

**What:** Use Griffe to parse signatures/docstrings without imports.
**When to use:** Default path for all tool packs.
**Trade-offs:** Some dynamic factories require fallback.

**Example:**
```python
result = engine.introspect_static(module_path)
if result.needs_runtime:
    result = engine.introspect_runtime(fn_id)
```

### Pattern 2: Two-Stage Pipeline

**What:** Stage 1 static, Stage 2 runtime fallback in tool env.
**When to use:** For tools with decorators/factories or compiled bindings.
**Trade-offs:** Runtime fallback is slower and requires env availability.

**Example:**
```python
if not ast_signature:
    schema = runtime.describe(fn_id, env_id)
```

### Pattern 3: Overlay/Patch Pipeline

**What:** Apply overlays after normalization, before schema emission.
**When to use:** When docstrings or type hints are incomplete.
**Trade-offs:** Requires clear precedence rules.

**Example:**
```python
spec = normalize(spec)
spec = apply_overlays(spec)
schema = emit_schema(spec)
```

## Data Flow

### Request Flow

```
tools/describe
    ↓
DiscoveryService → UnifiedIntrospectionEngine → SchemaCache/RegistryIndex
    ↓                         ↓
  Response  ←────────── merged schema
```

### State Management

```
RegistryIndex
    ↓ (refresh)
IntrospectionEngine → SchemaCache → RegistryIndex
```

### Key Data Flows

1. **Introspection pipeline:** AST parse → optional runtime fallback → overlays → schema emission.
2. **Cache invalidation:** tool_version/env lock/source hash → cache refresh.
3. **Overlay application:** built-in → manifest → user overrides.

## Scaling Considerations

| Scale (tools) | Architecture Adjustments |
|--------------|--------------------------|
| 0-10 tools | AST-only scan on startup is fine. |
| 10-100 tools | Cache schemas; background refresh on changes. |
| 100+ tools | Defer runtime fallback to on-demand describe. |

### Scaling Priorities

1. **First bottleneck:** full runtime fallback at startup → move to on-demand.
2. **Second bottleneck:** cache churn from low-quality hashes → include env lock hash.

## Anti-Patterns

### Anti-Pattern 1: In-Process Tool Imports

**What people do:** import tool packs in core server for signatures.
**Why it's wrong:** causes dependency conflicts and crashes.
**Do this instead:** AST-first + runtime fallback in tool env.

### Anti-Pattern 2: Always-On Runtime Fallback

**What people do:** use runtime introspection for every tool.
**Why it's wrong:** slow and couples to env availability.
**Do this instead:** AST-first default; fallback only when needed.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Conda/Micromamba | subprocess invocation | Used for tool env checks and runtime fallback. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Registry ↔ Runtimes | NDJSON meta.list/meta.describe | Cross-env tool discovery. |
| Registry ↔ Artifacts | IOPattern + FunctionHints | Keep artifact ports out of params_schema. |

## Sources

- https://mkdocstrings.github.io/griffe/
- https://modelcontextprotocol.io/specification/
- src/bioimage_mcp/registry/

---
*Architecture research for: MCP tool registry & introspection*
*Researched: 2026-01-27*
