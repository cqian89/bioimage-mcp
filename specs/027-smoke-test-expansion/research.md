# Research: Smoke Test Expansion (027)

**Date**: 2026-01-18  
**Status**: Complete

## Executive Summary
Summary of key decisions and approaches for implementing equivalence testing between MCP execution and native library execution.

## Research Topics

### 1. Numerical Array Comparison
**Decision**: Use numpy.testing.assert_allclose with rtol=1e-5, atol=1e-8 for floating-point comparison.

**Rationale**: 
- rtol=1e-5 is appropriate for float32 machine epsilon (~1.19e-7)
- atol=1e-8 handles comparison of values near zero
- numpy.testing provides detailed mismatch reporting (percentage, max difference)

**Alternatives Considered**:
- np.array_equal - rejected for floating-point as it requires exact equality
- Custom diff function - rejected as numpy.testing provides robust solution

**Code Pattern**:
```python
from numpy.testing import assert_allclose

def assert_arrays_equivalent(actual: np.ndarray, expected: np.ndarray):
    assert actual.shape == expected.shape, f"Shape mismatch: {actual.shape} vs {expected.shape}"
    assert_allclose(actual, expected, rtol=1e-5, atol=1e-8)
```

### 2. Label Image Comparison (IoU/Dice)
**Decision**: Use IoU with matching algorithm; threshold IoU > 0.99 for equivalence (IoU > 0.95 for Cellpose to account for nondeterminism).

**Rationale**:
- Instance labels can have different IDs (object 1 in A might be object 5 in B)
- Hungarian algorithm (scipy.optimize.linear_sum_assignment) provides optimal matching
- IoU > 0.99 accounts for floating-point differences in deep learning outputs
- cellpose.metrics provides optimized implementation

**Alternatives Considered**:
- Exact equality (np.array_equal) - rejected due to label ID permutation
- Adjusted Rand Index - considered but IoU is more interpretable for segmentation

**Code Pattern**:
```python
from scipy.optimize import linear_sum_assignment
import numpy as np

def compute_iou_matrix(masks_true, masks_pred):
    true_ids = np.unique(masks_true)[1:]  # Skip background
    pred_ids = np.unique(masks_pred)[1:]
    iou_matrix = np.zeros((len(true_ids), len(pred_ids)))
    for i, t_id in enumerate(true_ids):
        for j, p_id in enumerate(pred_ids):
            mask_t = (masks_true == t_id)
            mask_p = (masks_pred == p_id)
            intersection = np.logical_and(mask_t, mask_p).sum()
            union = np.logical_or(mask_t, mask_p).sum()
            iou_matrix[i, j] = intersection / union if union > 0 else 0
    return iou_matrix, true_ids, pred_ids

def assert_labels_equivalent(masks_true, masks_pred, threshold=0.99):
    iou_matrix, true_ids, pred_ids = compute_iou_matrix(masks_true, masks_pred)
    row_ind, col_ind = linear_sum_assignment(iou_matrix, maximize=True)
    matched_ious = iou_matrix[row_ind, col_ind]
    mean_iou = matched_ious.mean() if len(matched_ious) > 0 else 0.0
    assert mean_iou >= threshold, f"Mean IoU {mean_iou:.4f} < threshold {threshold}"
```

### 3. Native Script Execution via Conda Run
**Decision**: Create NativeExecutor utility class using subprocess.run with conda run -n <env>.

**Rationale**:
- conda run handles environment activation automatically
- subprocess.run with timeout prevents zombie processes
- JSON output parsing enables structured result comparison
- Environment existence check before execution prevents cryptic errors

**Alternatives Considered**:
- Direct conda activate - rejected due to shell dependency
- micromamba only - conda run works for both conda and micromamba

**Code Pattern**: See data_equivalence.py in implementation

### 4. Schema Drift Detection
**Decision**: Compare params_schema semantically, ignoring documentation fields (description, title, examples).

**Rationale**:
- JSON Schema objects may have different key ordering
- Documentation fields don't affect runtime behavior
- Focus on: property names, types, defaults, required fields, enums
- Path-based reporting ($.properties.sigma.type) enables actionable fixes

**Alternatives Considered**:
- Exact string comparison - rejected due to key ordering
- deepdiff library - good option, used in implementation

**Key Fields to Compare**:
| Field | Severity | Description |
|-------|----------|-------------|
| inputs | CRITICAL | Artifact type mismatches break workflows |
| outputs | CRITICAL | Missing outputs break chaining |
| properties (names) | CRITICAL | Removed params break calls |
| properties.*.type | CRITICAL | Type mismatches cause validation errors |
| properties.*.default | WARNING | Changed defaults alter behavior |
| required | CRITICAL | New required params break existing calls |

### 5. Matplotlib/Plot Artifact Validation
**Decision**: Use semantic validation (existence, dimensions, histogram variance) instead of pixel comparison.

**Rationale**:
- Pixel-perfect comparison is impractical due to font rendering, backend, OS differences
- Semantic checks verify "something was drawn" without false failures
- PIL/Pillow provides efficient metadata access

**Validation Checks**:
1. File exists and size > 1KB
2. Valid PNG format
3. Dimensions match expected DPI/figsize
4. Histogram variance > 1.0 (not blank/uniform)

**Alternatives Considered**:
- pytest-mpl with tolerance - still flaky across environments
- perceptual hashing - overkill for validation

### 6. Git LFS Pointer Detection
**Decision**: Detect LFS pointers by reading first ~100 bytes and checking for version signature.

**Rationale**:
- LFS pointers are small text files (< 1KB) with specific version header
- Works without git-lfs CLI installed
- Fast (no subprocess spawn)

**Code Pattern**:
```python
def is_lfs_pointer(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size > 1024:
        return False
    try:
        with open(path, "rb") as f:
            head = f.read(100).decode("utf-8", errors="ignore")
            return "version https://git-lfs.github.com/spec/v1" in head
    except Exception:
        return False

def skip_if_lfs_pointer(path: Path):
    if is_lfs_pointer(path):
        pytest.skip(f"Dataset '{path}' is a Git LFS pointer (content not fetched)")
```

## Dependencies Identified

| Dependency | Purpose | Already Installed |
|------------|---------|-------------------|
| numpy | Array comparison | Yes (core) |
| scipy | Hungarian matching for IoU | Yes (base env) |
| PIL/Pillow | Plot validation | Yes (base env) |
| deepdiff | Schema comparison | No - optional, can use custom |
| pytest | Test framework | Yes |

## Unresolved Questions
None - all technical approaches validated.

## Next Steps
1. Phase 1: Define data models (EquivalenceTest, DataEquivalenceHelper, etc.)
2. Phase 1: Generate contracts for utility APIs
3. Phase 1: Write quickstart guide
