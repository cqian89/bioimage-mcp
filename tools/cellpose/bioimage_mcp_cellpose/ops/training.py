"""Cellpose training operation.

Implements the cellpose.train_seg function for bioimage-mcp.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from bioio import BioImage

from .utils import _coerce_param, _uri_to_path


def run_train_seg(
    inputs: dict[str, Any],
    params: dict[str, Any],
    work_dir: Path,
    model: Any | None = None,
) -> dict[str, Any]:
    """Train or fine-tune a Cellpose model.

    Args:
        inputs: Input artifact references (must include 'image' and 'mask')
        params: Training parameters (model_type, n_epochs, learning_rate, etc.)
        work_dir: Working directory for output files

    Returns:
        Dict with output paths for weights and losses
    """
    import shutil

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
    print(f"Loading image from {image_path}")
    bio_img = BioImage(image_path)
    img_data = bio_img.reader.data
    img_data = img_data.compute() if hasattr(img_data, "compute") else img_data

    print(f"Loading mask from {mask_path}")
    bio_mask = BioImage(mask_path)
    mask_data = bio_mask.reader.data
    mask_data = mask_data.compute() if hasattr(mask_data, "compute") else mask_data

    # Squeeze to 2D/3D (Cellpose expects list of arrays)
    img = np.squeeze(img_data)
    mask = np.squeeze(mask_data)

    # Params with coercion
    model_type = params.get("model_type", "cyto3")
    n_epochs = _coerce_param(params.get("n_epochs", 10), int, "n_epochs")
    learning_rate = _coerce_param(params.get("learning_rate", 0.1), float, "learning_rate")
    weight_decay = _coerce_param(params.get("weight_decay", 0.0001), float, "weight_decay")
    batch_size = _coerce_param(params.get("batch_size", 8), int, "batch_size")
    channels = params.get("channels", [0, 0])
    gpu = _coerce_param(params.get("gpu", torch.cuda.is_available()), bool, "gpu")
    model_name = params.get("model_name", "finetuned_model")
    user_save_path_str = params.get("save_path")

    # Initialize model if not provided
    if model is None:
        print(f"Initializing Cellpose model: {model_type} (GPU={gpu})")
        model = CellposeModel(model_type=model_type, gpu=gpu)

    # Train
    train_data = [img]
    train_labels = [mask]

    # Use work_dir for saving (Internal Provenance)
    internal_save_path = work_dir / "models"
    internal_save_path.mkdir(parents=True, exist_ok=True)

    from cellpose import train

    print(f"Starting training for {n_epochs} epochs...")
    print(f"Internal save path: {internal_save_path}, Model name: {model_name}")

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
        save_path=str(internal_save_path),
        model_name=model_name,
        min_train_masks=1,
    )

    # train_seg returns (model_path, train_losses, test_losses)
    if isinstance(results, tuple):
        model_weights_path = results[0]
        train_losses = results[1]
    else:
        model_weights_path = results
        train_losses = [0.0] * n_epochs

    # If model_weights_path is None, find it in internal_save_path
    if not model_weights_path:
        weights_files = sorted(list(internal_save_path.glob(f"{model_name}_*")))
        if weights_files:
            model_weights_path = str(weights_files[-1])
        else:
            # Fallback
            model_weights_path = str(internal_save_path / model_name)

    print(f"Training complete. Weights saved to: {model_weights_path}")

    # For losses, use the real losses if available
    losses_path = work_dir / "training_losses.csv"
    losses_df = pd.DataFrame({"epoch": list(range(1, len(train_losses) + 1)), "loss": train_losses})
    losses_df.to_csv(losses_path, index=False)
    print(f"Losses saved to: {losses_path}")

    # Option C: Copy to user-specified path if provided
    user_copy_info = {}
    if user_save_path_str:
        user_save_path = Path(user_save_path_str)

        # Determine if it's a directory or a specific file path
        # If it has an extension, assume it's a file path
        if user_save_path.suffix:
            weights_dest = user_save_path
            target_dir = user_save_path.parent
        else:
            target_dir = user_save_path
            weights_dest = target_dir / Path(model_weights_path).name

        target_dir.mkdir(parents=True, exist_ok=True)

        print(f"Copying model to user path: {weights_dest}")
        shutil.copy2(model_weights_path, weights_dest)

        losses_dest = target_dir / "training_losses.csv"
        print(f"Copying losses to user path: {losses_dest}")
        shutil.copy2(losses_path, losses_dest)

        user_copy_info["user_copy_path"] = str(weights_dest)

    output = {
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

    if user_copy_info:
        output["weights"].update(user_copy_info)

    return output
