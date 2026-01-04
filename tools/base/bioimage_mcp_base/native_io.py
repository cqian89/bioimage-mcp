from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


def load_native(path: Path) -> tuple[np.ndarray, str, dict]:
    """Load image with native dimensions preserved.

    Uses img.reader.data to bypass bioio's 5D normalization.

    Returns:
        (data, dims, metadata) where dims is e.g. "ZYX" not "TCZYX"
    """
    from bioio import BioImage

    img = BioImage(path)
    reader = img.reader

    # Get native data (not normalized to 5D)
    data = reader.data
    if hasattr(data, "compute"):
        data = data.compute()

    # Get native dimension labels
    dims = reader.dims.order if reader.dims else ""

    # Get metadata from wrapper (safe defaults)
    pps = img.physical_pixel_sizes
    metadata = {
        "physical_pixel_sizes": {
            k: float(v) for k, v in {"X": pps.X, "Y": pps.Y, "Z": pps.Z}.items() if v is not None
        }
        if pps
        else {},
        "channel_names": [str(n) for n in img.channel_names] if img.channel_names else [],
        "dtype": str(data.dtype),
        "shape": list(data.shape),
        "dims": list(dims) if dims else [],
        "ndim": data.ndim,
    }

    return data, dims, metadata
