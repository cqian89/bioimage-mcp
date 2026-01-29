"""Cellpose denoise operation.

Implements the cellpose.denoise.DenoiseModel.eval function for bioimage-mcp.
Uses DenoiseModel.eval() from the Cellpose library.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .utils import _coerce_param, _uri_to_path


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

    # Transparently convert OME-Zarr to OME-TIFF if needed (fixes critical abstraction bug)
    from .utils import _ensure_ome_tiff_compatible

    image_path, reader = _ensure_ome_tiff_compatible(image_path, image_ref, work_dir)

    # Load image
    from bioio import BioImage

    bio_img = BioImage(image_path, reader=reader)
    img_data = bio_img.reader.data
    img_data = img_data.compute() if hasattr(img_data, "compute") else img_data

    # Squeeze singleton dimensions for cellpose
    img = np.squeeze(img_data)

    # Extract parameters with defaults and coercion
    diameter = _coerce_param(params.get("diameter"), float, "diameter")
    channels = params.get("channels")
    normalize = _coerce_param(params.get("normalize", True), bool, "normalize")
    tile = _coerce_param(params.get("tile", True), bool, "tile")

    # Handle diameter=0 or None as "auto-estimate"
    if diameter is None or diameter == 0:
        diameter = None  # Cellpose will estimate

    # Initialize model if not provided
    if model is None:
        model_type = params.get("model_type", "denoise_cyto3")
        gpu = _coerce_param(params.get("gpu", False), bool, "gpu")
        model = DenoiseModel(model_type=model_type, gpu=gpu)

    # Run denoising
    # DenoiseModel.eval returns the denoised image.
    denoised = model.eval(
        img,
        diameter=diameter,
        channels=channels,
        normalize=normalize,
        tile=tile,
    )

    # Output path
    denoised_path = work_dir / "denoised.ome.zarr"

    # Write OME-Zarr
    from bioio_ome_zarr.writers import OMEZarrWriter

    # Squeeze singleton trailing dimensions
    # Cellpose DenoiseModel.eval() returns [H, W, C] format with C=1 for grayscale inputs,
    # which causes dimension mismatches downstream. Squeeze these to get expected shapes.
    while denoised.ndim > 2 and denoised.shape[-1] == 1:
        denoised = denoised[..., 0]

    # Determine axes names/types based on squeezed array shape
    if denoised.ndim == 2:
        axes_names = ["y", "x"]
        axes_types = ["space", "space"]
    elif denoised.ndim == 3:
        axes_names = ["z", "y", "x"]
        axes_types = ["space", "space", "space"]
    elif denoised.ndim == 4:
        axes_names = ["c", "z", "y", "x"]
        axes_types = ["channel", "space", "space", "space"]
    else:
        # Fallback to standard OME names
        axes_names = [d.lower() for d in "TCZYX"[-denoised.ndim :]]
        type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
        axes_types = [type_map.get(d, "space") for d in axes_names]

    writer = OMEZarrWriter(
        store=str(denoised_path),
        level_shapes=[denoised.shape],
        dtype=denoised.dtype,
        axes_names=axes_names,
        axes_types=axes_types,
        zarr_format=2,
    )
    writer.write_full_volume(denoised)

    return {
        "denoised": {
            "type": "BioImageRef",
            "format": "OME-Zarr",
            "path": str(denoised_path),
            "storage_type": "zarr-temp",
            "metadata": {
                "dims": [d.upper() for d in axes_names],
                "shape": list(denoised.shape),
                "dtype": str(denoised.dtype),
            },
        }
    }
