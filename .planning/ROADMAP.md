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
**Status:** Complete (2026-01-27)
**Depends on:** Phase 11
**Plans:** 9/9 plans complete

Plans:
- [x] 12-01-PLAN.md — Static inspector foundation (griffe + fingerprint + normalization)
- [x] 12-02-PLAN.md — Runtime schema emission upgrade (TypeAdapter + docstrings)
- [x] 12-03-PLAN.md — DiscoveryEngine: AST-first + runtime fallback + skip rules
- [x] 12-04-PLAN.md — Persistent cache invalidation keys + callable_fingerprint storage
- [x] 12-05-PLAN.md — API wiring: single schema source + describe metadata contract
- [x] 12-06-PLAN.md — Diagnostics + doctor readiness checks (ENV-01)
- [x] 12-07-PLAN.md — DiscoveryEngine AST-first gating (conditional runtime fallback)
- [x] 12-08-PLAN.md — Cache invalidation keys enforcement + list/describe sync
- [x] 12-09-PLAN.md — Runtime schema description preservation + required/docstring alignment

**Details:**
[To be added during planning]

### Phase 13: Dynamic Introspection Cache Reuse (incl. trackpy)

**Goal:** Reuse dynamic introspection results across meta.list calls via a lockfile-gated cache stored under ~/.bioimage-mcp/cache/dynamic/, including trackpy.
**Status:** Complete (verified 2026-01-29)
**Depends on:** Phase 12
**Plans:** 4/4 plans complete

Plans:
- [x] 13-01-PLAN.md — Wire IntrospectionCache into tools.base meta.list + tests
- [x] 13-02-PLAN.md — Add trackpy cache reuse via IntrospectionCache + tests
- [x] 13-03-PLAN.md — Core-side cache for runtime meta.list (avoid subprocess on repeat list)
- [x] 13-04-PLAN.md — Fix trackpy project_root detection for lockfile cache writes

### Phase 14: OME-Zarr Standardization

**Goal:** Standardize OME-Zarr as the primary interchange format and fix directory-backed artifact materialization.
**Status:** Planning
**Depends on:** Phase 13
**Plans:** 2 plans

Plans:
- [ ] 14-01-PLAN.md — Standardize on OME-Zarr and Fix Directory Materialization
- [ ] 14-02-PLAN.md — Update tttrlib/Cellpose for OME-Zarr + custom axes

**Details:**
- Standardizes IOBridge default format to OME-Zarr.
- Enables core server to import directory-backed artifacts (OME-Zarr).
- Relax 5D/TCZYX constraints in tool packs.
- Switches tttrlib decay outputs to OME-Zarr with native 'bins' axis.

**Details:**
[To be added during planning]

---

*Roadmap updated: 2026-01-28*
