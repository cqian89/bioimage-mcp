from __future__ import annotations

CONVERT_TO_OME_ZARR_DESCRIPTIONS = {
    "chunk_size": "Chunk size for OME-Zarr storage (e.g., [1, 256, 256]).",
}

EXPORT_OME_TIFF_DESCRIPTIONS = {
    "compression": "Compression algorithm for OME-TIFF (e.g., 'zlib' or None).",
}

PROJECT_SUM_DESCRIPTIONS = {
    "axis": "Axis name or index to reduce over (e.g., 'Z' or 0).",
}

PROJECT_MAX_DESCRIPTIONS = {
    "axis": "Axis name or index to reduce over (e.g., 'Z' or 0).",
}

RESIZE_DESCRIPTIONS = {
    "output_shape": "Target shape as a list/tuple (e.g., [256, 256]).",
    "preserve_range": "Preserve input intensity range (avoid normalization).",
    "anti_aliasing": "Apply anti-aliasing when downsampling.",
}

RESCALE_DESCRIPTIONS = {
    "scale": "Scaling factor (e.g., 0.5 for half-size).",
    "preserve_range": "Preserve input intensity range (avoid normalization).",
    "anti_aliasing": "Apply anti-aliasing when downsampling.",
}

ROTATE_DESCRIPTIONS = {
    "angle": "Rotation angle in degrees.",
    "resize": "Resize output to fit rotated image.",
    "preserve_range": "Preserve input intensity range (avoid normalization).",
}

FLIP_DESCRIPTIONS = {
    "axis": "Axis name or index to flip (e.g., 'X' or -1).",
}

CROP_DESCRIPTIONS = {
    "start": "Start indices per axis (list of ints).",
    "stop": "Stop indices per axis (list of ints).",
}

PAD_DESCRIPTIONS = {
    "pad_width": "Pad widths per axis (e.g., [[0,0],[10,10],[10,10]]).",
    "mode": "Padding mode (e.g., 'constant', 'reflect').",
    "constant_values": "Constant value for padding when mode='constant'.",
}

NORMALIZE_INTENSITY_DESCRIPTIONS = {
    "pmin": "Lower percentile for intensity rescaling.",
    "pmax": "Upper percentile for intensity rescaling.",
    "clip": "Clip values to [0, 1] after normalization.",
}

GAUSSIAN_DESCRIPTIONS = {
    "sigma": "Standard deviation for Gaussian kernel.",
    "preserve_range": "Preserve input intensity range (avoid normalization).",
}

MEDIAN_DESCRIPTIONS = {
    "radius": "Radius of the median filter footprint.",
}

BILATERAL_DESCRIPTIONS = {
    "sigma_color": "Standard deviation for grayvalue distance.",
    "sigma_spatial": "Standard deviation for spatial distance.",
    "channel_axis": "Axis of channels, or None for single-channel.",
}

SOBEL_DESCRIPTIONS = {
    "axis": "Axis to compute gradient along (None for magnitude).",
}

DENOISE_NL_MEANS_DESCRIPTIONS = {
    "patch_size": "Patch size used for denoising.",
    "patch_distance": "Max distance to search for similar patches.",
    "h": "Cutoff distance (higher removes more noise).",
}

UNSHARP_MASK_DESCRIPTIONS = {
    "radius": "Radius of Gaussian blur used in unsharp mask.",
    "amount": "Strength of sharpening.",
    "preserve_range": "Preserve input intensity range (avoid normalization).",
}

EQUALIZE_ADAPTHIST_DESCRIPTIONS = {
    "kernel_size": "Shape of contextual regions for CLAHE.",
    "clip_limit": "Clipping limit for contrast enhancement.",
}

THRESHOLD_OTSU_DESCRIPTIONS = {
    "apply": "If true, return thresholded binary image; else return input unchanged.",
}

THRESHOLD_YEN_DESCRIPTIONS = {
    "apply": "If true, return thresholded binary image; else return input unchanged.",
}

MORPH_OPENING_DESCRIPTIONS = {
    "radius": "Radius of the structuring element.",
}

MORPH_CLOSING_DESCRIPTIONS = {
    "radius": "Radius of the structuring element.",
}

REMOVE_SMALL_OBJECTS_DESCRIPTIONS = {
    "min_size": "Minimum object size (in pixels) to keep.",
    "connectivity": "Connectivity for labeling (1 or 2 in 2D).",
}

PHASOR_FROM_FLIM_DESCRIPTIONS = {
    "time_axis": "Time/bin axis name or index for the FLIM signal (e.g., 'T' or 0).",
    "harmonic": "Phasor harmonic to compute (default 1).",
}

DENOISE_IMAGE_DESCRIPTIONS = {
    "filter_type": "Filter type to apply: median, gaussian, mean, or bilateral.",
    "radius": "Radius for median/mean filters.",
    "sigma": "Sigma for Gaussian filter.",
    "sigma_spatial": "Spatial sigma for bilateral filter.",
    "sigma_color": "Color/range sigma for bilateral filter.",
}

PHASOR_CALIBRATE_DESCRIPTIONS = {
    "lifetime": "Known lifetime of reference standard in nanoseconds (e.g., 4.04 for Fluorescein).",
    "frequency": "Laser repetition frequency in Hz (e.g., 80e6 for 80 MHz).",
    "harmonic": "Harmonic number for multi-harmonic analysis (default: 1).",
}
