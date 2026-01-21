# Smoke Test Expansion: Equivalence Testing Between MCP and Native Execution

## Summary
Expand smoke tests to cover each implemented library (phasorpy, cellpose, skimage, scipy, matplotlib, xarray, pandas) using:
- Real data from `datasets/` folder and synthetic minimal data.
- Workflows from official library documentation and tutorials.
- Dual execution: MCP tool calls vs native Python scripts (via `conda run`).
- Data equivalence validation (segmentation metrics for labels, semantic validation for plots).
- Schema "Self-Consistency" detection (MCP `describe` vs tool runtime `meta.describe`).

## Background & Motivation
- Current smoke tests validate basic MCP functionality but lack side-by-side verification against native library execution.
- Ensure MCP execution faithfully reproduces documented library behavior.
- Detect schema drift between MCP interface and tool runtime definitions.
- Verify consistency across different tool environments (Isolated Execution principle).

## Current State
- Existing smoke tests:
  - `tests/smoke/test_smoke_basic.py`: Minimal discovery and run checks.
  - `tests/smoke/test_tttrlib_live.py`: Multi-step workflow (tttrlib + cellpose + base).
  - `tests/smoke/test_flim_phasor_live.py`: FLIM phasor workflow with xarray/pandas.
  - `tests/smoke/test_cellpose_pipeline_live.py`: Cellpose segmentation pipeline.
  - `tests/smoke/test_multi_artifact_concat.py`: Multi-artifact list input regression.
  - `tests/smoke/test_smoke_recording.py`: Recording-mode log output validation.
- Current tests use MCP-only workflows; "dual execution" comparison against native scripts is new work.
- `conftest.py` enforces a `smoke_minimal` vs `smoke_full` distinction with a time budget for minimal CI.

## Design

### 1. Test Architecture: Dual Execution Pattern
For each library, tests run workflows twice:
1. **MCP Execution**: Through `live_server.call_tool("run", {...})`.
2. **Native Script Execution**: Direct Python API calls matching official tutorials, executed via `conda run -n <env> python ...` to ensure library isolation is respected.

All equivalence tests are marked as `smoke_full` to stay within CI time budgets and avoid dependency bloat in minimal runs.

### 2. Schema "Self-Consistency" Tests
New smoke tests that:
- Call `describe(fn_id)` to get the server-facing MCP schema.
- Compare against the tool runtime's `meta.describe` output for the same function.
- Verify that parameters, defaults, and port definitions match between what the server reports and what the runtime expects.

### 3. Library-Specific Tests

#### A. PhasorPy (v0.9 API)
Dataset: `datasets/FLUTE_FLIM_data_tif/Embryo.tif`
Workflow (using `base.` prefix):
1. `base.phasorpy.phasor.phasor_from_signal(signal, axis=None, harmonic=None)`
2. `base.phasorpy.lifetime.phasor_calibrate(real, imag, reference_mean, reference_real, reference_imag, frequency=80.0, lifetime=4.2)`
3. `base.phasorpy.filter.phasor_filter_median(mean, real, imag, size=3, repeat=3)`

Key parameters to verify: `axis`, `harmonic`, `reference_mean`, `reference_real`, `reference_imag`, `frequency`, `lifetime`.

#### B. Cellpose (v3.1.1.2)
Dataset: `datasets/FLUTE_FLIM_data_tif/hMSC control.tif`
Workflow:
1. `cellpose.segment(image, model_type='cyto3', diameter=30.0, channels=[0,0])`
Note: MCP enforces its own defaults which may differ from library native defaults (e.g., `diameter=None` in library vs `30.0` in tool). Comparison scripts must use explicit values to match MCP-defined defaults.

Equivalence: Use IoU/Dice thresholds (>0.99) for label comparisons instead of exact equality to account for nondeterministic behavior in torch kernels.

#### C. Scikit-image (v0.22+)
Dataset: `datasets/synthetic/test.tif`
Workflow:
1. `base.skimage.filters.gaussian(image, sigma=2.0)`
2. `base.skimage.filters.threshold_otsu(image)`
3. `base.skimage.morphology.binary_dilation(mask, footprint=disk(3))`

#### D. Matplotlib (Stable API)
Validation: **Semantic invariants** instead of pixel equality.
1. PlotRef artifact exists and is non-empty.
2. Dimensions match expected DPI and figure size.
3. Histogram/mean intensity of the rendered image is within an expected loose range.
Reference: `https://matplotlib.org/stable/api/`

#### E. Xarray & Pandas
Explicitly cover data manipulation steps:
1. `base.xarray.DataArray.transpose(img, dims=['z', 'y', 'x', 'c'])`
2. `base.pandas.DataFrame.describe(table)`
Ensure metadata (coordinates, column names) is preserved across MCP/Native boundary.

