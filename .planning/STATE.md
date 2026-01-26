# Project State: Bioimage-MCP

## Project Reference
- **Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
- **Current Milestone:** v0.3.0 Scipy Integration
- **Current Focus:** Phase 7 (Transforms & Measurements)

## Current Position
- **Phase:** 8
- **Plan:** 1 of 3 in current phase
- **Status:** In progress
- **Last activity:** 2026-01-26 - Completed 08-01-PLAN.md

Progress: ████████████████████░░░░░░ 78%

## Performance Metrics
- **Phase Coverage:** 9/11 phases completed (including 5.1)
...
| 7 | Multi-output naming convention | Standardized on `labels.ome.tiff` and `counts.json` for `label()` to ensure stable filenames under a provided `work_dir`. |
| 7 | Key-by-ID measurement payload | Using label ID strings as keys (e.g., `{"1": [y, x]}`) provides the most unambiguous representation for AI agents and downstream logic. |
| 8 | Composite Scipy Adapter | Using a dispatcher allows clean separation of concerns between image processing (`ndimage`) and statistics (`stats`) while maintaining a single registry entry. |
| 8 | Inheritance for Stats Adapter | `ScipyStatsAdapter` inherits from `ScipyNdimageAdapter` to reuse robust artifact loading and JSON serialization logic. |
| 8 | Native JSON Serialization | Statistical results are returned as `ScalarRef` (JSON) to allow easy consumption by AI agents and downstream logic. |

### Session Continuity
- v0.2.0 "Foundation" complete (Phases 1-5).
- Scipy research (SUMMARY.md) incorporated into roadmap.
- Phase 5.1 Complete: Protocol standardized across trackpy and cellpose, core parsers implemented.
- Phase 6 Complete: Scipy ndimage infrastructure established with metadata preservation and memory safety.
- Phase 7 Complete: IO patterns, zoom transforms, and Fourier workflow support implemented.
- Phase 8 Plan 1 Complete: Statistical Analysis foundation with composite adapter and stats discovery.
- Stopped at: Completed 08-01-PLAN.md
- Resume file: None

## Next Steps
1. Execute 07-04-PLAN.md: Add complex Fourier artifact support + expose scipy.fft

