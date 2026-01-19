# Data Model: Smoke Test Expansion (027)

**Date**: 2026-01-18

## Overview
This document defines the data structures and utility classes for implementing MCP-native equivalence testing.

## Entities

### 1. DataEquivalenceHelper

**Purpose**: Utility class for comparing MCP artifacts against native execution results with appropriate tolerance and normalization.

**Module**: tests/smoke/utils/data_equivalence.py

**Fields/Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| assert_arrays_equivalent | (actual: ndarray, expected: ndarray, rtol=1e-5, atol=1e-8) -> None | Compare float arrays with tolerance |
| assert_labels_equivalent | (actual: ndarray, expected: ndarray, iou_threshold=0.99) -> None | Compare label images using IoU matching |
| assert_plot_valid | (path: Path, min_size=1000, expected_dims=None) -> None | Semantic validation of PlotRef artifact |
| assert_table_equivalent | (actual: DataFrame, expected: DataFrame, rtol=1e-5) -> None | Compare table artifacts |
| assert_metadata_preserved | (actual: xr.DataArray, expected: xr.DataArray) -> None | Verify coordinates/attrs preserved |

**Validation Rules**:
- Shape mismatch raises AssertionError immediately
- Array comparison uses numpy.testing.assert_allclose
- Label comparison uses Hungarian algorithm for optimal matching
- Plot validation checks existence, size, format, histogram variance

**Example**:
```python
from tests.smoke.utils.data_equivalence import DataEquivalenceHelper

helper = DataEquivalenceHelper()

# Array comparison
helper.assert_arrays_equivalent(mcp_output, native_output)

# Label comparison (allows for ID permutation)
helper.assert_labels_equivalent(mcp_labels, native_labels, iou_threshold=0.95)

# Plot validation
helper.assert_plot_valid(plot_path, min_size=2000)
```

---

### 2. NativeExecutor

**Purpose**: Utility for running Python scripts in isolated conda environments via subprocess.

**Module**: tests/smoke/utils/native_executor.py

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| conda_exe | str | Path to conda/micromamba executable |
| default_timeout | int | Default timeout in seconds (300) |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| __init__ | (conda_path: Optional[str] = None) | Initialize with conda executable |
| env_exists | (env_name: str) -> bool | Check if conda environment exists |
| run_script | (env_name: str, script: Path, args: list, timeout: int) -> dict | Execute script and parse JSON output |

**Error Types**:
- EnvironmentNotFoundError: Raised when specified conda env doesn't exist
- NativeExecutorError: Base exception for execution failures
- TimeoutError: Raised when script exceeds timeout

**Example**:
```python
from tests.smoke.utils.native_executor import NativeExecutor

executor = NativeExecutor()

result = executor.run_script(
    env_name="bioimage-mcp-base",
    script=Path("tests/smoke/reference_scripts/skimage_baseline.py"),
    args=["--input", str(image_path), "--output", str(output_path)],
    timeout=60
)
# result is parsed JSON from stdout
```

---

### 3. ReferenceScript (Convention)

**Purpose**: Native Python script that executes library operations identically to MCP workflows.

**Location**: tests/smoke/reference_scripts/<library>_baseline.py

**Convention**:
- Accepts CLI args: --input, --output, --params (JSON)
- Outputs JSON to stdout with result metadata
- Logs to stderr (not stdout) to avoid corrupting JSON
- Returns exit code 0 on success, non-zero on failure

**Output Schema**:
```json
{
  "output_path": "/path/to/result.tif",
  "shape": [256, 256],
  "dtype": "float32",
  "checksum": "sha256:...",
  "metadata": { ... }
}
```

**Example Script Structure**:
```python
#!/usr/bin/env python
"""Reference script for scikit-image gaussian filter."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from skimage import io, filters

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sigma", type=float, default=1.0)
    args = parser.parse_args()

    # Load and process
    img = io.imread(args.input)
    result = filters.gaussian(img, sigma=args.sigma)
    
    # Save
    io.imsave(args.output, result.astype(np.float32))
    
    # Output JSON to stdout
    print(json.dumps({
        "output_path": args.output,
        "shape": list(result.shape),
        "dtype": str(result.dtype)
    }))

if __name__ == "__main__":
    main()
```

---

### 4. SchemaAlignmentResult

**Purpose**: Result of comparing MCP describe() with runtime meta.describe().

**Module**: Inline dataclass in tests/smoke/test_schema_alignment.py

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| fn_id | str | Function identifier |
| passed | bool | True if schemas align |
| mcp_schema | dict | Schema from MCP describe() |
| runtime_schema | dict | Schema from meta.describe() |
| differences | list[SchemaDiff] | List of detected differences |

**SchemaDiff Fields**:

| Field | Type | Description |
|-------|------|-------------|
| path | str | JSON path to differing field ($.properties.sigma.type) |
| mcp_value | Any | Value in MCP schema |
| runtime_value | Any | Value in runtime schema |
| severity | str | CRITICAL, WARNING, or INFO |

---

### 5. EquivalenceTestResult

**Purpose**: Result structure for equivalence test assertions.

**Module**: Inline dataclass in test files

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| fn_id | str | Function being tested |
| library | str | Library name (phasorpy, skimage, etc.) |
| passed | bool | True if equivalence check passed |
| mcp_result | dict | Artifact metadata from MCP run |
| native_result | dict | Result from native execution |
| comparison_metric | str | Metric used (allclose, iou, semantic) |
| metric_value | float | Actual metric value |
| threshold | float | Required threshold |
| error_message | Optional[str] | Error details if failed |

---

## Relationships

```
┌─────────────────────┐
│   EquivalenceTest   │
│   (pytest module)   │
└──────────┬──────────┘
           │ uses
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│ DataEquivalenceHelper│◄───│   NativeExecutor    │
└──────────┬──────────┘     └──────────┬──────────┘
           │                           │
           │ compares                  │ executes
           ▼                           ▼
┌─────────────────────┐     ┌─────────────────────┐
│  MCP Artifact       │     │  ReferenceScript    │
│  (BioImageRef, etc) │     │  (native Python)    │
└─────────────────────┘     └─────────────────────┘
```

## State Transitions
N/A - These are stateless utility classes and test structures.

## Validation Rules Summary

| Entity | Rule | Error |
|--------|------|-------|
| DataEquivalenceHelper | Shape must match | AssertionError |
| DataEquivalenceHelper | rtol/atol must be respected | AssertionError |
| DataEquivalenceHelper | IoU must exceed threshold | AssertionError |
| NativeExecutor | Environment must exist | EnvironmentNotFoundError |
| NativeExecutor | Script must complete in timeout | TimeoutError |
| ReferenceScript | Must output valid JSON | NativeExecutorError |