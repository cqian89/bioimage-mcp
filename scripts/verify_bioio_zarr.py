from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
from bioio import BioImage
from bioio_ome_zarr.writers import OMEZarrWriter


def verify_zarr_roundtrip():
    print("--- Verifying OME-Zarr Roundtrip ---")
    # 1. Create a 3D ndarray (e.g., ZYX)
    data = np.zeros((10, 256, 256), dtype=np.uint16)

    test_dir = Path("test_3d.ome.zarr")
    if test_dir.exists():
        shutil.rmtree(test_dir)

    print(f"Original shape: {data.shape}")

    # 2. Save via OMEZarrWriter
    writer = OMEZarrWriter(
        store=str(test_dir),
        level_shapes=[data.shape],
        dtype=data.dtype,
        axes_names=["z", "y", "x"],
        axes_types=["space", "space", "space"],
        zarr_format=2,
    )
    writer.write_full_volume(data)
    print("Saved with axes_names=['z', 'y', 'x'].")

    # 3. Read back using BioImage
    img = BioImage(test_dir)

    # 4. Check img.reader.dims
    print(f"Read back dims: {img.reader.dims}")
    print(f"Read back dims order: {img.reader.dims.order}")

    # 5. Try explicit C instead of Z
    test_dir_2 = Path("test_3d_cyx.ome.zarr")
    if test_dir_2.exists():
        shutil.rmtree(test_dir_2)

    writer_2 = OMEZarrWriter(
        store=str(test_dir_2),
        level_shapes=[data.shape],
        dtype=data.dtype,
        axes_names=["c", "y", "x"],
        axes_types=["channel", "space", "space"],
        zarr_format=2,
    )
    writer_2.write_full_volume(data)
    img_2 = BioImage(test_dir_2)
    print(f"\nSaved with axes_names=['c', 'y', 'x'], read back dims: {img_2.reader.dims}")
    # 6. Check order specifically
    print(f"Read back dims order (C,Y,X): {img_2.reader.dims.order}")
    print(
        f"Read back dims properties (C,Y,X): T={getattr(img_2.reader.dims, 'T', 'N/A')}, C={img_2.reader.dims.C}, Z={getattr(img_2.reader.dims, 'Z', 'N/A')}"
    )

    # Cleanup
    for p in [test_dir, test_dir_2]:
        if p.exists():
            shutil.rmtree(p)


if __name__ == "__main__":
    verify_zarr_roundtrip()
