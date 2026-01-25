# Project State: Bioimage-MCP

## Project Reference
- **Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
- **Current Milestone:** v0.3.0 Scipy Integration
- **Current Focus:** Phase 5.1 (Discovery Standardization)

## Current Position
- **Phase:** 5.1 of 10 (Research Dynamic Discovery Standardization)
- **Plan:** 3 of 4 in current phase
- **Status:** In progress
- **Last activity:** 2026-01-25 - Completed 05.1-02-PLAN.md

Progress: █████████████████░░░ 85%

## Performance Metrics
- **Phase Coverage:** 5/10 phases completed
- **Requirement Coverage:** 0/21 v1 requirements implemented
- **Test Health:** N/A (Milestone start)

## Accumulated Context

### Roadmap Evolution
- Phase 5.1 inserted: Research Dynamic Discovery Standardization (URGENT)

### Key Decisions
- **Dynamic Adapter Pattern:** Chosen over manual wrappers to minimize maintenance for Scipy's large API surface.
- **Float32 Forcing:** Standardized for memory safety and consistency in Scipy operations (GEN-03).
- **Native Dimensions:** Using `BioImageRef.reader` directly to avoid implicit dimension squeezing (GEN-02).
- **Discovery Protocol:** Standardized on `meta.list` and `meta.describe` with strict metadata requirements (`tool_version`, `introspection_source`).

### Decisions table
| Phase | Decision | Rationale |
|-------|----------|-----------|
| 5.1 | Standardized `meta.describe` error shape | Chose string-based `error` to simplify parsing and match existing `cellpose` implementation. |
| 5.1 | Required `tool_version` in discovery | Critical for reliable `SchemaCache` invalidation when underlying scientific libraries are updated. |
| 5.1 | Enriched `meta.list` entries | Added `module` and `io_pattern` to enable server-side classification and better search results. |

### Session Continuity
- v0.2.0 "Foundation" complete (Phases 1-5).
- Scipy research (SUMMARY.md) incorporated into roadmap.
- Phase 5.1 Plan 1, 2 & 4 complete: Protocol defined, audit finished, core parsers added, and cellpose aligned.
- Stopped at: Completed 05.1-02-PLAN.md
- Resume file: None

## Next Steps
1. Execute `05.1-03-PLAN.md` to align trackpy meta.* responses.
