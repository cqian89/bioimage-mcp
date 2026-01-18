# Smoke Test Expansion: Equivalence Testing Between MCP and Native Execution

## Summary
Expand smoke tests to cover each implemented library (phasorpy, cellpose, skimage, scipy, matplotlib) using:
- Real data from `datasets/` folder
- Workflows from official library documentation
- Dual execution: MCP tool calls vs native Python scripts
- Data equivalence validation (not format equivalence)
- Schema mismatch detection

## Background & Motivation
- Current smoke tests (tttrlib, FLIM phasor) validate basic MCP functionality.
- Need comprehensive coverage for all implemented tool packs.
- Ensure MCP execution faithfully reproduces documented library behavior.
- Detect schema drift between MCP interface and actual function signatures.

## Current State
- Existing smoke tests: `test_tttrlib_live.py`, `test_flim_phasor_live.py`
- `tttrlib` tests demonstrate the dual execution pattern with cross-tool workflows (tttrlib + base tools)
- `conftest.py` provides a `live_server` fixture for testing MCP interactions against a real subprocess-based server.

## Design

### 1. Test Architecture: Dual Execution Pattern
For each library, tests run workflows twice:
1. **MCP Execution**: Through `live_server.call_tool("run", {...})`
2. **Native Script Execution**: Direct Python API calls matching official tutorials

Then compare underlying data (via `bioio.BioImage(path).reader.data` or numpy arrays).

### 2. Schema Alignment Tests
New smoke tests that:
- Call `describe()` to get MCP schema.
- Compare against library's actual function signatures via `inspect.signature()`.
- Detect parameter mismatches (missing params, wrong types, wrong defaults).

### 3. Library-Specific Tests

#### A. PhasorPy (from https://www.phasorpy.org/docs/stable/tutorials/api/)
Dataset: `datasets/FLUTE_FLIM_data_tif/Embryo.tif`, `Fluorescein_Embryo.tif`
Workflow:
1. Load signal from TIFF
2. Compute phasors via `phasor_from_signal(signal, axis=0)`
3. Calibrate with reference via `phasor_calibrate(real, imag, ref_mean, ref_real, ref_imag, frequency=80.0, lifetime=4.2)`
4. Filter with `phasor_filter_median(mean, real, imag, size=3, repeat=3)`
5. Threshold with `phasor_threshold(mean_filt, real_filt, imag_filt, mean_min=1)`

Key params to verify: `axis`, `harmonic`, `frequency`, `lifetime`, `size`, `repeat`, `mean_min`

#### B. Cellpose (from https://cellpose.readthedocs.io/en/v3.1.1.1/notebook.html)
Dataset: `datasets/FLUTE_FLIM_data_tif/hMSC control.tif` (intensity image)
Workflow:
1. Initialize model: `CellposeModel(model_type='cyto3', gpu=False)`
2. Run eval: `model.eval(img, diameter=30.0, channels=[0,0], flow_threshold=0.4, cellprob_threshold=0.0)`
3. Return masks, flows, diams

Key params to verify: `model_type`, `diameter`, `channels`, `flow_threshold`, `cellprob_threshold`, `do_3D`, `min_size`, `normalize`

#### C. Scikit-image (from https://scikit-image.org/docs/stable/auto_examples/)
Dataset: `datasets/synthetic/test.tif` or sample FLIM images

Workflow 1 - Filtering:
1. Apply `gaussian(image, sigma=2.0)`
2. Apply `median(image, footprint=disk(3))`

Workflow 2 - Segmentation:
1. Compute `threshold_otsu(image)`
2. Create binary mask
3. Apply morphological operations

Key params to verify: `sigma` (float or sequence), `footprint`, threshold functions

#### D. Matplotlib (from https://matplotlib.org/stable/gallery/)
Dataset: Any loaded image from above workflows
Workflow:
1. Create figure with `plt.subplots()`
2. Display image with `imshow(data, cmap='gray', origin='lower')`
3. Save with `savefig(path, dpi=150, bbox_inches='tight')`

