# Project State: Bioimage-MCP

## Project Reference
- **Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
- **Current Milestone:** v0.3.0 Scipy Integration
- **Current Focus:** Phase 5.1 (Research Dynamic Discovery Standardization)

## Current Position
- **Phase:** 5.1
- **Plan:** 6 of 6 in current phase
- **Status:** Phase complete
- **Last activity:** 2026-01-25 - Completed 05.1-06-PLAN.md

Progress: ████████████████████ 92%

## Performance Metrics
- **Phase Coverage:** 6/10 phases completed
...
### Decisions table
| Phase | Decision | Rationale |
|-------|----------|-----------|
| 5.1 | Standardized `meta.describe` error shape | Chose string-based `error` to simplify parsing and match existing `cellpose` implementation. |
| 5.1 | Required `tool_version` in discovery | Critical for reliable `SchemaCache` invalidation when underlying scientific libraries are updated. |
| 5.1 | Enriched `meta.list` entries | Added `module` and `io_pattern` to enable server-side classification and better search results. |
| 5.1 | String-only errors in discovery | Standardized all tool-pack meta.* handlers to return string errors for parsing simplicity. |
| 5.1 | `tool_version` requirement | Required `tool_version` in both `meta.list` and `meta.describe` for reliable cache invalidation. |
| 5.1 | Aggregated introspection_source in CLI | Show provenance of tool metadata in `bioimage-mcp list` for better transparency. |
| 5.1 | Persisted module/io_pattern in DB | Added columns to functions table to ensure metadata survives server restarts. |

### Session Continuity
- v0.2.0 "Foundation" complete (Phases 1-5).
- Scipy research (SUMMARY.md) incorporated into roadmap.
- Phase 5.1 Complete: Protocol standardized across trackpy and cellpose, core parsers implemented.
- Stopped at: Completed 05.1-06-PLAN.md
- Resume file: None

## Next Steps
1. Transition to Phase 6 (Infrastructure & N-D Foundation).

