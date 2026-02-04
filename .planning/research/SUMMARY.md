# Research Summary: Interactive Annotation

**Domain:** napari + µSAM Interactive Annotation
**Researched:** 2026-02-04
**Overall confidence:** HIGH

## Executive Summary

The v0.5.0 milestone aims to transition `bioimage-mcp` from a pure CLI/server tool to a "Human-in-the-loop" platform. Research indicates that `napari` integrated with `micro-sam` (µSAM) is the current state-of-the-art for this workflow. The primary technical challenge is the integration of a blocking Desktop GUI (Qt) with a non-blocking MCP server (asyncio).

The recommended approach is a **Process-Isolated Interactive Manager**. This architecture spawns the napari viewer in a managed subprocess, preventing server hangs and dependency conflicts. User interaction is centered around SAM-based prompting, which provides high-accuracy segmentation with minimal manual effort.

## Key Findings

**Stack:** `napari` (0.5.5+) + `micro-sam` (1.4.2+) + `PyTorch` (2.5.1+) running in an isolated conda environment.
**Architecture:** Parent-Child process model with file-based artifact bridging (OME-Zarr).
**Critical pitfall:** GPU VRAM exhaustion and event loop blocking in a headless-capable server environment.

## Implications for Roadmap

Based on research, the suggested phase structure for this milestone is:

1. **Phase 1: Isolated Interactive Runtime** - Rationale: Establishing the hub-and-spoke architecture for the interactive tool pack is the highest technical risk.
   - Addresses: Subprocess management, `napari` environment isolation, and artifact-to-viewer bridging.
   - Avoids: Server-side event loop blocking and dependency bloat.

2. **Phase 2: µSAM Inference Pipeline** - Rationale: Delivering the core segmentation capability.
   - Addresses: Embedding precomputation, specialist model selection (LM/EM), and point/box prompt processing.
   - Avoids: GPU out-of-memory (OOM) by enforcing model size limits.

3. **Phase 3: Human-in-the-loop Bridge** - Rationale: Closing the loop between manual refinement and automated artifacts.
   - Addresses: "Commit" button logic, OME-Zarr persistence, and "Scribble-to-Point" conversion.
   - Avoids: Manual data loss and synchronization drift.

4. **Phase 4: Advanced Annotations & Tracking** - Rationale: Enhancing the UX with specialized features.
   - Addresses: 3D volume propagation and integration with `trackastra` for temporal annotation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | `micro-sam` 1.4.2 is stable; `PyTorch` 2.5 provides optimal support for current GPUs. |
| Features | HIGH | Table-stakes features are well-implemented in the `micro-sam` plugin ecosystem. |
| Architecture | MEDIUM | Cross-platform subprocess management (WSL2/macOS) requires careful implementation. |
| Pitfalls | HIGH | VRAM management and headless detection are known bottlenecks. |

## Gaps to Address

- **Remote-Desktop / Cloud:** This research assumes a local GUI. Research into web-based fallbacks (e.g., `napari-canvas` or `vizarr`) may be needed if cloud deployment is prioritized.
- **Multi-user VRAM:** No standard strategy exists for sharing a single GPU across multiple concurrent interactive napari sessions on one server.

---
*Research completed: 2026-02-04*
*Ready for roadmap: yes*
