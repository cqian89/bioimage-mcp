# Cellpose Implementation Verification Report and Plan

## Verification Report

This report compares the current `bioimage-mcp` Cellpose implementation against the [official Cellpose API documentation](https://cellpose.readthedocs.io/en/latest/api.html).

### Summary
The current implementation (`tools/cellpose/bioimage_mcp_cellpose/ops/segment.py`) successfully wraps the core `CellposeModel.eval` function but fails to expose or utilize many relevant parameters that are defined in its own `descriptions.py`. This leads to a misleading user experience where parameters appear available (and are even valid inputs) but are silently ignored during execution.

### Discrepancies

#### 1. Ignored Parameters
The following parameters are present in `descriptions.py` (implying they are exposed to the user) but are **NOT passed** to `CellposeModel.eval` in `segment.py`:

| Parameter | Default (API) | Default (MCP) | Description | Impact |
|-----------|---------------|---------------|-------------|--------|
| `min_size` | 15 | - | Min number of pixels per mask | Users cannot filter small artifacts. |
| `batch_size` | 64 | - | Batch size for GPU | Performance tuning impossible. |
| `resample` | True (usually) | - | Run dynamics at original resolution | Quality/Performance trade-off fixed. |
| `stitch_threshold` | 0.0 | - | 3D stitching threshold | Cannot stitch 2D masks into 3D. |
| `normalize` | True | - | Image normalization | Users cannot disable normalization or customize it. |
| `invert` | False | - | Invert intensities | Users cannot process dark-on-light images (essential for some modalities). |
| `augment` | False | - | Test-time augmentation | Better accuracy option unavailable. |
| `tile` | True | - | Tile large images | Key for large image support. |
| `tile_overlap` | 0.1 | - | Tile overlap fraction | Edge artifact control unavailable. |

**Recommendation**: Pass these parameters to `model.eval()`.

#### 2. Missing GPU Control
- **Issue**: `gpu` parameter is described but not used.
- **Code**: `model = CellposeModel(model_type=model_type)`
- **Correctness**: To enforce GPU usage or fallback, `gpu=True/False` should be passed to `CellposeModel` constructor or `use_gpu` utils should be checked.
- **Impact**: User cannot force CPU execution if desired, or ensure GPU is used.

#### 3. Channel Handling
- **Issue**: `channels` argument is completely missing.
- **Documentation**: Cellpose expects `channels = [cytoplasm, nucleus]`. Default behavior if missing depends on input shape.
- **Impact**: Multi-channel images (e.g., standard Cellpose training data often has 2 channels) might differ in behavior if channels are not explicitly specified.
- **Risk**: High. If the user passes a 2-channel image, Cellpose might misinterpret it without explicit channel indices.

#### 4. 3D Segmentation Details
- **Issue**: `do_3D` is passed, but `anisotropy` is missing.
- **Impact**: 3D segmentation incorrectly assumes isotropic data (Z resolution = XY resolution), which is rarely true in microscopy (`anisotropy` usually > 1.0).

#### 5. Input Data Handling
- **Code**: `img = tifffile.imread(str(image_path))`
- **Issue**: `tifffile` reads the image as-is. `CellposeModel.eval` expects specific shapes.
    - If `do_3D=False`: Expects 2D (Y, X) or 3D (C, Y, X) or (Y, X, C)?
    - `image_path` defines the input. Unclear handling of axes (C, Z, T).
- **Recommendation**: Add explicit `channel_axis` and `z_axis` handling or metadata reading to ensure dimensions are correct.

---

## Implementation Plan

### Goal Description
Update the Cellpose wrapper implementation (`segment.py`) to fully utilize the parameters described in `descriptions.py` and supported by the Cellpose API. This ensures that user-provided configurations (like `min_size`, `flip`, `resample`, `gpu`) are respected instead of ignored. It also adds proper 3D parameter handling and channel configuration.

### User Review Required
> [!IMPORTANT]
> **Breaking Change Potential**: Default behaviors might change slightly if users were relying on ignored parameters keeping their default values. However, since the parameters were ignored, they were likely unused or confused users.
> **Channels**: We will default to `channels=[0,0]` (grayscale/auto) if not specified, but allowing users to specify channels is new behavior.

### Proposed Changes

#### Cellpose Tool (`tools/cellpose/bioimage_mcp_cellpose`)

##### [MODIFY] [segment.py](file:///mnt/c/Users/meqia/bioimage-mcp/tools/cellpose/bioimage_mcp_cellpose/ops/segment.py)
- Update `run_segment` to extract all documented parameters:
    - Core: `diameter`, `flow_threshold`, `cellprob_threshold`
    - Advanced: `min_size`, `resample`, `normalize`, `invert`, `tile`, `tile_overlap`, `augment`
    - 3D: `do_3D`, `stitch_threshold`, `anisotropy` (new)
- Add GPU handling:
    - Check `params["gpu"]`.
    - Initialize `CellposeModel` with `gpu=True` if requested (and available).
- Add Channel handling:
    - Extract `channels` from params (default `[0,0]`).
    - Pass to `eval`.
- Update `eval` call to include all these arguments.

##### [MODIFY] [descriptions.py](file:///mnt/c/Users/meqia/bioimage-mcp/tools/cellpose/bioimage_mcp_cellpose/descriptions.py)
- Ensure all new parameters (like `anisotropy`, `channels`) are described.
- Verify existing descriptions match intended usage.

### Verification Plan

#### Automated Tests
- **New Unit Test**: Create `tests/unit/test_segment_mock.py` (or similar) to verify parameter passing.
    - **Strategy**: Mock `cellpose` modules (`cellpose.models`, `cellpose.io`) before calling `run_segment`.
    - **Check**: Assert that `CellposeModel.eval` is called with the exact parameters provided in the input dictionary.
    - **Command**: `pytest tests/unit/test_segment_mock.py`

#### Manual Verification
- Not fully possible without a Cellpose environment with GPU, but the unit test with mocks gives high confidence in argument passing correctness.
