"""Cellpose segmentation operation.

Implements the cellpose.segment function for bioimage-mcp.
Uses CellposeModel.eval() from the Cellpose library.
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


def run_segment(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    """Run Cellpose segmentation on an input image.

    Args:
        inputs: Input artifact references (must include 'image')
        params: Segmentation parameters (model_type, diameter, etc.)
        work_dir: Working directory for output files

    Returns:
        Dict with output paths for labels and optional cellpose_bundle
    """
    # Import cellpose here to avoid import errors when not in cellpose env
    from cellpose import io as cellpose_io
    from cellpose.models import CellposeModel

    # Get input image path
    image_ref = inputs.get("image", {})
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
    img = tifffile.imread(str(image_path))

    # Extract parameters with defaults
    model_type = params.get("model_type", "cyto3")
    diameter = params.get("diameter", 30.0)
    flow_threshold = params.get("flow_threshold", 0.4)
    cellprob_threshold = params.get("cellprob_threshold", 0.0)
    do_3d = params.get("do_3D", False)

    # Handle diameter=0 or None as "auto-estimate"
    if diameter is None or diameter == 0:
        diameter = None  # Cellpose will estimate

    # Initialize model
    model = CellposeModel(model_type=model_type)

    # Run segmentation
    # Note: CellposeModel.eval() returns (masks, flows, styles)
    # For older versions it might return (masks, flows, styles, diams)
    result = model.eval(
        img,
        diameter=diameter,
        flow_threshold=flow_threshold,
        cellprob_threshold=cellprob_threshold,
        do_3D=do_3d,
    )

    # Handle different return signatures
    if len(result) == 3:
        masks, flows, styles = result
        diams = diameter
    else:
        masks, flows, styles, diams = result

    # Output paths
    labels_path = work_dir / "labels.ome.tiff"
    bundle_path = work_dir / "cellpose_seg.npy"

    # Write OME-TIFF label image (T019)
    # Convert to uint16/uint32 for label images
    if masks.max() < 65536:
        masks_out = masks.astype(np.uint16)
    else:
        masks_out = masks.astype(np.uint32)

    tifffile.imwrite(
        str(labels_path),
        masks_out,
        compression="zlib",
        metadata={"axes": "YX" if masks.ndim == 2 else "ZYX"},
    )

    # Write Cellpose native bundle (T019a)
    # This preserves flows, styles, and other Cellpose-specific data
    # masks_flows_to_seg appends _seg.npy to the base filename
    base_name = str(bundle_path.with_suffix(""))
    cellpose_io.masks_flows_to_seg(
        images=img,
        masks=masks,
        flows=flows,
        file_names=base_name,
        diams=diams if isinstance(diams, (int, float)) else diameter,
    )
    # masks_flows_to_seg creates a file named {base_name}_seg.npy
    actual_bundle_path = Path(base_name + "_seg.npy")
    if actual_bundle_path.exists():
        actual_bundle_path.rename(bundle_path)

    return {
        "labels": {
            "type": "LabelImageRef",
            "format": "OME-TIFF",
            "path": str(labels_path),
        },
        "cellpose_bundle": {
            "type": "NativeOutputRef",
            "format": "cellpose-seg-npy",
            "path": str(bundle_path),
        },
    }
