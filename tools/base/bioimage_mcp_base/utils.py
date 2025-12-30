from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from bioio import BioImage

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


def get_bioimage(path: str | Path, format_hint: str | None = None) -> BioImage:
    """Get a BioImage object, optionally with a format hint for extensionless files."""
    if format_hint and format_hint.upper() == "OME-TIFF":
        try:
            import bioio_ome_tiff

            return BioImage(path, reader=bioio_ome_tiff.Reader)
        except ImportError:
            pass
    return BioImage(path)


def load_image_fallback(
    path: Path, format_hint: str | None = None
) -> tuple[np.ndarray, list[dict[str, str]], str]:
    """Load image using BioImage with fallback to tifffile."""
    import tifffile

    warnings: list[dict[str, str]] = []
    try:
        img = get_bioimage(path, format_hint=format_hint)
        data = img.data
        data = data.compute() if hasattr(data, "compute") else data
        return data, warnings, "bioio"
    except Exception as e:
        warnings.append(
            {
                "code": "BIOIMAGE_FALLBACK",
                "message": f"BioImage failed: {e}. Falling back to tifffile.",
            }
        )
        data = tifffile.imread(str(path))
        return data, warnings, "tifffile"


def load_image(path: Path, format_hint: str | None = None) -> np.ndarray:
    """Load an image from disk, with fallback for unsupported formats.

    Tries BioImage first, falls back to tifffile for files with
    OME-XML metadata that bioio cannot parse.

    Note: For operations that need to track fallback usage, use
    load_image_with_warnings() instead.
    """
    data, _ = load_image_with_warnings(path, format_hint=format_hint)
    return data


def load_image_with_warnings(
    path: Path, format_hint: str | None = None
) -> tuple[np.ndarray, list[dict[str, str]]]:
    """Load an image from disk, returning data and any warnings.

    Tries BioImage first, falls back to tifffile for files with
    OME-XML metadata that bioio cannot parse.

    Returns:
        Tuple of (data, warnings) where warnings is a list of warning
        dicts with 'code' and 'message' keys.
    """
    data, warnings, _ = load_image_fallback(path, format_hint=format_hint)
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
