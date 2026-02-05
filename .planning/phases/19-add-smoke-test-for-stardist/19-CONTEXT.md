# Phase 19: StarDist Smoke Test — Implementation Context

## Decisions Summary

### Test Coverage & Scope

**Decision:** The smoke test will replicate a segmentation example from the StarDist repository using their provided test image, and compare the output with a reference script (also based on the StarDist example).

| Aspect | Decision |
|--------|----------|
| Coverage Level | Full example replication + reference comparison |
| Dimensionality | 2D only |
| Model Verification | Download full pre-trained model (not mocked) |
| Execution Time Budget | Up to 5 minutes |

**Rationale:** Using the official example ensures we're testing realistic usage patterns. The 5-minute budget accommodates model download + inference, making this suitable for scheduled/nightly CI builds rather than every-commit runs.

---

### Test Data Strategy

**Decision:** Download the official StarDist example data on demand during test execution.

| Aspect | Decision |
|--------|----------|
| Data Source | StarDist repository examples (e.g., dsb2018_test.zip) |
| Storage Strategy | Download on demand (not bundled) |
| Image Size | Full example image (not synthetic/small) |
| Comparison Method | Pixel comparison with tolerance |

**Rationale:** Using official test data ensures compatibility with the reference script. Download-on-demand keeps the repo small while ensuring tests always use current example data.

---

### Validation Criteria

**Decision:** Validate functional correctness through label agreement and structural properties.

| Aspect | Decision |
|--------|----------|
| Pixel Comparison | Label agreement only (tolerant approach) |
| Required Validations | Output shape, dtype, label count range, artifact types |
| Performance | Timeout only (5 minutes total) |
| StarDist Outputs | Labels only (skip probabilities, distances, polyhedra) |

**Rationale:** Label agreement avoids brittle pixel-exact comparisons while still verifying correct segmentation. Structural checks ensure the full pipeline works (artifacts, metadata). Limiting to labels keeps the test focused and faster.

---

### Environment & Execution

**Decision:** Full server integration test with pre-installed environment requirement.

| Aspect | Decision |
|--------|----------|
| Environment | Require pre-installed `bioimage-mcp-stardist` conda env |
| Test Location | `tests/smoke/` (follow existing smoke test pattern) |
| CI Integration | Manual trigger only (workflow_dispatch), not automatic |
| Test Approach | Full server integration (start MCP, use tools/run) |

**Rationale:** Pre-installed env with pytest marker allows local opt-in. Full integration validates the complete stack (env → server → tool pack → StarDist). Manual-only CI prevents blocking PRs with slow/model-heavy tests.

---

### Failure Handling

**Decision:** Hard-failing test with standard diagnostics and download retry.

| Aspect | Decision |
|--------|----------|
| Failure Impact | Fail the test suite (blocking, not warning) |
| Diagnostics | Standard pytest logs + traceback |
| Retry Policy | Retry model download up to 3 times for transient network issues |
| Error Scenarios | Happy path only (no negative testing) |

**Rationale:** Blocking failure ensures StarDist regressions are caught. Retry handles common model download flakiness. Standard diagnostics provide enough context without excessive verbosity.

---

## Deferred Ideas (Future Phases)

These were discussed but deferred as they're out of scope for Phase 19:

- **3D smoke test:** Full 3D segmentation validation (separate phase if needed)
- **Performance benchmarking:** Specific inference time limits on reference hardware
- **Error scenario testing:** Missing model, invalid inputs, graceful degradation
- **CI automation:** Automatic PR CI runs with model caching
- **Output comparison:** Probabilities, distances, polyhedra validation

---

## Constraints for Planning

When planning Phase 19 implementation:

1. **Must use:** `tests/smoke/` location following existing smoke test structure
2. **Must implement:** pytest marker `requires_stardist` (like `requires_cellpose`)
3. **Must reference:** StarDist official example script for both implementation and comparison
4. **Must handle:** Model download with retry logic (3 attempts)
5. **Must integrate:** Full MCP server lifecycle (start → test → stop)
6. **Should validate:** LabelImageRef and NativeOutputRef artifacts from the run response
7. **Should use:** Downloaded test data, not synthetic images
8. **Should complete:** Within 5 minutes including model download

## Reference Materials

- StarDist repository examples: https://github.com/stardist/stardist/tree/master/examples
- Similar pattern: Cellpose smoke tests in `tests/smoke/test_cellpose_smoke.py`
- Model download: Use StarDist's model zoo (2D_versatile_fluo or similar)