### 4. Test File Structure
```text
tests/smoke/
├── test_phasorpy_equivalence.py    # Phasorpy dual execution tests
├── test_cellpose_equivalence.py    # Cellpose dual execution tests
├── test_skimage_equivalence.py     # Skimage dual execution tests
├── test_matplotlib_equivalence.py  # Matplotlib semantic validation
├── test_xarray_pandas_equivalence.py # Xarray/Pandas metadata parity
├── test_schema_alignment.py        # Self-consistency (describe vs meta.describe)
├── reference_scripts/              # Pure Python reference implementations
│   ├── phasorpy_reference.py       # (Run via conda run -n bioimage-mcp-base)
│   └── cellpose_reference.py       # (Run via conda run -n bioimage-mcp-cellpose)
└── utils/
    ├── data_equivalence.py         # Helpers for array/label/semantic comparison
    └── schema_validation.py        # Self-consistency helpers
```

### 5. Data Equivalence Validation
```python
def assert_data_equivalent(mcp_artifact: dict, native_array: np.ndarray, rtol=1e-5, atol=1e-8):
    """Compare MCP output artifact data to native execution result."""
    from bioio import BioImage
    import numpy as np
    
    uri = mcp_artifact["uri"]
    path = uri.replace("file://", "")
    # Handle BioImage reading for both OME-TIFF and .ome.zarr
    img = BioImage(path)
    mcp_data = img.reader.data
    
    # Normalize to canonical shape (remove singleton dims)
    np.testing.assert_allclose(mcp_data.squeeze(), native_array.squeeze(), rtol=rtol, atol=atol)
```

### 6. Schema Mismatch Detection (Self-Consistency)
```python
async def test_schema_self_consistency(live_server, fn_id: str):
    """Verify MCP describe() matches tool runtime meta.describe()."""
    # 1. Get server-facing schema
    describe_result = await live_server.call_tool("describe", {"fn_id": fn_id})
    mcp_params = describe_result["params_schema"]["properties"]
    
    # 2. Get runtime metadata (via a specialized internal tool or direct call to runtime)
    # This ensures the server's view matches the implementation's view
    runtime_meta = await live_server.call_tool("internal.get_runtime_meta", {"fn_id": fn_id})
    runtime_params = runtime_meta["params_schema"]["properties"]
    
    assert mcp_params == runtime_params, f"Schema mismatch for {fn_id}"
```

### 7. Reference Documentation Alignment
Test signatures should align with the following versions:

**PhasorPy (v0.9)**:
- `base.phasorpy.phasor.phasor_from_signal(signal, /, *, axis=None, harmonic=None, ...)`
- `base.phasorpy.lifetime.phasor_calibrate(real, imag, reference_mean, reference_real, reference_imag, frequency, lifetime)`

**Cellpose (v3.1.1.2)**:
- `cellpose.segment(image, model_type='cyto3', diameter=30.0, channels=[0,0])`
- Note: `CellposeModel.eval` native defaults (`diameter=None`) differ from MCP-exposed defaults.

**Matplotlib (Stable)**:
- Use `https://matplotlib.org/stable/api/` as source of truth for signature parity where supported.

## Test Markers
- `@pytest.mark.smoke_full`: For all dual execution and equivalence tests.
- `@pytest.mark.schema_alignment`: For self-consistency tests.
- `@pytest.mark.requires_env("bioimage-mcp-*")`: For specific conda environment requirements.

## Success Criteria
1. All equivalence tests pass within defined tolerances (numeric for arrays, IoU for labels, semantic for plots).
2. Schema self-consistency checks pass (no drift between server and runtime).
3. Large datasets (Git LFS) are correctly gated; tests use synthetic data when real data is missing.
4. Native execution is correctly isolated using `conda run`.

## Implementation Plan

### Phase 0: Prerequisites
- Fix `ScipyNdimageAdapter` to use `bioio.writers.OmeTiffWriter` instead of `tifffile.imwrite` to ensure project-wide I/O consistency.
- Ensure all datasets in `datasets/` have verified Git LFS presence.

### Phase 1: Infrastructure
- Create `tests/smoke/utils/data_equivalence.py` with segmentation (IoU) and semantic (plot) comparison helpers.
- Implement `conda run` wrapper for executing reference scripts in isolated environments.

### Phase 2: Reference Scripts
- Write reference scripts following exactly the tutorials for PhasorPy, Cellpose, and Scikit-image.
- Define shared helpers for axis normalization to ensure consistent comparison between different I/O backends.

### Phase 3: MCP Equivalence Tests
- Implement `smoke_full` tests for each library.
- Add axis convention guidance to ensure `BioImage` vs native library loading matches.

### Phase 4: Schema Alignment
- Implement "Self-Consistency" tests comparing `describe()` against `meta.describe`.
- Document and fix any discovered mismatches in parameter defaults or typing.

## CI Integration
Note: CI configurations are aspirational and should be adapted to the project's actual CI runner capabilities.

```yaml
# Example CI job for equivalence testing
smoke-test-full:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        lfs: true # Required for real datasets
    - name: Setup all environments
      run: |
        ./scripts/setup_envs.sh
    - name: Run equivalence suite
      run: pytest tests/smoke/ -m "smoke_full" -v
```

## References
- PhasorPy v0.9: https://www.phasorpy.org/docs/stable/tutorials/api/
- Cellpose v3.1.1.2: https://cellpose.readthedocs.io/en/latest/
- Matplotlib API: https://matplotlib.org/stable/api/
- BioImage Axis Conventions: `AGENTS.md` Standard BioImage Loading Pattern
