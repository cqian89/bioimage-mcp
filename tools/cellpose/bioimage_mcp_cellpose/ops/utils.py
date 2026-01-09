"""Shared utilities for Cellpose operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote


def _uri_to_path(uri: str) -> Path:
    """Convert a file:// URI to a Path."""
    if uri.startswith("file://"):
        # Handle Windows paths that may have extra slash: file:///C:/...
        path_str = uri[7:]  # Remove file://
        if len(path_str) > 2 and path_str[0] == "/" and path_str[2] == ":":
            path_str = path_str[1:]  # Remove leading / for Windows paths
        return Path(unquote(path_str))
    return Path(uri)


def _ensure_ome_tiff_compatible(
    image_path: Path,
    image_ref: dict,
    work_dir: Path,
) -> tuple[Path, Any]:
    """Ensure image is in OME-TIFF compatible format for Cellpose.

    Transparently converts OME-Zarr to OME-TIFF if needed.

    Args:
        image_path: Path to the input image
        image_ref: Artifact reference dict with format metadata
        work_dir: Working directory for temporary files

    Returns:
        Tuple of (path_to_use, reader_hint)
    """
    input_format = image_ref.get("format", "").lower()

    # If already OME-TIFF compatible, return original path
    if "zarr" not in input_format:
        reader = None
        if input_format == "ome-tiff":
            try:
                import bioio_ome_tiff

                reader = bioio_ome_tiff.Reader
            except ImportError:
                pass
        return image_path, reader

    # Convert OME-Zarr to OME-TIFF
    import numpy as np
    from bioio import BioImage
    from bioio.writers import OmeTiffWriter

    # Use OME-Zarr reader
    reader = None
    try:
        from bioio_ome_zarr import Reader as OmeZarrReader

        reader = OmeZarrReader
    except ImportError:
        pass

    bio_img = BioImage(image_path, reader=reader)
    data = bio_img.data
    data = data.compute() if hasattr(data, "compute") else data

    # Write to temporary OME-TIFF
    temp_path = work_dir / "converted_input.ome.tiff"

    # Ensure 5D for OmeTiffWriter
    while data.ndim < 5:
        data = np.expand_dims(data, axis=0)

    OmeTiffWriter.save(data, str(temp_path), dim_order="TCZYX")

    # Return converted path with OME-TIFF reader hint
    tiff_reader = None
    try:
        import bioio_ome_tiff

        tiff_reader = bioio_ome_tiff.Reader
    except ImportError:
        pass

    return temp_path, tiff_reader


def _coerce_param(value: Any, param_type: type, param_name: str) -> Any:
    """Coerce parameter to expected type with helpful error messages.

    Args:
        value: The parameter value (might be wrong type)
        param_type: Expected type (int, float, bool)
        param_name: Name of parameter for error messages

    Returns:
        The value coerced to the expected type

    Raises:
        ValueError: If coercion fails
    """
    if value is None:
        return None

    if isinstance(value, param_type):
        return value

    try:
        if param_type is bool:
            # Handle string booleans
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        return param_type(value)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Parameter '{param_name}' must be {param_type.__name__}, "
            f"got {type(value).__name__}: {value!r}"
        ) from e
