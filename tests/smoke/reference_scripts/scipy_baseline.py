from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from bioio import BioImage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input image path")
    parser.add_argument("--sigma", type=float, default=1.0, help="Gaussian sigma")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(json.dumps({"status": "error", "message": f"Input not found: {args.input}"}))
        sys.exit(1)

    # Load image using BioImage
    img = BioImage(input_path)
    # Get the data as a numpy array.
    data = img.reader.data
    if hasattr(data, "compute"):
        data = data.compute()

    # Run gaussian filter
    # Note: scipy.ndimage.gaussian_filter works on the whole array
    result = ndimage.gaussian_filter(data, sigma=args.sigma)

    # Save as .npy for easy comparison in the test
    # We'll save it in the same directory as a temporary file
    import tempfile

    fd, output_path = tempfile.mkstemp(suffix=".npy")
    import os

    os.close(fd)

    np.save(output_path, result)

    # Output JSON contract
    print(
        json.dumps(
            {
                "status": "success",
                "output_path": output_path,
                "shape": list(result.shape),
                "dtype": str(result.dtype),
            }
        )
    )


if __name__ == "__main__":
    main()
