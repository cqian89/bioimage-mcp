---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: milestone
status: in_progress
stopped_at: Completed 25-07-PLAN.md
last_updated: "2026-03-06T14:41:36.715Z"
last_activity: 2026-03-06 - Completed 25-07-PLAN.md
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 23
  completed_plans: 22
  percent: 98
---

# Project State: Bioimage-MCP

## Project Reference

- **Core Value:** Empower AI agents to perform complex bioimage analysis via isolated, reproducible tool environments.
- **Current Milestone:** v0.5.0 Interactive Annotation
- **Current Goal:** Enable napari-based image annotation for µSAM segmentation.

## Current Position

- **Phase:** 25 of 25 (Add missing TTTR methods)
- **Plan:** 7 of 8 in current phase
- **Status:** In Progress
- **Last activity:** 2026-03-06 - Completed 25-07-PLAN.md

Progress: [██████████] 99%

## Performance Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| V1 Req Coverage | 100% | 100% | ✅ |
| Test Coverage | >80% | 89% | ✅ |
| Tool Isolation | 100% | 100% | ✅ |
| Phase 25 P01 | 4 min | 2 tasks | 5 files |
| Phase 25 P02 | 15 min | 2 tasks | 7 files |
| Phase 25 P03 | 11 min | 2 tasks | 7 files |
| Phase 25 P04 | 17 min | 2 tasks | 8 files |
| Phase 25 P05 | 12 min | 2 tasks | 3 files |
| Phase 25 P06 | 10 min | 2 tasks | 5 files |
| Phase 25 P07 | 12 min | 2 tasks | 9 files |

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
- [Phase 25]: Expose TTTR selection wrappers with the live tttrlib input/time_window/n_ph_max signatures and keep unsupported branches rejected instead of silently broadening support.
- [Phase 25]: Persist get_tttr_by_selection outputs as file-backed TTTRRef artifacts under work_dir because core execution currently only registers TTTR outputs that include a path.
- [Phase 25]: Call specialized write_spc132_events/write_hht3v2_events with the explicit tttr object and keep positive SPC export coverage in smoke to guard the SWIG-specific signature.
- [Phase 25]: Serialize CLSMImage.get_settings by walking public CLSMSettings attributes and converting nested SWIG containers to JSON-safe values instead of relying on json default=str.
- [Phase 25]: Treat CorrelatorCurve as an object with x/y accessors and reuse a shared TableRef writer so constructor and getter outputs keep the same metadata contract.
- [Phase 25]: Route deferred and denied tttrlib IDs through the tttrlib manifest only for run() lookups by consulting coverage metadata in core.
- [Phase 25]: Preserve selection-table metadata by emitting metadata.columns/row_count from the worker and merging top-level table fields into execution import overrides.
- [Phase 25]: Handle one-column and header-only CSVs with deterministic header parsing instead of relying solely on csv.Sniffer().
- [Phase 25]: Remove write_header, write_hht3v2_events, and write_spc132_events from discovery because the live Python bindings are not filename-safe.
- [Phase 25]: Keep tttrlib.TTTR.write as a supported subset that must prove file creation before returning a TTTRRef.
- [Phase 25]: Use coverage metadata to preserve TTTRLIB_UNSUPPORTED_METHOD failures for removed export IDs without re-exposing them in the public surface.

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

- **Last Session:** 2026-03-06T14:41:36.692Z
- **Stopped at:** Completed 25-07-PLAN.md
- **Resume file:** None
