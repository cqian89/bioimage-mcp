# Project State: Bioimage-MCP

## Project Reference
- **Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
- **Current Milestone:** v0.3.0 SciPy Integration (Verification)
- **Current Focus:** Adding guardrail smoke tests for datasets and discovery.

## Current Position
Phase: 10 of 10 (Verification & Smoke Testing)
Plan: 1 of 3 in current phase
Status: In progress
Last activity: 2026-01-27 - Completed 10-03-PLAN.md

Progress: █████████░ 92%

## Performance Metrics
- **Phase Coverage:** 10/10 phases in progress (9/10 completed)

## Accumulated Context

### Session Continuity
- Scipy integration (v0.3.0) is nearing completion.
- Phase 10 (Verification) is in progress.
- 10-03-PLAN.md completed: dataset guardrails and discovery verification tests added.

### Decisions Made
| Phase | Decision | Rationale |
|-------|----------|-----------|
| 8 | Curated Stats Wrappers | Exposing specific `*_table` wrappers instead of raw `scipy.stats` functions ensures reliable artifact I/O and easier agent consumption. |
| 8 | TABLE_PAIR_TO_JSON pattern | Introduced a specific I/O pattern for two-sample tests to simplify port mapping for t-tests and KS-tests. |
| 9 | Spatial/Signal Routing | Used prefix-based routing in ScipyAdapter to support submodules like scipy.spatial and scipy.signal without breaking ndimage/stats. |
| 9 | KDTree Lifecycle Patterns | Introduced TABLE_TO_OBJECT and OBJECT_AND_TABLE_TO_JSON to support stateful KDTree building and querying. |
| 9 | Direct SciPy API Mapping | Exposing direct `scipy.spatial` fn_ids (cdist, Voronoi) while wrapping execution logic to handle artifacts and coordinate selection. |
| 9 | KDTree Lifecycle Persistence | Used `obj://` URIs and `OBJECT_CACHE` to persist KDTree objects across tool calls, enabling efficient multi-query workflows. |
| 9 | String-to-Table Normalization | Centralized plain URI string normalization in `PandasAdapterForRegistry._load_table` to support flexible artifact passing across adapters. |
| 10 | Path-based discovery | Decided to use explicit path-based listing in discovery tests to handle non-recursive catalog structure. |

## Blockers/Concerns Carried Forward
- None.

## Next Steps
1. Execute 10-01-PLAN.md (live-server smoke test matrix).
2. Execute 10-02-PLAN.md (strict equivalence tests).
