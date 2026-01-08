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
    # Evaluation
    "threshold": (
        "Intersection over Union (IoU) threshold(s) for matching masks. "
        "Can be a single value or a list/array of values."
    ),
}

# Training-specific parameter descriptions
TRAINING_DESCRIPTIONS: dict[str, str] = {
    "n_epochs": (
        "Number of training epochs. Higher values may improve accuracy but increase training time. "
        "Default is 2000, but 100-500 is often sufficient for fine-tuning."
    ),
    "learning_rate": (
        "Initial learning rate for optimizer. "
        "Lower values (0.001-0.01) for fine-tuning, higher (0.1) for training from scratch."
    ),
    "weight_decay": (
        "L2 regularization weight. Helps prevent overfitting. "
        "Default 1e-5 works well for most cases."
    ),
    "save_path": (
        "Directory to save trained model weights. If None, saves to current working directory."
    ),
    "save_every": (
        "Save checkpoint every N epochs. "
        "Useful for long training runs to recover from interruptions."
    ),
    "save_each": (
        "Save model after each epoch instead of just at checkpoints. "
        "Creates many files but allows fine-grained recovery."
    ),
    "model_name": ("Name for saved model file. If None, uses a timestamp-based name."),
    "momentum": (
        "Momentum for SGD optimizer (0.0-1.0). "
        "Higher values (0.9-0.99) can help overcome local minima."
    ),
    "SGD": (
        "Use SGD optimizer instead of AdamW. "
        "SGD may generalize better but requires careful learning rate tuning."
    ),
    "min_train_masks": (
        "Minimum number of masks required per training image. "
        "Images with fewer masks are skipped during training."
    ),
    "rescale": (
        "Rescale images during training for data augmentation. "
        "Helps model generalize to different cell sizes."
    ),
    "scale_range": (
        "Range of scale factors for augmentation as (min, max). Default None uses built-in range."
    ),
    "bsize": (
        "Size of image patches for training in pixels. "
        "Larger patches capture more context but use more memory."
    ),
    "nimg_per_epoch": ("Number of images to use per epoch. If None, uses all training images."),
    "compute_flows": (
        "Compute flow fields for training images. Required if labels don't have pre-computed flows."
    ),
    "load_files": (
        "Load images from file paths instead of arrays. "
        "Set True when using train_files/train_labels_files."
    ),
    "rgb": (
        "Treat input as RGB image. Set True for color images, False for grayscale or multi-channel."
    ),
}

# Merge training descriptions into segment descriptions for unified lookup
SEGMENT_DESCRIPTIONS.update(TRAINING_DESCRIPTIONS)
