# Project Research Summary

**Project:** Bioimage-MCP
**Domain:** Bioimage Analysis / MCP Server
**Researched:** 2026-01-22
**Confidence:** HIGH

## Executive Summary

The `bioimage-mcp` project aims to build a robust, AI-driven Model Context Protocol (MCP) server specialized for bioimage analysis. Research confirms that the optimal architecture is a **Hub-and-Spoke model** with persistent subprocesses. This design decouples the lightweight core server (Python 3.13) from heavy, conflicting scientific environments (PyTorch, TensorFlow, etc.), ensuring stability and resolving the "dependency hell" endemic to this domain.

The recommended approach prioritizes **reproducibility and performance**. Key technical decisions include using `micromamba` for rapid environment management, `NDJSON` over standard streams for IPC, and a strict **Artifact-based I/O** strategy (using `bioio` and OME-TIFF/Zarr) to handle gigapixel images without serialization overhead. This setup allows the server to remain responsive while heavy analysis runs in isolated, GPU-enabled environments.

The most critical risks identified are **lifecycle management failures** (zombie processes) and **data boundary violations** (the "memory:// illusion"). Mitigation strategies heavily influence the roadmap, requiring robust process supervision (heartbeats, `atexit` handlers) and explicit data materialization protocols before implementing advanced features like memory artifacts.

## Key Findings

### Recommended Stack

**Summary:** The stack splits into a lightweight Core and heavy Worker environments. Python 3.13 is chosen for the Core for performance, while `micromamba` + `conda-lock` ensures reproducible environments for tools.

**Core technologies:**
- **Python 3.13**: Core Server Language — Latest stable with performance improvements; keeps core deps light.
- **Micromamba**: Package Manager — Significantly faster than Conda; essential for responsive user experience.
- **Subprocess + NDJSON**: Isolation & IPC — Standard, robust isolation without Docker overhead; NDJSON enables streaming.
- **bioio / OME-TIFF**: Data & I/O — Universal read/write for microscopy formats; avoids re-inventing I/O wrappers.

### Expected Features

**Must have (table stakes):**
- **Environment Isolation** — Users expect different tools (Cellpose vs. StarDist) to coexist without conflict.
- **GPU Passthrough** — Deep learning tools must access hardware acceleration transparently.
- **Progress Reporting** — Long-running bioimage tasks need feedback to the LLM/User.
- **Cancellation** — Ability to stop expensive zombie processes.

**Should have (competitive):**
- **Persistent Workers** — Eliminates 5-10s startup penalty per tool call; critical for chat flow.
- **Memory Artifacts (`mem://`)** — Avoids disk I/O for intermediate steps (e.g., smoothing -> thresholding).
- **Dynamic Discovery** — Automatically exposes new library features without code changes.

**Defer (v2+):**
- **Complex DAG execution engine** — Pydra/etc. add too much complexity for MVP.
- **Advanced Memory Management** — Spilling memory artifacts to disk.

### Architecture Approach

**Hub-and-Spoke with Persistent Subprocesses**: The Core acts as the MCP Server and Orchestrator, while "Spokes" (Workers) are isolated Python processes running specific environments.

**Major components:**
1. **Core / API** — Handles MCP protocol, session management, and routing.
2. **Runtime Manager** — Manages worker lifecycle (spawn, kill, heartbeat) and IPC.
3. **Worker Process** — Runs the actual tool code inside a specific Conda environment, bridging via a "Shim" entrypoint.
4. **Artifact Store** — Manages file/memory references to prevent passing large data over JSON.

### Critical Pitfalls

1. **Zombie Processes** — Workers staying alive after Core death. **Avoid:** Use `atexit` handlers, stdin polling, and heartbeats.
2. **The "Memory://" Illusion** — Assuming `mem://` is global. **Avoid:** Explicitly track ownership; auto-materialize to disk when crossing worker boundaries.
3. **Serialization Overhead** — Passing arrays in JSON. **Avoid:** Strict Artifact-based passing (pointers, not data).

## Implications for Roadmap

Based on research, the roadmap should prioritize infrastructure and isolation before tool integration.

### Phase 1: Core Architecture & IPC
**Rationale:** The Hub-and-Spoke model relies entirely on robust process management. Getting this wrong leads to the "Zombie" pitfall immediately.
**Delivers:** Core server shell, Runtime Manager, IPC protocol (NDJSON), and basic Process Spawning.
**Addresses:** Table stakes (Environment Isolation fundamentals).
**Avoids:** Zombie Processes (by implementing lifecycle management first).

### Phase 2: Artifacts & Data I/O
**Rationale:** Bioimage analysis is useless without data handling. We must solve "how to pass images" before running tools.
**Delivers:** Artifact Store, `bioio` integration, OME-TIFF/Zarr support, `mem://` vs `file://` abstraction.
**Uses:** `bioio`, `pydantic`.
**Avoids:** Serialization Overhead (by enforcing artifact passing early).

### Phase 3: Environment Management & Registry
**Rationale:** We need environments to run workers *in*.
**Delivers:** `micromamba` integration, Tool Registry, Manifest parsing, Conda env creation/verification.
**Uses:** `micromamba`, `conda-lock`.
**Implements:** Registry component.

### Phase 4: Worker Implementation & Tool Integration
**Rationale:** Now we have the core, data, and envs. We can build the actual workers.
**Delivers:** The "Shim" entrypoint script, persistent worker loop, integration of "Base" and "Cellpose" tool packs.
**Addresses:** GPU Passthrough, Persistent Workers.
**Avoids:** The "Memory://" Illusion (by implementing the boundary logic here).

### Phase 5: Advanced Control Flow
**Rationale:** Polish features that rely on a working system.
**Delivers:** Progress Reporting, Cancellation (SIGTERM/KILL logic), Dynamic Discovery.

### Phase Ordering Rationale

- **Infrastructure First:** We cannot build workers without the IPC and Process Manager (Phase 1).
- **Data Second:** We cannot run tools without a way to pass input/output data (Phase 2).
- **Envs Third:** We cannot spawn specific workers without the Registry and Envs (Phase 3).
- **Integration Fourth:** Bringing it all together.

### Research Flags

**Needs Research:**
- **Phase 2 (Artifacts):** Exact `bioio` API compatibility with `mem://` buffers needs verification.
- **Phase 5 (Cancellation):** Windows vs. Linux signal handling for subprocesses can be tricky.

**Standard Patterns (Skip Research):**
- **Phase 1 (IPC):** NDJSON over Stdin/Stdout is a standard pattern.
- **Phase 3 (Micromamba):** CLI usage is well-documented.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Validated against existing `bioimage-mcp` code and industry standards. |
| Features | HIGH | Clear distinction between table stakes and differentiators. |
| Architecture | HIGH | Hub-and-Spoke is the standard solution for Python dependency isolation. |
| Pitfalls | HIGH | Specific, actionable warnings derived from domain experience. |

**Overall confidence:** HIGH

### Gaps to Address

- **Windows Path Handling:** While identified as a pitfall, specific testing on Windows CI/CD pipelines is a gap to address during Phase 3/4 implementation.
- **Memory Eviction:** The research mentions "Complex memory management" as a deferral, but basic eviction for `mem://` in long sessions might be needed sooner.

## Sources

### Primary (HIGH confidence)
- **Existing `bioimage-mcp` Codebase** — Verified architectural patterns.
- **MicroscopyLM** — validated architectural patterns.

### Secondary (MEDIUM confidence)
- **Community Consensus** — Use of Conda/Micromamba in scientific computing.

---
*Research completed: 2026-01-22*
*Ready for roadmap: yes*
