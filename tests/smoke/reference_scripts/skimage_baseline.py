from __future__ import annotations

import argparse
import json
from pathlib import Path

from bioio import BioImage
from bioio.writers import OmeTiffWriter
from skimage.filters import gaussian, sobel


def main():
    parser = argparse.ArgumentParser(description="Run skimage filter baseline.")
    parser.add_argument(
        "--filter", required=True, choices=["gaussian", "sobel"], help="Filter to apply"
    )
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument("--output", required=True, help="Path to save output image")
    parser.add_argument("--sigma", type=float, default=1.0, help="Sigma for gaussian filter")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    # Load image
    img = BioImage(input_path)
    # BioImage data is an xarray DataArray. Squeeze to remove singleton dimensions.
    data = img.data.squeeze()

    # Run filter
    data_np = data.values if hasattr(data, "values") else data
    if args.filter == "gaussian":
        # Match MCP tool defaults: preserve_range=False
        result = gaussian(data_np, sigma=args.sigma, preserve_range=False)
    elif args.filter == "sobel":
        result = sobel(data_np)
    else:
        raise ValueError(f"Unknown filter: {args.filter}")

    # Save result as OME-TIFF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    OmeTiffWriter.save(result, output_path)

    # JSON output contract
    print(
        json.dumps(
            {
                "status": "success",
                "filter": args.filter,
                "output_path": str(output_path),
                "shape": list(result.shape),
                "dtype": str(result.dtype),
            }
        )
    )


if __name__ == "__main__":
    main()
