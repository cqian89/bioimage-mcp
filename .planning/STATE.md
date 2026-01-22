# Project State

**Project:** Bioimage-MCP
**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current Focus:** Phase 1 & 2 Cleanup

## Overall Progress (~95% complete)

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

- **Phase 3: Data & Artifacts** (~95% complete)
  - ✅ File artifacts fully operational
  - ✅ `mem://` protocol implemented

- **Phase 4: Reproducibility** (~80% complete)
  - ✅ Session recording complete with provenance
  - ⚠️ `session_export` works
  - ⚠️ `session_replay` implemented but lacks validation

## Current Position

Phase: 1 of 4 (Core Runtime)
Plan: 1 of 1 in current phase
Status: Phase complete
Last activity: 2026-01-22 - Completed 01-01-PLAN.md (MPS Detection)

Progress: ██████████ 100% (Phases 1 & 2)

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

### Blockers
- None.

### Next Steps
- Plan and execute Phase 4: Reproducibility (Validation & Production-readiness)

## Session Continuity

Last session: 2026-01-22T13:15:00Z
Stopped at: Completed 01-01-PLAN.md
Resume file: None
