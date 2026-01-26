# Project State: Bioimage-MCP

## Project Reference
- **Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
- **Current Milestone:** v0.3.0 Scipy Integration
- **Current Focus:** Phase 7 (Transforms & Measurements)

## Current Position
- **Phase:** 9
- **Plan:** 1 of 4 in current phase
- **Status:** In progress
- **Last activity:** 2026-01-26 - Completed 09-01-PLAN.md
- **Next Phase:** 11

Progress: ███████████████████████░░░ 88%

## Performance Metrics
- **Phase Coverage:** 9/11 phases completed (including 5.1)
...
| 7 | Multi-output naming convention | Standardized on `labels.ome.tiff` and `counts.json` for `label()` to ensure stable filenames under a provided `work_dir`. |
| 7 | Key-by-ID measurement payload | Using label ID strings as keys (e.g., `{"1": [y, x]}`) provides the most unambiguous representation for AI agents and downstream logic. |
| 8 | Composite Scipy Adapter | Using a dispatcher allows clean separation of concerns between image processing (`ndimage`) and statistics (`stats`) while maintaining a single registry entry. |
| 8 | Inheritance for Stats Adapter | `ScipyStatsAdapter` inherits from `ScipyNdimageAdapter` to reuse robust artifact loading and JSON serialization logic. |
| 8 | Native JSON Serialization | Statistical results are returned as `ScalarRef` (JSON) to allow easy consumption by AI agents and downstream logic. |
| 8 | Curated Stats Wrappers | Exposing specific `*_table` wrappers instead of raw `scipy.stats` functions ensures reliable artifact I/O and easier agent consumption. |
| 8 | TABLE_PAIR_TO_JSON pattern | Introduced a specific I/O pattern for two-sample tests to simplify port mapping for t-tests and KS-tests. |
| 9 | Spatial/Signal Routing | Used prefix-based routing in ScipyAdapter to support submodules like scipy.spatial and scipy.signal without breaking ndimage/stats. |
| 9 | KDTree Lifecycle Patterns | Introduced TABLE_TO_OBJECT and OBJECT_AND_TABLE_TO_JSON to support stateful KDTree building and querying. |

## Accumulated Context

### Roadmap Evolution
- Phase 11 added: Fix scipy.stats dynamic discovery and adapter gaps

### Session Continuity
- v0.2.0 "Foundation" complete (Phases 1-5).
- Scipy research (SUMMARY.md) incorporated into roadmap.
- Phase 5.1 Complete: Protocol standardized across trackpy and cellpose, core parsers implemented.
- Phase 6 Complete: Scipy ndimage infrastructure established with metadata preservation and memory safety.
- Phase 7 Complete: IO patterns, zoom transforms, and Fourier workflow support implemented.
- Phase 8 Complete: Statistical Analysis foundation, wrappers, distributions, and comprehensive testing implemented.
- Phase 9 Plan 1 Complete: Spatial/Signal routing established.
- Stopped at: Completed 09-01-PLAN.md
- Resume file: None

## Next Steps
1. Execute 09-02-PLAN.md: Spatial distances + Voronoi/Delaunay wrappers.
2. Implement KDTree build/query wrappers (09-03).
