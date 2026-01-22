# Bioimage-MCP

## What This Is

Bioimage-MCP is a local Python package that exposes bioimage analysis tools to AI agents via the Model Context Protocol (MCP). It manages isolated conda environments for each tool to ensure reproducibility and dependency safety, allowing chatbots to interactively execute complex analysis workflows on local hardware.

## Core Value

Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.

## Requirements

### Validated

- ✓ Core server infrastructure (Python) — existing
- ✓ Basic tool definition structure (`tools/`) — existing
- ✓ Conda environment management (micromamba/conda) — existing
- ✓ **CLI Tool Manager (partial)**: Install and doctor commands work (`bioimage-mcp install`, `bioimage-mcp doctor`)
- ✓ **Workflow Recording**: Session recording with provenance capture implemented
- ✓ **Artifact-based I/O**: File and memory artifacts fully operational

### Active

- [ ] **CLI List/Remove**: `bioimage-mcp list` and `bioimage-mcp remove` not yet exposed
- [ ] **Extensible Install**: Install command hardcoded to base/cellpose; needs manifest-driven installation
- [ ] **Plugin System**: Support for external tool repositories/packages
- [ ] **Workflow Replay Validation**: session_replay implemented but needs validation before production use
- [ ] **Interactive Mode**: Support tools asking users for input during execution
- [ ] **GPU Passthrough (MPS)**: NVIDIA detection works; Apple Silicon MPS detection missing
- [ ] **Streaming Progress**: Real-time progress streaming (currently polling only)
- [ ] **Cross-platform CI/CD**: Testing for Linux/Mac/Win

### Out of Scope

- **Multi-user server** — v1 is local/single-user only.
- **Web Dashboard** — CLI is sufficient for v1.
- **Containerization (Docker)** — Conda provides sufficient isolation and better GPU UX.

## Context

Developing a "standard library" for bioimage AI. Building on top of the `mcp` Python SDK. The system must bridge the gap between heavy bioimage dependencies (which often conflict) and the lightweight JSON-based MCP interface.

## Constraints

- **Tech Stack**: Python 3.10+, Conda/Micromamba.
- **Platform**: Cross-platform (Linux, macOS, Windows).
- **Security**: Local execution, process isolation only (no sandbox).
- **Performance**: Must support native GPU acceleration (CUDA/MPS).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| **Hub-and-Spoke Architecture** | Persistent workers for performance | ✓ Implemented |
| **Artifact I/O** | JSON too slow for images; pass paths | ✓ Implemented |
| **Native GPU** | Docker GPU support complex for end-users | ⚠️ Partial (NVIDIA only) |
| **Interactive Mode** | Agents need human feedback | — Pending |
| **NDJSON over stdio** | Robust, streamable IPC | ✓ Implemented |
| **SQLite persistence** | Lightweight, file-based storage | ✓ Implemented |

---
*Last updated: Thu Jan 22 2026*
