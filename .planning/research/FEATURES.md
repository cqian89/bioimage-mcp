# Feature Landscape: Scipy Integration

**Domain:** Bioimage Analysis / Scientific Computing
**Researched:** 2026-01-25
**Overall confidence:** HIGH

## Executive Summary

Scipy is the backbone of scientific computing in Python. For bioimage analysis, it provides essential multidimensional processing (`ndimage`), signal processing (`signal`), spatial analysis (`spatial`), and statistical tools (`stats`). The integration milestone focuses on exposing these capabilities dynamically through the Bioimage-MCP adapter pattern, ensuring that AI agents can leverage Scipy's robust algorithms without manual tool wrapping.

## Table Stakes

Features users expect in any scientific image analysis integration. Missing these makes the toolkit feel incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **N-D Linear Filtering** | Gaussian, Uniform, and Laplace filters are fundamental for noise reduction and feature enhancement. | Low | Leverages `scipy.ndimage`. |
| **Morphological Ops** | Binary and grayscale dilation, erosion, opening, and closing for structure extraction. | Low | Core for mask cleanup. |
| **Image Interpolation** | Zooming, rotating, and affine transformations for registration and geometric correction. | Medium | Requires handling boundary modes and orders. |
| **Object Measurements** | Labeling, center of mass, and basic statistics on segmented regions. | Medium | Key bridge to tabular data. |
| **Statistical Summaries** | T-tests, ANOVA, and distribution moments (mean, skew, kurtosis) for data validation. | Low | Leverages `scipy.stats`. |
| **Generic Convolution** | Applying arbitrary kernels to N-D arrays. | Low | Found in `scipy.ndimage` and `scipy.signal`. |

## Differentiators

Features that set Bioimage-MCP's Scipy integration apart by optimizing for AI agents and multi-step workflows.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Dynamic API Discovery** | Automatically exposes hundreds of Scipy functions as MCP tools using `numpydoc` parsing. | Medium | Uses the `BaseAdapter` introspection pattern. |
| **Dimension Autocorrection** | Intelligent "squeezing" and axis-mapping to ensure TCZYX artifacts work with Scipy's expected 2D/3D inputs. | Medium | Prevents common "ndim mismatch" errors. |
| **Coordinate-to-Index Bridge** | Native support for `scipy.spatial.KDTree` and `Voronoi` using coordinate tables from Trackpy/Skimage. | High | Enables neighbor analysis and spatial statistics. |
| **Serializable "Measure" API** | Normalizes Scipy's heterogeneous measurement outputs (lists, dicts, arrays) into standard `TableRef` artifacts. | Medium | Critical for agent-driven data analysis. |
| **Metadata Preservation** | Carries physical pixel sizes and axis names through transforms (e.g., `zoom` updates resolution). | Medium | Ensures downstream tools remain calibrated. |

## Anti-Features

Features to explicitly NOT build to avoid security risks, complexity, or architectural drift.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Optimization Callbacks** | `scipy.optimize` functions requiring user-defined Python callbacks are unsafe in a dynamic MCP context. | Use pre-defined optimization "recipes" or specialized tools. |
| **Sparse Matrix Support** | `scipy.sparse` lacks a standard serializable artifact format in the current MCP ecosystem. | Convert to dense arrays for intermediate steps if size allows. |
| **Interactive Plotting** | Scipy's internal plotting should not be wrapped directly. | Use the `matplotlib` adapter to render results to `FigureRef`. |
| **Raw Pointer Access** | Bypassing the Artifact boundary to access internal Scipy/C pointers. | Always use `BioImageRef` or `ObjectRef` via the adapter. |

## Feature Dependencies

- **Core Server (v0.2.0)**: Required for the dynamic adapter registry and session management.
- **BioIO Integration**: Required for loading multi-dimensional image artifacts into Scipy-compatible NumPy arrays.
- **Skimage Integration**: Shared patterns for coordinate handling and dimension hints.
- **Trackpy Integration**: Provides the primary source of coordinate data for `scipy.spatial` analysis.

## MVP Recommendation

For the Scipy Integration milestone (v0.3.0), prioritize:
1.  **Comprehensive `ndimage` Adapter**: Full coverage of filters, morphology, and interpolation.
2.  **Dynamic `scipy.stats` Exposure**: Standard statistical tests (t-test, etc.) and summary descriptors using `numpydoc` for schema generation.
3.  **Spatial Analysis Bridge**: specifically `scipy.spatial.distance` and `KDTree` for neighbor analysis on point-data.

Defer to v0.4.0+:
-   Advanced Fourier domain filters (`scipy.fftpack` / `scipy.ndimage.fourier`).
-   Complex Signal processing submodules (`scipy.signal.windows`, etc.).
-   Clustering (`scipy.cluster.vq`).

## Sources

- [Scipy ndimage User Guide](https://docs.scipy.org/doc/scipy/tutorial/ndimage.html) (HIGH confidence)
- [Bioimage-MCP Adapter Architecture](src/bioimage_mcp/registry/dynamic/adapters/base.py) (HIGH confidence)
- [Skimage Adapter Reference](src/bioimage_mcp/registry/dynamic/adapters/skimage.py) (HIGH confidence)
- [Scipy spatial documentation](https://docs.scipy.org/doc/scipy/reference/spatial.html) (HIGH confidence)
