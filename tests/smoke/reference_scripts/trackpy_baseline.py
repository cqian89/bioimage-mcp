from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

import numpy as np
import trackpy as tp
from bioio import BioImage
import pandas as pd


def set_seeds(seed: int = 42):
    """Set random seeds for reproducibility."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)


def main():
    parser = argparse.ArgumentParser(description="Run Trackpy locate baseline.")
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument("--output", required=True, help="Path to save results (CSV)")
    parser.add_argument("--diameter", type=int, default=11, help="Feature diameter")
    parser.add_argument("--minmass", type=float, default=0, help="Minimum mass")
    parser.add_argument("--invert", action="store_true", help="Invert image (for dark features)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()
    set_seeds(args.seed)

    input_path = Path(args.input)
    output_path = Path(args.output)

    # Load image via BioImage (matches MCP tool behavior)
    img = BioImage(input_path)

    # Extract data values and squeeze to 2D/3D as trackpy expects
    # BioImage.data is usually (C, Z, Y, X) or similar
    data = img.data.squeeze()
    if hasattr(data, "values"):
        data = data.values

    # Run native trackpy.locate
    # Note: trackpy.locate returns a pandas DataFrame
    f = tp.locate(data, args.diameter, minmass=args.minmass, invert=args.invert)

    # Save output as CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    f.to_csv(output_path, index=False)

    # Print JSON result contract to stdout for NativeExecutor to capture
    print(
        json.dumps(
            {
                "status": "success",
                "output_path": str(output_path),
                "n_features": len(f),
                "columns": list(f.columns),
                "params": {
                    "diameter": args.diameter,
                    "minmass": args.minmass,
                    "invert": args.invert,
                    "seed": args.seed,
                },
            }
        )
    )


if __name__ == "__main__":
    main()
