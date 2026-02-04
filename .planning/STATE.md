# Project State: Bioimage-MCP

## Project Reference

- **Core Value:** Empower AI agents to perform complex bioimage analysis via isolated, reproducible tool environments.
- **Current Milestone:** v0.5.0 Interactive Annotation
- **Current Goal:** Enable napari-based image annotation for µSAM segmentation.

## Current Position

- **Phase:** 21 - µSAM Tool Pack Foundation
- **Plan:** 2 of 4 in current phase
- **Status:** In progress
- **Last activity:** 2026-02-05 - Completed 21-02-PLAN.md

Progress: ███████████████████░ 97%

## Performance Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| V1 Req Coverage | 100% | 100% | ✅ |
| Test Coverage | >80% | 0% | ⚠️ |
| Tool Isolation | 100% | 100% | ✅ |

## Accumulated Context

### Decisions
- **Bridge over Build:** Reusing the existing `micro-sam` napari plugin instead of building a custom annotation UI.
- **Process Isolation:** Spawning napari in a managed subprocess to prevent event loop blocking.
- **Cache Priority:** SAM embeddings will be cached as hidden artifacts to enable instant session resume.
- **Conda Lock naming:** Used `micro_sam` (underscore) for conda-forge compatibility in foundation environment.

### Decisions Made (History)
| Phase | Decision | Rationale |
|-------|----------|-----------|
| 21 | Use micro_sam (underscore) for conda package | Matches conda-forge registry name. |
| 21 | Use vit_b variants as the minimum model requirement | Balances capability with download size/speed. |
| 20 | Designated representative PR tests (skimage, cellpose, trackpy) | Balances coverage with PR latency. |
| 20 | Demoted non-representative smoke tests to smoke_extended | Keeps the PR-gating tier lean and focused. |
| 15 | Use OME-Zarr as default save format in SkimageAdapter | Aligns with project-wide standardization. |

### Blockers
- None currently.

## Session Continuity

- **Last Session:** Created Roadmap for v0.5.0.
- **Next Step:** Plan Phase 21 (µSAM Tool Pack Foundation).
