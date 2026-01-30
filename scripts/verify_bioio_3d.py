from __future__ import annotations

from pathlib import Path

import numpy as np
from bioio import BioImage
from bioio.writers import OmeTiffWriter


def verify_3d_roundtrip():
    # 1. Create a 3D ndarray (e.g., ZYX)
    data = np.zeros((10, 256, 256), dtype=np.uint16)
    data[5, 128, 128] = 1000  # Add a spot

    test_file = Path("test_3d.ome.tiff")

    print(f"Original shape: {data.shape}")

    # 2. Save via OmeTiffWriter
    # bioio OmeTiffWriter.save expects data in TCZYX or with axes specified
    # If we just pass a 3D array, let's see what it does.
    try:
        OmeTiffWriter.save(data, test_file)
        print("Saved without explicit axes.")
    except Exception as e:
        print(f"Failed to save without axes: {e}")
        # Try again with TCZYX expansion or explicit axes
        # Most bioio writers assume TCZYX if not told otherwise
        OmeTiffWriter.save(data, test_file, dim_order="ZYX")
        print("Saved with dim_order='ZYX'.")

    # 3. Read back using BioImage
    img = BioImage(test_file)

    # 4. Check img.reader.dims
    print(f"img.dims: {img.dims}")
    print(f"img.reader.dims: {img.reader.dims}")
    print(f"img.reader.dims type: {type(img.reader.dims)}")

    # Check if there are other dimension-related metadata
    # bioio_base.Dimensions usually has a .order or similar
    try:
        print(f"img.reader.dims.order: {img.reader.dims.order}")
    except AttributeError:
        pass

    # 5. Try with explicit dim_order
    test_file_2 = Path("test_3d_cyx.ome.tiff")
    OmeTiffWriter.save(data, test_file_2, dim_order="CYX")
    img_2 = BioImage(test_file_2)
    print(f"\nSaved as CYX, read back dims: {img_2.reader.dims}")

    # 6. Try with a 3D array that looks like RGB or CYX (small first dim)
    data_small = np.zeros((3, 256, 256), dtype=np.uint16)
    test_file_3 = Path("test_3d_small.ome.tiff")
    OmeTiffWriter.save(data_small, test_file_3)
    img_3 = BioImage(test_file_3)
    print(f"\nSaved (3, 256, 256) without axes, read back dims: {img_3.reader.dims}")

    # Cleanup
    if test_file_3.exists():
        test_file_3.unlink()


def verify_explicit_dims():
    print("\n--- Verifying Explicit Dims ---")
    data_3d = np.zeros((10, 256, 256), dtype=np.uint16)

    # Case A: 3D array with explicit 3D dim_order
    test_a = Path("test_3d_explicit.ome.tiff")
    OmeTiffWriter.save(data_3d, test_a, dim_order="CYX")
    img_a = BioImage(test_a)
    print(f"3D data + dim_order='CYX' -> {img_a.reader.dims}")

    # Case B: 4D array with explicit 4D dim_order
    data_4d = np.zeros((2, 10, 256, 256), dtype=np.uint16)
    test_b = Path("test_4d_explicit.ome.tiff")
    OmeTiffWriter.save(data_4d, test_b, dim_order="ZCYX")
    img_b = BioImage(test_b)
    print(f"4D data (2, 10, 256, 256) + dim_order='ZCYX' -> {img_b.reader.dims}")

    # Case C: 3D array with explicit 4D dim_order (mismatch)
    test_c = Path("test_mismatch.ome.tiff")
    print("Testing 3D data + dim_order='ZCYX' (mismatch)...")
    try:
        OmeTiffWriter.save(data_3d, test_c, dim_order="ZCYX")
        img_c = BioImage(test_c)
        print(f"Result: {img_c.reader.dims}")
    except Exception as e:
        print(f"Caught expected error: {e}")

    # Cleanup
    for p in [test_a, test_b, test_c]:
        if p.exists():
            p.unlink()


if __name__ == "__main__":
    verify_3d_roundtrip()
    verify_explicit_dims()
