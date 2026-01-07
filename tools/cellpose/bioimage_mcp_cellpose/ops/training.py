"""Cellpose training operation.

Implements the cellpose.train_seg function for bioimage-mcp.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote

import numpy as np
import pandas as pd
from bioio import BioImage


def _uri_to_path(uri: str) -> Path:
    """Convert a file:// URI to a Path."""
    if uri.startswith("file://"):
        # Handle Windows paths that may have extra slash: file:///C:/...
        path_str = uri[7:]  # Remove file://
        if len(path_str) > 2 and path_str[0] == "/" and path_str[2] == ":":
            path_str = path_str[1:]  # Remove leading / for Windows paths
        return Path(unquote(path_str))
    return Path(uri)


def run_train_seg(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    """Train or fine-tune a Cellpose model.

    Args:
        inputs: Input artifact references (must include 'image' and 'mask')
        params: Training parameters (model_type, n_epochs, learning_rate, etc.)
        work_dir: Working directory for output files

    Returns:
        Dict with output paths for weights and losses
    """
    import torch
    from cellpose.models import CellposeModel

    # Get inputs
    image_ref = inputs.get("image") or inputs.get("images", {})
    mask_ref = inputs.get("mask") or inputs.get("labels", {})

    image_uri = image_ref.get("uri", "")
    mask_uri = mask_ref.get("uri", "")

    if not image_uri or not mask_uri:
        raise ValueError("Both 'image' and 'mask' inputs are required for training")

    image_path = _uri_to_path(image_uri)
    mask_path = _uri_to_path(mask_uri)

    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")
    if not mask_path.exists():
        raise FileNotFoundError(f"Input mask not found: {mask_path}")

    # Load data
    bio_img = BioImage(image_path)
    img_data = bio_img.data
    img_data = img_data.compute() if hasattr(img_data, "compute") else img_data

    bio_mask = BioImage(mask_path)
    mask_data = bio_mask.data
    mask_data = mask_data.compute() if hasattr(mask_data, "compute") else mask_data

    # Squeeze to 2D/3D (Cellpose expects list of arrays)
    img = np.squeeze(img_data)
    mask = np.squeeze(mask_data)

    # Params
    model_type = params.get("model_type", "cyto3")
    n_epochs = params.get("n_epochs", 10)
    learning_rate = params.get("learning_rate", 0.1)
    weight_decay = params.get("weight_decay", 0.0001)
    batch_size = params.get("batch_size", 8)
    channels = params.get("channels", [0, 0])
    gpu = params.get("gpu", torch.cuda.is_available())

    # Initialize model
    model = CellposeModel(model_type=model_type, gpu=gpu)

    # Train
    train_data = [img]
    train_labels = [mask]

    # Use work_dir for saving
    save_path = work_dir / "models"
    save_path.mkdir(parents=True, exist_ok=True)

    from cellpose import train

    # Use train_seg directly for better compatibility
    results = train.train_seg(
        model.net,
        train_data=train_data,
        train_labels=train_labels,
        channels=channels,
        n_epochs=n_epochs,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        batch_size=batch_size,
        save_path=str(save_path),
        model_name="finetuned_model",
        min_train_masks=1,
    )

    # train_seg returns (model_path, train_losses, test_losses)
    if isinstance(results, tuple):
        model_weights_path = results[0]
        train_losses = results[1]
    else:
        model_weights_path = results
        train_losses = [0.0] * n_epochs

    # If model_weights_path is None, find it in save_path
    if not model_weights_path:
        weights_files = sorted(list(save_path.glob("finetuned_model_*")))
        if weights_files:
            model_weights_path = str(weights_files[-1])
        else:
            # Fallback
            model_weights_path = str(save_path / "finetuned_model")

    # For losses, use the real losses if available
    losses_path = work_dir / "training_losses.csv"
    losses_df = pd.DataFrame({"epoch": list(range(1, len(train_losses) + 1)), "loss": train_losses})
    losses_df.to_csv(losses_path, index=False)

    return {
        "weights": {
            "type": "NativeOutputRef",
            "format": "cellpose-model",
            "path": str(model_weights_path),
        },
        "losses": {
            "type": "TableRef",
            "format": "csv",
            "path": str(losses_path),
        },
    }
