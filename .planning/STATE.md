# Project State: Bioimage-MCP

## Project Reference

- **Core Value:** Empower AI agents to perform complex bioimage analysis via isolated, reproducible tool environments.
- **Current Milestone:** v0.5.0 Interactive Annotation
- **Current Goal:** Enable napari-based image annotation for µSAM segmentation.

## Current Position

- **Phase:** 21 of 24 (µSAM Tool Pack Foundation)
- **Plan:** Complete
- **Status:** Phase verified ✓
- **Last activity:** 2026-02-05 - Human verification passed, ready for Phase 22

Progress: ████████████████████ 100%

## Performance Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| V1 Req Coverage | 100% | 100% | ✅ |
| Test Coverage | >80% | 85% | ✅ |
| Tool Isolation | 100% | 100% | ✅ |

## Accumulated Context

### Decisions
- **Bridge over Build:** Reusing the existing `micro-sam` napari plugin instead of building a custom annotation UI.
- **Process Isolation:** Spawning napari in a managed subprocess to prevent event loop blocking.
- **Cache Priority:** SAM embeddings will be cached as hidden artifacts to enable instant session resume.
- **Conda Lock naming:** Used `micro_sam` (underscore) for conda-forge compatibility in foundation environment.
- **Tool-specific Config Wiring:** Use a dedicated `tool_config` payload in `execute_step` to pass tool-specific preferences (like `microsam.device`) without bloating the generic request schema.
- **Lazy Torch Imports:** Microsam tools import `torch` lazily during device selection to maintain fast discovery and capability detection in non-torch environments.

### Decisions Made (History)
| Phase | Decision | Rationale |
|-------|----------|-----------|
| 21 | Use tool_config for microsam.device | Keeps execution protocol lean while propagating user preferences to the isolated tool environment. |
| 21 | Strict device availability check | Fails fast with actionable errors if a forced accelerator (CUDA/MPS) is missing, but allows meta.describe to skip check. |
| 21 | Use StrEnum for MicrosamDevice | Ensures str(enum) returns the value string, satisfying validation and user-facing requirements. |
| 21 | Check for microsam models only if env is installed | Avoids noise in base-only installations; models are only required for microsam tools. |
| 21 | Use micro_sam (underscore) for conda package | Matches conda-forge registry name. |
| 21 | Use vit_b variants as the minimum model requirement | Balances capability with download size/speed. |
| 21 | Default microsam install to CPU profile if unspecified | Keeps default install lean and compatible. |
| 21 | Use pytorch-cuda=12.1 for Linux GPU installs of microsam | Aligns with modern microsam/torch requirements. |
| 20 | Designated representative PR tests (skimage, cellpose, trackpy) | Balances coverage with PR latency. |
| 20 | Demoted non-representative smoke tests to smoke_extended | Keeps the PR-gating tier lean and focused. |
| 15 | Use OME-Zarr as default save format in SkimageAdapter | Aligns with project-wide standardization. |

### Blockers
- None. (Phase 21 device-selection gap resolved in 21-05)

## Session Continuity

- **Last Session:** 2026-02-05 - Completed 21-05-PLAN.md
- **Stopped at:** Completed 21-05-PLAN.md
- **Resume file:** None
