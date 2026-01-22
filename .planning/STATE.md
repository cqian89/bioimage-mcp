# Project State

**Project:** Bioimage-MCP
**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current Focus:** Milestone Complete

## Overall Progress (100% complete)

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

## Current Position

Phase: 4 of 4 (Reproducibility)
Plan: 4 of 4 in current phase
Status: Phase complete
Last activity: 2026-01-22 - Completed 04-04-PLAN.md (Resume Capability & Error Handling)

Progress: ██████████ 100%

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

### Blockers
- None.

### Next Steps
- Finalize documentation and prepare for release.

## Session Continuity

Last session: 2026-01-22T18:22:00Z
Stopped at: Completed 04-04-PLAN.md
Resume file: None
