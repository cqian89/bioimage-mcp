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
    warnings: list[dict[str, str]] = []
    try:
        from bioio import BioImage  # type: ignore

        img = BioImage(str(path))
        return img.get_image_data(), warnings  # type: ignore[attr-defined]
    except Exception as exc:
        # Fallback: use tifffile for TIFF files with incompatible OME-XML metadata
        import tifffile

        warnings.append(
            {
                "code": "TIFFFILE_FALLBACK",
                "message": (
                    f"BioImage failed to load file ({type(exc).__name__}); "
                    "using tifffile fallback. Metadata may be incomplete."
                ),
            }
        )
        return tifffile.imread(str(path)), warnings


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
