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

### Active

- [ ] **CLI Tool Manager**: Install/List/Remove tools via CLI (`bioimage-mcp install`).
- [ ] **Plugin System**: Support for external tool repositories/packages.
- [ ] **Workflow Recording**: Capture inputs/outputs for replay.
- [ ] **Interactive Mode**: Support tools asking users for input.
- [ ] **GPU Passthrough**: Configure environments to use local GPU.
- [ ] **Cross-platform Support**: CI/CD and testing for Linux/Mac/Win.

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
| **Hybrid Plugin Model** | Allows curated core tools + community extensions | — Pending |
| **Artifact I/O** | JSON is too slow/limited for images; pass paths | — Pending |
| **Native GPU** | Docker GPU support is complex for end-users | — Pending |
| **Interactive Mode** | Agents need human feedback for ambiguous analysis | — Pending |

---
*Last updated: Thu Jan 22 2026 after initialization*
