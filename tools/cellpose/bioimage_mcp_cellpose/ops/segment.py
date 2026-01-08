"""Cellpose segmentation operation.

Implements the cellpose.segment function for bioimage-mcp.
Uses CellposeModel.eval() from the Cellpose library.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .utils import _coerce_param, _uri_to_path


def run_segment(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
    model: Any | None = None,
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

    # Load image (T025)
    from bioio import BioImage

    # Robust reader selection for OME-TIFF (especially extensionless artifacts)
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

    # Handle 5D normalization (T026)
    # Squeeze singleton dimensions for cellpose
    # Cellpose expects (Y, X) or (Z, Y, X) or (C, Y, X) or (Z, C, Y, X)
    img = np.squeeze(img_data)

    # Extract and coerce parameters with type safety
    model_type = params.get("model_type", "cyto3")  # string is fine
    diameter = _coerce_param(params.get("diameter", 30.0), float, "diameter")
    flow_threshold = _coerce_param(params.get("flow_threshold", 0.4), float, "flow_threshold")
    cellprob_threshold = _coerce_param(
        params.get("cellprob_threshold", 0.0), float, "cellprob_threshold"
    )
    do_3d = _coerce_param(params.get("do_3D", False), bool, "do_3D")
    channels = params.get("channels", [0, 0])  # array handling is separate
    min_size = _coerce_param(params.get("min_size", 15), int, "min_size")

    # Handle diameter=0 or None as "auto-estimate"
    if diameter is None or diameter == 0:
        diameter = None  # Cellpose will estimate

    # Initialize model if not provided
    if model is None:
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
        channels=channels,
        min_size=min_size,
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

    from bioio.writers import OmeTiffWriter

    # Determine dim order based on array shape
    if masks_out.ndim == 2:
        dim_order = "YX"
    elif masks_out.ndim == 3:
        dim_order = "ZYX"
    elif masks_out.ndim == 4:
        dim_order = "CZYX"
    else:
        dim_order = "TCZYX"[-masks_out.ndim :]

    OmeTiffWriter.save(masks_out, str(labels_path), dim_order=dim_order)

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
