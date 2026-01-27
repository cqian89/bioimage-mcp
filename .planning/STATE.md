# Project State: Bioimage-MCP

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-27)

**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current focus:** v0.4.0 Unified Introspection Engine

## Current Position

Phase: 11 of 11+ (Discovery Gap Closure)
Plan: Not started
Status: Ready to plan
Last activity: 2026-01-27 — v0.3.0 milestone complete

Progress: ░░░░░░░░░░ 0%

## Accumulated Context

### Decisions Made
| Phase | Decision | Rationale |
|-------|----------|-----------|
| 10 | Use 'datasets/smoke_tmp' for test CSVs | Ensure live server read access within allowed paths. |
| 10 | Map mean_table to tmean | scipy.stats lacks a bare mean function. |
| 10 | Standardize on NativeOutputRef for stats JSON | Allows flexible structured output for distribution/summary stats. |
| 10 | Automatic Float32 Promotion | Ensures precision parity for filters/transforms on uint16 inputs. |
| 10 | Stable JSON Contract | Facilitates strict comparison of statistical test outputs. |
| 11 | Audit Gap Cleanup | Address descriptions and schema types identified in v0.3.0 audit. |

### Blockers/Concerns Carried Forward
- trackpy schema descriptions missing (contract test failure).
- base.phasorpy schema type mismatch (contract test failure).
- contract tests need to skip non-manifest YAMLs.

### Session Continuity
Last session: 2026-01-27T14:00:00Z
Stopped at: v0.3.0 Audited & Shipped; transitioning to v0.4.0.
Resume file: None

## Next Steps
1. Execute Phase 11: Fix scipy.stats dynamic discovery and adapter gaps.
2. Address contract test regressions identified in v0.3.0 audit.
