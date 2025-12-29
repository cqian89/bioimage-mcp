"""Wrapper package for bioimage-mcp base tool functions.

This package contains essential wrapper functions that provide additional
logic beyond simple library calls (e.g., metadata handling, multi-output,
format bridging).

Submodules:
    - io: Format conversion (OME-Zarr, OME-TIFF)
    - axis: Axis manipulation (relabel, squeeze, expand, move, swap)
    - phasor: FLIM phasor analysis (phasor_from_flim, phasor_calibrate)
    - denoise: Image denoising with multiple filter types
    - edge_cases: Transform/preprocess operations requiring custom handling
"""

__all__ = [
    "axis",
    "denoise",
    "edge_cases",
    "io",
    "phasor",
]
