from __future__ import annotations

from pathlib import Path

import numpy as np
from bioimage_mcp_base.utils import load_image_fallback, uri_to_path


def convert_to_ome_zarr(*, inputs: dict, params: dict, work_dir: Path) -> Path:
    _ = params
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    in_path = uri_to_path(str(uri))

    try:
        import zarr
        from bioio import BioImage  # type: ignore
    except Exception as exc:
        raise RuntimeError("Missing dependencies for convert_to_ome_zarr") from exc

    img = BioImage(str(in_path))
    data = img.get_image_data()  # type: ignore[attr-defined]

    out_dir = work_dir / "converted.ome.zarr"
    if out_dir.exists():
        raise FileExistsError(out_dir)

    root = zarr.open_group(str(out_dir), mode="w")
    root.create_dataset("0", data=data, chunks=True)
    return out_dir


def export_ome_tiff(*, inputs: dict, params: dict, work_dir: Path) -> dict:
    """Export image to OME-TIFF format.

    Returns a dict with 'path' and 'warnings' keys.
    """
    image_ref = inputs.get("image") or {}
    uri = image_ref.get("uri")
    if not uri:
        raise ValueError("Input 'image' must include uri")

    in_path = uri_to_path(str(uri))
    compression = params.get("compression")
    input_format = (image_ref.get("format") or "").lower()

    try:
        from bioio.writers import OmeTiffWriter  # type: ignore
    except Exception as exc:
        raise RuntimeError("Missing dependencies for export_ome_tiff") from exc

    # Load data based on format
    data = None
    warnings: list[dict[str, str]] = []

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
                    if size_bytes > 4 * 1024**3:  # 4GB threshold
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
                    if size_bytes > 4 * 1024**3:
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
