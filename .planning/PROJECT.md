# Bioimage-MCP

## What This Is

Bioimage-MCP is a local Python package that exposes bioimage analysis tools to AI agents via the Model Context Protocol (MCP). It manages isolated conda environments for each tool to ensure reproducibility and dependency safety, allowing chatbots to interactively execute complex analysis workflows on local hardware.

## Core Value

Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.

## Current Milestone: v0.5.0 TBD (Planned after v0.4.0)

**Goal:** TBD (Run /gsd-new-milestone to define)

**Target features:**
- TBD

## Current State

Shipped v0.4.0 Unified Introspection Engine (2026-02-04) featuring AST-first discovery, OME-Zarr standardization, multimodal artifact previews, StarDist integration, and automated storage management.

## Next Milestone Goals

- TBD

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
- ✓ **Scipy Integration**: ndimage/stats/spatial/signal adapters with parity testing — v0.3.0
- ✓ **Unified Introspection Engine**: AST-first discovery with isolated runtime fallback — v0.4.0
- ✓ **OME-Zarr Standardization**: Standardized interchange format with directory support — v0.4.0
- ✓ **Multimodal Previews**: Image, Table, and Label previews in artifact_info — v0.4.0
- ✓ **StarDist Integration**: Isolated inference pipeline for StarDist — v0.4.0
- ✓ **Artifact Retention**: Automated storage quota and retention management — v0.4.0

### Active

<!-- Current scope. Building toward these. -->

- [ ] TBD

### Out of Scope

- **Multi-user server** — v1 is local/single-user only.
- **Web Dashboard** — CLI is sufficient for v1.
- **Containerization (Docker)** — Conda provides sufficient isolation and better GPU UX.

## Context

Shipped v0.3.0 "Scipy Integration" with ~81k LOC Python.
Tech stack: Python 3.10+, Conda, MCP.
Key capabilities: Hub-and-spoke isolation, zero-copy artifacts, reproducible workflows.
Integrations: Trackpy (v0.7), Scipy (ndimage/stats/spatial/signal).
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
| **Discovery Protocol Standardization** | Align meta.list/meta.describe across tool packs | ✓ Implemented (v0.3.0) |
| **NativeOutputRef for stats JSON** | Stable structured payloads for stats outputs | ✓ Implemented (v0.3.0) |
| **Automatic float32 promotion** | Prevent uint16 overflow, ensure parity | ✓ Implemented (v0.3.0) |

---
*Last updated: 2026-01-27 after v0.3.0 milestone completion*
