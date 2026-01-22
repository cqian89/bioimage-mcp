from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

import numpy as np
import torch
from bioio import BioImage
from bioio.writers import OmeTiffWriter
from cellpose import models


def set_seeds(seed: int = 42):
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def main():
    parser = argparse.ArgumentParser(description="Run Cellpose baseline.")
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument("--output", required=True, help="Path to save labels")
    parser.add_argument("--model_type", default="cyto3", help="Cellpose model type")
    parser.add_argument("--diameter", type=float, default=30.0, help="Cell diameter")
    parser.add_argument("--gpu", action="store_true", help="Use GPU")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()
    set_seeds(args.seed)

    input_path = Path(args.input)
    output_path = Path(args.output)

    # Load image
    img = BioImage(input_path)
    # BioImage data is usually an xarray DataArray (C, Z, Y, X).
    # Squeeze to get (Y, X) for 2D grayscale.
    data = img.data.squeeze()
    if hasattr(data, "values"):
        data = data.values

    # Initialize model
    # Note: Using CellposeModel to match the MCP tool's underlying call
    model = models.CellposeModel(model_type=args.model_type, gpu=args.gpu)

    # Run evaluation
    # Default channels=[0,0] for grayscale
    masks, flows, styles = model.eval(
        data,
        diameter=args.diameter,
        channels=[0, 0],
        resample=True,
    )

    # Save masks as OME-TIFF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # MCP tool saves as uint16 or uint32
    if masks.max() < 65536:
        masks_out = masks.astype(np.uint16)
    else:
        masks_out = masks.astype(np.uint32)

    OmeTiffWriter.save(masks_out, str(output_path), dim_order="YX")

    # JSON output contract
    print(
        json.dumps(
            {
                "status": "success",
                "model_type": args.model_type,
                "output_path": str(output_path),
                "shape": list(masks.shape),
                "dtype": str(masks.dtype),
                "n_labels": int(np.max(masks)),
            }
        )
    )


if __name__ == "__main__":
    main()
