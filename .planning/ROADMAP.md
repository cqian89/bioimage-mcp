# Roadmap: Bioimage-MCP

## Milestones

- ✅ **v0.3.0 Scipy Integration** — Phases 5.1–10 (shipped 2026-01-27). Archive: `.planning/milestones/v0.3.0-ROADMAP.md`
- ✅ **v0.4.0 Unified Introspection Engine** — Phases 11–20 (shipped 2026-02-04). Archive: `.planning/milestones/v0.4.0-ROADMAP.md`
- 🚧 **v0.5.0 Interactive Annotation** — Phases 21–24 (In Progress)

### Phase 21: µSAM Tool Pack Foundation
Establish the isolated environment and prerequisite models for µSAM.

- **Goal:** The µSAM tool pack is installed and ready for local inference.
- **Progress:** 100%

### Phase 22: µSAM Headless API
Expose the `micro_sam` Python library API to MCP `run()` (all submodules except `micro_sam.sam_annotator`).

- **Goal:** Enable headless SAM segmentation (prompts, auto-mask) via MCP `run()`.
- **Key Submodules:** All `micro_sam.*` except `micro_sam.sam_annotator`.
- **Plans:** 4 plans

Plans:
- [x] 22-01-PLAN.md — Rename tool_id to tools.micro_sam and add persistent entrypoint + dynamic_sources
- [x] 22-02-PLAN.md — Implement MicrosamAdapter discovery (exclude sam_annotator) and register adapter
- [x] 22-03-PLAN.md — Implement headless execution + compute_embedding + ObjectRef reuse
- [x] 22-04-PLAN.md — Add live smoke tests for prompt and auto-mask segmentation
- **Status:** ✓ Complete
- **Progress:** 100%

### Phase 23: µSAM Interactive Bridge
Enable launching the `micro_sam` napari annotators from MCP.

- **Goal:** Launch GUI annotators with pre-loaded image artifacts and embeddings.
- **Status:** In progress
- **Progress:** 0%

### Phase 24: µSAM Session & Optimization
Optimize lifecycle of heavy model objects and large embeddings.

- **Goal:** Predictor caching and standardized embedding storage for low-latency workflows.
- **Status:** Pending
- **Progress:** 0%

| Phase | Description | Status | Progress |
|-------|-------------|--------|----------|
| 21 | µSAM Tool Pack Foundation | ✓ Complete | 100% |
| 22 | Headless API Integration | ✓ Complete | 100% |
| 23 | Interactive Bridge (Napari) | In progress | 0% |
| 24 | Session Management & Opt | Pending | 0% |

---

*Roadmap updated: 2026-02-05*
