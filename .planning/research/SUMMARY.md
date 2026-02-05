# Research Summary: micro_sam Integration (API + Annotators)

**Domain:** `micro_sam` Python API exposure + napari annotators
**Researched:** 2026-02-04 (updated 2026-02-05)
**Overall confidence:** HIGH

## Executive Summary

The v0.5.0 milestone integrates upstream `micro_sam` into `bioimage-mcp` in two layers:

1. **API-first exposure (Phase 22):** expose the `micro_sam` Python library API (organized by submodule) to MCP `run()` with stable IDs of the form `micro_sam.<submodule>.<callable>`, excluding only `micro_sam.sam_annotator`.
2. **Interactive bridge (Phase 23):** reuse the existing `micro_sam` napari annotators instead of building custom UI; bridge MCP artifacts to/from napari layers.

Across both phases, parameter schemas should be generated via the unified introspection engine (`Introspector`) using AST + docstring parsing, as done for existing tool packs.

For the interactive layer, the recommended operational approach remains a **process-isolated interactive manager** (napari launched in a managed subprocess) to avoid event-loop coupling and dependency conflicts.

## Key Findings

**Stack:** `micro_sam` in isolated conda env (`bioimage-mcp-microsam`) with `napari` available for Phase 23.
**API exposure:** Prefer library API callables over CLI entrypoints; CLI schemas are harder to derive reliably via AST/docstring parsing.
**Artifact boundary:** Predictor/state objects should travel via `ObjectRef`; image inputs/outputs should be `BioImageRef`/`LabelImageRef` where feasible.
**Critical pitfall (interactive):** GPU VRAM exhaustion and event loop blocking if napari runs in-process; prefer subprocess isolation.

## Implications for Roadmap

The adjusted phase structure for this milestone is:

1. Phase 21: Tool pack foundation (env + model/device bootstrap)
2. Phase 22: Headless API exposure (all `micro_sam.*` except `micro_sam.sam_annotator`)
3. Phase 23: Annotator exposure + artifact bridge (`micro_sam.sam_annotator`)
4. Phase 24: Caching/state artifacts + end-to-end verification

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
