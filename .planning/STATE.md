# Project State

**Project:** Bioimage-MCP
**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current Focus:** Phase 5 - Trackpy Integration

## Overall Progress (86% complete)

- **Phase 1: Core Runtime** (100% complete) - **PHASE COMPLETE**
  - ✅ Conda isolation (`persistent.py`, `executor.py`)
  - ✅ NDJSON IPC (`worker_ipc.py`)
  - ✅ Process lifecycle (`PersistentWorkerManager`)
  - ✅ Unified GPU detection (NVIDIA CUDA + Apple Silicon MPS)

- **Phase 2: Tool Management** (100% complete) - **PHASE COMPLETE**
  - ✅ `doctor` command complete
  - ✅ `install` command refactored and extensible
  - ✅ `list` command implemented
  - ✅ `remove` CLI implemented

- **Phase 3: Data & Artifacts** (100% complete) - **PHASE COMPLETE**
  - ✅ File artifacts fully operational
  - ✅ `mem://` protocol implemented

- **Phase 4: Reproducibility** (100% complete) - **PHASE COMPLETE**
  - ✅ Session recording complete with provenance
  - ✅ `session_export` works
  - ✅ `session_replay` implemented with validation, resume, and error handling

- **Phase 5: Trackpy Integration** (66% complete) - **IN PROGRESS**
  - ✅ Environment determination (base vs. separate) (05-01)
  - ✅ Dynamic introspection for function signatures (05-02)
  - ✅ Full API coverage from trackpy v0.7 (05-02)
  - ⬜ Test data from trackpy repo/docs
  - ⬜ Live smoke test matching reference output

## Current Position

Phase: 5 of 5 (Trackpy Integration)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-01-23 - Completed 05-02-PLAN.md

Progress: ██████████ 93%

**Next Phase:** Phase 5 - Trackpy Integration (Plan 3)

## Context & Memory

### Key Decisions
- **Hub-and-Spoke Architecture**: Core server manages persistent worker processes for each tool environment.
- **NDJSON IPC**: Using NDJSON over stdio for reliable, language-agnostic communication.
- **Artifact-based I/O**: Core server handles metadata; tool packs read/write actual data via artifacts. No raw arrays in core.
- **SQLite Registry**: Using SQLite for tool registry and session persistence.
- **Dynamic Tool Discovery**: (Phase 2-02) Tools are discovered from `envs/bioimage-mcp-*.yaml` files, enabling easy addition of new tool packs.
- **Installation Profiles**: (Phase 2-02) Support for `cpu`, `gpu`, and `minimal` profiles to simplify environment setup.
- **Active Worker Safety**: (Phase 2-03) Tool removal is blocked if an active worker process is detected, preventing disruption of running sessions.
- **Base Environment Protection**: (Phase 2-03) The 'base' environment is protected from removal as it contains core server components.
- **Filesystem-over-Database Priority**: (Phase 2-04) The `list` command was refactored to read manifests directly from disk, ensuring consistency with `doctor` and avoiding reliance on a potentially stale SQLite registry.
- **Unified GPU Detection**: (Phase 1-01) Single 'gpu' check reports both CUDA and MPS status using dependency-free system probing.
- **Pre-execution Replay Validation**: (Phase 4-01) Validate parameter overrides against tool schemas before starting replay to fail fast on invalid inputs.
- **Environment & Version Pre-flight**: (Phase 4-02) Verify environment installation and warn about tool version mismatches before session replay, offering auto-install hints.
- **Replay Progress History**: (Phase 4-03) Include a complete step-by-step progress log in the final replay response to provide retrospective observability for AI agents.
- **Dry-run Workflow Preview**: (Phase 4-03) Support dry-run mode that validates all overrides and inputs, returning a 'pending' progress list to show the intended execution plan.
- **Ordinal-based Resume**: (Phase 4-04) Support resuming replays from a specific step, skipping already successful steps and restoring intermediate outputs.
- **Structured Missing Input Hints**: (Phase 4-04) Return structured error details with JSON Pointers for missing external inputs during replay.
- **Human-readable Error Summaries**: (Phase 4-04) Generate formatted error summaries in replay responses to make failures actionable for users and agents.
- **Out-of-process discovery**: (Phase 5-01) Decided to use a specialized `meta.list` command in the worker entrypoint to discover functions, as trackpy cannot be safely imported in the server's Python 3.13 process.
- **Dual-mode Worker Entrypoint**: (Phase 5-01) Entrypoint supports both legacy single-request JSON and persistent-worker NDJSON protocols for backward compatibility and performance.
- **Subprocess Discovery Fallback**: (Phase 5-02) The registry loader now automatically falls back to out-of-process discovery via the tool's entrypoint if the required adapter is missing or if in-process import fails.
- **TableRef for DataFrames**: (Phase 5-02) Trackpy results (features, trajectories) are serialized as CSV files and returned as `TableRef` artifacts to ensure cross-environment portability.

### Blockers
- None.

### Next Steps
- Implement TrackpyAdapter for dynamic introspection (05-02-PLAN.md)
- Research trackpy API and dependencies
- Determine environment strategy

### Roadmap Evolution
- Phase 5 added: Trackpy Integration - Integrate trackpy particle tracking library as a tool pack with full API coverage and live smoke tests

## Session Continuity

Last session: 2026-01-23T17:23:00Z
Stopped at: Completed 05-01-PLAN.md
Resume file: None
