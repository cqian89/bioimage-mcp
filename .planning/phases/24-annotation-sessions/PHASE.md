# Phase 24: µSAM Session Management & Optimization

## Goal
Make the `micro_sam` MCP integration practical for real workflows by adding caching, artifactized embedding/state storage, and end-to-end verification across headless + interactive tools.

## Scope Boundaries
- **In-Scope:**
  - Predictor/model lifecycle management (`ObjectRef` cache policy, eviction, pinning)
  - Embedding/state storage as artifacts (file-backed, reusable across calls/sessions where feasible)
  - Performance ergonomics (avoid recomputing embeddings; clear logging of cache hits/misses)
  - Cross-phase E2E: Phase 22 -> Phase 23 -> artifact export
  - Optional: CLI-parity wrappers where the upstream API is path-centric

## Deliverables
1. **Embedding/State Artifact Format:** Define how `micro_sam` embeddings and related state are stored (likely `NativeOutputRef` bundle and/or zarr-temp).
2. **Cache Policy:** Documented and implemented cache policy for heavy `ObjectRef` instances (predictors, decoders, generators).
3. **E2E Workflow Test:** A smoke/integration test that:
   - runs a Phase 22 headless segmentation step
   - launches (or dry-runs) the Phase 23 annotator entrypoint
   - exports the committed labels as artifacts

## Success Criteria
1. Subsequent calls on the same image can reuse stored embeddings/state (measurably fewer compute steps; at minimum, explicit cache hit in logs).
2. Memory management can purge old predictors/embeddings safely without corrupting sessions.
3. The headless -> interactive -> export workflow is documented and verified.
