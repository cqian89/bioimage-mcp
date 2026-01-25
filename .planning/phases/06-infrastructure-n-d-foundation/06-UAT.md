---
status: complete
phase: 06-infrastructure-n-d-foundation
source: 06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md
started: 2026-01-25T20:00:00Z
updated: 2026-01-25T20:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. CLI Discovery Status
expected: Run `bioimage-mcp list`. Output shows `tools.base` with `scipy_ndimage` introspection and ~800 functions.
result: pass

### 2. Rich Metadata Availability
expected: In an MCP client (or via API), `scipy.ndimage.gaussian_filter` shows a full description and typed parameters (sigma, order, etc.), not just "args/kwargs".
result: pass

### 3. Execution: Image Filter
expected: Running `scipy.ndimage.gaussian_filter` on an image returns an OME-TIFF artifact.
result: pass

### 4. Execution: Measurement
expected: Running `scipy.ndimage.center_of_mass` (or `mean`) returns a JSON artifact with scalar values.
result: pass

### 5. Metadata Preservation
expected: Processed output images retain the physical pixel size metadata (microns/ms) from the input.
result: issue
reported: "Input image (test_dims.tif) had physical pixel sizes: Y=1.0, X=1.0. Output image (08152ccc2e7e4468b592d24b34a3a122.ome.tiff) after gaussian_filter had physical pixel sizes: Y=None, X=None. Inspection of the output file's OME-XML confirmed it was nearly empty, losing the spatial metadata."
severity: major

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Processed output images retain the physical pixel size metadata (microns/ms) from the input."
  status: failed
  reason: "User reported: Input image (test_dims.tif) had physical pixel sizes: Y=1.0, X=1.0. Output image ... had physical pixel sizes: Y=None, X=None."
  severity: major
  test: 5
  artifacts: []
  missing: []
