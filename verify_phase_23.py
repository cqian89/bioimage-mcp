import asyncio
import os
import subprocess
from pathlib import Path


def create_sample_data():
    """Ensure sample data exists for verification."""
    # 2D image
    img_2d = Path("datasets/synthetic/test_2d.tif")
    if not img_2d.exists():
        img_2d.parent.mkdir(parents=True, exist_ok=True)
        import numpy as np
        import tifffile

        img = np.random.randint(0, 255, (128, 128), dtype=np.uint8)
        tifffile.imwrite(img_2d, img)

    # 3D image
    img_3d = Path("datasets/synthetic/test_3d.tif")
    if not img_3d.exists():
        import numpy as np
        import tifffile

        img = np.random.randint(0, 255, (16, 128, 128), dtype=np.uint8)
        tifffile.imwrite(img_3d, img)

    # Tracking (Time-series)
    img_tracking = Path("datasets/synthetic/test_tracking.tif")
    if not img_tracking.exists():
        import numpy as np
        import tifffile

        img = np.random.randint(0, 255, (10, 128, 128), dtype=np.uint8)
        tifffile.imwrite(img_tracking, img)

    return img_2d, img_3d, img_tracking


async def verify_phase_23():
    print("=== Phase 23: Interactive Bridge Verification ===")
    img_2d, img_3d, img_tracking = create_sample_data()

    print("\nInstructions:")
    print("1. We will launch 3 annotators sequentially.")
    print("2. For each, verify napari opens with the image.")
    print("3. For the first one, keep it open and check responsiveness in another terminal:")
    print("   'bioimage-mcp list --tool micro_sam'")
    print("4. Add labels, close napari, and verify run success.")

    tools = [
        ("2D Annotator", "micro_sam.sam_annotator.annotator_2d", img_2d),
        ("3D Annotator", "micro_sam.sam_annotator.annotator_3d", img_3d),
        ("Tracking Annotator", "micro_sam.sam_annotator.annotator_tracking", img_tracking),
    ]

    for label, tool_id, img_path in tools:
        print(f"\n--- Testing {label} ---")
        cmd = [
            "python",
            "-m",
            "bioimage_mcp",
            "run",
            tool_id,
            "--input",
            f"image={img_path.absolute()}",
        ]
        print(f"Running: {' '.join(cmd)}")

        # Start the process
        proc = subprocess.Popen(cmd)
        print("Waiting for you to finish with the GUI...")
        proc.wait()

        if proc.returncode == 0:
            print(f"✓ {label} completed successfully.")
        else:
            print(f"✗ {label} failed with exit code {proc.returncode}.")
            break

    print("\nVerification session finished.")


if __name__ == "__main__":
    asyncio.run(verify_phase_23())
