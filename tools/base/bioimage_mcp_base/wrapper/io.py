"""I/O wrappers for format conversion.

These functions handle format bridging between different image formats
(OME-TIFF, OME-Zarr) with proper metadata handling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioimage_mcp_base.io import (
    convert_to_ome_zarr as _convert_to_ome_zarr,
)
from bioimage_mcp_base.io import (
    export_ome_tiff as _export_ome_tiff,
)


def convert_to_ome_zarr(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Convert an input image to OME-Zarr format."""
    result = _convert_to_ome_zarr(inputs=inputs, params=params, work_dir=work_dir)
    # Underlying function returns Path, wrap in standard output dict
    return {
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "format": "OME-Zarr",
                "path": str(result),
            }
        },
        "warnings": [],
        "log": "ok",
    }


def export_ome_tiff(
    *, inputs: dict[str, Any], params: dict[str, Any], work_dir: Path
) -> dict[str, Any]:
    """Export an input image to OME-TIFF format."""
    # Underlying function already returns dict with outputs
    return _export_ome_tiff(inputs=inputs, params=params, work_dir=work_dir)
