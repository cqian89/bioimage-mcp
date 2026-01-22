# Feature Landscape

**Domain:** Bioimage Analysis MCP Server
**Researched:** 2026-01-22

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Environment Isolation** | Scientific tools have conflicting dependencies (e.g., different CUDA/PyTorch versions). | High | Solved via Conda envs. |
| **GPU Passthrough** | Deep learning tools (Cellpose, StarDist) require GPU. | Low | Implicit via env var inheritance. |
| **Progress Reporting** | Long-running tasks need feedback. | Medium | Needs async IPC updates. |
| **Cancellation** | Users change their minds; zombie processes are bad. | Medium | SIGTERM/SIGKILL management. |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Persistent Workers** | Eliminates 5-10s startup penalty per tool call. Makes interactive chat fluid. | High | Requires robust lifecycle management. |
| **Memory Artifacts** | `mem://` URIs avoid disk I/O for intermediate steps (e.g., smoothing -> thresholding). | High | Complex memory management/eviction logic. |
| **Dynamic Discovery** | Automatically exposes new library features without code changes. | Medium | Uses Python introspection. |

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Base64 Images in JSON** | Bloats context, hits token limits, slow. | Use Artifact References (`file://`, `mem://`). |
| **Monolithic Environment** | "Dependency Hell" guarantees breakage. | Use Isolated Environments. |
| **Custom Image Wrappers** | Reinventing the wheel, hard to maintain. | Use `bioio` for standard 5D arrays. |

## MVP Recommendation

For MVP, prioritize:
1.  **Subprocess Execution** (even if not fully persistent initially)
2.  **Artifact I/O** (File-based)
3.  **Manifest-based Discovery**

Defer to post-MVP:
-   Advanced Memory Management (spilling to disk)
-   Complex DAG execution engine (Pydra)
