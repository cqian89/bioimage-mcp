# Pitfalls Research

**Domain:** MCP tool registry & introspection
**Researched:** 2026-01-27
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Environment-Blind Introspection

**What goes wrong:** Core server imports tool code directly and crashes when heavy deps are missing.

**Why it happens:** Introspection logic is consolidated without respecting tool-pack isolation.

**How to avoid:** Use AST-first parsing with Griffe; only run runtime fallback in tool env.

**Warning signs:** ImportError/DLL errors during server startup; CUDA library mismatches.

**Phase to address:** Phase 1 (Core engine + AST-first)

---

### Pitfall 2: Decorator Erasure (Signature Loss)

**What goes wrong:** Decorated functions expose only `*args/**kwargs` and schemas become unusable.

**Why it happens:** inspect.signature sees wrapper instead of original function.

**How to avoid:** Prefer AST parsing; for runtime fallback, use __wrapped__ and functools.wraps.

**Warning signs:** params_schema missing required fields or shows only kwargs.

**Phase to address:** Phase 1 (AST-first extraction)

---

### Pitfall 3: Stale Schema Cache

**What goes wrong:** Schemas do not update after tool-pack changes.

**Why it happens:** Cache keys only include version numbers; devs forget to bump them.

**How to avoid:** Add content hash + env lock hash to cache key.

**Warning signs:** Validation errors when calling tools that appear unchanged.

**Phase to address:** Phase 2 (Cache consolidation)

---

### Pitfall 4: Overlay Precedence Drift

**What goes wrong:** Manual overrides override each other unpredictably.

**Why it happens:** No deterministic merge order across built-in, manifest, user overlays.

**How to avoid:** Define precedence and log applied overlays.

**Warning signs:** Same function shows different schemas depending on load order.

**Phase to address:** Phase 3 (Overlay pipeline)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip overlay normalization | Faster patching | Schema drift and duplication | Never |
| Cache key without env hash | Simpler cache | Stale schemas after env updates | Only for local dev scratch envs |
| Runtime fallback for everything | Quick success on dynamic tools | Slow startup and brittle behavior | Only for diagnostic mode |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Conda/Micromamba | Assume env exists without checks | Verify env before exposing tools. |
| meta.describe | Return params_schema with artifact ports | Strip artifact ports, keep I/O separate. |
| RegistryIndex | Maintain parallel JSON cache | Consolidate into single SQLite-backed store. |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full runtime fallback on startup | Server boot takes minutes | AST-first default + on-demand fallback | 50+ tools |
| Re-introspect every list | High latency for tools/list | Cache schemas and reuse | 10+ tools |
| Hashing entire repo | Discovery slows to a crawl | Hash only tool-pack sources | 100+ tools |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Importing untrusted tool code in core server | Code execution in trusted process | AST-first parsing only. |
| Accepting arbitrary import paths | Path traversal / arbitrary code | Restrict to registered tool packs. |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent fallback without diagnostics | Hard to debug schema issues | Report fallback + missing docs. |
| Inconsistent list/describe data | Agents call tools incorrectly | Single source of introspection truth. |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Schema emission:** missing required fields or wrong defaults — verify with real calls
- [ ] **Cache invalidation:** changes not reflected — verify hash inputs
- [ ] **Overlay precedence:** non-deterministic merges — verify ordering logs
- [ ] **Diagnostics:** missing remediation guidance — verify operator instructions

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Environment-blind imports | HIGH | Remove imports, re-run discovery via AST-first only. |
| Decorator erasure | MEDIUM | Add overlays or use __wrapped__ in runtime fallback. |
| Stale cache | LOW | Clear cache store and rebuild with hashes. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Environment-blind introspection | Phase 1 | Discovery runs with heavy deps missing. |
| Decorator erasure | Phase 1 | Schemas include required params. |
| Stale schema cache | Phase 2 | Schema updates after source change. |
| Overlay precedence drift | Phase 3 | Logs show deterministic order. |

## Sources

- https://mkdocstrings.github.io/griffe/
- https://docs.python.org/3/library/inspect.html
- https://modelcontextprotocol.io/specification/

---
*Pitfalls research for: MCP tool registry & introspection*
*Researched: 2026-01-27*
