# Roadmap: Bioimage-MCP

## Milestones

- ✅ **v0.3.0 Scipy Integration** — Phases 5.1–10 (shipped 2026-01-27). Archive: `.planning/milestones/v0.3.0-ROADMAP.md`
- ✅ **v0.4.0 Unified Introspection Engine** — Phases 11–20 (shipped 2026-02-04). Archive: `.planning/milestones/v0.4.0-ROADMAP.md`
- 🚧 **v0.5.0 Interactive Annotation** — Phases 21–24 (In Progress)

---

# Milestone: v0.5.0 Interactive Annotation

This milestone enables "Human-in-the-loop" bioimage analysis by bridging the MCP server with the `napari` ecosystem. We leverage the existing `micro-sam` plugin to provide state-of-the-art interactive segmentation (point prompts, scribbles, 3D propagation) while managing the infrastructure, artifact bridging, and subprocess isolation required for a seamless agent-assisted workflow.

## Summary

- **Goal:** Enable napari-based image annotation workflows for µSAM segmentation
- **Phases:** 4 (21-24)
- **Coverage:** 22/22 v1 requirements mapped

## Phases

### Phase 21: µSAM Tool Pack Foundation
Establish the isolated environment and prerequisite models for µSAM.

- **Goal:** The µSAM tool pack is installed and ready for local inference.
- **Dependencies:** None
- **Requirements:** USAM-01, USAM-05, USAM-06, INFRA-05
- **Success Criteria:**
  1. `bioimage-mcp install --profile usam` completes successfully on Linux/macOS.
  2. Specialist SAM models (LM, EM, Generalist) are present in local cache after installation.
  3. Tool execution automatically selects the fastest available device (CUDA > MPS > CPU).

### Phase 22: Headless Tools
Implement the non-interactive core of SAM to verify inference before adding GUI complexity.

- **Goal:** Users can run SAM segmentation workflows via headless MCP tools.
- **Dependencies:** Phase 21
- **Requirements:** USAM-03, USAM-04, INFRA-04, SESS-04
- **Success Criteria:**
  1. User can run `compute_embeddings` on an OME-Zarr image and see progress in the terminal.
  2. User can run `segment_automatic` and receive a new OME-Zarr artifact containing labels.
  3. Running interactive tools on a headless server returns a graceful "GUI not available" error.

### Phase 23: Interactive Bridge
Build the parent-child process model to launch and communicate with the napari µSAM plugin.

- **Goal:** Users can interactively segment images using the napari µSAM plugin via MCP.
- **Dependencies:** Phase 22
- **Requirements:** INFRA-01, INFRA-02, INFRA-03, USAM-02, ANNOT-01, ANNOT-02, ANNOT-03, ANNOT-04, ANNOT-05, ANNOT-06, ANNOT-07
- **Success Criteria:**
  1. Agent launches napari with µSAM plugin; user sees their image pre-loaded.
  2. User adds point prompts/scribbles and sees the mask update in real-time.
  3. User clicks "Commit" or closes the viewer, and results are saved as a new MCP artifact.

### Phase 24: Session Management
Ensure robustness, session persistence, and resource cleanup.

- **Goal:** Interactive sessions are robust, resumable, and clean up after themselves.
- **Dependencies:** Phase 23
- **Requirements:** SESS-01, SESS-02, SESS-03
- **Success Criteria:**
  1. Re-opening a session for the same image is instant (uses cached embeddings).
  2. Closing the MCP server automatically terminates any orphaned napari subprocesses.
  3. User can resume a half-finished session with previous prompts and masks intact.

## Progress

| Phase | Description | Status | Progress |
|-------|-------------|--------|----------|
| 21 | µSAM Tool Pack Foundation | Pending | 0% |
| 22 | Headless Tools | Pending | 0% |
| 23 | Interactive Bridge | Pending | 0% |
| 24 | Session Management | Pending | 0% |

---

*Roadmap updated: 2026-02-04*
