from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import numpy as np
from bioimage_mcp_base.utils import uri_to_path
from bioio import BioImage
from bioio.writers import OmeTiffWriter
from PIL import Image


def infer_export_format(
    artifact: dict[str, Any],
    data_shape: tuple[int, ...] | None = None,
    data_dtype: str | None = None,
) -> str:
    metadata = artifact.get("metadata", {})
    ndim = metadata.get("ndim", len(data_shape) if data_shape else 5)
    dtype = metadata.get("dtype", data_dtype or "float32")

    # Determine effective ndim by ignoring singletons
    shape = metadata.get("shape") or data_shape or artifact.get("shape")
    if shape:
        effective_ndim = len([d for d in shape if d > 1])
    else:
        effective_ndim = ndim

    # Table artifacts -> CSV
    if artifact.get("type") == "TableRef":
        return "CSV"

    # Large files -> OME-Zarr
    size_bytes = artifact.get("size_bytes", 0)
    if size_bytes > 4 * 1024**3:
        return "OME-Zarr"

    # Simple 2D (or effectively 2D) uint8 -> PNG
    if (ndim == 2 or (effective_ndim <= 2 and ndim > 0)) and str(dtype) in (
        "uint8",
        "uint16",
    ):
        has_rich_metadata = bool(
            metadata.get("physical_pixel_sizes") or metadata.get("channel_names")
        )
        if not has_rich_metadata:
            return "PNG"

    # Default: OME-TIFF for microscopy data
    return "OME-TIFF"


def export_png(data: np.ndarray, path: Path):
    if data.ndim != 2:
        # Squeeze if possible
        if data.ndim > 2:
            data = np.squeeze(data)
            if data.ndim != 2:
                raise ValueError(f"PNG export requires 2D data, got {data.ndim}D")
        else:
            raise ValueError("PNG export requires 2D data")
    Image.fromarray(data).save(path)


def export_ome_tiff(data: np.ndarray, path: Path):
    # Expand to 5D for OME-TIFF compatibility
    while data.ndim < 5:
        data = np.expand_dims(data, axis=0)
    OmeTiffWriter.save(data, str(path), dim_order="TCZYX")


def export_ome_zarr(data: np.ndarray, path: Path, dims: list[str] | None = None):
    try:
        from bioio_ome_zarr.writers import OMEZarrWriter
    except ImportError:
        # Fallback if bioio-ome-zarr is not installed in this env
        raise RuntimeError("bioio-ome-zarr is required for OME-Zarr export")

    # Use native dimensions
    if dims is None:
        if data.ndim == 5:
            dims = ["T", "C", "Z", "Y", "X"]
        else:
            dims = ["T", "C", "Z", "Y", "X"][-data.ndim :]

    axis_type_map = {"t": "time", "c": "channel", "z": "space", "y": "space", "x": "space"}
    axes_names = [d.lower() for d in dims]
    axes_types = [axis_type_map.get(d, "space") for d in axes_names]

    writer = OMEZarrWriter(
        store=str(path),
        level_shapes=[data.shape],
        dtype=data.dtype,
        axes_names=axes_names,
        axes_types=axes_types,
    )
    writer.write_full_volume(data)


def export_csv(artifact: dict[str, Any], dest_path: Path):
    uri = artifact.get("uri", "")
    if not uri:
        raise ValueError("Artifact missing URI")
    src_path = uri_to_path(uri)
    shutil.copy2(src_path, dest_path)


def export(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    """Export artifact to specified format.

    Args:
        inputs: dict containing 'image' or 'table' artifact
        params: dict containing 'format' (optional)
        work_dir: working directory

    Returns:
        dict with 'outputs' key
    """
    artifact = inputs.get("image") or inputs.get("table")
    if not artifact:
        raise ValueError("Missing input 'image' or 'table'")

    dest_format = params.get("format")
    if dest_format is None:
        dest_format = infer_export_format(artifact)

    dest_format = dest_format.upper()

    # Generate output path
    ext_map = {
        "PNG": ".png",
        "OME-TIFF": ".ome.tiff",
        "OME-ZARR": ".ome.zarr",
        "CSV": ".csv",
        "NPY": ".npy",
    }
    ext = ext_map.get(dest_format, ".bin")
    out_path = work_dir / f"exported{ext}"

    if dest_format == "CSV":
        export_csv(artifact, out_path)
    else:
        # Load data for image formats
        uri = artifact.get("uri")
        if not uri:
            raise ValueError("Artifact missing URI")

        in_path = uri_to_path(uri)
        img = BioImage(in_path)
        data = img.data
        data = data.compute() if hasattr(data, "compute") else data

        if dest_format == "PNG":
            export_png(data, out_path)
        elif dest_format == "OME-TIFF":
            export_ome_tiff(data, out_path)
        elif dest_format == "OME-ZARR":
            dims = artifact.get("metadata", {}).get("dims") or artifact.get("dims")
            export_ome_zarr(data, out_path, dims=dims)
        elif dest_format == "NPY":
            np.save(out_path, data)
        else:
            raise ValueError(f"Unsupported export format: {dest_format}")

    result = {
        "outputs": {
            "output": {
                "type": artifact.get("type", "BioImageRef"),
                "format": dest_format,
                "path": str(out_path),
            }
        }
    }

    # Preserve provenance (source_ref_id)
    source_ref_id = artifact.get("ref_id")
    if source_ref_id:
        result["outputs"]["output"].setdefault("metadata", {})["source_ref_id"] = source_ref_id

    return result
