# Project State

**Project:** Bioimage-MCP
**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current Focus:** Phase 2: Tool Management & CLI Completion

## Overall Progress (~75% complete)

- **Phase 1: Core Runtime** (~90% complete)
  - ✅ Conda isolation (`persistent.py`, `executor.py`)
  - ✅ NDJSON IPC (`worker_ipc.py`)
  - ✅ Process lifecycle (`PersistentWorkerManager`)
  - ⚠️ GPU detection partial (NVIDIA only, no MPS)

- **Phase 2: Tool Management** (~60% complete) - **CURRENT FOCUS**
  - ✅ `doctor` command complete
  - ⚠️ `install` command exists but hardcoded to base/cellpose
  - ❌ `list` CLI not exposed (API exists)
  - ❌ `remove` CLI not implemented

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

## Immediate Plan

1. **Complete Phase 2 CLI gaps**: Expose `list` and implement `remove` commands.
2. **Refactor `install`**: Make the command extensible and not hardcoded to specific tool packs.
3. **Enhance GPU detection**: Add MPS support for Apple Silicon.
4. **Stabilize Reproducibility**: Validate and harden `session_replay` for production use.

## Context & Memory

### Key Decisions
- **Hub-and-Spoke Architecture**: Core server manages persistent worker processes for each tool environment.
- **NDJSON IPC**: Using NDJSON over stdio for reliable, language-agnostic communication.
- **Artifact-based I/O**: Core server handles metadata; tool packs read/write actual data via artifacts. No raw arrays in core.
- **SQLite Registry**: Using SQLite for tool registry and session persistence.

### Blockers
- None.

### Next Steps
- Implement `bioimage-mcp list` and `bioimage-mcp remove` CLI commands.
