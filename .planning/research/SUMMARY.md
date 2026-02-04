# Research Summary: Interactive Annotation

**Domain:** napari + µSAM Interactive Annotation
**Researched:** 2026-02-04
**Overall confidence:** HIGH

## Executive Summary

The v0.5.0 milestone aims to transition `bioimage-mcp` from a pure CLI/server tool to a "Human-in-the-loop" platform. Research indicates that `napari` with the **micro-sam plugin** is the current state-of-the-art for this workflow.

**Key architectural decision:** We are **reusing the existing micro-sam napari plugin** rather than building custom annotation UI. The plugin already provides point prompts, box prompts, scribble refinement, undo/redo, and 3D propagation. Our work focuses on:
1. Launching the plugin via MCP `run()` calls
2. Bridging MCP artifacts (OME-Zarr) to/from napari layers
3. Managing the subprocess lifecycle and embedding cache

The recommended approach is a **Process-Isolated Interactive Manager**. This architecture spawns napari with the micro-sam plugin in a managed subprocess, preventing server hangs and dependency conflicts.

## Key Findings

**Stack:** `napari` (0.5.5+) + `micro-sam` plugin (1.4.2+) + `PyTorch` (2.5.1+) in isolated conda environment.
**Architecture:** Parent-Child process model. Agent launches napari+plugin via MCP, plugin handles all annotation UI.
**Integration scope:** Artifact bridging (OME-Zarr ↔ napari layers), subprocess lifecycle, embedding cache.
**Not building:** Custom annotation UI, prompt handling, mask preview, undo/redo (all provided by plugin).
**Critical pitfall:** GPU VRAM exhaustion and event loop blocking in a headless-capable server environment.

## Implications for Roadmap

Based on research, the suggested phase structure for this milestone is:

1. **Phase 1: µSAM Tool Pack Foundation** - Rationale: Establish isolated environment with all dependencies.
   - Addresses: Conda environment, model download during install, device detection (CUDA/MPS/CPU).
   - Avoids: First-run download latency, dependency conflicts.

2. **Phase 2: Headless Tools** - Rationale: Verify SAM inference works before adding GUI complexity.
   - Addresses: `compute_embeddings`, `segment_automatic` (headless), embedding caching.
   - Avoids: Debugging inference issues through GUI layer.

3. **Phase 3: Interactive Bridge** - Rationale: Core integration work connecting MCP to micro-sam plugin.
   - Addresses: Launch napari+plugin via `run()`, artifact bridging (OME-Zarr ↔ layers), subprocess isolation.
   - Note: All annotation UI (prompts, preview, undo/redo) provided by plugin, not custom code.

4. **Phase 4: Session Management** - Rationale: Production-readiness and robustness.
   - Addresses: Orphan cleanup, session resume, progress indicators, headless detection.

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
