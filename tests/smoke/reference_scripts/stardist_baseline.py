from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description="Run StarDist baseline.")
    parser.add_argument("--input", required=True, help="Path to save input image")
    parser.add_argument("--output", required=True, help="Path to save labels")
    parser.add_argument("--model_name", default="2D_versatile_fluo", help="StarDist model name")
    parser.add_argument(
        "--retries", type=int, default=3, help="Number of retries for model download"
    )

    args = parser.parse_args()

    # Redirect stdout to stderr for everything except our final JSON
    old_stdout = sys.stdout

    class StdoutToStderr:
        def write(self, data):
            sys.stderr.write(data)

        def flush(self):
            sys.stderr.flush()

    sys.stdout = StdoutToStderr()

    try:
        from bioio.writers import OmeTiffWriter
        from csbdeep.utils import normalize
        from stardist.data import test_image_nuclei_2d
        from stardist.models import StarDist2D

        # 1. Generate and save input image
        img = test_image_nuclei_2d()
        input_path = Path(args.input)
        input_path.parent.mkdir(parents=True, exist_ok=True)
        # stardist test image is nuclei, usually grayscale
        OmeTiffWriter.save(img.astype(np.uint16), str(input_path), dim_order="YX")

        # 2. Load model with retries
        model = None
        last_error = None
        for attempt in range(args.retries):
            try:
                # StarDist uses tensorflow which might print a lot to stdout
                model = StarDist2D.from_pretrained(args.model_name)
                if model is not None:
                    break
            except Exception as e:
                last_error = e
                sys.stderr.write(f"Attempt {attempt + 1} failed: {e}\n")
                if attempt < args.retries - 1:
                    wait = 5 * (attempt + 1)
                    sys.stderr.write(f"Waiting {wait}s before retry...\n")
                    time.sleep(wait)

        if model is None:
            raise last_error or RuntimeError(f"Failed to load model {args.model_name}")

        # 3. Predict
        # normalize(img) is standard for StarDist
        labels, _details = model.predict_instances(normalize(img))

        # 4. Save labels
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Labels are instances, uint16 is standard
        OmeTiffWriter.save(labels.astype(np.uint16), str(output_path), dim_order="YX")

        # 5. Success JSON
        sys.stdout = old_stdout  # Restore stdout
        print(
            json.dumps(
                {
                    "status": "success",
                    "input_path": str(input_path),
                    "labels_path": str(output_path),
                    "label_count": int(np.max(labels)),
                }
            )
        )

    except Exception as e:
        sys.stdout = old_stdout
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": str(e),
                }
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
