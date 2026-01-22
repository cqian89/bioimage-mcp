# Project State

**Project:** Bioimage-MCP
**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current Focus:** Phase 2: Tool Management & CLI Completion

## Overall Progress (~78% complete)

- **Phase 1: Core Runtime** (~90% complete)
  - ✅ Conda isolation (`persistent.py`, `executor.py`)
  - ✅ NDJSON IPC (`worker_ipc.py`)
  - ✅ Process lifecycle (`PersistentWorkerManager`)
  - ⚠️ GPU detection partial (NVIDIA only, no MPS)

- **Phase 2: Tool Management** (100% complete) - **PHASE COMPLETE**
  - ✅ `doctor` command complete
  - ✅ `install` command refactored and extensible
  - ✅ `list` command implemented
  - ✅ `remove` CLI implemented

- **Phase 3: Data & Artifacts** (~95% complete)
  - ✅ File artifacts fully operational
  - ✅ `mem://` protocol implemented

- **Phase 4: Interactive Execution** (~40% partial)
  - ❌ User input during execution not implemented
  - ⚠️ Status polling exists, no streaming progress

- **Phase 5: Reproducibility** (~80% complete)
  - ✅ Session recording complete with provenance
  - ⚠️ `session_export` works
  - ⚠️ `session_replay` implemented but lacks validation

## Current Position

Phase: 2 of 5 (Tool Management)
Plan: 3 of 3 in current phase
Status: Phase complete
Last activity: 2026-01-22 - Completed 02-01-PLAN.md

Progress: ██████████ 100% (Phase 2)

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

### Blockers
- None.

### Next Steps
- Implement `bioimage-mcp list` (02-01-PLAN.md)

## Session Continuity

Last session: 2026-01-22T12:09:12Z
Stopped at: Completed 02-03-PLAN.md
Resume file: None
