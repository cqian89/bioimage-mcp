from __future__ import annotations

import pytest
from bioimage_mcp.artifacts.export import infer_export_format


def test_infer_export_format_returns_png_for_2d_uint8():
    """T029: infer_export_format returns PNG for 2D uint8/uint16 with no rich metadata."""
    artifact = {
        "artifact_id": "test-png",
        "artifact_type": "BioImageRef",
        "metadata": {
            "ndim": 2,
            "dtype": "uint8",
        },
    }
    assert infer_export_format(artifact) == "PNG"


def test_infer_export_format_returns_ome_tiff_for_3d():
    """T030: infer_export_format returns OME-TIFF for 3D+ or rich metadata."""
    # 3D case
    artifact_3d = {
        "artifact_id": "test-3d",
        "artifact_type": "BioImageRef",
        "metadata": {
            "ndim": 3,
            "dtype": "float32",
        },
    }
    assert infer_export_format(artifact_3d) == "OME-TIFF"

    # 2D with metadata case
    artifact_meta = {
        "artifact_id": "test-meta",
        "artifact_type": "BioImageRef",
        "metadata": {
            "ndim": 2,
            "dtype": "uint8",
            "physical_pixel_sizes": [1.0, 1.0],
        },
    }
    assert infer_export_format(artifact_meta) == "OME-TIFF"


def test_infer_export_format_returns_ome_zarr_for_large():
    """T031: infer_export_format returns OME-Zarr for files > 4GB."""
    artifact = {
        "artifact_id": "test-large",
        "artifact_type": "BioImageRef",
        "metadata": {
            "ndim": 2,
            "dtype": "uint8",
            "size_bytes": 5 * 1024**3,  # 5GB
        },
    }
    assert infer_export_format(artifact) == "OME-Zarr"


def test_infer_export_format_returns_csv_for_table():
    """infer_export_format returns CSV for TableRef."""
    artifact = {
        "artifact_id": "test-table",
        "artifact_type": "TableRef",
        "metadata": {"row_count": 10},
    }
    assert infer_export_format(artifact) == "CSV"
