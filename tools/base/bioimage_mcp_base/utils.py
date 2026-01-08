from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote

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
        return Path(unquote(path_str))
    return Path(uri)


def load_image_fallback(
    path: Path, format_hint: str | None = None
) -> tuple[np.ndarray, list[dict[str, str]], str]:
    """Load image using BioImage.

    If the initial BioImage load fails (e.g. because the file has no extension in the
    artifact store), retry using a temporary symlink with the appropriate extension.
    """
    return _load_image_internal(path, format_hint=format_hint, native=False)


def load_native_image_fallback(
    path: Path, format_hint: str | None = None
) -> tuple[np.ndarray, list[dict[str, str]], str]:
    """Load image using BioImage, preserving native dimensions.

    If the initial BioImage load fails (e.g. because the file has no extension in the
    artifact store), retry using a temporary symlink with the appropriate extension.
    """
    return _load_image_internal(path, format_hint=format_hint, native=True)


def _load_image_internal(
    path: Path, format_hint: str | None = None, native: bool = False
) -> tuple[np.ndarray, list[dict[str, str]], str]:
    """Internal core for image loading."""
    warnings: list[dict[str, str]] = []

    def _get_data(img: BioImage) -> np.ndarray:
        data = img.reader.data if native else img.data
        return data.compute() if hasattr(data, "compute") else data

    try:
        img = BioImage(path)
        return _get_data(img), warnings, "bioio"
    except Exception as first_error:
        # If path has no suffix, try with a temporary symlink with extension
        if not path.suffix:
            import os
            import shutil
            import tempfile

            fmt_lower = (format_hint or "").lower()
            suffix = ".tif"
            if "zarr" in fmt_lower:
                suffix = ".ome.zarr"
            elif "tiff" in fmt_lower or "tif" in fmt_lower:
                suffix = ".ome.tiff"
            elif "png" in fmt_lower:
                suffix = ".png"

            tmp_dir = Path(tempfile.mkdtemp())
            try:
                tmp_file = tmp_dir / f"image{suffix}"
                if path.is_dir():
                    os.symlink(path, tmp_file, target_is_directory=True)
                else:
                    os.symlink(path, tmp_file)

                img = BioImage(tmp_file)
                return _get_data(img), warnings, "bioio+symlink"
            except Exception:
                pass
            finally:
                try:
                    shutil.rmtree(tmp_dir)
                except Exception:
                    pass

        # If symlink trick failed or wasn't applicable, try explicit readers as last resort
        path_str = str(path)
        is_ome_format = format_hint and (
            "OME-TIFF" in format_hint.upper() or "OME-ZARR" in format_hint.upper()
        )

        if not path.suffix or is_ome_format:
            # Try OME-TIFF reader
            if not format_hint or "OME-TIFF" in format_hint.upper() or not path.suffix:
                try:
                    from bioio_ome_tiff.reader import Reader as OmeTiffReader

                    img = BioImage(path_str, reader=OmeTiffReader)
                    return _get_data(img), warnings, "bioio+ome-tiff-reader"
                except Exception:
                    pass

            # Try OME-Zarr reader
            if format_hint and "OME-ZARR" in format_hint.upper():
                try:
                    from bioio_ome_zarr.reader import Reader as OmeZarrReader

                    img = BioImage(path_str, reader=OmeZarrReader)
                    return _get_data(img), warnings, "bioio+ome-zarr-reader"
                except Exception:
                    pass

        raise first_error


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


def load_native_image(path: Path, format_hint: str | None = None) -> np.ndarray:
    """Load an image from disk, preserving native dimensions."""
    data, _ = load_native_image_with_warnings(path, format_hint=format_hint)
    return data


def load_native_image_with_warnings(
    path: Path, format_hint: str | None = None
) -> tuple[np.ndarray, list[dict[str, str]]]:
    """Load an image from disk, preserving native dimensions, returning data and any warnings."""
    data, warnings, _ = load_native_image_fallback(path, format_hint=format_hint)
    return data, warnings


def save_zarr(data: np.ndarray, work_dir: Path, name: str) -> Path:
    """Save array as OME-Zarr."""
    try:
        from bioio_ome_zarr.writers import OMEZarrWriter
    except ImportError:
        import zarr

        out_dir = work_dir / name
        if out_dir.exists():
            raise FileExistsError(out_dir) from None
        root = zarr.open_group(str(out_dir), mode="w")
        root.create_array("0", data=data, chunks=data.shape)
        return out_dir

    out_dir = work_dir / name
    if out_dir.exists():
        raise FileExistsError(out_dir)

    # Ensure 5D for OMEZarrWriter
    data_5d = data
    while data_5d.ndim < 5:
        data_5d = data_5d[np.newaxis, ...]

    full_shape = data_5d.shape
    writer = OMEZarrWriter(
        store=str(out_dir),
        level_shapes=[full_shape],
        dtype=data_5d.dtype,
        zarr_format=2,
    )
    writer.write_full_volume(data_5d)
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
