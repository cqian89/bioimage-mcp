# Project State: Bioimage-MCP

## Project Reference
- **Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
- **Current Milestone:** v0.3.0 Scipy Integration
- **Current Focus:** Phase 6 (Infrastructure & N-D Foundation)

## Current Position
- **Phase:** 6
- **Plan:** 4 of 4 in current phase (Phase complete)
- **Status:** Phase complete
- **Last activity:** 2026-01-25 - Completed 06-04-PLAN.md

Progress: ████████████████████████ 100%

## Performance Metrics
- **Phase Coverage:** 8/11 phases completed (including 5.1)
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
| 6 | Unified docstring parsing | Switched to `docstring-parser` as primary parser in `Introspector` for better cross-format support (Numpydoc, Google, Sphinx). |
| 6 | Transparent provenance | Prefixed subprocess-based discovery source with `subprocess:` to distinguish it from in-process discovery. |
| 6 | Inject `_manifest_path` into adapter config | Allows resolution of relative paths (like blacklists) without global state. |
| 6 | Filter deprecated functions in discovery | Ensures stable AI interaction by excluding stale scientific APIs. |
| 6 | Curated allowlist for callables | Ensures security while supporting scipy measurements by restricting callables to safe numpy equivalents. |
| 6 | 16MB uint16 threshold | Automatically cast large uint16 images to float32 to prevent overflow during processing. |
| 6 | Context-dependent return format | Return OME-TIFF for image arrays and JSON for scalar measurements to optimize agent UX. |
| 6 | Forward physical metadata to writers | Ensured scipy.ndimage outputs retain physical pixel size and channel name metadata by explicitly passing them to `OmeTiffWriter.save`. |

### Session Continuity
- v0.2.0 "Foundation" complete (Phases 1-5).
- Scipy research (SUMMARY.md) incorporated into roadmap.
- Phase 5.1 Complete: Protocol standardized across trackpy and cellpose, core parsers implemented.
- Phase 6 Complete: Scipy ndimage infrastructure established with metadata preservation and memory safety.
- Stopped at: Completed 06-04-PLAN.md
- Resume file: None

## Next Steps
1. Transition to Phase 7: Transforms & Measurements.

