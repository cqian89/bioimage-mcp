"""Cellpose metrics operations.

Implements cellpose.metrics functions for bioimage-mcp.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import numpy as np


def _uri_to_path(uri: str) -> Path:
    """Convert a file:// URI to a Path."""
    if uri.startswith("file://"):
        path_str = uri[7:]
        if len(path_str) > 2 and path_str[0] == "/" and path_str[2] == ":":
            path_str = path_str[1:]
        return Path(unquote(path_str))
    return Path(uri)


def run_average_precision(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    """Compute average precision between predicted and ground truth masks.

    Args:
        inputs: Input artifact references (masks_pred, masks_true)
        params: Parameters (threshold list)
        work_dir: Working directory for output files

    Returns:
        Dict with results TableRef containing AP values
    """
    from bioio import BioImage
    from cellpose import metrics

    # Load predicted masks
    pred_ref = inputs.get("masks_pred", {})
    pred_uri = pred_ref.get("uri", "")
    if not pred_uri:
        raise ValueError("No masks_pred input provided")
    pred_path = _uri_to_path(pred_uri)
    pred_bio = BioImage(pred_path)
    pred_data = pred_bio.reader.data
    pred_data = pred_data.compute() if hasattr(pred_data, "compute") else pred_data
    masks_pred = np.squeeze(pred_data).astype(np.int32)

    # Load true masks
    true_ref = inputs.get("masks_true", {})
    true_uri = true_ref.get("uri", "")
    if not true_uri:
        raise ValueError("No masks_true input provided")
    true_path = _uri_to_path(true_uri)
    true_bio = BioImage(true_path)
    true_data = true_bio.reader.data
    true_data = true_data.compute() if hasattr(true_data, "compute") else true_data
    masks_true = np.squeeze(true_data).astype(np.int32)

    # Get thresholds parameter
    thresholds = params.get("threshold", [0.5, 0.75, 0.9])

    # Compute average precision
    # metrics.average_precision returns (ap, tp, fp, fn)
    ap, tp, fp, fn = metrics.average_precision(masks_true, masks_pred, threshold=thresholds)

    # Build results
    results = {
        "thresholds": thresholds,
        "average_precision": ap.tolist() if hasattr(ap, "tolist") else list(ap),
        "true_positives": tp.tolist() if hasattr(tp, "tolist") else list(tp),
        "false_positives": fp.tolist() if hasattr(fp, "tolist") else list(fp),
        "false_negatives": fn.tolist() if hasattr(fn, "tolist") else list(fn),
    }

    # Write results to JSON
    results_path = work_dir / "average_precision_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    return {
        "results": {
            "type": "TableRef",
            "format": "json",
            "path": str(results_path),
        }
    }
