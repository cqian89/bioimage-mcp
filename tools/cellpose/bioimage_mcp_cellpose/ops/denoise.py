"""Cellpose denoise operation.

Implements the cellpose.denoise.DenoiseModel.eval function for bioimage-mcp.
Uses DenoiseModel.eval() from the Cellpose library.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote

import numpy as np
import tifffile


def _uri_to_path(uri: str) -> Path:
    """Convert a file:// URI to a Path."""
    if uri.startswith("file://"):
        # Handle Windows paths that may have extra slash: file:///C:/...
        path_str = uri[7:]  # Remove file://
        if len(path_str) > 2 and path_str[0] == "/" and path_str[2] == ":":
            path_str = path_str[1:]  # Remove leading / for Windows paths
        return Path(unquote(path_str))
    return Path(uri)


def run_denoise(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
    model: Any | None = None,
) -> dict[str, Any]:
    """Run Cellpose denoising on an input image.

    Args:
        inputs: Input artifact references (must include 'x' or 'image')
        params: Denoise parameters
        work_dir: Working directory for output files
        model: Pre-initialized DenoiseModel instance

    Returns:
        Dict with output path for denoised image
    """
    # Import cellpose here to avoid import errors when not in cellpose env
    from cellpose.denoise import DenoiseModel

    # Get input image path
    image_ref = inputs.get("x") or inputs.get("image", {})
    image_uri = image_ref.get("uri", "")

    if not image_uri:
        raise ValueError("No image input provided")

    image_path = _uri_to_path(image_uri)
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    # Check format - fail fast for unsupported formats
    input_format = image_ref.get("format", "").lower()
    if "zarr" in input_format:
        raise ValueError(
            f"OME-Zarr format is not supported in v0.1. "
            f"Please convert to OME-TIFF first. Got format: {image_ref.get('format')}"
        )

    # Load image
    from bioio import BioImage

    # Robust reader selection for OME-TIFF
    reader = None
    if input_format == "ome-tiff":
        try:
            import bioio_ome_tiff

            reader = bioio_ome_tiff.Reader
        except ImportError:
            pass

    bio_img = BioImage(image_path, reader=reader)
    img_data = bio_img.data
    img_data = img_data.compute() if hasattr(img_data, "compute") else img_data  # 5D TCZYX

    # Squeeze singleton dimensions for cellpose
    img = np.squeeze(img_data)

    # Extract parameters with defaults
    diameter = params.get("diameter")
    flow_threshold = params.get("flow_threshold", 0.4)
    cellprob_threshold = params.get("cellprob_threshold", 0.0)
    channels = params.get("channels")
    channel_axis = params.get("channel_axis")
    z_axis = params.get("z_axis")
    do_3D = params.get("do_3D", False)
    stitch_threshold = params.get("stitch_threshold", 0.0)
    normalize = params.get("normalize", True)
    invert = params.get("invert", False)
    min_size = params.get("min_size", 15)
    rescale = params.get("rescale")
    tile = params.get("tile", True)
    tile_overlap = params.get("tile_overlap", 0.1)
    augment = params.get("augment", False)
    resample = params.get("resample", True)
    net_avg = params.get("net_avg", True)

    # Handle diameter=0 or None as "auto-estimate"
    if diameter is None or diameter == 0:
        diameter = None  # Cellpose will estimate

    # Initialize model if not provided
    if model is None:
        model_type = params.get("model_type", "denoise_cyto3")
        gpu = params.get("gpu", False)
        model = DenoiseModel(model_type=model_type, gpu=gpu)

    # Run denoising
    # DenoiseModel.eval returns the denoised image.
    denoised = model.eval(
        img,
        diameter=diameter,
        flow_threshold=flow_threshold,
        cellprob_threshold=cellprob_threshold,
        channels=channels,
        channel_axis=channel_axis,
        z_axis=z_axis,
        do_3D=do_3D,
        stitch_threshold=stitch_threshold,
        normalize=normalize,
        invert=invert,
        min_size=min_size,
        rescale=rescale,
        tile=tile,
        tile_overlap=tile_overlap,
        augment=augment,
        resample=resample,
        net_avg=net_avg,
    )

    # Output path
    denoised_path = work_dir / "denoised.ome.tiff"

    # Write OME-TIFF
    tifffile.imwrite(
        str(denoised_path),
        denoised,
        compression="zlib",
        metadata={"axes": "YX" if denoised.ndim == 2 else "ZYX"},
    )

    return {
        "denoised": {
            "type": "BioImageRef",
            "format": "OME-TIFF",
            "path": str(denoised_path),
        }
    }
