#!/usr/bin/env python
"""Reference script for phasorpy operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile
from phasorpy.phasor import phasor_from_signal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--axis", type=int, default=0)
    args = parser.parse_args()

    # Load input
    data = tifffile.imread(args.input)

    # Execute native operation
    # phasor_from_signal returns (mean, real, imag)
    mean, real, imag = phasor_from_signal(data, axis=args.axis)

    # Save output as NPY
    combined = np.stack([mean, real, imag])
    np.save(args.output, combined)

    # Output JSON to stdout
    print(
        json.dumps(
            {
                "output_path": str(Path(args.output).absolute()),
                "shape": list(real.shape),
                "dtype": str(real.dtype),
                "real_mean": float(np.mean(real)),
                "imag_mean": float(np.mean(imag)),
            }
        )
    )


if __name__ == "__main__":
    main()
