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
- ✓ **CLI Tool Manager**: Full suite (`install`, `list`, `remove`, `doctor`) — v0.2.0
- ✓ **Workflow Recording**: Session recording with provenance capture — v0.2.0
- ✓ **Artifact-based I/O**: File and memory artifacts fully operational — v0.2.0
- ✓ **Workflow Replay**: Validated export and replay engine — v0.2.0
- ✓ **GPU Passthrough**: NVIDIA (CUDA) and Apple Silicon (MPS) detection — v0.2.0
- ✓ **Trackpy Integration**: First major tool pack with dynamic introspection — v0.2.0

### Active

- [ ] **Interactive Mode**: Support tools asking users for input during execution (INTR-01)
- [ ] **Streaming Progress**: Real-time progress streaming (INTR-02)
- [ ] **Plugin System**: Support for external tool repositories/packages (ECO-02)
- [ ] **Cross-platform CI/CD**: Testing for Linux/Mac/Win

### Out of Scope

- **Multi-user server** — v1 is local/single-user only.
- **Web Dashboard** — CLI is sufficient for v1.
- **Containerization (Docker)** — Conda provides sufficient isolation and better GPU UX.

## Context

Shipped v0.2.0 "Foundation" with ~28k LOC Python.
Tech stack: Python 3.10+, Conda, MCP.
Key capabilities: Hub-and-spoke isolation, zero-copy artifacts, reproducible workflows.
First integration: Trackpy (v0.7).
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
*Last updated: 2026-01-25 after v0.2.0 milestone*
