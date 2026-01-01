from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from bioimage_mcp_base.utils import load_image_fallback, uri_to_path
from bioio import BioImage
from bioio.writers import OmeTiffWriter

__all__ = [
    "convert_to_ome_zarr",
    "export_ome_tiff",
    "export",
    "load_image_fallback",
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

    # Try to import bioio_ome_zarr writer - if import fails, raise RuntimeError
    try:
        from bioio_ome_zarr.writers import OMEZarrWriter
    except ImportError as exc:
        raise RuntimeError("Missing 'bioio-ome-zarr' dependency for OME-Zarr export") from exc

    # Use BioImage directly for auto-detection
    img = BioImage(str(in_path))
    data = img.data
    data = data.compute() if hasattr(data, "compute") else data

    out_dir = work_dir / "converted.ome.zarr"
    if out_dir.exists():
        raise FileExistsError(out_dir)

    # Use bioio-ome-zarr writer for spec-compliant output
    # Data is 5D TCZYX, level_shapes must match data rank
    full_shape = data.shape

    writer = OMEZarrWriter(
        store=str(out_dir),
        level_shapes=[full_shape],
        dtype=data.dtype,
        zarr_format=2,  # OME-Zarr 0.4 uses Zarr v2
    )
    writer.write_full_volume(data)

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

    warnings: list[dict[str, str]] = []
    oversized_threshold = _get_oversized_input_threshold_bytes()

    try:
        img = BioImage(in_path)
        data = img.data

        # Check size before full materialization
        size_bytes = data.nbytes if hasattr(data, "nbytes") else 0
        if size_bytes > oversized_threshold:
            gb_size = size_bytes / 1024**3
            warnings.append(
                {
                    "code": "LARGE_MATERIALIZATION",
                    "message": (
                        f"Materializing large array ({gb_size:.1f}GB). "
                        "This may consume significant memory."
                    ),
                }
            )

        data = data.compute() if hasattr(data, "compute") else data

        # Preserve physical pixel sizes and channel names
        try:
            physical_pixel_sizes = img.physical_pixel_sizes
        except Exception:
            physical_pixel_sizes = None

        try:
            channel_names = img.channel_names
        except Exception:
            channel_names = None

    except Exception as e:
        warnings.append(
            {
                "code": "BIOIMAGE_LOAD_FAILED",
                "message": f"BioImage failed to load {in_path}: {e}. Using fallback.",
            }
        )
        # Extract format hint from image_ref metadata
        format_hint = None
        if isinstance(image_ref, dict):
            format_hint = image_ref.get("format")
        data, fallback_warnings, _ = load_image_fallback(in_path, format_hint=format_hint)
        warnings.extend(fallback_warnings)
        physical_pixel_sizes = None
        channel_names = None

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

    # Ensure 5D TCZYX
    while data.ndim < 5:
        data = data[np.newaxis, ...]

    OmeTiffWriter.save(
        data,
        str(out_path),
        dim_order="TCZYX",
        physical_pixel_sizes=physical_pixel_sizes,
        channel_names=channel_names,
        compression=compression,
    )
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


def export(*, inputs: dict, params: dict, work_dir: Path) -> dict:
    """Materialize artifact to file-backed artifact.

    Supports OME-TIFF (default) and OME-Zarr.
    """
    image_ref = inputs.get("image") or {}
    source_ref_id = image_ref.get("ref_id")

    fmt = params.get("format", "OME-TIFF")
    if fmt == "OME-TIFF":
        result = export_ome_tiff(inputs=inputs, params=params, work_dir=work_dir)
        if source_ref_id:
            result["outputs"]["output"].setdefault("metadata", {})["source_ref_id"] = source_ref_id
        return result
    if fmt == "OME-Zarr":
        out_path = convert_to_ome_zarr(inputs=inputs, params=params, work_dir=work_dir)
        output_metadata = {}
        if source_ref_id:
            output_metadata["source_ref_id"] = source_ref_id
        return {
            "outputs": {
                "output": {
                    "type": "BioImageRef",
                    "format": "OME-Zarr",
                    "path": str(out_path),
                    "metadata": output_metadata,
                }
            },
            "log": "ok",
        }
    raise ValueError(f"Unsupported export format: {fmt}")
