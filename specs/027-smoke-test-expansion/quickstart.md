# Quickstart: Smoke Test Expansion

## Overview
This guide shows how to run and extend the smoke test suite with equivalence testing.

## Running Tests

### Run minimal smoke tests (CI mode)
```bash
pytest tests/smoke/ -m smoke_minimal -v
```

### Run full smoke tests (includes equivalence)
```bash
pytest tests/smoke/ -m smoke_full -v
```

### Run schema alignment tests only
```bash
pytest tests/smoke/test_schema_alignment.py -v
```

### Run equivalence tests for a specific library
```bash
pytest tests/smoke/test_equivalence_skimage.py -v
```

## Prerequisites

### Required conda environments
The following environments must be installed for full equivalence testing:
- `bioimage-mcp-base` - For PhasorPy, scikit-image, scipy, xarray, pandas, matplotlib
- `bioimage-mcp-cellpose` - For Cellpose segmentation

### Git LFS datasets
Some tests require real datasets. Fetch LFS files:
```bash
git lfs pull
```

Tests automatically skip if datasets are LFS pointers.

## Writing New Equivalence Tests

### 1. Create reference script
```python
# tests/smoke/reference_scripts/my_baseline.py
import argparse
import json
from my_library import my_function

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    # Execute native operation
    result = my_function(args.input)
    save(result, args.output)
    
    # Output metadata as JSON
    print(json.dumps({"output_path": args.output}))

if __name__ == "__main__":
    main()
```

### 2. Create equivalence test
```python
# tests/smoke/test_equivalence_mylib.py
import pytest
from pathlib import Path
from tests.smoke.utils.data_equivalence import DataEquivalenceHelper
from tests.smoke.utils.native_executor import NativeExecutor

@pytest.mark.smoke_full
@pytest.mark.anyio
async def test_mylib_equivalence(live_server, sample_image):
    helper = DataEquivalenceHelper()
    executor = NativeExecutor()
    
    # 1. Run via MCP
    mcp_result = await live_server.call_tool("run", {
        "fn_id": "base.mylib.my_function",
        "inputs": {"image": sample_image_ref},
        "params": {"param1": 10}
    })
    mcp_array = load_artifact(mcp_result["outputs"]["output"])
    
    # 2. Run native
    native_result = executor.run_script(
        env_name="bioimage-mcp-base",
        script_path=Path("tests/smoke/reference_scripts/my_baseline.py"),
        args=["--input", str(sample_image), "--output", "/tmp/native_out.tif"]
    )
    native_array = load_image(native_result["output_path"])
    
    # 3. Compare
    helper.assert_arrays_equivalent(mcp_array, native_array)
```

### 3. Use appropriate markers
```python
@pytest.mark.smoke_minimal  # Fast, synthetic data
@pytest.mark.smoke_full     # Slow, real data or heavy computation
@pytest.mark.requires_env("bioimage-mcp-cellpose")  # Requires specific env
```

## Utility Usage Examples

### Compare arrays
```python
from tests.smoke.utils.data_equivalence import DataEquivalenceHelper

helper = DataEquivalenceHelper()
helper.assert_arrays_equivalent(actual, expected, rtol=1e-5, atol=1e-8)
```

### Compare label images
```python
mean_iou = helper.assert_labels_equivalent(mcp_labels, native_labels, iou_threshold=0.95)
print(f"Achieved IoU: {mean_iou:.4f}")
```

### Validate plot artifact
```python
helper.assert_plot_valid(
    Path("output.png"),
    expected_width=800,
    expected_height=600,
    min_variance=1.0
)
```

### Execute native script
```python
from tests.smoke.utils.native_executor import NativeExecutor

executor = NativeExecutor()
result = executor.run_script(
    env_name="bioimage-mcp-base",
    script_path=Path("reference_scripts/skimage_baseline.py"),
    args=["--input", "img.tif", "--sigma", "2.0"],
    timeout=120
)
```

## Troubleshooting

### Test skipped: "Environment not available"
Install the required conda environment:
```bash
micromamba create -f envs/bioimage-mcp-base.lock.yml
```

### Test skipped: "Git LFS pointer"
Fetch LFS content:
```bash
git lfs pull
```

### Equivalence test fails with shape mismatch
Check that MCP and native scripts use the same input data and parameters. Verify dimension handling (some MCP operations may squeeze singleton dimensions).