Key params to verify: `cmap`, `origin`, `dpi`, `bbox_inches`

#### E. SciPy ndimage (from https://docs.scipy.org/doc/scipy/reference/ndimage.html)
Dataset: `datasets/synthetic/test.tif` or any 2D/3D image
Workflow:
1. Apply `gaussian_filter(image, sigma=2.0)`
2. Compute `label(binary_image)` for connected components
3. Compute `binary_dilation(binary, iterations=2)`

Key params to verify: `sigma`, `mode`, `cval`, `structure`, `iterations`

### 4. Test File Structure
```text
tests/smoke/
├── test_phasorpy_equivalence.py    # Phasorpy dual execution tests
├── test_cellpose_equivalence.py    # Cellpose dual execution tests
├── test_skimage_equivalence.py     # Skimage dual execution tests
├── test_matplotlib_equivalence.py  # Matplotlib dual execution tests
├── test_schema_alignment.py        # Cross-library schema validation
├── reference_scripts/              # Pure Python reference implementations
│   ├── phasorpy_reference.py
│   ├── cellpose_reference.py
│   ├── skimage_reference.py
│   └── matplotlib_reference.py
└── utils/
    ├── data_equivalence.py         # Helpers for array comparison
    └── schema_validation.py        # Schema introspection helpers
```

### 5. Data Equivalence Validation
```python
def assert_data_equivalent(mcp_artifact_uri: str, native_array: np.ndarray, rtol=1e-5, atol=1e-8):
    """Compare MCP output artifact data to native execution result."""
    from bioio import BioImage
    import numpy as np
    mcp_data = BioImage(mcp_artifact_uri.replace("file://", "")).reader.data
    # Handle dimension ordering differences
    np.testing.assert_allclose(mcp_data.squeeze(), native_array.squeeze(), rtol=rtol, atol=atol)
```

### 6. Schema Mismatch Detection
```python
async def test_schema_matches_library(live_server, fn_id: str, target_callable):
    """Verify MCP schema matches actual function signature."""
    import inspect
    
    # Get MCP schema
    describe_result = await live_server.call_tool("describe", {"fn_id": fn_id})
    mcp_schema = describe_result["params_schema"]["properties"]
    
    # Get actual signature
    sig = inspect.signature(target_callable)
    actual_params = {name: param for name, param in sig.parameters.items() if name != 'self'}
    
    # Compare
    for param_name, param in actual_params.items():
        if param_name in ['kwargs', 'args']:
            continue
        assert param_name in mcp_schema, f"Missing param {param_name} in MCP schema"
        if param.default is not inspect.Parameter.empty:
            # Check default matches
            mcp_default = mcp_schema[param_name].get("default")
            assert mcp_default == param.default, f"Default mismatch for {param_name}"
```

### 7. Reference Documentation Alignment
Include specific documentation links and function signatures that tests should verify:

**PhasorPy (v0.5+)**:
- `phasorpy.phasor.phasor_from_signal(signal, *, axis=-1, harmonic=1)` → Returns (mean, real, imag)
- `phasorpy.lifetime.phasor_calibrate(real, imag, reference_mean, reference_real, reference_imag, frequency, lifetime)` → Returns (calibrated_real, calibrated_imag)
- `phasorpy.filter.phasor_filter_median(mean, real, imag, *, size=3, repeat=1)` → Returns (filtered_mean, filtered_real, filtered_imag)

**Cellpose (v3.x)**:
- `cellpose.models.CellposeModel(model_type='cyto3', gpu=False)` → Returns model instance
- `model.eval(x, *, diameter=30.0, channels=[0,0], flow_threshold=0.4, cellprob_threshold=0.0, ...)` → Returns (masks, flows, styles, diams)

