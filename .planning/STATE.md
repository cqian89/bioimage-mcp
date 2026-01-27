# Project State: Bioimage-MCP

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-27)

**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current focus:** v0.4.0 Unified Introspection Engine

## Current Position

Phase: 12 of 12 (Core Engine + AST-First)
Plan: 1 of 6 in current phase
Status: In progress
Last activity: 2026-01-27 — Completed 12-01-PLAN.md

Progress: █████████░ 90%

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
| 12 | Used griffe for zero-import static inspection | Avoids heavy tool-pack dependencies in core server. |
| 12 | sha256 source fingerprinting | Enables stable tracking of callable changes across runs. |
| 12 | Deterministic JSON Schema normalization | Ensures consistent schema emission for caching and comparison. |

### Roadmap Evolution
- Phase 12 added: Core Engine + AST-First

### Blockers/Concerns Carried Forward
- trackpy schema descriptions missing (contract test failure).
- base.phasorpy schema type mismatch (contract test failure).
- contract tests need to skip non-manifest YAMLs.

### Session Continuity
Last session: 2026-01-27T13:07:38Z
Stopped at: Completed 12-01-PLAN.md
Resume file: None

## Next Steps
1. Execute Plan 12-02: Runtime schema emission upgrade (TypeAdapter + docstrings).
