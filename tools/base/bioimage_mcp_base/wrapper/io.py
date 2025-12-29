from __future__ import annotations

from pathlib import Path
from typing import Any

from bioimage_mcp_base.io import (
    convert_to_ome_zarr as _convert_to_ome_zarr,
    export_ome_tiff as _export_ome_tiff,
)


def convert_to_ome_zarr(*, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path) -> Path:
    """Thin wrapper for convert_to_ome_zarr."""
    return _convert_to_ome_zarr(inputs=inputs, params=params, work_dir=work_dir)


def export_ome_tiff(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Thin wrapper for export_ome_tiff."""
    return _export_ome_tiff(inputs=inputs, params=params, work_dir=work_dir)
