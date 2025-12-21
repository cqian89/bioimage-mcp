# Research Phase 0: FLIM Phasor Analysis

## Decisions & Rationale

### 1. Phasor Transformation Library
**Decision**: Use `phasorpy` library, specifically `phasor.phasor_from_signal`.
**Rationale**: 
- `phasorpy` is a specialized, validated library for phasor analysis.
- It provides `phasor_from_signal` which computes DC (intensity), G (real), and S (imag) in one go.
- It supports `sample_phase` for handling physical timing vs uniform binning, directly addressing FR-008.
- It is already present in the `bioimage-mcp-base` environment.

### 2. Time/Bin Axis Handling
**Decision**: 
- Identify the time/bin axis from OME-TIFF metadata (DimensionOrder).
- If physical timing metadata (frequency/time_bins) is present in OME-TIFF, calculate `sample_phase`.
- If not, pass `sample_phase=None` to use `phasorpy`'s default uniform mapping (0..2π).
- Ensure the input array is shaped correctly for `phasorpy` (likely expects signal on last axis or supports `axis` parameter). If `axis` parameter is missing, use `numpy.moveaxis`.

### 3. Integrated Intensity
**Decision**: Derive intensity from the `mean` component returned by `phasor_from_signal` (multiply by N_bins to get Sum if strictly required by "Sum" wording, or use `mean` if "Integrated Intensity" allows average - Spec says "Sum over time/bins". So `mean * n_bins` or `signal.sum(axis=t)`).
**Rationale**: `phasor_from_signal` computes the 0-th harmonic (DC) which is the mean. To strictly satisfy "Sum", we can compute `signal.sum(axis=time_axis)` separately or scale the mean. Computing separately `signal.sum(axis=time_axis)` is safer and explicit.

### 4. Denoising Implementation
**Decision**: Support 4 methods via `scikit-image` (and `scipy` for Mean on floats).
- **Median**: `skimage.filters.median` with `skimage.morphology.disk(radius)`.
- **Gaussian**: `skimage.filters.gaussian(sigma=...)`.
- **Mean**: `scipy.ndimage.uniform_filter(size=...)` (handles floats, unlike `skimage.filters.rank.mean`).
- **Bilateral**: `skimage.restoration.denoise_bilateral`.
**Rationale**: These cover the standard requirements. `rank.mean` is integer-only, so `scipy` is needed for float phasor maps.

### 5. Multi-channel Handling
**Decision**: Iterate over channel dimension (if C > 1) and apply phasor transform/denoising per channel 2D plane.
**Rationale**: Phasor analysis is typically single-channel (lifetime per pixel), but multi-channel FLIM exists. Spec requires preserving channel dimension.

## Alternatives Considered
- **Manual FFT for Phasor**: Could use `numpy.fft.rfft`.
    - *Rejected*: `phasorpy` is more robust, handles phase wrapping/unwrapping semantics if needed (though phasors are just complex numbers), and is a project dependency.
- **Scikit-image `rank.mean`**:
    - *Rejected*: Only supports integer types, necessitating casting which loses precision for phasor coordinates (-1 to 1).

## Unknowns Resolved
- **PhasorPy Usage**: Confirmed `phasor_from_signal` handles the core logic and timing.
- **Denoising Params**: Defined standard parameters (sigma, radius).
