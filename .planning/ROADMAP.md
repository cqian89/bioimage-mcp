# Roadmap: Bioimage-MCP

## Milestones

- ✅ **v0.3.0 Scipy Integration** — Phases 5.1–10 (shipped 2026-01-27). Archive: `.planning/milestones/v0.3.0-ROADMAP.md`
- 🚧 **v0.4.0 Unified Introspection Engine** — planning (see `.planning/PROJECT.md`)

## Current Milestone: v0.4.0 Unified Introspection Engine

### Phase 11: Discovery Gap Closure

**Goal:** Gap closure for scipy discovery identified in v0.3.0 audit.
**Status:** Complete (2026-01-27)
**Depends on:** Phase 10
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 11 to break down)

**Details:**
[To be added during planning]

### Phase 12: Core Engine + AST-First

**Goal:** Unified introspection engine that is AST-first with isolated runtime fallback, deterministic schema emission, and consistent metadata across list/describe.
**Status:** In progress
**Depends on:** Phase 11
**Plans:** 5/6 plans complete

Plans:
- [x] 12-01-PLAN.md — Static inspector foundation (griffe + fingerprint + normalization)
- [x] 12-02-PLAN.md — Runtime schema emission upgrade (TypeAdapter + docstrings)
- [x] 12-03-PLAN.md — DiscoveryEngine: AST-first + runtime fallback + skip rules
- [x] 12-04-PLAN.md — Persistent cache invalidation keys + callable_fingerprint storage
- [x] 12-05-PLAN.md — API wiring: single schema source + describe metadata contract
- [ ] 12-06-PLAN.md — Diagnostics + doctor readiness checks (ENV-01)

**Details:**
[To be added during planning]

---

*Roadmap updated: 2026-01-27*
