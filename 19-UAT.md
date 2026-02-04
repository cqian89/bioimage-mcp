# Phase 19 UAT: Add smoke test for stardist

## Test List

- [x] **Test 1: Pytest Marker Registration**
  - **Expected Behavior:** Running `pytest --markers` should show `requires_stardist` with a description indicating it requires the StarDist environment.
- [x] **Test 2: StarDist Native Baseline Execution**
  - **Expected Behavior:** Running the native baseline script `tests/smoke/reference_scripts/stardist_baseline.py` (within a stardist-enabled environment) should successfully generate a reference segmentation and print its shape/stats to stderr.
- [x] **Test 3: StarDist Equivalence Smoke Test**
  - **Expected Behavior:** Running `pytest tests/smoke/test_equivalence_stardist.py` (in an environment with StarDist available) should pass, confirming that the MCP StarDist tool produces results equivalent to the native baseline (IoU > 0.95).

## Results

| Test | Status | Notes |
|------|--------|-------|
| Test 1 | PASS | Marker found: @pytest.mark.requires_stardist: marks tests that require the bioimage-mcp-stardist conda environment |
| Test 2 | PASS | Generated labels for 119 nuclei using 2D_versatile_fluo model. |
| Test 3 | PASS | 1 passed in 46.24s with --smoke-full. |
