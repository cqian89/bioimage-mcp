# Phase 7: Transforms & Measurements - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable coordinate-aware operations (transforms) and analytical extraction (measurements) using `scipy.ndimage`.
This phase delivers atomic tools for geometric transformations and image measurements, ensuring metadata preservation where possible but prioritizing raw Scipy behavior/fidelity.

</domain>

<decisions>
## Implementation Decisions

### Measurement Output Structure
- **Return format:** Dictionary keyed by label ID (e.g., `{"1": [y, x], "2": [y, x]}`) for batch consistency.
- **Granularity:** Atomic tools (e.g., `measure_mean`, `measure_center_of_mass`) matching Scipy's API structure.
- **Label output:** `label` function returns two artifacts: the Label Mask (Image) and a Counts summary (JSON).
- **Missing labels:** Return `null` for requested labels that do not exist (do not error).

### Transform Boundaries
- **Default behavior:** Follow Scipy defaults (e.g., `rotate` uses `reshape=True` by default).
- **Parameters:** Expose `reshape`, `mode`, and `cval` to the agent.
- **API:** Provide `zoom` (factor-based) only; do not add a synthetic `resize` (shape-based) wrapper.

### Complex Number Handling (Fourier)
- **Artifact format:** Multi-channel OME-TIFF where Channel 0 is "real" and Channel 1 is "imag".
- **Input detection:** Detect complex inputs via channel names ("real", "imag") in metadata.
- **Architecture:** Expose raw components (`fft`, `fourier_gaussian`, `ifft`) separately. Do not auto-chain to enforce Real-to-Real workflows.
- **Normalization:** Expose the `norm` parameter.

### Physical Metadata Updates
- **Zoom:** Support anisotropic factors (tuple inputs) to update X/Y/Z pixel sizes independently.
- **Rotation:** Raw Scipy behavior (manual). Do not auto-resample anisotropic images before rotation.
- **Affine:** Expect **Inverse Matrix** inputs (matches `scipy.ndimage.affine_transform` convention).

### OpenCode's Discretion
- Exact naming of JSON keys for specific measurement tools.
- Error messaging format for matrix shape mismatches.

</decisions>

<specifics>
## Specific Ideas

- **"Follow scipy defaults as a rule"** — User prefers fidelity to the underlying library over "smart" convenience wrappers.
- **"Raw Scipy (Manual)"** — Avoid "magic" logic that obscures what the library is doing (e.g., auto-resampling).

</specifics>

<deferred>
## Deferred Ideas

- `resize` tool (target shape wrapper) — excluded to match Scipy API.
- Auto-chaining Fourier filters (Real -> FFT -> Filter -> IFFT -> Real) — excluded for flexibility.
- Smart rotation for anisotropic images (auto-isotropic resampling) — excluded to preserve raw behavior.

</deferred>

---

*Phase: 07-transforms-measurements*
*Context gathered: 2026-01-25*
