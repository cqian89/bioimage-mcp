# Project State: Bioimage-MCP

## Project Reference
- **Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
- **Current Milestone:** v0.3.0 Scipy Integration
- **Current Focus:** Phase 9 (Spatial & Signal Processing)

## Current Position
- **Phase:** 9
- **Plan:** 3 of 4 in current phase
- **Status:** In progress
- **Last activity:** 2026-01-26 - Completed 09-03-PLAN.md
- **Next Phase:** 11

Progress: ██████████████████████████ 95%

## Performance Metrics
- **Phase Coverage:** 9/11 phases completed (including 5.1)
...
| 8 | Curated Stats Wrappers | Exposing specific `*_table` wrappers instead of raw `scipy.stats` functions ensures reliable artifact I/O and easier agent consumption. |
| 8 | TABLE_PAIR_TO_JSON pattern | Introduced a specific I/O pattern for two-sample tests to simplify port mapping for t-tests and KS-tests. |
| 9 | Spatial/Signal Routing | Used prefix-based routing in ScipyAdapter to support submodules like scipy.spatial and scipy.signal without breaking ndimage/stats. |
| 9 | KDTree Lifecycle Patterns | Introduced TABLE_TO_OBJECT and OBJECT_AND_TABLE_TO_JSON to support stateful KDTree building and querying. |
| 9 | Direct SciPy API Mapping | Exposing direct `scipy.spatial` fn_ids (cdist, Voronoi) while wrapping execution logic to handle artifacts and coordinate selection. |
| 9 | KDTree Lifecycle Persistence | Used `obj://` URIs and `OBJECT_CACHE` to persist KDTree objects across tool calls, enabling efficient multi-query workflows. |

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
- Phase 9 Plan 1, 2, 3, 4 Complete: Spatial/Signal routing, distances, tessellations, KDTree, and signal processing implemented.
- Stopped at: Completed 09-03-PLAN.md
- Resume file: None

## Next Steps
1. Transition to Phase 10: Verification & Smoke Testing.
