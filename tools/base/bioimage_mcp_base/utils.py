from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

AXIS_ALIASES = {
    "z": 0,
    "y": -2,
    "x": -1,
    "c": -1,
    "t": 0,
}


def uri_to_path(uri: str) -> Path:
    if uri.startswith("file://"):
        path_str = uri[7:]
        if len(path_str) > 2 and path_str[0] == "/" and path_str[2] == ":":
            path_str = path_str[1:]
        return Path(path_str)
    return Path(uri)


def _try_bioio_ome_tiff(path: Path) -> np.ndarray:
    """Try loading with bioio-ome-tiff reader."""
    try:
        from bioio import BioImage
        from bioio_ome_tiff import Reader as OmeTiffReader

        img = BioImage(str(path), reader=OmeTiffReader)
        return img.get_image_data()
    except ImportError:
        raise RuntimeError("bioio-ome-tiff not available") from None


def _try_bioio_bioformats(path: Path) -> np.ndarray:
    """Try loading with bioio-bioformats reader."""
    try:
        from bioio import BioImage
        from bioio_bioformats import Reader as BioformatsReader

        img = BioImage(str(path), reader=BioformatsReader)
        return img.get_image_data()
    except ImportError:
        raise RuntimeError("bioio-bioformats not available") from None


def _load_image_fallback_with_readers(
    path: Path,
    try_ome_tiff,
    try_bioformats,
) -> tuple[np.ndarray, list[dict[str, str]], str]:
    """Load image with explicit fallback chain using supplied readers."""
    import tifffile

    warnings: list[dict[str, str]] = []

    # 1. Try bioio-ome-tiff
    try:
        data = try_ome_tiff(path)
        return data, warnings, "bioio-ome-tiff"
    except Exception as e:
        warnings.append(
            {
                "code": "OME_TIFF_FALLBACK",
                "message": f"bioio-ome-tiff failed: {e}",
            }
        )

    # 2. Try bioio-bioformats
    try:
        data = try_bioformats(path)
        return data, warnings, "bioio-bioformats"
    except Exception as e:
        warnings.append(
            {
                "code": "BIOFORMATS_FALLBACK",
                "message": f"bioio-bioformats failed: {e}",
            }
        )

    # 3. Final fallback to tifffile
    warnings.append(
        {
            "code": "TIFFFILE_FALLBACK",
            "message": "Using tifffile - metadata may be incomplete",
        }
    )
    data = tifffile.imread(str(path))
    return data, warnings, "tifffile"


def load_image_fallback(path: Path) -> tuple[np.ndarray, list[dict[str, str]], str]:
    """Load image with explicit fallback chain.

    Tries readers in order:
    1. bioio-ome-tiff (fast, pure Python)
    2. bioio-bioformats (heavier, Java-based, more compatible)
    3. tifffile (minimal fallback, raw pixels only)

    Args:
        path: Path to the image file

    Returns:
        Tuple of (data, warnings, reader_used) where:
        - data: numpy array of image data
        - warnings: list of warning dicts with 'code' and 'message' keys
        - reader_used: string identifying which reader succeeded
    """
    return _load_image_fallback_with_readers(
        path,
        _try_bioio_ome_tiff,
        _try_bioio_bioformats,
    )


def load_image(path: Path) -> np.ndarray:
    """Load an image from disk, with fallback for unsupported formats.

    Tries BioImage first, falls back to tifffile for files with
    OME-XML metadata that bioio cannot parse.

    Note: For operations that need to track fallback usage, use
    load_image_with_warnings() instead.
    """
    data, _ = load_image_with_warnings(path)
    return data


def load_image_with_warnings(path: Path) -> tuple[np.ndarray, list[dict[str, str]]]:
    """Load an image from disk, returning data and any warnings.

    Tries BioImage first, falls back to tifffile for files with
    OME-XML metadata that bioio cannot parse.

    Returns:
        Tuple of (data, warnings) where warnings is a list of warning
        dicts with 'code' and 'message' keys.
    """
    data, warnings, _ = load_image_fallback(path)
    return data, warnings


def save_zarr(data: np.ndarray, work_dir: Path, name: str) -> Path:
    import zarr

    out_dir = work_dir / name
    if out_dir.exists():
        raise FileExistsError(out_dir)
    root = zarr.open_group(str(out_dir), mode="w")
    root.create_array("0", data=data, chunks=data.shape)
    return out_dir


def resolve_axis(axis: Any, ndim: int) -> int:
    if isinstance(axis, str):
        idx = AXIS_ALIASES.get(axis.lower())
        if idx is None:
            raise ValueError(f"Unknown axis: {axis}")
        axis = idx
    axis = int(axis)
    if axis < 0:
        axis += ndim
    if axis < 0 or axis >= ndim:
        raise ValueError(f"Axis {axis} out of bounds for ndim={ndim}")
    return axis
