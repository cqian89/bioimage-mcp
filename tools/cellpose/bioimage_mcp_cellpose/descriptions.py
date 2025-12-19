"""Curated parameter descriptions for Cellpose functions.

These descriptions provide user-friendly documentation for the parameters
that are introspected from CellposeModel.eval(). They are merged with
the automatically generated schema.
"""

SEGMENT_DESCRIPTIONS: dict[str, str] = {
    # Core parameters
    "diameter": (
        "Estimated cell diameter in pixels. "
        "Use 0 for automatic diameter estimation. "
        "Critical for accurate segmentation."
    ),
    "flow_threshold": (
        "Flow error threshold for mask reconstruction (0.0-1.0). "
        "Lower values = stricter, fewer masks. "
        "Higher values = more permissive, more masks."
    ),
    "cellprob_threshold": (
        "Cell probability threshold (-6.0 to 6.0). "
        "Lower values = larger cells. "
        "Higher values = smaller, more confident detections."
    ),
    "model_type": (
        "Pretrained model to use. Options include 'cyto3' (cells), "
        "'nuclei' (nuclei), or path to custom model."
    ),
    # GPU/performance
    "gpu": ("Use GPU acceleration if available. Significantly faster for large images."),
    "batch_size": (
        "Number of tiles to process in parallel on GPU. "
        "Increase for faster processing if GPU memory allows."
    ),
    # 3D parameters
    "do_3D": (
        "Run 3D segmentation. Input must have Z dimension. More computationally intensive than 2D."
    ),
    "stitch_threshold": (
        "Threshold for stitching 2D masks into 3D (0.0-1.0). Only used when do_3D=False on 3D data."
    ),
    # Advanced
    "min_size": ("Minimum mask size in pixels. Masks smaller than this are removed."),
    "normalize": ("Normalize image intensities. Set to False if image is already normalized."),
    "invert": (
        "Invert image intensities before processing. "
        "Useful for bright-field images with dark cells."
    ),
    "tile": ("Tile large images for processing. Set to True for images that don't fit in memory."),
    "tile_overlap": (
        "Overlap between tiles (fraction of tile size). "
        "Higher values reduce edge artifacts but increase processing time."
    ),
    "augment": (
        "Use test-time augmentation. May improve results at the cost of 4x processing time."
    ),
    "resample": ("Resample image to model's native resolution. Generally improves results."),
}
