---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: milestone
status: completed
stopped_at: Completed 25-03-PLAN.md
last_updated: "2026-03-05T15:15:24.696Z"
last_activity: 2026-03-05 - Completed 25-03-PLAN.md
progress:
  total_phases: 6
  completed_phases: 5
  total_plans: 18
  completed_plans: 18
  percent: 100
---

# Project State: Bioimage-MCP

## Project Reference

- **Core Value:** Empower AI agents to perform complex bioimage analysis via isolated, reproducible tool environments.
- **Current Milestone:** v0.5.0 Interactive Annotation
- **Current Goal:** Enable napari-based image annotation for µSAM segmentation.

## Current Position

- **Phase:** 25 of 25 (Add missing TTTR methods)
- **Plan:** 3 of 3 in current phase
- **Status:** Milestone complete
- **Last activity:** 2026-03-05 - Completed 25-03-PLAN.md

Progress: [██████████] 100%

## Performance Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| V1 Req Coverage | 100% | 100% | ✅ |
| Test Coverage | >80% | 89% | ✅ |
| Tool Isolation | 100% | 100% | ✅ |
| Phase 25 P01 | 4 min | 2 tasks | 5 files |
| Phase 25 P02 | 15 min | 2 tasks | 7 files |
| Phase 25 P03 | 11 min | 2 tasks | 7 files |

## Accumulated Context

### Decisions
- **Bridge over Build:** Reusing the existing `micro-sam` napari plugin instead of building a custom annotation UI.
- **Process Isolation:** Spawning napari in a managed subprocess to prevent event loop blocking.
- **Cache Priority:** SAM embeddings will be cached as hidden artifacts to enable instant session resume.
- **Conda Lock naming:** Used `micro_sam` (underscore) for conda-forge compatibility in foundation environment.
- **Tool-specific Config Wiring:** Use a dedicated `tool_config` payload in `execute_step` to pass tool-specific preferences (like `microsam.device`) without bloating the generic request schema.
- **Lazy Torch Imports:** Microsam tools import `torch` lazily during device selection to maintain fast discovery and capability detection in non-torch environments.
- **Library-Tool Alignment:** Decided to rename `tools.microsam` to `tools.micro_sam` to better match the upstream library name `micro_sam`.
- **Hybrid SAM Discovery:** Relaxed re-export restrictions in `MicrosamAdapter` to ensure critical segmentation functions (often re-exported from `torch_em`) are exposed to the API.
- **SAM-specific I/O Patterns:** Introduced `SAM_PROMPT` and `SAM_AMG` patterns to handle different input requirements for SAM-based tools.
- **Side-channel Warnings:** Use `adapter.warnings` for propagating interactive warnings (like `MICROSAM_NO_CHANGES`) through the `BaseAdapter.execute` protocol.
- **Explicit Annotator Denylist:** Only main annotator entrypoints are supported for interactive bridge; others remain denylisted to ensure stable I/O.
- **Deterministic Cache Keying:** Use a composite key of `image_uri + model_type` for session-scoped predictor reuse.
- **Cache Status Visibility:** Emit machine-readable cache status warnings (HIT/MISS/RESET) for transparent performance monitoring.
- **Progressive Shutdown Escalation:** Ensure worker shutdown always converges using progressive escalation (graceful -> timeout -> force-kill).
- **Deadlock-safe IPC ACK:** Use timeouts for NDJSON IPC ACKs during shutdown to prevent deadlocks on blocked stdout/stderr pipes.
- [Phase 25]: Use strict upstream IDs (tttrlib.Class.method) in the coverage registry to prevent alias drift.
- [Phase 25]: Run unsupported-method checks before handler dispatch so denied/deferred IDs are deterministic and explicit.
- [Phase 25]: Mapped scalar TTTR statistics to NativeOutputRef and tabular traces/selections to TableRef outputs.
- [Phase 25]: Selection APIs remain supported_subset with explicit allowlists and TTTRLIB_UNSUPPORTED_ARGUMENT_PATTERN failures for unsupported patterns.
- [Phase 25]: TTTR write-family handlers now enforce work_dir path boundaries with format-specific extension checks for specialized exports.
- [Phase 25]: Classified Correlator getter-family methods as supported_subset with constrained constructor arguments.
- [Phase 25]: Exposed CLSMImage metadata accessors via NativeOutputRef JSON artifacts to preserve artifact boundaries.
- [Phase 25]: Linked parity closure to smoke_extended representative method IDs in contract tests.

### Roadmap Evolution
- Phase 25 added: Add missing TTTR methods

### Decisions Made (History)
| Phase | Decision | Rationale |
|-------|----------|-----------|
| 24 | Keepalive Heartbeat | Prevents client-side timeouts during long-running interactive sessions by sending periodic progress notifications. |
| 24 | Thread-safe SQLite | Enabled `check_same_thread=False` to support concurrent status monitoring from async worker threads. |
| 24 | Progressive Shutdown Escalation | Guarantees deterministic cleanup of interactive subprocesses even when GUI runtimes block IPC. |
| 24 | Deadlock-safe IPC ACK | Prevents the MCP server from hanging indefinitely during shutdown when worker pipes are saturated. |
| 24 | Deterministic Cache Keying | Prevents incorrect predictor reuse when model types differ for the same image. |
| 24 | Cache Status Visibility | Enables agents to monitor and optimize workflow latency via structured feedback. |
| 23 | Preserved stable error codes in tool entrypoint | Enables deterministic headless testing and better UX across conda boundary. |
| 23 | Forced headless mode support | Added BIOIMAGE_MCP_FORCE_HEADLESS env var to enable reliable simulation of headless Linux in desktop sessions (WSLg). |
| 23 | Side-channel Warnings | Enables propagating interactive metadata through a protocol that only returns artifacts. |
| 23 | Explicit Annotator Denylist | Avoids ambiguous runtime failures by only supporting known-stable annotator entrypoints in the bridge. |
| 23 | Artifact-Port Discovery for sam_annotator | Classifying annotator entrypoints as SAM_ANNOTATOR enables specialized interactive execution logic while maintaining artifact boundary contracts. |
| 22 | Specialized SAM Patterns | SAM functions have specific optionality for predictor/image ports that standard patterns didn't cover. |
| 22 | Relaxed Re-export Discovery | micro_sam re-exports many core functions from torch_em; strict discovery was excluding them. |
| 22 | Renamed tool_id to tools.micro_sam | Aligns tool ID with upstream library name micro_sam for cleaner mapping. |
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
- None.

## Session Continuity

- **Last Session:** 2026-03-05T14:58:29.950Z
- **Stopped at:** Completed 25-03-PLAN.md
- **Resume file:** None
