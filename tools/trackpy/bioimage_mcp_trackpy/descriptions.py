"""Manual description overrides for trackpy functions.

These override or supplement the auto-extracted docstrings to improve
LLM usability and parameter clarity.
"""

from __future__ import annotations

# Core feature finding
LOCATE_DESCRIPTIONS = {
    "diameter": "Approximate feature diameter in pixels. Must be odd integer. For 3D, use tuple (z, y, x).",
    "minmass": "Minimum integrated brightness. Filters out dim features. Start with 0 and increase to remove noise.",
    "maxsize": "Maximum radius-of-gyration of blob. Filters out clusters. Optional.",
    "separation": "Minimum separation between features. Default is diameter+1.",
    "noise_size": "Size of Gaussian blur for noise removal. Default 1.",
    "smoothing_size": "Size of boxcar smoothing. Default is diameter.",
    "threshold": "Clip bandpass result below this value. Default is 1/255 for float images.",
    "percentile": "Threshold based on percentile of pixel values. Overrides threshold.",
    "topn": "Return only brightest N features. Optional.",
    "preprocess": "Apply bandpass filter before locating. Default True.",
    "max_iterations": "Max refinement iterations for centroid. Default 10.",
    "characterize": "Compute additional properties (mass, size, eccentricity). Default True.",
    "engine": "Computation engine: 'auto', 'python', or 'numba'. Default 'auto' uses numba if available.",
}

BATCH_DESCRIPTIONS = {
    "frames": "Iterable of image frames (movie). Can be list, generator, or PIMS object.",
    "processes": "Number of parallel processes. Default 1 (single process).",
    "meta": "Include frame metadata in output. Default True.",
}

# Linking
LINK_DESCRIPTIONS = {
    "search_range": "Maximum distance a particle can move between frames in pixels.",
    "memory": "Number of frames a particle can disappear and reappear. Default 0.",
    "pos_columns": "Column names for coordinates. Default ['y', 'x'] or ['z', 'y', 'x'] for 3D.",
    "t_column": "Column name for frame number. Default 'frame'.",
    "predictor": "Predictor object for velocity-based linking. Default None (nearest neighbor).",
    "adaptive_stop": "Stop when all particles linked for this many frames. Optimization.",
    "adaptive_step": "Reduce search_range by this factor adaptively. Optimization.",
    "link_strategy": "Strategy for linking: 'auto', 'recursive', 'nonrecursive', 'numba', 'drop', 'hybrid'. Default 'auto'.",
}

# Motion analysis
MSD_DESCRIPTIONS = {
    "mpp": "Microns per pixel. Converts coordinates to physical units.",
    "fps": "Frames per second. Converts frame numbers to time.",
    "max_lagtime": "Maximum lag time in frames. Default is 100.",
    "detail": "Include detailed statistics. Default False.",
    "pos_columns": "Column names for coordinates.",
}

# Export for use by introspect.py
DESCRIPTION_OVERRIDES = {
    "trackpy.locate": LOCATE_DESCRIPTIONS,
    "trackpy.batch": {**LOCATE_DESCRIPTIONS, **BATCH_DESCRIPTIONS},
    "trackpy.link": LINK_DESCRIPTIONS,
    "trackpy.link_df": LINK_DESCRIPTIONS,
    "trackpy.motion.msd": MSD_DESCRIPTIONS,
    "trackpy.motion.imsd": MSD_DESCRIPTIONS,
    "trackpy.motion.emsd": MSD_DESCRIPTIONS,
}
