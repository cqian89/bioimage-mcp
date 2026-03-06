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
- **Plans:** 3 plans

Plans:
- [x] 23-01-PLAN.md — Expose `micro_sam.sam_annotator.*` discovery with artifact-safe I/O pattern mapping
- [x] 23-02-PLAN.md — Implement interactive napari execution bridge, label export, and stable headless error handling
- [x] 23-03-PLAN.md — Add live smoke coverage and run blocking human GUI verification checkpoint
- **Status:** ✓ Complete
- **Progress:** 100%

### Phase 24: µSAM Session & Optimization
Optimize lifecycle of heavy model objects and large embeddings.

- **Goal:** Predictor caching and standardized embedding storage for low-latency workflows.
- **Plans:** 3 plans

Plans:
- [x] 24-01-PLAN.md — Implement session-scoped predictor/embedding cache contract with force-fresh and clear controls
- [x] 24-02-PLAN.md — Harden worker shutdown to guarantee interactive subprocess cleanup on server termination
- [ ] 24-03-PLAN.md — Add interactive resume and progress visibility with smoke + human verification
- **Status:** In progress
- **Progress:** 66%

| Phase | Description | Status | Progress |
|-------|-------------|--------|----------|
| 21 | µSAM Tool Pack Foundation | ✓ Complete | 100% |
| 22 | Headless API Integration | ✓ Complete | 100% |
| 23 | Interactive Bridge (Napari) | ✓ Complete | 100% |
| 24 | Session Management & Opt | In progress | 66% |


### Phase 25: Add missing TTTR methods

**Goal:** Reach near-full MCP-safe parity with the installed `tttrlib` runtime by expanding TTTR/CLSMImage/Correlator callable coverage and explicitly classifying unsupported methods.
**Requirements**: [TTTR-01, TTTR-02, TTTR-03, TTTR-04, TTTR-05]
**Depends on:** Phase 24
**Plans:** 8/8 plans complete

Plans:
- [x] 25-01-PLAN.md — Build runtime parity inventory and stable unsupported-method policy
- [x] 25-02-PLAN.md — Expand TTTR method families with guarded output and export mappings
- [x] 25-03-PLAN.md — Expand CLSMImage/Correlator method families and finalize live parity verification
- [x] 25-04-PLAN.md — Close TTTR getter/signature and specialized export UAT gaps
- [x] 25-05-PLAN.md — Close remaining CLSM settings and Correlator UAT gaps
- [x] 25-06-PLAN.md — Close core execution routing and selection-table import UAT gaps
- [x] 25-07-PLAN.md — Close TTTR export runtime contract gaps
- [x] 25-08-PLAN.md — Close CLSM metadata payload regression gaps

- **Status:** ✓ Complete
- **Progress:** 100%

---

*Roadmap updated: 2026-03-06*
