# Project State: Bioimage-MCP

## Project Reference
- **Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
- **Current Milestone:** v0.3.0 Scipy Integration
- **Current Focus:** Phase 6 (Infrastructure & N-D Foundation)

## Current Position
- **Phase:** 6
- **Plan:** 2 of 3 in current phase
- **Status:** In progress
- **Last activity:** 2026-01-25 - Completed 06-02-PLAN.md

Progress: █████████████████████░ 94%

## Performance Metrics
- **Phase Coverage:** 7/11 phases completed (including 5.1)
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
| 6 | Inject `_manifest_path` into adapter config | Allows resolution of relative paths (like blacklists) without global state. |
| 6 | Filter deprecated functions in discovery | Ensures stable AI interaction by excluding stale scientific APIs. |

### Session Continuity
- v0.2.0 "Foundation" complete (Phases 1-5).
- Scipy research (SUMMARY.md) incorporated into roadmap.
- Phase 5.1 Complete: Protocol standardized across trackpy and cellpose, core parsers implemented.
- Stopped at: Completed 06-02-PLAN.md
- Resume file: None

## Next Steps
1. Complete Phase 6 (Infrastructure & N-D Foundation).

