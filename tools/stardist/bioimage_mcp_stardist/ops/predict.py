from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .utils import _coerce_param, _uri_to_path


def run_predict(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
    model: Any | None = None,
) -> dict[str, Any]:
    """Run StarDist inference on an input image.

    Args:
        inputs: Input artifact references (must include 'image')
        params: Inference parameters (prob_thresh, nms_thresh, etc.)
        work_dir: Working directory for output files
        model: Optional pre-initialized model object

    Returns:
        Dict with output artifact details for 'labels' and 'details'
    """
    from bioio import BioImage
    from csbdeep.utils import normalize

    # 1. Get input image
    image_ref = inputs.get("image", {})
    image_uri = image_ref.get("uri", "")
    if not image_uri:
        raise ValueError("No image input provided")

    image_path = _uri_to_path(image_uri)
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    # 2. Load and normalize image
    bio_img = BioImage(image_path)
    # Preservation of native axes: stardist expects (Y, X) or (Z, Y, X)
    # We should squeeze singleton dimensions
    img_data = bio_img.reader.data
    img_data = img_data.compute() if hasattr(img_data, "compute") else img_data
    img = np.squeeze(img_data)

    # StarDist expects float32 normalized image
    img = normalize(img)

    # 3. Model check
    if model is None:
        raise ValueError("StarDist model must be provided via ObjectRef")

    # 4. Extract parameters
    prob_thresh = _coerce_param(params.get("prob_thresh"), float, "prob_thresh")
    nms_thresh = _coerce_param(params.get("nms_thresh"), float, "nms_thresh")
    n_tiles = params.get("n_tiles")  # Should be a tuple/list matching dims

    # 5. Run inference
    # predict_instances returns (labels, details)
    # labels: ndarray
    # details: dict with 'coord', 'prob', 'dist', 'points'
    predict_kwargs = {}
    if prob_thresh is not None:
        predict_kwargs["prob_thresh"] = prob_thresh
    if nms_thresh is not None:
        predict_kwargs["nms_thresh"] = nms_thresh
    if n_tiles is not None:
        predict_kwargs["n_tiles"] = n_tiles

    labels, details = model.predict_instances(img, **predict_kwargs)

    # 6. Save results
    labels_path = work_dir / "labels.ome.zarr"
    details_path = work_dir / "details.json"

    # Write labels as OME-Zarr
    from bioio_ome_zarr.writers import OMEZarrWriter

    # Convert to uint16/uint32 for label images
    if labels.max() < 65536:
        labels_out = labels.astype(np.uint16)
    else:
        labels_out = labels.astype(np.uint32)

    # Determine axes names
    if labels_out.ndim == 2:
        axes_names = ["y", "x"]
        axes_types = ["space", "space"]
    elif labels_out.ndim == 3:
        axes_names = ["z", "y", "x"]
        axes_types = ["space", "space", "space"]
    else:
        axes_names = [d.lower() for d in "TCZYX"[-labels_out.ndim :]]
        type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
        axes_types = [type_map.get(d, "space") for d in axes_names]

    writer = OMEZarrWriter(
        store=str(labels_path),
        level_shapes=[labels_out.shape],
        dtype=labels_out.dtype,
        axes_names=axes_names,
        axes_types=axes_types,
        zarr_format=2,
    )
    writer.write_full_volume(labels_out)

    # Write details as JSON
    # Convert numpy arrays in details to lists for JSON serialization
    def _make_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: _make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_make_serializable(x) for x in obj]
        return obj

    serializable_details = _make_serializable(details)
    with open(details_path, "w") as f:
        json.dump(serializable_details, f)

    return {
        "labels": {
            "type": "LabelImageRef",
            "format": "OME-Zarr",
            "path": str(labels_path),
            "storage_type": "zarr-temp",
            "metadata": {
                "dims": [d.upper() for d in axes_names],
                "shape": list(labels_out.shape),
                "dtype": str(labels_out.dtype),
            },
        },
        "details": {
            "type": "NativeOutputRef",
            "format": "stardist-details-json",
            "path": str(details_path),
        },
    }
