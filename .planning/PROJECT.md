# Bioimage-MCP

## What This Is

Bioimage-MCP is a local Python package that exposes bioimage analysis tools to AI agents via the Model Context Protocol (MCP). It manages isolated conda environments for each tool to ensure reproducibility and dependency safety, allowing chatbots to interactively execute complex analysis workflows on local hardware.

## Core Value

Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.

## Current Milestone: v0.4.0 Unified Introspection Engine

**Goal:** Consolidate discovery/introspection into a single engine and align meta.describe schema output.

**Target features:**
- Shared introspection engine (AST-first + runtime fallback) replacing duplicate paths
- Unified params_schema emission (tool_version + introspection_source) with artifact separation
- Consolidated schema cache with strong invalidation (tool_version + env lock + engine version)
- Overlay/patch pipeline consolidation with diagnostics
- fn_id/module metadata cleanup with callable_fingerprint

## Current State

Shipped v0.3.0 Scipy Integration (2026-01-27) with dynamic adapters for `scipy.ndimage`, `scipy.stats`, `scipy.spatial`, and `scipy.signal`, plus metadata preservation and parity-grade testing.

## Next Milestone Goals

- Consolidate discovery/introspection into a single AST-first engine with runtime fallback.
- Align params_schema emission (tool_version + introspection_source) with artifact separation.
- Unify schema caching, overlays, and diagnostic reporting.

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

### Active

<!-- Current scope. Building toward these. -->

- [ ] **Unified Introspection Engine**: Single engine for discovery + meta.describe (v0.4.0)
- [ ] **Schema Emission Alignment**: params_schema pipeline with tool_version/introspection_source
- [ ] **Cache Consolidation**: Single schema cache with strong invalidation
- [ ] **Overlay/Patch Consolidation**: Unified patch pipeline with diagnostics
- [ ] **fn_id & Module Metadata Cleanup**: Full module paths + callable_fingerprint

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