**Scikit-image (v0.22+)**:
- `skimage.filters.gaussian(image, sigma=1, *, channel_axis=None, ...)` → Returns filtered image
- `skimage.filters.threshold_otsu(image)` → Returns threshold value
- `skimage.morphology.disk(radius)` → Returns structuring element

### 8. Known Schema Gaps to Detect
Document specific schema mismatches the tests should catch:
- Dynamic functions from adapters may have incomplete param schemas
- Default values in MCP manifest vs actual library defaults
- Parameter type annotations (especially array vs list)
- Optional parameters not marked with defaults

## Test Markers
- `@pytest.mark.smoke_equivalence`: For dual execution tests
- `@pytest.mark.schema_alignment`: For schema validation tests
- `@pytest.mark.requires_env("bioimage-mcp-*")`: For environment requirements

## Success Criteria
1. All smoke tests pass with data equivalence within tolerance.
2. No schema mismatches detected between MCP and library docs.
3. Tests run in CI (minimal markers) and full suite locally.
4. Coverage includes at least one workflow from each library's documentation.

### 9. Environment Requirements

| Test File | Required Environment | Marker |
|-----------|---------------------|--------|
| test_phasorpy_equivalence.py | bioimage-mcp-base | @pytest.mark.requires_env("bioimage-mcp-base") |
| test_cellpose_equivalence.py | bioimage-mcp-cellpose | @pytest.mark.requires_env("bioimage-mcp-cellpose") |
| test_skimage_equivalence.py | bioimage-mcp-base | @pytest.mark.requires_env("bioimage-mcp-base") |
| test_scipy_equivalence.py | bioimage-mcp-base | @pytest.mark.requires_env("bioimage-mcp-base") |
| test_matplotlib_equivalence.py | bioimage-mcp-base | @pytest.mark.requires_env("bioimage-mcp-base") |
| test_schema_alignment.py | All tool envs | Multiple markers |

## Implementation Plan

**Phase 1: Infrastructure**
- Create `tests/smoke/utils/data_equivalence.py` with array comparison helpers
- Create `tests/smoke/utils/schema_validation.py` with introspection helpers
- Update `tests/smoke/conftest.py` with new fixtures

**Phase 2: Reference Scripts**
- Write `reference_scripts/phasorpy_reference.py` following official tutorial
- Write `reference_scripts/cellpose_reference.py` following official notebook
- Write `reference_scripts/skimage_reference.py` following gallery examples
- Write `reference_scripts/scipy_reference.py` following documentation
- Write `reference_scripts/matplotlib_reference.py` following gallery examples

**Phase 3: MCP Smoke Tests**
- Implement equivalence tests for each library
- Each test runs both MCP workflow and calls reference script
- Compare outputs using data_equivalence utilities

**Phase 4: Schema Alignment**
- Implement schema alignment tests
- Document any discovered schema gaps
- Create issues for schema fixes

### 10. CI Integration

```yaml
# Example CI job configuration
smoke-test-minimal:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Setup environments
      run: conda run -n bioimage-mcp-base pip install -e .
    - name: Run minimal smoke tests
      run: pytest tests/smoke/ -m "smoke_minimal and not requires_env" -v

smoke-test-full:
  runs-on: ubuntu-latest
  needs: smoke-test-minimal
  steps:
    - uses: actions/checkout@v4
    - name: Setup all environments
      run: |
        conda run -n bioimage-mcp-base pip install -e .
        conda run -n bioimage-mcp-cellpose pip install -e .
    - name: Run full smoke suite
      run: pytest tests/smoke/ -v
```

## References
- PhasorPy API: https://www.phasorpy.org/docs/stable/tutorials/api/
- Cellpose Notebook: https://cellpose.readthedocs.io/en/v3.1.1.1/notebook.html
- Scikit-image Examples: https://scikit-image.org/docs/stable/auto_examples/
- Matplotlib Gallery: https://matplotlib.org/stable/gallery/
