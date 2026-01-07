from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioimage_mcp.artifacts.models import ArtifactRef
    from bioimage_mcp.artifacts.store import ArtifactStore


def infer_export_format(
    artifact: ArtifactRef | dict[str, Any],
    data_shape: tuple[int, ...] | None = None,
    data_dtype: str | None = None,
) -> str:
    """Infer export format from artifact metadata.

    Args:
        artifact: ArtifactRef or dict containing artifact metadata
        data_shape: Optional actual data shape
        data_dtype: Optional actual data dtype

    Returns:
        Format string (PNG, OME-TIFF, OME-Zarr, CSV)
    """
    if isinstance(artifact, dict):
        a_type = artifact.get("artifact_type") or artifact.get("type")
        metadata = artifact.get("metadata", {})
        size_bytes = artifact.get("size_bytes", 0)
        current_format = artifact.get("format")
        # Check if size_bytes is in metadata (some tests do this)
        if not size_bytes and "size_bytes" in metadata:
            size_bytes = metadata["size_bytes"]
    else:
        # ArtifactRef
        a_type = artifact.type
        metadata = artifact.metadata or {}
        size_bytes = artifact.size_bytes
        current_format = artifact.format

    # Table artifacts -> CSV
    if a_type == "TableRef":
        return "CSV"

    # If it's not a BioImageRef or LabelImageRef, return its current format
    if a_type not in ("BioImageRef", "LabelImageRef"):
        return current_format or "text"

    # Large files -> OME-Zarr
    if size_bytes > 4 * 1024**3:
        return "OME-Zarr"

    ndim = metadata.get("ndim", len(data_shape) if data_shape else 5)
    dtype = metadata.get("dtype", data_dtype or "float32")

    # Determine effective ndim by ignoring singletons
    shape = metadata.get("shape") or data_shape
    if shape:
        effective_ndim = len([d for d in shape if d > 1])
    else:
        effective_ndim = ndim

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


def export_artifact(
    store: ArtifactStore,
    *,
    ref_id: str,
    dest_path: Path,
    format: str | None = None,
) -> Path:
    """Export artifact to specified format.

    Args:
        store: Artifact store
        ref_id: Reference ID of artifact
        dest_path: Destination path
        format: Optional format (PNG, OME-TIFF, OME-Zarr, CSV, NPY)

    Returns:
        Path to exported file
    """
    return store.export(ref_id, dest_path=dest_path, format=format)
