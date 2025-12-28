from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from bioimage_mcp_base.utils import (
    _load_image_fallback_with_readers,
    _try_bioio_bioformats,
    _try_bioio_ome_tiff,
    uri_to_path,
)

__all__ = [
    "convert_to_ome_zarr",
    "export_ome_tiff",
    "load_image_fallback",
    "_try_bioio_ome_tiff",
    "_try_bioio_bioformats",
]


DEFAULT_OVERSIZED_INPUT_THRESHOLD_BYTES = 4 * 1024**3


def _get_oversized_input_threshold_bytes() -> int:
    env_value = os.environ.get("BIOIMAGE_MCP_OVERSIZED_INPUT_THRESHOLD_BYTES")
    if not env_value:
        return DEFAULT_OVERSIZED_INPUT_THRESHOLD_BYTES
    try:
        threshold = int(env_value)
    except ValueError:
        return DEFAULT_OVERSIZED_INPUT_THRESHOLD_BYTES
    if threshold <= 0:
        return DEFAULT_OVERSIZED_INPUT_THRESHOLD_BYTES
    return threshold


def load_image_fallback(path: Path) -> tuple[np.ndarray, list[dict[str, str]], str]:
    """Proxy to utils.load_image_fallback with patchable readers."""
    return _load_image_fallback_with_readers(
        path,
        _try_bioio_ome_tiff,
        _try_bioio_bioformats,
    )


def _extract_image_uri(image_ref: object) -> str | None:
    if isinstance(image_ref, str):
        return image_ref
    if isinstance(image_ref, dict):
        return str(image_ref.get("uri") or image_ref.get("path") or "") or None
    return None


def convert_to_ome_zarr(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    _ = params
    image_ref = inputs.get("image")
    uri = _extract_image_uri(image_ref)
    if not uri:
        raise ValueError("Input 'image' must include uri")

    in_path = uri_to_path(str(uri))

    try:
        import zarr
    except Exception as exc:
        raise RuntimeError("Missing dependencies for convert_to_ome_zarr") from exc

    try:
        from bioio import BioImage  # type: ignore

        img = BioImage(str(in_path))
        data = img.get_image_data()  # type: ignore[attr-defined]
    except Exception:
        data, _warnings, _reader = load_image_fallback(in_path)

    out_dir = work_dir / "converted.ome.zarr"
    if out_dir.exists():
        raise FileExistsError(out_dir)

    root = zarr.open_group(str(out_dir), mode="w")
    root.create_array("0", data=data, chunks=data.shape)
    return out_dir


def export_ome_tiff(*, inputs: dict, params: dict, work_dir: Path) -> dict:
    """Export image to OME-TIFF format.

    Returns a dict with 'path' and 'warnings' keys.
    """
    image_ref = inputs.get("image")
    uri = _extract_image_uri(image_ref)
    if not uri:
        raise ValueError("Input 'image' must include uri")

    in_path = uri_to_path(str(uri))
    compression = params.get("compression")
    input_format = (image_ref.get("format") or "").lower() if isinstance(image_ref, dict) else ""

    try:
        from bioio.writers import OmeTiffWriter  # type: ignore
    except Exception as exc:
        raise RuntimeError("Missing dependencies for export_ome_tiff") from exc

    # Load data based on format
    data = None
    warnings: list[dict[str, str]] = []
    oversized_threshold = _get_oversized_input_threshold_bytes()

    # Handle OME-Zarr directories
    if "zarr" in input_format or in_path.suffix.lower() == ".zarr" or in_path.is_dir():
        try:
            import zarr

            root = zarr.open_group(str(in_path), mode="r")
            # Try common array paths in zarr stores
            for array_path in ["0", "data", "image"]:
                if array_path in root:
                    arr = root[array_path]
                    # Check size before full materialization
                    size_bytes = arr.nbytes if hasattr(arr, "nbytes") else 0
                    if size_bytes > oversized_threshold:
                        gb_size = size_bytes / 1024**3
                        warnings.append(
                            {
                                "code": "LARGE_ZARR_MATERIALIZATION",
                                "message": (
                                    f"Materializing large OME-Zarr array ({gb_size:.1f}GB). "
                                    "This may consume significant memory."
                                ),
                            }
                        )
                    data = arr[:]
                    break
            if data is None:
                # Try first array found
                for key in root.array_keys():
                    arr = root[key]
                    size_bytes = arr.nbytes if hasattr(arr, "nbytes") else 0
                    if size_bytes > oversized_threshold:
                        gb_size = size_bytes / 1024**3
                        warnings.append(
                            {
                                "code": "LARGE_ZARR_MATERIALIZATION",
                                "message": (
                                    f"Materializing large OME-Zarr array ({gb_size:.1f}GB). "
                                    "This may consume significant memory."
                                ),
                            }
                        )
                    data = arr[:]
                    break
        except Exception:
            pass

    # Try BioImage for other formats
    if data is None:
        data, fallback_warnings, _ = load_image_fallback(in_path)
        warnings.extend(fallback_warnings)

    out_path = work_dir / "export.ome.tiff"
    if out_path.exists():
        raise FileExistsError(out_path)

    # Convert uint64/int64 to float64 for OmeTiffWriter compatibility
    # OmeTiffWriter doesn't support uint64, but float64 preserves values for typical sums
    original_dtype = data.dtype
    if data.dtype == np.uint64:
        warnings.append(
            {
                "code": "DTYPE_CONVERSION",
                "message": (
                    f"Converting {original_dtype} to float64 for OME-TIFF export. "
                    "Integer values >2^53 may lose precision. "
                    "Avoid using this on label/mask data where exact integer values are required."
                ),
            }
        )
        data = data.astype(np.float64)
    elif data.dtype == np.int64:
        warnings.append(
            {
                "code": "DTYPE_CONVERSION",
                "message": (
                    f"Converting {original_dtype} to float64 for OME-TIFF export. "
                    "Integer values >2^53 may lose precision. "
                    "Avoid using this on label/mask data where exact integer values are required."
                ),
            }
        )
        data = data.astype(np.float64)

    OmeTiffWriter.save(data, str(out_path), compression=compression)
    return {
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "path": str(out_path),
            }
        },
        "warnings": warnings,
        "log": "ok",
    }
